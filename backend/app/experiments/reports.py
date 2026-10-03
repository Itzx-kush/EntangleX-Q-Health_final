

import html
import json
from sqlalchemy import select
from ..artifacts.service import register_file
from ..api.schemas import ExperimentOut, ModelOut, ExplanationOut
from ..config import DISCLAIMER
from ..database import session_scope
from ..demo_readiness import verify_installed_model
from ..storage.entities import Artifact, Experiment, ModelRecord, ExplanationRecord, PipelineVersion, Run, ExperimentProtocolVersion
from ..pipelines.service import pipeline_payload
from ..storage.repository import require
from ..storage.files import atomic_bytes, safe_path
from ..utils.serialization import utcnow
from .comparison import comparison

def report_data(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity)))
        explanations = list(session.scalars(select(ExplanationRecord).where(ExplanationRecord.model_id.in_([m.id for m in models])))) if models else []
        pipeline = session.get(PipelineVersion, experiment.pipeline_version_id) if experiment.pipeline_version_id else None
        pipeline_data = pipeline_payload(session, pipeline) if pipeline else {
            "status": "LEGACY_UNRESOLVED",
            "message": "No pipeline version was recorded for this experiment.",
        }
        protocol = session.get(ExperimentProtocolVersion, experiment.protocol_version_id) if experiment.protocol_version_id else None
        protocol_data = {
            "protocol_version_id": protocol.id,
            "protocol_id": protocol.protocol_id,
from ..storage.entities import Artifact, Experiment, ModelRecord, ExplanationRecord, PipelineVersion, Run
from ..pipelines.service import pipeline_payload
from ..storage.repository import require
from ..storage.files import atomic_bytes, safe_path
from ..utils.serialization import utcnow
from .comparison import comparison

def report_data(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity)))
        explanations = list(session.scalars(select(ExplanationRecord).where(ExplanationRecord.model_id.in_([m.id for m in models])))) if models else []
        pipeline = session.get(PipelineVersion, experiment.pipeline_version_id) if experiment.pipeline_version_id else None
        pipeline_data = pipeline_payload(session, pipeline) if pipeline else {
            "status": "LEGACY_UNRESOLVED",
            "message": "No pipeline version was recorded for this experiment.",
        }
        from ..audit.service import get_experiment_timeline
        timeline = get_experiment_timeline(session, identity, limit=10)
        audit_summary = {
            "total_events": timeline.total_events,
            "integrity_status": timeline.integrity_status,
            "recent_events": [e.model_dump(mode="json") for e in timeline.events[:5]],
            "legacy_disclaimer": timeline.legacy_disclaimer,
        }
    experiment_kind = experiment.summary.get("experiment_kind", "live_experiment")
    for model in models:
        verify_installed_model(model)
    return {"title": "EntangleX Q-Health Research Experiment Report", "generated_at": utcnow().isoformat(),
        "experiment_kind": experiment_kind, "experiment_label": "PRECOMPUTED VERIFIED DEMO EXPERIMENT" if experiment_kind == "precomputed_verified_demo" else "LIVE RESEARCH EXPERIMENT",
        "disclaimer": DISCLAIMER, "experiment": ExperimentOut.model_validate(experiment).model_dump(mode="json"),
        "dataset": experiment.summary.get("dataset_provenance", {}), "preprocessing": experiment.config["pipeline"],
        "pipeline_version": pipeline_data,
        "audit_summary": audit_summary,
        "models": [{**ModelOut.model_validate(m).model_dump(mode="json"), "display_name": "PennyLane + PyTorch Hybrid" if m.model_type == "hybrid_pennylane_torch" else m.model_type} for m in models],
        "interpretation": [ExplanationOut.model_validate(e).model_dump(mode="json") for e in explanations],
        "comparison": comparison(identity),
        "scientific_boundary": "Model probabilities, test metrics, and simulation results do not establish diagnosis, clinical validity, regulatory approval, or quantum advantage. Uncomputed measurements remain absent, not zero."}

def html_report(identity: str) -> str:
    data = report_data(identity)
    def escaped(value):
        return html.escape(str(value), quote=True)
    def pre(value):
        return "<pre>" + escaped(json.dumps(value, indent=2, ensure_ascii=False)) + "</pre>"
    sections = ["<h1>EntangleX Q-Health</h1><p>" + escaped(data["experiment_label"]) + "</p>", "<aside>" + escaped(DISCLAIMER) + "</aside>",
        "<h2>Dataset and provenance</h2>" + pre(data["dataset"]),
        "<h2>Preprocessing and feature engineering</h2>" + pre(data["preprocessing"]),
        "<h2>Pipeline version</h2>" + pre(data["pipeline_version"]),
        "<h2>Shared split and reproducibility</h2>" + pre(data["experiment"]["summary"]),
        "<h2>Model configuration</h2>" + pre(data["experiment"]["config"]),
        "<h2>Model configuration</h2>" + pre(data["experiment"]["config"])]
    for model in data["models"]:
        sections.append("<h2>Model: " + escaped(model.get("display_name", model["model_type"])) + "</h2><p>Model ID: " + escaped(model["id"]) + "; status: " + escaped(model["status"]) + "</p>")
        metrics = model["metrics"]
        sections.append("<h3>Evaluation: held-out test</h3>" + pre(metrics.get("test", "Not computed")))
        sections.append("<h3>Generalization: training and validation</h3>" + pre({"training_resubstitution": metrics.get("training"), "cross_validation": metrics.get("validation")}))
        sections.append("<h3>Computational measurements and quantum training metadata</h3>" + pre({"timing": metrics.get("timing"), "quantum": model["details"].get("quantum"), "optimization_objective": model["details"].get("optimization_objective"), "probability_status": model["details"].get("probability_status")}))
        sections.append("<h3>Research operating point</h3>" + pre(metrics.get("operating_point") or model["details"].get("operating_point") or {"threshold_source": "legacy_fixed_configuration"}))
        sections.append("<h3>Probability calibration diagnostics</h3>" + pre(metrics.get("calibration", "Not computed")))
        sections.append("<h3>Limitations and warnings</h3>" + pre({"limitations": model["details"].get("limitations", []), "warnings": model["details"].get("warnings", []), "error": model["details"].get("error")}))
    sections.append("<h2>Interpretation: model feature influence / quantum perturbation</h2>" + pre(data["interpretation"] or "Not computed; request an explanation for a trained model."))
    controlled = [pair for pair in data["comparison"]["pairs"] if pair.get("benchmark_type") == "fair_controlled_diabetes_benchmark"]
    sections.append("<h2>FAIR CONTROLLED BENCHMARK</h2>" + pre({
        "dataset_and_provenance": data["dataset"],
        "shared_data_budget_split_preprocessing_and_representation": [
            {"fairness": pair.get("fairness"), "common_representation": pair.get("common_representation")} for pair in controlled
        ],
        "threshold_protocol": [pair.get("operating_points") for pair in controlled],
        "classical_and_hybrid_holdout_results": [pair.get("holdout_results") for pair in controlled],
        "metric_and_timing_deltas": [{"metrics": pair.get("metric_deltas"), "timing": pair.get("computational_cost")} for pair in controlled],
        "quantum_simulator_metadata": [pair.get("quantum_resources") for pair in controlled],
        "robustness_evidence": [pair.get("robustness") for pair in controlled],
        "scientific_limitations": [pair.get("limitations") for pair in controlled],
    } if controlled else "No Random Forest / PennyLane + PyTorch hybrid benchmark pair is available."))
    sections.append("<h2>All classical and quantum model evidence</h2>" + pre({"conclusion": data["comparison"]["conclusion"], "pairs": data["comparison"]["pairs"]}))
    sections.append("<h2>Robustness and degradation evidence</h2>" + pre([
        {"quantum_model": pair["quantum_model"], "classical_model": pair["classical_model"], "robustness": pair.get("robustness", {"status": "not_evaluated"})}
        for pair in data["comparison"]["pairs"]
    ] or "Not evaluated; run a bounded Robustness Lab condition to add evidence."))
    sections.append("<h2>Clinical validation boundary</h2><p>" + escaped(data["scientific_boundary"]) + "</p><footer>Report generated " + escaped(data["generated_at"]) + ". No raw records are exported.</footer>")
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><title>EntangleX Q-Health research report</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:20px;color:#183442}h1,h2{color:#126675}aside{border-left:5px solid #378593;padding:18px;background:#eff7f7}pre{font:12px/1.5 monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fa;padding:18px}h2{margin-top:36px}@media print{body{margin:0;max-width:none}pre{font-size:10px}h2,h3{break-after:avoid}}</style><body>' + "".join(sections) + "</body></html>"
    path = safe_path("experiments", identity, ".html")
    atomic_bytes(path, document.encode("utf-8"))
    with session_scope() as session:
        runs = list(session.scalars(select(Run).where(Run.experiment_id == identity)))
        # The existing report is experiment-wide. Associate it with a Run only
        # when that lineage is unambiguous; never fabricate historical lineage.
        run_id = runs[0].id if len(runs) == 1 else None
        register_file(
            session,
            experiment_id=identity,
            run_id=run_id,
            model_id=None,
            artifact_type="report",
            name="Experiment HTML report",
            description="Existing experiment-wide research report.",
            path=path,
            storage_reference=f"experiments/{identity}.html",
            content_type="text/html",
            operation_key=f"experiment-report:{identity}:html",
            immutable=False,
            details={"scope": "experiment", "format": "html"},
        )
    return document
