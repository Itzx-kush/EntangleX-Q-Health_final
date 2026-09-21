import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.api.schemas import DatasetUploadMetadata
from app.config import get_settings
from app.data.service import delete_dataset, parse_csv, register_csv, register_demo
from app.storage.files import atomic_bytes, load_model, safe_path
from app.utils.errors import AppError


def test_csv_rejects_inconsistent_rows_and_malformed_quotes():
    invalid = [
        b"a,b,target\n1,2,yes\n3,4\n",
        b"a,b,target\n1,2,yes\n3,4,no,extra\n",
        b'a,b,target\n"unterminated,2,yes\n',
    ]
    for content in invalid:
        with pytest.raises(AppError):
            parse_csv(content, "target")


def test_csv_row_and_column_limits(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "max_columns", 2)
    with pytest.raises(AppError, match="column"):
        parse_csv(b"a,b,target\n1,2,yes\n" + b"3,4,no\n" * 9, "target")
    monkeypatch.setattr(settings, "max_columns", 200)
    monkeypatch.setattr(settings, "max_rows", 10)
    rows = b"\n".join([b"1,2,yes"] * 11)
    with pytest.raises(AppError, match="row"):
        parse_csv(b"a,b,target\n" + rows + b"\n", "target")


def test_rejected_registration_leaves_no_dataset_files():
    settings = get_settings()
    before = sorted((settings.root / "data" / "datasets").glob("*"))
    metadata = DatasetUploadMetadata(name="Rejected", target="missing", positive_label="yes", deidentified=True)
    with pytest.raises(AppError):
        register_csv(b"a,b,target\n1,2,yes\n" + b"3,4,no\n" * 9, "rejected.csv", metadata)
    after = sorted((settings.root / "data" / "datasets").glob("*"))
    assert after == before
    assert not list(settings.root.rglob("*.tmp"))


def test_atomic_write_failure_cleans_temporary_file(tmp_path):
    target = tmp_path / "existing-directory"
    target.mkdir()
    with pytest.raises(OSError):
        atomic_bytes(target, b"content")
    assert list(tmp_path.glob(".*.tmp")) == []


def test_invalid_model_artifact_is_rejected_before_use():
    identity = str(uuid4())
    path = safe_path("models", identity, ".dill")
    digest = atomic_bytes(path, b"not-a-dill-payload")
    with pytest.raises(AppError, match="could not be loaded safely"):
        load_model(identity, digest)
    path.unlink(missing_ok=True)
    with pytest.raises(AppError, match="integrity"):
        load_model(identity, digest)


def test_restricted_unpickler_blocks_malicious_dill_payloads():
    import os
    import subprocess
    import dill

    class ExploitSystem:
        def __reduce__(self):
            return (os.system, ("echo EXPLOIT_EXECUTED",))

    class ExploitEval:
        def __reduce__(self):
            return (eval, ("1 + 1",))

    class ExploitSubprocess:
        def __reduce__(self):
            return (subprocess.Popen, (["echo", "EXPLOIT"],))

    from types import FunctionType
    code = compile("import os; os.system('echo EXPLOIT_BYTECODE')", "<string>", "exec")
    exploit_function = FunctionType(code, globals())

    for exploit in [ExploitSystem(), ExploitEval(), ExploitSubprocess(), exploit_function]:
        identity = str(uuid4())
        path = safe_path("models", identity, ".dill")
        payload = dill.dumps(exploit)
        digest = atomic_bytes(path, payload)
        try:
            with pytest.raises(AppError, match="could not be loaded safely"):
                load_model(identity, digest)
        finally:
            path.unlink(missing_ok=True)


def test_symlinked_artifact_path_cannot_escape_storage(tmp_path):
    identity = str(uuid4())
    path = safe_path("data/datasets", identity, ".csv")
    outside = tmp_path / "outside.csv"
    outside.write_bytes(b"private")
    path.symlink_to(outside)
    with pytest.raises(AppError, match="Unsafe storage path"):
        safe_path("data/datasets", identity, ".csv")
    path.unlink()


def test_unreferenced_dataset_delete_removes_row_and_file(registered):
    path = safe_path("data/datasets", registered.id, ".csv")
    assert path.is_file()
    delete_dataset(registered.id)
    assert not path.exists()


def test_missing_dataset_file_blocks_delete_and_preserves_row(registered):
    path = safe_path("data/datasets", registered.id, ".csv")
    path.unlink()
    with pytest.raises(AppError, match="missing"):
        delete_dataset(registered.id)
    from app.database import session_scope
    from app.storage.entities import Dataset
    with session_scope() as session:
        assert session.get(Dataset, registered.id) is not None


def test_api_rejected_upload_leaves_no_file(client):
    settings = get_settings()
    before = sorted((settings.root / "data" / "datasets").glob("*"))
    metadata = {"name": "Rejected upload", "target": "missing", "positive_label": "yes", "deidentified": True}
    response = client.post(
        "/api/datasets/upload",
        data={"metadata_json": json.dumps(metadata)},
        files={"file": ("rejected.csv", b"a,b,target\n1,2,yes\n" + b"3,4,no\n" * 9, "text/csv")},
    )
    assert response.status_code == 422
    after = sorted((settings.root / "data" / "datasets").glob("*"))
    assert after == before


def test_malformed_content_length_is_rejected(client):
    for value in ("-1", "not-an-integer"):
        response = client.post("/api/datasets/upload", content=b"", headers={"Content-Length": value})
        assert response.status_code == 413


def test_concurrent_demo_registration_does_not_duplicate():
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = list(pool.map(lambda _item: register_demo(), range(2)))
    assert records[0].id == records[1].id
