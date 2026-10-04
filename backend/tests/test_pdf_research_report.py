def test_pdf_report_is_valid_and_existing_formats_remain_available(client, config, registered, monkeypatch):
    from app.storage.entities import Experiment, ModelRecord
    from app.database import session_scope
    from app.experiments import reports
    from app.api import experiments as experiments_api

    with session_scope() as session:
        experiment = Experiment(name="PDF evidence test", dataset_id=registered.id, status="completed", config=config.model_dump(mode="json"), summary={"experiment_kind": "live_experiment", "dataset_provenance": registered.provenance})
        session.add(experiment); session.flush()
        model = ModelRecord(experiment_id=experiment.id, dataset_id=registered.id, model_type="logistic_regression", status="ready", details={"limitations": ["No external validation"]}, metrics={"test": {"accuracy": .8, "precision": .75, "recall": .7, "specificity": .9, "f1": .72, "roc_auc": .84}, "timing": {"final_training_seconds": .2}})
        session.add(model); identity = experiment.id

    monkeypatch.setattr(reports, "verify_installed_model", lambda model: None)
    captured = {}
    original_pdf_report = experiments_api.pdf_report
    def capture_report(data):
        captured.update(data)
        return original_pdf_report(data)
    monkeypatch.setattr(experiments_api, "pdf_report", capture_report)
    pdf = client.get(f"/api/experiments/{identity}/report?format=pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert f'qhealth-{identity}.pdf' in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF-")
    assert pdf.content.rstrip().endswith(b"%%EOF")
    assert b"/Type /Page" in pdf.content
    assert len(pdf.content) > 5000
    assert captured["experiment"]["id"] == identity
    assert captured["experiment"]["name"] == "PDF evidence test"
    assert captured["models"][0]["metrics"]["test"]["roc_auc"] == .84
    assert captured["dataset"] == registered.provenance
    serialized = __import__("json").dumps(captured).lower()
    assert "access_token" not in serialized and "service_role" not in serialized

    assert client.get(f"/api/experiments/{identity}/report?format=json").status_code == 200
    assert client.get(f"/api/experiments/{identity}/report?format=html").status_code == 200


def test_pdf_report_unknown_experiment_uses_existing_error_convention(client):
    response = client.get("/api/experiments/00000000-0000-0000-0000-000000000000/report?format=pdf")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_pdf_generation_failure_is_safely_reported(client, config, registered, monkeypatch):
    from app.database import session_scope
    from app.storage.entities import Experiment
    from app.experiments import reports
    from app.api import experiments as experiments_api

    with session_scope() as session:
        experiment = Experiment(name="PDF failure fixture", dataset_id=registered.id, status="completed", config=config.model_dump(mode="json"), summary={"dataset_provenance": registered.provenance})
        session.add(experiment); session.flush(); identity = experiment.id
    monkeypatch.setattr(reports, "verify_installed_model", lambda model: None)
    monkeypatch.setattr(experiments_api, "pdf_report", lambda data: (_ for _ in ()).throw(RuntimeError("private failure detail")))
    response = client.get(f"/api/experiments/{identity}/report?format=pdf")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "pdf_generation_failed"
    assert "private failure detail" not in response.text
