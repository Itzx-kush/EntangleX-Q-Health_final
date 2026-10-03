import copy
from typing import Any
from sqlalchemy import select
from backend.app.api.schemas import TrainingConfig
from backend.app.database import session_scope
from backend.app.jobs.manager import manager
from backend.app.storage.entities import AblationStudy, Experiment, Run
from backend.app.utils.errors import AppError
from backend.app.utils.serialization import fingerprint, utcnow
from .schemas import AblationComponentConfig, AblationPreflightResponse

SUPPORTED_MODELS={"logistic_regression","svm","random_forest","vqc","qsvc","qnn","hybrid_pennylane_torch"}

def get_base_experiment(session,experiment_id:str)->Experiment:
    experiment=session.scalar(select(Experiment).where(Experiment.id==experiment_id))
    if not experiment: raise AppError("not_found","Base experiment not found.",404)
    if experiment.status!="completed": raise AppError("invalid_state","Base experiment must be completed to use as an ablation baseline.",400)
    return experiment

def extract_base_run(session,experiment_id:str)->Run|None:
    return session.scalar(select(Run).where(Run.experiment_id==experiment_id).order_by(Run.created_at.desc()).limit(1))

def _set_value(config:dict[str,Any],path:list[str],value:Any)->None:
    target=config
    for key in path[:-1]: target=target.setdefault(key,{})
    target[path[-1]]=value

def apply_ablation(config:dict[str,Any],change:AblationComponentConfig)->tuple[dict[str,Any],list[str]]:
    new_config=copy.deepcopy(config); c,o,v=change.component,change.operator,change.ablation_value; changed=[]
    if c=="preprocessing.scaler":
        if o in {"REMOVE","DISABLE"}: v="none"
        elif o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Scaler ablation requires a supported operator.",422)
        _set_value(new_config,["pipeline","scaler"],v); changed.append(f"pipeline.scaler={v}")
    elif c=="preprocessing.imputer":
        if o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Imputation ablation requires SUBSTITUTE.",422)
        _set_value(new_config,["pipeline","imputer"],v); changed.append(f"pipeline.imputer={v}")
    elif c=="preprocessing.outlier_strategy":
        if o in {"REMOVE","DISABLE"}: v="none"
        elif o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Outlier ablation requires a supported operator.",422)
        _set_value(new_config,["pipeline","outlier_strategy"],v); changed.append(f"pipeline.outlier_strategy={v}")
    elif c=="preprocessing.pca":
        if o in {"REMOVE","DISABLE"}: v=None
        elif o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","PCA ablation requires a supported operator.",422)
        _set_value(new_config,["pipeline","pca_components"],v); changed.append(f"pipeline.pca_components={v}")
    elif c=="preprocessing.feature_selection":
        if o in {"REMOVE","DISABLE"}: v="none"
        elif o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Feature-selection ablation requires a supported operator.",422)
        _set_value(new_config,["pipeline","selection"],v); changed.append(f"pipeline.selection={v}")
    elif c=="features.subset":
        if o!="REMOVE": raise AppError("invalid_request","Feature-subset ablation supports REMOVE only.",422)
        feature=str(v or "").strip(); features=new_config.get("features")
        if not isinstance(features,list) or feature not in features: raise AppError("invalid_request","The requested feature is not present in the explicit baseline feature list.",422)
        if len(features)<=1: raise AppError("invalid_request","Feature-subset ablation cannot remove the only selected feature.",422)
        features.remove(feature); changed.append(f"features.removed={feature}")
    elif c=="model.family":
        if o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Model-family ablation requires SUBSTITUTE.",422)
        model=str(v or "").strip()
        if model not in SUPPORTED_MODELS: raise AppError("invalid_request","Unsupported ablation model family.",422)
        _set_value(new_config,["models"],[model]); changed.append(f"models={model}")
    elif c=="calibration.policy":
        if o in {"REMOVE","DISABLE"}: v="none"
        elif o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Calibration-policy ablation requires a supported operator.",422)
        _set_value(new_config,["calibration"],v); changed.append(f"calibration={v}")
    elif c=="threshold.policy":
        if o not in {"SUBSTITUTE","REPLACE_WITH_BASELINE"}: raise AppError("invalid_request","Threshold-policy ablation requires SUBSTITUTE.",422)
        _set_value(new_config,["threshold_strategy"],v); changed.append(f"threshold_strategy={v}")
    else: raise AppError("invalid_request",f"Unsupported ablation component: {c}",422)
    return new_config,changed

def derive_held_constants(baseline:dict[str,Any],ablated:dict[str,Any])->list[str]:
    tracked=["dataset_id","dataset_version_id","condition_task_id","seed","test_size","cv_folds","max_samples","duplicate_policy","probability_threshold","sampling_unit","group_column","parameters"]
    return [f"{k} (unchanged)" for k in tracked if baseline.get(k)==ablated.get(k)]

def preflight_ablation_study(session,experiment:Experiment,request:Any)->AblationPreflightResponse:
    if request.max_total_runs<len(request.ablation_configs):
        return AblationPreflightResponse(feasible=False,base_experiment_info={"id":experiment.id,"name":experiment.name},baseline_configuration=experiment.config,ablation_configurations=[],configuration_diff={},changed_components=[],held_constant=[],blockers=[f"Requested {len(request.ablation_configs)} ablations exceed max_total_runs={request.max_total_runs}."],warnings=[],limitations=[],estimated_run_count=len(request.ablation_configs))
    configs=[]; changed=[]; blockers=[]
    for change in request.ablation_configs:
        try:
            candidate,delta=apply_ablation(experiment.config,change); validated=TrainingConfig.model_validate(candidate)
        except AppError as exc: blockers.append(exc.message); continue
        except Exception as exc: blockers.append(f"Invalid TrainingConfig for {change.component}: {exc}"); continue
        configs.append(validated.model_dump(mode="json")); changed.extend(delta)
    feasible=not blockers and len(configs)==len(request.ablation_configs); first=configs[0] if configs else {}
    return AblationPreflightResponse(feasible=feasible,base_experiment_info={"id":experiment.id,"name":experiment.name},baseline_configuration=experiment.config,ablation_configurations=configs,configuration_diff={"baseline":experiment.config,"first_ablation":first},changed_components=list(dict.fromkeys(changed)),held_constant=derive_held_constants(experiment.config,first) if first else [],blockers=blockers,warnings=[],limitations=["Ablation runs are independent research experiments and do not modify the baseline model."],estimated_run_count=len(configs))

def enqueue_ablation_studies(experiment:Experiment,request:Any,preflight:AblationPreflightResponse)->list[AblationStudy]:
    studies=[]
    with session_scope() as session:
        base_run=extract_base_run(session,experiment.id); base_run_id=base_run.id if base_run else None
    for change,new_config in zip(request.ablation_configs,preflight.ablation_configurations):
        operation_key=fingerprint({"ablation_version":"1","base_experiment_id":experiment.id,"component":change.component,"operator":change.operator,"value":change.ablation_value,"configuration":new_config})
        with session_scope() as session:
            existing=session.scalar(select(AblationStudy).where(AblationStudy.operation_key==operation_key))
            if existing: studies.append(existing); continue
            study=AblationStudy(base_experiment_id=experiment.id,base_run_id=base_run_id,dataset_id=experiment.dataset_id,dataset_version_id=new_config.get("dataset_version_id"),condition_task_id=new_config.get("condition_task_id"),status="created",operation_key=operation_key,baseline_configuration=experiment.config,ablation_configuration=new_config,changed_components=" / ".join([change.component,change.operator]),held_constant=derive_held_constants(experiment.config,new_config),configuration_diff={"component":change.component,"operator":change.operator,"value":change.ablation_value},configuration_fingerprint=fingerprint(new_config),comparison_results={},limitations=["Metrics remain separate until the ablation execution completes."],warnings=[])
            session.add(study); session.flush(); study_id=study.id
        try:
            _job,ablation_experiment=manager.enqueue(TrainingConfig.model_validate(new_config),parent_id=experiment.id,idempotency_key=f"ablation:{operation_key}")
        except Exception as exc:
            with session_scope() as session:
                study=session.get(AblationStudy,study_id)
                if study: study.status="failed"; study.failure={"type":type(exc).__name__,"message":str(exc)}; study.completed_at=utcnow(); study.updated_at=utcnow()
            raise
        with session_scope() as session:
            study=session.get(AblationStudy,study_id)
            if study: study.ablation_experiment_id=ablation_experiment.id; study.status="queued"; study.updated_at=utcnow(); studies.append(study)
    return studies
