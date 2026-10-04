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
    assert "quantum_evidence" not in captured
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


def test_quantum_pdf_report_uses_persisted_quantum_and_diagnostic_evidence(
    client, config, registered, monkeypatch, tmp_path
):
    from app.database import session_scope
    from app.experiments import reports
    from app.storage.entities import Experiment, ModelRecord, QuantumDiagnosticReport

    quantum_configuration = config.quantum.model_dump(mode="json")
    circuit = {
        "model_type": "qsvc",
        "qubits": quantum_configuration["qubits"],
        "logical_depth": 4,
        "gate_counts": {"h": 4, "cx": 3},
        "parameter_count": 0,
        "text": "H q[0] -> CX q[0], q[1]",
        "gates": [
            {"name": "h", "qubits": [0], "parameters": []},
            {"name": "cx", "qubits": [0, 1], "parameters": []},
        ],
        "limitation": "QSVC feature-map structure; kernel output is not computed in a structural preview.",
    }
    quantum_metadata = {
        "provider_id": "qiskit_local",
        "framework": "Qiskit",
        "backend": "statevector",
        "execution_mode": "local_simulator",
        "execution_kind": "local Qiskit simulation",
        "real_hardware": False,
        "feature_map": "ZZFeatureMap",
        "configuration": quantum_configuration,
        "circuit": circuit,
    }
    with session_scope() as session:
        experiment = Experiment(
            name="Persisted quantum evidence report",
            dataset_id=registered.id,
            status="completed",
            config=config.model_dump(mode="json"),
            summary={
                "experiment_kind": "live_experiment",
                "dataset_provenance": registered.provenance,
            },
        )
        session.add(experiment)
        session.flush()
        model = ModelRecord(
            experiment_id=experiment.id,
            dataset_id=registered.id,
            model_type="qsvc",
            status="ready",
            details={
                "quantum": quantum_metadata,
                "configuration": config.model_dump(mode="json"),
                "input_features": ["feature_1", "feature_2", "feature_3", "feature_4"],
                "preprocessing": {"final_representation_dimension": 4},
                "limitations": ["Persisted model result is simulator-based."],
            },
            metrics={"test": {"accuracy": 0.75}},
        )
        session.add(model)
        session.flush()
        identity, model_id = experiment.id, model.id
        diagnostic = QuantumDiagnosticReport(
            experiment_id=identity,
            model_record_id=model_id,
            model_type="qsvc",
            status="completed",
            model_configuration=quantum_configuration,
            feature_encoding={"mapping_strategy": "ZZFeatureMap"},
            circuit_structure={"depth": 4},
            resource_profile={"qubits_configured": quantum_configuration["qubits"]},
            optimizer_profile={"optimizer": "COBYLA"},
            execution_profile={"execution_mode": "local_simulator"},
            warnings=[],
            limitations=["Stored diagnostic profile is configuration-derived."],
            configuration_fingerprint="a" * 64,
            provenance={"experiment_id": identity, "model_record_id": model_id},
        )
        session.add(diagnostic)
        session.flush()
        diagnostic_id = diagnostic.id

    monkeypatch.setattr(reports, "verify_installed_model", lambda model: None)
    response = client.get(f"/api/experiments/{identity}/report?format=pdf")
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")
    (tmp_path / "quantum-report.pdf").write_bytes(response.content)

    structured = client.get(f"/api/experiments/{identity}/report?format=json").json()
    quantum_evidence = structured["quantum_evidence"]
    assert quantum_evidence["schema_version"] == "quantum_report_evidence_v1"
    assert quantum_evidence["experiment_id"] == identity
    evidence_model = quantum_evidence["models"][0]
    assert evidence_model["model_id"] == model_id
    assert evidence_model["evidence_status"] == "AVAILABLE"
    assert evidence_model["execution"]["provider_id"] == "qiskit_local"
    assert evidence_model["execution"]["real_hardware"] is False
    assert evidence_model["circuit"]["gate_counts"] == {"h": 4, "cx": 3}
    assert evidence_model["circuit"]["gates"][1]["name"] == "cx"
    assert evidence_model["diagnostics"]["id"] == diagnostic_id
    assert evidence_model["state_evidence"]["status"] == "NOT_RECORDED"
    assert "amplitudes" not in evidence_model["state_evidence"]
    assert evidence_model["limitations"]


def test_pdf_quantum_simulation_evidence_uses_persisted_backend_values(
    client, config, registered, monkeypatch, tmp_path
):
    import subprocess
    import pytest
    pytest.importorskip("qiskit_machine_learning")
    from app.artifacts.service import register_metadata
    from app.database import session_scope
    from app.experiments import reports
    from app.quantum.schemas import QuantumVisualizationSimulationRequest
    from app.quantum.visualization import visualization_service
    from app.storage.entities import Experiment, ModelRecord

    with session_scope() as session:
        experiment = Experiment(
            name="Persisted quantum simulation report", dataset_id=registered.id,
            status="completed", config=config.model_dump(mode="json"),
            summary={"experiment_kind": "live_experiment", "dataset_provenance": registered.provenance},
        )
        session.add(experiment)
        session.flush()
        model = ModelRecord(
            experiment_id=experiment.id, dataset_id=registered.id, model_type="qsvc",
            status="ready", details={
                "quantum": {
                    "provider_id": "qiskit_local", "framework": "Qiskit",
                    "backend": "statevector", "execution_mode": "local_simulator",
                    "execution_kind": "local Qiskit simulation", "real_hardware": False,
                    "feature_map": "ZZFeatureMap", "configuration": config.quantum.model_dump(mode="json"),
                    "circuit": {"qubits": config.quantum.qubits, "logical_depth": 2,
                                "parameter_count": 0, "gate_counts": {"h": 4, "cx": 3},
                                "gates": [{"name": "h", "qubits": [0], "parameters": []}],
                                "text": "H q[0]", "limitation": "Structure-only fitted model record."},
                },
                "configuration": config.model_dump(mode="json"),
                "preprocessing": {"final_representation_dimension": config.quantum.qubits},
                "limitations": ["Persisted model evidence is not a clinical result."],
            },
            metrics={"test": {"accuracy": 0.5}},
        )
        session.add(model)
        session.flush()
        experiment_id, model_id = experiment.id, model.id

    simulation = visualization_service.simulate(QuantumVisualizationSimulationRequest(
        model_type="qsvc", quantum=config.quantum,
        encoded_vector=[0.1 * (index + 1) for index in range(config.quantum.qubits)],
        dataset_id=registered.id, experiment_id=experiment_id, seed=13,
    ))
    with session_scope() as session:
        register_metadata(
            session,
            experiment_id=experiment_id,
            model_id=model_id,
            artifact_type="quantum_visualization_evidence",
            name="Quantum visualization simulation",
            description="Backend-generated bounded local-simulator evidence.",
            payload={
                "schema_version": "quantum_visualization_evidence_v1",
                "evidence_status": "AVAILABLE",
                "source": "backend_bounded_local_simulator",
                "experiment_id": experiment_id,
                "model_record_id": model_id,
                "run_id": None,
                "dataset_id": registered.id,
                "request_fingerprint": simulation.request_fingerprint,
                "interpretation": "Explicit visualization simulation only; not a fitted-model prediction.",
                "contract": simulation.model_dump(mode="json"),
            },
            operation_key=f"pdf-test-quantum:{model_id}:{simulation.request_fingerprint}",
        )
    monkeypatch.setattr(reports, "verify_installed_model", lambda _model: None)
    pdf_response = client.get(f"/api/experiments/{experiment_id}/report?format=pdf")
    assert pdf_response.status_code == 200, pdf_response.text
    pdf_path = tmp_path / "quantum-simulation-report.pdf"
    text_path = tmp_path / "quantum-simulation-report.txt"
    pdf_path.write_bytes(pdf_response.content)
    extracted = subprocess.run(["pdftotext", "-layout", str(pdf_path), str(text_path)], check=True, capture_output=True)
    assert extracted.returncode == 0
    text = text_path.read_text()
    assert "Saved backend simulation evidence" in text
    assert "Highest-probability basis states" in text
    assert "Amplitude (real + imag)" in text
    assert "local_simulator" in text
    assert "not a fitted-model prediction" in text.lower()
    assert "normalized_probability" not in text
