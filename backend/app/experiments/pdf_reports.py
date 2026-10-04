"""Deterministic, read-only PDF rendering of canonical experiment report data."""
from __future__ import annotations

from io import BytesIO
from typing import Any, Iterable

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, PageBreak, Paragraph,
    Spacer, Table, TableStyle,
)
from reportlab.pdfgen.canvas import Canvas

MISSING = "Not recorded"
FAMILIES = {
    "logistic_regression": "Classical", "svm": "Classical", "random_forest": "Classical",
    "vqc": "Quantum", "qsvc": "Quantum", "qnn": "Quantum", "hybrid_pennylane_torch": "Hybrid",
}
METRICS = ("accuracy", "precision", "recall", "specificity", "f1", "roc_auc")


def _safe(value: Any, fallback: str = MISSING) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return fallback
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_safe(v) for v in value) or fallback
    if isinstance(value, dict):
        return "; ".join(f"{str(k).replace('_', ' ').title()}: {_safe(v)}" for k, v in value.items())
    return str(value)


def _get(value: Any, *path: str, default: Any = None) -> Any:
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value


def _metric(value: Any) -> str:
    return MISSING if not isinstance(value, (int, float)) else f"{value:.4f}"


def _model_name(model: dict) -> str:
    return _safe(model.get("display_name") or model.get("model_type"))


def _family(model: dict) -> str:
    return FAMILIES.get(model.get("model_type"), "Other")


def _leading(models: list[dict]) -> tuple[dict | None, str | None, float | None]:
    for metric in ("roc_auc", "f1", "accuracy", "recall", "specificity", "precision"):
        ranked = [(m, _get(m, "metrics", "test", metric)) for m in models]
        ranked = [(m, v) for m, v in ranked if isinstance(v, (int, float))]
        if ranked:
            model, value = max(ranked, key=lambda item: item[1])
            return model, metric, value
    return None, None, None


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=24, leading=29, textColor=colors.HexColor("#0C6070"), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="Kicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#268393"), alignment=TA_CENTER, spaceAfter=7))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#0C6070"), spaceBefore=13, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#244C57"), spaceBefore=9, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#243A40"), spaceAfter=5))
    styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.3, leading=11.5, textColor=colors.HexColor("#3E5359"), backColor=colors.HexColor("#EDF7F8"), borderColor=colors.HexColor("#8EC6CF"), borderWidth=.5, borderPadding=7, spaceBefore=5, spaceAfter=8))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9.2, textColor=colors.HexColor("#20363C"), splitLongWords=True))
    styles.add(ParagraphStyle(name="CellHead", parent=styles["Cell"], fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_LEFT))
    return styles


def _p(value: Any, style) -> Paragraph:
    from xml.sax.saxutils import escape
    text = escape(_safe(value)).replace("\n", "<br/>")
    return Paragraph(text, style)


def _table(rows: Iterable[Iterable[Any]], styles, widths=None, header=True) -> Table:
    cooked = [[_p(cell, styles["CellHead"] if header and r == 0 else styles["Cell"]) for cell in row] for r, row in enumerate(rows)]
    table = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT", splitByRow=1)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#B8CED3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0C6070"))]
        if len(cooked) > 1:
            commands += [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8F9")])]
    table.setStyle(TableStyle(commands))
    return table


def _kv(rows: Iterable[tuple[str, Any]], styles) -> Table:
    return _table([["Field", "Recorded value"], *[(label, _safe(value)) for label, value in rows]], styles, [50 * mm, 130 * mm])


def _metric_chart(models: list[dict], styles):
    rows = []
    for model in models:
        value = _get(model, "metrics", "test", "roc_auc")
        if isinstance(value, (int, float)):
            rows.append((_model_name(model), max(0.0, min(1.0, float(value)))))
    if not rows:
        return _p("ROC-AUC visual summary is not available because no persisted ROC-AUC values were recorded.", styles["BodySmall"])
    height = 20 + 18 * len(rows)
    drawing = Drawing(480, height)
    for index, (name, value) in enumerate(rows):
        y = height - 16 - index * 18
        drawing.add(String(0, y, name[:36], fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#243A40")))
        drawing.add(Rect(170, y - 2, 260, 8, fillColor=colors.HexColor("#DFECEF"), strokeColor=None))
        drawing.add(Rect(170, y - 2, 260 * value, 8, fillColor=colors.HexColor("#2A8797"), strokeColor=None))
        drawing.add(String(438, y, f"{value:.4f}", fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#243A40")))
    return drawing


def _quantum_evidence_story(evidence: dict, styles) -> list[Any]:
    """Render only persisted quantum model/diagnostic values into the report."""
    story: list[Any] = [_p("Quantum computation evidence", styles["Subsection"])]
    models = evidence.get("models") or []
    for model in models:
        execution = model.get("execution") or {}
        configuration = model.get("configuration") or {}
        feature_encoding = model.get("feature_encoding") or {}
        circuit = model.get("circuit") or {}
        resources = model.get("resource_profile") or {}
        diagnostic = model.get("diagnostics") or {}
        dataset_hash = model.get("dataset_hash") or evidence.get("dataset_hash")
        dataset_name = evidence.get("dataset_name")

        story.append(_p(
            f"{_model_name({'display_name': model.get('model_type')})} - model {model.get('model_id')}",
            styles["BodySmall"],
        ))
        rows = [
            ("Experiment ID", evidence.get("experiment_id")),
            ("Dataset", dataset_name),
            ("Dataset ID", model.get("dataset_id") or evidence.get("dataset_id")),
            ("Dataset hash", dataset_hash),
            ("Model record ID", model.get("model_id")),
            ("Run ID", model.get("run_id")),
            ("Quantum evidence status", model.get("evidence_status")),
            ("Execution provider", execution.get("provider_id")),
            ("Quantum framework", execution.get("framework")),
            ("Backend", execution.get("backend")),
            ("Execution mode", execution.get("execution_mode")),
            ("Execution kind", execution.get("execution_kind")),
            ("Hardware execution recorded", execution.get("real_hardware")),
            ("Feature map / encoding", feature_encoding.get("method")),
            ("Represented feature dimension", feature_encoding.get("represented_feature_dimension")),
            ("PCA components", feature_encoding.get("pca_components")),
            ("Angle scaling", feature_encoding.get("angle_scaling")),
            ("Logical qubits", circuit.get("qubits")),
            ("Circuit depth", circuit.get("logical_depth")),
            ("Parameter count", circuit.get("parameter_count")),
            ("Gate counts", circuit.get("gate_counts")),
            ("Sample count", resources.get("sample_count")),
            ("Configured shots", resources.get("configured_shots")),
            ("Optimizer", configuration.get("optimizer")),
            ("Configured maximum iterations", configuration.get("maxiter") or configuration.get("epochs")),
        ]
        rows = [(label, value) for label, value in rows if value is not None and value != "" and value != {}]
        story.append(_kv(rows, styles))

        gates = circuit.get("gates")
        if isinstance(gates, list) and gates:
            max_rows = 80
            gate_rows = [["Order", "Gate", "Qubits", "Parameters"]]
            for index, gate in enumerate(gates[:max_rows], start=1):
                if not isinstance(gate, dict):
                    continue
                gate_rows.append([
                    index,
                    gate.get("name"),
                    gate.get("qubits"),
                    gate.get("parameters"),
                ])
            if len(gate_rows) > 1:
                story += [_p("Persisted ordered circuit operations", styles["BodySmall"]),
                          _table(gate_rows, styles, [18*mm, 42*mm, 45*mm, 65*mm])]
            if len(gates) > max_rows:
                story.append(_p(
                    f"Showing the first {max_rows} of {len(gates)} persisted circuit operations.",
                    styles["BodySmall"],
                ))
        if circuit.get("text"):
            circuit_text = str(circuit["text"]).replace("→", "->").replace("←", "<-")
            story += [_p("Persisted circuit description", styles["BodySmall"]),
                      _p(circuit_text, styles["BodySmall"]), Spacer(1, 2 * mm)]
        if circuit.get("limitation"):
            story.append(_p(circuit["limitation"], styles["Note"]))

        state = model.get("state_evidence") or {}
        story.append(_kv([
            ("State / measurement evidence status", state.get("status")),
            ("State / measurement note", state.get("reason")),
        ], styles))

        if diagnostic:
            diagnostic_rows = [
                ("Diagnostic report ID", diagnostic.get("id")),
                ("Diagnostic status", diagnostic.get("status")),
                ("Diagnostic recorded", diagnostic.get("created_at")),
                ("Configuration fingerprint", diagnostic.get("configuration_fingerprint")),
                ("Persisted diagnostic resource profile", diagnostic.get("resource_profile")),
                ("Diagnostic warnings", diagnostic.get("warnings")),
                ("Diagnostic limitations", diagnostic.get("limitations")),
            ]
            diagnostic_rows = [(label, value) for label, value in diagnostic_rows if value is not None and value != "" and value != [] and value != {}]
            story += [_p("Persisted quantum diagnostics", styles["BodySmall"]), _kv(diagnostic_rows, styles)]

        limitations = model.get("limitations") or []
        if limitations:
            story.append(_p("Model limitations: " + "; ".join(str(value) for value in limitations), styles["Note"]))

    if evidence.get("limitations"):
        story.append(_p("; ".join(str(value) for value in evidence["limitations"]), styles["Note"]))
    story.append(_p(
        "This section summarizes persisted model and diagnostic records. It does not represent an unsaved preview, infer missing simulator state, claim hardware execution, or establish quantum advantage or clinical validity.",
        styles["Note"],
    ))
    return story


class _ReportDoc(BaseDocTemplate):
    def __init__(self, buffer: BytesIO, experiment_id: str, generated_at: str):
        super().__init__(buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=17 * mm, bottomMargin=18 * mm, title="EntangleX Q-Health Research Experiment Report", author="EntangleX Q-Health")
        self.experiment_id = experiment_id
        self.generated_at = generated_at
        self.addPageTemplates(PageTemplate(id="report", frames=[Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")], onPage=self._footer))

    def _footer(self, canvas: Canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B8CED3")); canvas.line(self.leftMargin, 12 * mm, A4[0] - self.rightMargin, 12 * mm)
        canvas.setFont("Helvetica", 6.5); canvas.setFillColor(colors.HexColor("#4F666C"))
        canvas.drawString(self.leftMargin, 9 * mm, "EntangleX Q-Health")
        canvas.drawCentredString(A4[0] / 2, 9 * mm, f"Experiment {self.experiment_id}")
        canvas.drawRightString(A4[0] - self.rightMargin, 9 * mm, f"Page {doc.page}")
        canvas.setFont("Helvetica", 5.8)
        canvas.drawCentredString(A4[0] / 2, 6.4 * mm, f"Generated from persisted experiment evidence · {self.generated_at}")
        canvas.restoreState()


def pdf_report(data: dict) -> bytes:
    """Render canonical report_data() without database writes or scientific computation."""
    s = _styles(); story = []
    experiment = data.get("experiment") or {}; models = data.get("models") or []; dataset = data.get("dataset") or {}
    config = experiment.get("config") or {}; summary = experiment.get("summary") or {}; package = data.get("evidence_package") or {}
    experiment_id = _safe(experiment.get("id")); generated_at = _safe(data.get("generated_at"))
    leader, ranking_metric, leading_value = _leading(models)

    story += [Spacer(1, 18 * mm), _p("ENTANGLEX Q-HEALTH", s["Kicker"]), _p("RESEARCH EXPERIMENT REPORT", s["ReportTitle"]), Spacer(1, 5 * mm)]
    story += [_kv([
        ("Experiment", experiment.get("name") or experiment_id), ("Experiment ID", experiment_id),
        ("Dataset", dataset.get("name") or dataset.get("dataset_name") or experiment.get("dataset_id")),
        ("Status", experiment.get("status")), ("Report generated", generated_at), ("Evidence source", data.get("experiment_label")),
    ], s), Spacer(1, 6 * mm), _p(data.get("disclaimer"), s["Note"]), PageBreak()]

    story += [_p("1 — Experiment overview", s["Section"]), _kv([
        ("Experiment ID", experiment_id), ("Experiment name", experiment.get("name")), ("Status", experiment.get("status")),
        ("Experiment type", data.get("experiment_kind")), ("Created", experiment.get("created_at")), ("Completed", summary.get("completed_at")),
        ("Dataset ID", experiment.get("dataset_id")), ("Dataset hash", dataset.get("dataset_hash") or dataset.get("sha256")),
        ("Samples", dataset.get("row_count") or dataset.get("sample_count")), ("Features", dataset.get("feature_count")),
        ("Target", dataset.get("target")), ("Class labels", dataset.get("class_labels") or dataset.get("target_labels")),
        ("Model count", len(models)), ("Classical / Quantum / Hybrid", f"{sum(_family(m)=='Classical' for m in models)} / {sum(_family(m)=='Quantum' for m in models)} / {sum(_family(m)=='Hybrid' for m in models)}"),
    ], s)]

    story += [_p("2 — Dataset & provenance", s["Section"]), _kv([
        ("Dataset name", dataset.get("name") or dataset.get("dataset_name")), ("Source", dataset.get("source") or dataset.get("dataset_origin")),
        ("Version", dataset.get("version") or dataset.get("version_label")), ("SHA-256", dataset.get("dataset_hash") or dataset.get("sha256")),
        ("Rows / samples", dataset.get("row_count") or dataset.get("sample_count")), ("Feature count", dataset.get("feature_count")),
        ("Target", dataset.get("target")), ("Target labels", dataset.get("target_labels") or dataset.get("class_labels")),
        ("Quality", dataset.get("quality") or dataset.get("quality_summary")), ("Provenance", dataset.get("provenance") or dataset),
    ], s), _p("Raw biomedical rows and patient identifiers are not included in this report.", s["Note"])]

    pipeline = data.get("preprocessing") or {}
    story += [_p("3 — Experimental configuration", s["Section"]), _kv([
        ("Imputation", pipeline.get("imputer")), ("Scaling", pipeline.get("scaler")), ("Outlier handling", pipeline.get("outlier_strategy")),
        ("Feature selection", pipeline.get("selection")), ("PCA components", pipeline.get("pca_components")), ("Angle scaling", pipeline.get("angle_scaling")),
        ("Test split", config.get("test_size")), ("CV folds", config.get("cv_folds")), ("Random seed", config.get("seed")),
        ("Threshold strategy", config.get("threshold_strategy")), ("Threshold", config.get("probability_threshold")),
        ("Target sensitivity", config.get("target_sensitivity")), ("Calibration", config.get("calibration")), ("Configured models", config.get("models")),
    ], s)]

    pipeline_version = data.get("pipeline_version") or {}; protocol = data.get("protocol") or {}
    story += [_p("4 — Pipeline & protocol", s["Section"]), _p("Pipeline", s["Subsection"]), _kv([
        ("Status", pipeline_version.get("status")), ("Name", pipeline_version.get("name")), ("Version", pipeline_version.get("version") or pipeline_version.get("version_label")),
        ("Fingerprint", pipeline_version.get("pipeline_fingerprint") or pipeline_version.get("definition_fingerprint")), ("Lifecycle", pipeline_version.get("lifecycle_status")),
        ("Recorded note", pipeline_version.get("message") or "Pipeline version details shown only when persisted."),
    ], s), _p("Protocol", s["Subsection"]), _kv([
        ("Status", protocol.get("status")), ("Name", _get(protocol, "summary", "study_name")), ("Version", protocol.get("version")),
        ("Fingerprint", protocol.get("definition_fingerprint")), ("Study type", _get(protocol, "summary", "task_type")),
        ("Primary metric", _get(protocol, "summary", "primary_metric")), ("CV folds", _get(protocol, "summary", "cv_folds")),
        ("Recorded note", protocol.get("message") or "Protocol details shown only when persisted."),
    ], s)]

    model_rows = [["Model", "Family", "Status", "Accuracy", "Precision", "Recall", "Specificity", "F1", "ROC-AUC"]]
    for model in models:
        test = _get(model, "metrics", "test", default={}) or {}
        model_rows.append([_model_name(model), _family(model), model.get("status"), *[_metric(test.get(metric)) for metric in METRICS]])
    story += [_p("5 — Model evaluation", s["Section"]), _table(model_rows or [["Model", "Status"]], s, [35*mm,15*mm,16*mm]+[19*mm]*6), _p("Runtime evidence", s["Subsection"])]
    runtime_rows = [["Model", "Training runtime", "CV runtime", "Inference runtime"]]
    for model in models:
        timing = _get(model, "metrics", "timing", default={}) or {}
        runtime_rows.append([_model_name(model), timing.get("final_training_seconds"), timing.get("cv_total_seconds"), timing.get("test_inference_seconds_per_sample")])
    story += [_table(runtime_rows, s, [65*mm,38*mm,38*mm,39*mm])]

    story += [_p("6 — Cross-validation evidence", s["Section"])]
    cv_rows = [["Model", "Metric", "Mean", "Standard deviation", "Valid folds", "Fold values"]]
    for model in models:
        validation = _get(model, "metrics", "validation", default={}) or {}
        summaries = validation.get("summary") or {}
        folds = validation.get("folds") or []
        for metric_name, values in summaries.items():
            if isinstance(values, dict):
                cv_rows.append([_model_name(model), metric_name, _metric(values.get("mean")), _metric(values.get("std")), values.get("valid_folds"), [f.get(metric_name) for f in folds if isinstance(f, dict) and f.get(metric_name) is not None]])
    story += [_table(cv_rows if len(cv_rows)>1 else [["Cross-validation evidence", "Not recorded"]], s)]

    cv_summary = _get(leader or {}, "metrics", "validation", "summary", ranking_metric or "", default={}) or {}
    story += [_p("7 — Primary comparison result", s["Section"]), _kv([
        ("Ranking metric", ranking_metric.replace("_", " ").upper() if ranking_metric else None), ("Leading observed model", _model_name(leader) if leader else None),
        ("Observed value", _metric(leading_value)), ("CV", f"{_metric(cv_summary.get('mean'))} ± {_metric(cv_summary.get('std'))}" if cv_summary else None),
    ], s), _p("This result identifies the highest observed persisted metric under this experiment. It does not establish clinical validity, causality, statistical significance, robustness, or quantum advantage.", s["Note"])]

    family_rows = [["Family", "Best observed model", "Metric", "Observed value"]]
    for family in ("Classical", "Quantum", "Hybrid"):
        family_models = [m for m in models if _family(m)==family]
        fm, met, val = _leading(family_models)
        family_rows.append([family, _model_name(fm) if fm else MISSING, met or MISSING, _metric(val)])
    story += [_p("8 — Classical / quantum / hybrid comparison", s["Section"]), _table(family_rows, s), _p("Values are observed differences under this experiment. They do not establish quantum advantage, superiority, or speedup.", s["Note"])]

    story += [_p("9 — Diagnostic evidence", s["Section"]), _metric_chart(models, s)]
    diagnostic_rows = [["Model", "Confusion matrix", "Threshold", "Calibration", "Runtime"]]
    for model in models:
        metrics = model.get("metrics") or {}; test = metrics.get("test") or {}; op = metrics.get("operating_point") or _get(model, "details", "operating_point", default={}) or {}
        diagnostic_rows.append([_model_name(model), test.get("confusion_matrix"), op.get("selected_threshold"), metrics.get("calibration"), metrics.get("timing")])
    story += [_table(diagnostic_rows, s)]

    explanations = data.get("interpretation") or []
    story += [_p("10 — Explainability", s["Section"])]
    if explanations:
        story += [_table([["Model / record", "Method", "Persisted explanation", "Limitations"], *[[x.get("model_id") or x.get("id"), x.get("method"), x.get("result") or x.get("explanation") or x.get("details"), x.get("limitations")] for x in explanations]], s)]
    else: story += [_p("Explainability evidence was not recorded for this experiment.", s["Note"])]

    story += [_p("11 — Prediction", s["Section"]), _p("Prediction evidence was not recorded in the canonical experiment report data. No fresh prediction was generated for this PDF.", s["Note"])]

    pairs = _get(data, "comparison", "pairs", default=[]) or []
    robustness_rows = [["Model comparison", "Scenario", "Baseline", "Degraded result", "Observed difference"]]
    for pair in pairs:
        robustness = pair.get("robustness") or {}
        results = robustness.get("results") if isinstance(robustness, dict) else None
        for item in results or []:
            robustness_rows.append([f"{pair.get('classical_model')} / {pair.get('quantum_model')}", item.get("scenario"), item.get("baseline"), item.get("degraded_result") or item.get("result"), item.get("difference") or item.get("delta")])
    story += [_p("12 — Robustness", s["Section"]), _table(robustness_rows if len(robustness_rows)>1 else [["Robustness evidence", "Not recorded"]], s)]

    quantum_rows = [["Model", "Framework", "Execution mode", "Backend", "Qubits", "Layers", "Shots", "Optimizer", "Iterations", "Runtime"]]
    for model in models:
        if _family(model) in ("Quantum", "Hybrid"):
            q = _get(model, "details", "quantum", default={}) or {}
            quantum_rows.append([_model_name(model), q.get("framework"), q.get("execution_mode") or q.get("execution_kind"), q.get("backend"), q.get("qubits"), q.get("quantum_layers") or q.get("layers"), q.get("shots"), q.get("optimizer"), q.get("iterations") or q.get("maxiter"), _get(model, "metrics", "timing", "final_training_seconds")])
    story += [_p("13 — Quantum / hybrid execution", s["Section"]), _table(quantum_rows if len(quantum_rows)>1 else [["Quantum / hybrid execution evidence", "Not recorded"]], s), _p("Local simulation is distinct from real quantum hardware. No hardware performance or quantum advantage is inferred.", s["Note"])]
    if isinstance(data.get("quantum_evidence"), dict) and data["quantum_evidence"].get("models"):
        story += _quantum_evidence_story(data["quantum_evidence"], s)

    artifact = package.get("artifact") or {}
    story += [_p("14 — Provenance / traceability", s["Section"]), _kv([
        ("Dataset hash", dataset.get("dataset_hash") or dataset.get("sha256")), ("Pipeline version", pipeline_version.get("version") or pipeline_version.get("version_label")),
        ("Pipeline fingerprint", pipeline_version.get("pipeline_fingerprint") or pipeline_version.get("definition_fingerprint")), ("Protocol version", protocol.get("version")),
        ("Protocol fingerprint", protocol.get("definition_fingerprint")), ("Experiment ID", experiment_id), ("Model IDs", [m.get("id") for m in models]),
        ("Evidence-package ID", package.get("package_id") or package.get("id")), ("Evidence-package fingerprint", package.get("package_fingerprint")),
        ("Artifact ID", artifact.get("id")), ("Artifact integrity hash", artifact.get("integrity_hash")),
    ], s)]

    audit = data.get("audit_summary") or {}
    story += [_p("15 — Audit / integrity", s["Section"]), _kv([
        ("Integrity status", audit.get("integrity_status")), ("Event count", audit.get("total_events")), ("Legacy note", audit.get("legacy_disclaimer")),
    ], s)]
    events = audit.get("recent_events") or []
    if events: story += [_table([["Time", "Event", "Category", "Status"], *[[e.get("occurred_at"), e.get("event_type"), e.get("event_category"), e.get("status")] for e in events]], s)]

    gaps = package.get("evidence_gaps") or []
    limitations = list(package.get("limitations") or [])
    for model in models:
        limitations.extend(_get(model, "details", "limitations", default=[]) or [])
    story += [_p("16 — Evidence gaps & limitations", s["Section"])]
    if gaps: story += [_table([["Category", "Status", "Reason"], *[[g.get("category"), g.get("status"), g.get("reason")] for g in gaps]], s)]
    if limitations: story += [_p("; ".join(dict.fromkeys(map(str, limitations))), s["Note"])]
    if not gaps and not limitations: story += [_p("No dedicated evidence-gap manifest was recorded. Absence of a recorded gap is not evidence of external or clinical validation.", s["Note"])]

    story += [_p("17 — Scientific boundary", s["Section"]), _p(data.get("disclaimer"), s["Note"]), _p(data.get("scientific_boundary"), s["Note"]), _p("Research use only. Explainability is not causal interpretation. Simulation is not real hardware. Results are limited to the evaluated experiment and dataset.", s["BodySmall"])]

    story += [_p("18 — Reproducibility", s["Section"]), _kv([
        ("Dataset hash", dataset.get("dataset_hash") or dataset.get("sha256")), ("Pipeline version", pipeline_version.get("version") or pipeline_version.get("version_label")),
        ("Pipeline fingerprint", pipeline_version.get("pipeline_fingerprint") or pipeline_version.get("definition_fingerprint")), ("Protocol version", protocol.get("version")),
        ("Protocol fingerprint", protocol.get("definition_fingerprint")), ("Seed", config.get("seed")), ("Split", config.get("test_size")), ("CV folds", config.get("cv_folds")),
        ("Model IDs", [m.get("id") for m in models]), ("Artifact IDs", [m.get("artifact_sha256") for m in models if m.get("artifact_sha256")]), ("Evidence-package fingerprint", package.get("package_fingerprint")),
    ], s)]

    execution_modes = sorted({_safe(_get(m, "details", "quantum", "execution_mode") or _get(m, "details", "quantum", "execution_kind")) for m in models if _family(m) in ("Quantum", "Hybrid")})
    finding = (f"Under the recorded experimental configuration, {_model_name(leader)} achieved the highest observed held-out {ranking_metric.replace('_', ' ').upper()} ({leading_value:.4f}) among evaluated models with that persisted metric." if leader and ranking_metric and leading_value is not None else "The persisted evidence does not support a held-out model ranking.")
    if execution_modes: finding += f" Quantum models were evaluated using {', '.join(execution_modes)}."
    finding += " Available evidence is summarized above; external clinical validation was not established by this experiment."
    story += [_p("19 — Final research finding", s["Section"]), _p(finding, s["Note"]), _p("20 — Document footer", s["Section"]), _p("Every page identifies EntangleX Q-Health, the experiment ID, page number, generation timestamp, and persisted-evidence origin.", s["BodySmall"])]

    output = BytesIO(); _ReportDoc(output, experiment_id, generated_at).build(story)
    return output.getvalue()
