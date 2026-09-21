import html
import json
from sqlalchemy import select
from ..api.schemas import ExperimentOut, ModelOut, ExplanationOut
from ..config import DISCLAIMER
from ..database import session_scope
from ..storage.entities import Experiment, ModelRecord, ExplanationRecord
from ..storage.repository import require
from ..storage.files import atomic_bytes, safe_path
from ..utils.serialization import utcnow
from .comparison import comparison

def report_data(identity: str) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, identity)
        models = list(session.scalars(select(ModelRecord).where(ModelRecord.experiment_id == identity)))
        explanations = list(session.scalars(select(ExplanationRecord).where(ExplanationRecord.model_id.in_([m.id for m in models])))) if models else []
    return {"title": "EntangleX Q-Health Research Experiment Report", "generated_at": utcnow().isoformat(),
        "disclaimer": DISCLAIMER, "experiment": ExperimentOut.model_validate(experiment).model_dump(mode="json"),
        "dataset": experiment.summary.get("dataset_provenance", {}), "preprocessing": experiment.config["pipeline"],
        "models": [ModelOut.model_validate(m).model_dump(mode="json") for m in models],
        "interpretation": [ExplanationOut.model_validate(e).model_dump(mode="json") for e in explanations],
        "comparison": comparison(identity),
        "scientific_boundary": "Model probabilities, test metrics, and simulation results do not establish diagnosis, clinical validity, regulatory approval, or quantum advantage. Uncomputed measurements remain absent, not zero."}

def html_report(identity: str) -> str:
    data = report_data(identity)
    def escaped(value):
        return html.escape(str(value), quote=True)
    def pre(value):
        return "<pre>" + escaped(json.dumps(value, indent=2, ensure_ascii=False)) + "</pre>"
    sections = ["<h1>EntangleX Q-Health</h1><p>Research experiment report</p>", "<aside>" + escaped(DISCLAIMER) + "</aside>",
        "<h2>Dataset and provenance</h2>" + pre(data["dataset"]),
        "<h2>Preprocessing and feature engineering</h2>" + pre(data["preprocessing"]),
        "<h2>Shared split and reproducibility</h2>" + pre(data["experiment"]["summary"]),
        "<h2>Model configuration</h2>" + pre(data["experiment"]["config"])]
    for model in data["models"]:
        sections.append("<h2>Model: " + escaped(model["model_type"]) + "</h2><p>Model ID: " + escaped(model["id"]) + "; status: " + escaped(model["status"]) + "</p>")
        metrics = model["metrics"]
        sections.append("<h3>Evaluation: held-out test</h3>" + pre(metrics.get("test", "Not computed")))
        sections.append("<h3>Generalization: training and validation</h3>" + pre({"training_resubstitution": metrics.get("training"), "cross_validation": metrics.get("validation")}))
        sections.append("<h3>Computational measurements</h3>" + pre({"timing": metrics.get("timing"), "quantum": model["details"].get("quantum")}))
        sections.append("<h3>Probability calibration diagnostics</h3>" + pre(metrics.get("calibration", "Not computed")))
        sections.append("<h3>Limitations and warnings</h3>" + pre({"limitations": model["details"].get("limitations", []), "warnings": model["details"].get("warnings", []), "error": model["details"].get("error")}))
    sections.append("<h2>Interpretation: model feature influence / quantum perturbation</h2>" + pre(data["interpretation"] or "Not computed; request an explanation for a trained model."))
    sections.append("<h2>Scientific conclusion from measured results</h2>" + pre({"conclusion": data["comparison"]["conclusion"], "pairs": data["comparison"]["pairs"]}))
    sections.append("<h2>Clinical validation boundary</h2><p>" + escaped(data["scientific_boundary"]) + "</p><footer>Report generated " + escaped(data["generated_at"]) + ". No raw records are exported.</footer>")
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><title>EntangleX Q-Health research report</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:20px;color:#183442}h1,h2{color:#126675}aside{border-left:5px solid #378593;padding:18px;background:#eff7f7}pre{font:12px/1.5 monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7fa;padding:18px}h2{margin-top:36px}@media print{body{margin:0;max-width:none}pre{font-size:10px}h2,h3{break-after:avoid}}</style><body>' + "".join(sections) + "</body></html>"
    atomic_bytes(safe_path("experiments", identity, ".html"), document.encode("utf-8"))
    return document
