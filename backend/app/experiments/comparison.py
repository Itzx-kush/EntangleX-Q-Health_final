from sqlalchemy import select
from ..database import session_scope
from ..storage.entities import Experiment, ModelRecord
from ..storage.repository import require
from ..api.schemas import ModelOut

COMPARE_METRICS = ["sensitivity", "specificity", "roc_auc", "f1", "accuracy", "precision", "recall"]

def comparison(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity).order_by(ModelRecord.created_at)))
    ready = [m for m in models if m.status == "ready"]
    classical = [m for m in ready if m.model_type not in {"vqc", "qsvc", "qnn"}]
    quantum = [m for m in ready if m.model_type in {"vqc", "qsvc", "qnn"}]
    pairs = []
    for q in quantum:
        for c in classical:
            delta = {key: q.metrics["test"][key] - c.metrics["test"][key] if q.metrics["test"][key] is not None and c.metrics["test"][key] is not None else None for key in COMPARE_METRICS}
            direction = lambda value: "higher" if value > 0 else "lower" if value < 0 else "equal"
            sensitivity, specificity = delta["sensitivity"], delta["specificity"]
            conclusion = f"On this shared held-out benchmark, {q.model_type} had {direction(sensitivity)} sensitivity and {direction(specificity)} specificity than {c.model_type}." if sensitivity is not None and specificity is not None else "Some class-specific metrics are undefined; no comparative claim is made."
            pairs.append({"quantum_model": q.id, "classical_model": c.id, "quantum_type": q.model_type, "classical_type": c.model_type, "test_metric_delta_quantum_minus_classical": delta,
                "final_training_seconds_delta": q.metrics["timing"]["final_training_seconds"] - c.metrics["timing"]["final_training_seconds"],
                "conclusion": conclusion + " This descriptive result does not establish statistical significance, clinical utility, or general quantum advantage."})
    return {"experiment_id": identity, "comparison_fingerprint": experiment.summary.get("comparison_fingerprint"), "split": experiment.summary.get("split"),
            "models": [ModelOut.model_validate(m).model_dump(mode="json") for m in models], "pairs": pairs,
            "conclusion": "No completed classical-quantum pair is available." if not pairs else "All completed pairs are shown, including unfavorable quantum results. Review sensitivity, specificity, ROC-AUC, F1, validation dispersion and measured cost together.",
            "limitations": ["Comparison is restricted to a single experiment to enforce shared data, target, selected features, preprocessing and splits.", "A benchmark result is not clinical validation or a proof of quantum advantage."]}
