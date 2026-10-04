

import html
import json
from sqlalchemy import select
from ..artifacts.service import register_file
from ..api.schemas import ExperimentOut, ModelOut, ExplanationOut
from ..config import DISCLAIMER
from ..database import session_scope
from ..demo_readiness import verify_installed_model
from ..storage.entities import Artifact, Experiment, ModelRecord, ExplanationRecord, PipelineVersion, Run, ExperimentProtocolVersion, QuantumDiagnosticReport
from ..pipelines.service import pipeline_payload
from ..storage.repository import require
from ..storage.files import atomic_bytes, safe_path
from ..utils.serialization import utcnow
from .comparison import comparison


QUANTUM_MODEL_TYPES = {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}


def _quantum_report_evidence(
    experiment: Experiment,
    dataset: dict,
    models: list[dict],
    diagnostics: list[QuantumDiagnosticReport],
) -> dict | None:
    """Project persisted model/diagnostic records into the report's optional quantum section.

    This is deliberately read-only: it does not run a preview, simulator, resource
    advisor, or training workflow while producing a report.
    """
    latest_diagnostic: dict[str, QuantumDiagnosticReport] = {}
    for diagnostic in sorted(
        diagnostics,
        key=lambda item: (item.created_at or utcnow(), item.id),
    ):
        if diagnostic.status == "completed":
            latest_diagnostic[diagnostic.model_record_id] = diagnostic

    records = []
    for model in models:
        model_type = model.get("model_type")
        if model_type not in QUANTUM_MODEL_TYPES:
            continue

        details = model.get("details") if isinstance(model.get("details"), dict) else {}
        metadata = details.get("quantum") if isinstance(details.get("quantum"), dict) else {}
        configuration = details.get("configuration") if isinstance(details.get("configuration"), dict) else {}
        config_key = "hybrid" if model_type == "hybrid_pennylane_torch" else "quantum"
        model_config = metadata.get("configuration")
        if not isinstance(model_config, dict):
            model_config = configuration.get(config_key)
        if not isinstance(model_config, dict):
            model_config = {}

        circuit = metadata.get("circuit")
        if not isinstance(circuit, dict):
            circuit = {}
        pipeline = configuration.get("pipeline") if isinstance(configuration.get("pipeline"), dict) else {}
        preprocessing = details.get("preprocessing") if isinstance(details.get("preprocessing"), dict) else {}
        feature_dimension = preprocessing.get("final_representation_dimension")
        comparison_conditions = details.get("comparison_conditions")
        if not isinstance(comparison_conditions, dict):
            comparison_conditions = {}

        feature_encoding = {
            key: value
            for key, value in {
                "method": metadata.get("feature_map") or model_config.get("feature_map"),
                "represented_feature_dimension": feature_dimension,
                "pca_components": pipeline.get("pca_components"),
                "angle_scaling": pipeline.get("angle_scaling"),
            }.items()
            if value is not None
        }
        execution = {}
        for key in (
            "provider_id", "framework", "classical_framework", "backend",
            "execution_mode", "execution_kind", "real_hardware",
        ):
            value = metadata.get(key)
            if value is None and key in {"provider_id", "backend", "execution_mode"}:
                value = model_config.get(key)
            if value is not None:
                execution[key] = value
        resources = {
            key: circuit[key]
            for key in ("qubits", "logical_depth", "gate_counts", "parameter_count")
            if key in circuit and circuit[key] is not None
        }
        if metadata.get("sample_count") is not None:
            resources["sample_count"] = metadata["sample_count"]
        if model_config.get("shots") is not None:
            resources["configured_shots"] = model_config["shots"]

        diagnostic = latest_diagnostic.get(model.get("id"))
        diagnostic_payload = None
        if diagnostic is not None:
            diagnostic_payload = {
                "id": diagnostic.id,
                "status": diagnostic.status,
                "created_at": diagnostic.created_at.isoformat() if diagnostic.created_at else None,
                "configuration_fingerprint": diagnostic.configuration_fingerprint,
                "feature_encoding": diagnostic.feature_encoding,
                "circuit_structure": diagnostic.circuit_structure,
                "resource_profile": diagnostic.resource_profile,
                "optimizer_profile": diagnostic.optimizer_profile,
                "execution_profile": diagnostic.execution_profile,
                "warnings": diagnostic.warnings,
                "limitations": diagnostic.limitations,
                "provenance": diagnostic.provenance,
            }

        stored_limitations = details.get("limitations")
        limitations = (
            list(stored_limitations)
            if isinstance(stored_limitations, list)
            else [stored_limitations] if isinstance(stored_limitations, str) else []
        )
        if circuit.get("limitation"):
            limitations.append(circuit["limitation"])
        if diagnostic_payload:
            limitations.extend(diagnostic_payload.get("limitations") or [])
        state_evidence = metadata.get("state_evidence")
        if not isinstance(state_evidence, dict):
            state_evidence = {
                "status": "NOT_RECORDED",
                "reason": (
                    "No statevector, state probabilities, phase, Bloch state, or shot-count "
                    "result is persisted with this model record."
                ),
            }

        records.append({
            "model_id": model.get("id"),
            "model_type": model_type,
            "model_status": model.get("status"),
            "evidence_status": "AVAILABLE" if metadata else "NOT_AVAILABLE",
            "run_id": model.get("run_id"),
            "dataset_id": model.get("dataset_id") or experiment.dataset_id,
            "dataset_version_id": details.get("dataset_version_id")
            or comparison_conditions.get("dataset_version_id"),
            "dataset_hash": dataset.get("dataset_hash") or dataset.get("sha256"),
            "execution": execution,
            "configuration": model_config,
            "feature_encoding": feature_encoding,
            "circuit": circuit or None,
            "resource_profile": resources,
            "state_evidence": state_evidence,
            "diagnostics": diagnostic_payload,
            "limitations": list(dict.fromkeys(str(value) for value in limitations if value)),
        })

    if not records:
        return None
    return {
        "schema_version": "quantum_report_evidence_v1",
        "source": "persisted model records and linked quantum diagnostics",
        "experiment_id": experiment.id,
        "dataset_id": experiment.dataset_id,
        "dataset_name": dataset.get("name") or dataset.get("dataset_name"),
        "dataset_hash": dataset.get("dataset_hash") or dataset.get("sha256"),
        "models": records,
        "limitations": [
            "This section reports persisted configuration and execution evidence only.",
            "Transient visualization previews and unsaved simulator responses are not included.",
            "Simulation is not real quantum hardware execution and does not establish quantum advantage.",
        ],
    }


def report_data(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity)))
        explanations = list(session.scalars(select(ExplanationRecord).where(ExplanationRecord.model_id.in_([m.id for m in models])))) if models else []
        has_quantum_models = any(
            model.model_type in QUANTUM_MODEL_TYPES for model in models
        )
        quantum_diagnostics = list(session.scalars(
            select(QuantumDiagnosticReport)
            .where(QuantumDiagnosticReport.experiment_id == identity)
            .order_by(QuantumDiagnosticReport.created_at, QuantumDiagnosticReport.id)
        )) if has_quantum_models else []
        pipeline = session.get(PipelineVersion, experiment.pipeline_version_id) if experiment.pipeline_version_id else None
        pipeline_data = pipeline_payload(session, pipeline) if pipeline else {
            "status": "LEGACY_UNRESOLVED",
            "message": "No pipeline version was recorded for this experiment.",
        }
        protocol = session.get(ExperimentProtocolVersion, experiment.protocol_version_id) if experiment.protocol_version_id else None
        protocol_data = {
            "protocol_version_id": protocol.id,
            "protocol_id": protocol.protocol_id,
            "version": protocol.version_label,
            "status": protocol.status,
            "definition_fingerprint": protocol.definition_fingerprint,
            "summary": {
                "study_name": protocol.canonical_definition.get("study", {}).get("name") if protocol.canonical_definition else None,
                "task_type": protocol.canonical_definition.get("study", {}).get("task_type") if protocol.canonical_definition else None,
                "primary_metric": protocol.canonical_definition.get("evaluation", {}).get("primary_metric") if protocol.canonical_definition else None,
                "cv_folds": protocol.canonical_definition.get("split", {}).get("cv_folds") if protocol.canonical_definition else None,
                "seed_count": len(protocol.canonical_definition.get("randomness", {}).get("seeds", [])) if protocol.canonical_definition and protocol.canonical_definition.get("randomness") else 0,
            },
            "canonical_definition": protocol.canonical_definition,
        } if protocol else {
            "status": "LEGACY_UNSPECIFIED",
            "message": "No experiment protocol version was declared or attached to this experiment.",
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
    report = {"title": "EntangleX Q-Health Research Experiment Report", "generated_at": utcnow().isoformat(),
        "experiment_kind": experiment_kind, "experiment_label": "PRECOMPUTED VERIFIED DEMO EXPERIMENT" if experiment_kind == "precomputed_verified_demo" else "LIVE RESEARCH EXPERIMENT",
        "disclaimer": DISCLAIMER, "experiment": ExperimentOut.model_validate(experiment).model_dump(mode="json"),
        "dataset": experiment.summary.get("dataset_provenance", {}), "preprocessing": experiment.config["pipeline"],
        "pipeline_version": pipeline_data,
        "protocol": protocol_data,
        "audit_summary": audit_summary,
        "models": [{**ModelOut.model_validate(m).model_dump(mode="json"), "display_name": "PennyLane + PyTorch Hybrid" if m.model_type == "hybrid_pennylane_torch" else m.model_type} for m in models],
        "interpretation": [ExplanationOut.model_validate(e).model_dump(mode="json") for e in explanations],
        "comparison": comparison(identity),
        "scientific_boundary": "Model probabilities, test metrics, and simulation results do not establish diagnosis, clinical validity, regulatory approval, or quantum advantage. Uncomputed measurements remain absent, not zero."}
    quantum_evidence = _quantum_report_evidence(
        experiment,
        report["dataset"] if isinstance(report["dataset"], dict) else {},
        report["models"],
        quantum_diagnostics,
    )
    # Keep the historical report payload unchanged for experiments without
    # persisted quantum model records.
    if quantum_evidence is not None:
        report["quantum_evidence"] = quantum_evidence
    return report

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
        "<h2>Experiment protocol</h2>" + pre(data["protocol"]),
        "<h2>Audit timeline</h2>" + pre(data["audit_summary"]),
        "<h2>Shared split and reproducibility</h2>" + pre(data["experiment"]["summary"]),
        "<h2>Model configuration</h2>" + pre(data["experiment"]["config"])]
    if data.get("quantum_evidence"):
        sections.append("<h2>Quantum computation evidence</h2>" + pre(data["quantum_evidence"]))
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
