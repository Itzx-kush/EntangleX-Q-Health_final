def test_pdf_report_is_valid_and_existing_formats_remain_available(client, config, registered, monkeypatch):
    from app.storage.entities import Experiment, ModelRecord
    from app.database import session_scope
    from app.experiments import reports

    with session_scope() as session:
        experiment = Experiment(name="PDF evidence test", dataset_id=registered.id, status="completed", config=config.model_dump(mode="json"), summary={"experiment_kind": "live_experiment", "dataset_provenance": registered.provenance})
        session.add(experiment); session.flush()
        model = ModelRecord(experiment_id=experiment.id, dataset_id=registered.id, model_type="logistic_regression", status="ready", details={"limitations": ["No external validation"]}, metrics={"test": {"accuracy": .8, "precision": .75, "recall": .7, "specificity": .9, "f1": .72, "roc_auc": .84}, "timing": {"final_training_seconds": .2}})
        session.add(model); identity = experiment.id

    monkeypatch.setattr(reports, "verify_installed_model", lambda model: None)
    pdf = client.get(f"/api/experiments/{identity}/report?format=pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert f'qhealth-{identity}.pdf' in pdf.headers["content-disposition"]
    assert pdf.content.startswith(b"%PDF-")
    assert pdf.content.rstrip().endswith(b"%%EOF")
    assert b"/Type /Page" in pdf.content
    assert len(pdf.content) > 5000

    assert client.get(f"/api/experiments/{identity}/report?format=json").status_code == 200
    assert client.get(f"/api/experiments/{identity}/report?format=html").status_code == 200


def test_pdf_report_unknown_experiment_uses_existing_error_convention(client):
    response = client.get("/api/experiments/00000000-0000-0000-0000-000000000000/report?format=pdf")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
