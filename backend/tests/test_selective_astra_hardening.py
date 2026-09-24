from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.data.service import parse_csv
from app.storage.files import get_artifact_key, safe_path
from app.utils.errors import AppError


def test_csv_row_limit_is_enforced_during_streamed_scan(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_rows", 20)
    content = ("feature,target\n" + "\n".join("1,yes" for _ in range(21))).encode()
    with pytest.raises(AppError, match="row limit"):
        parse_csv(content, "target")


def test_symlinked_storage_directory_cannot_escape(tmp_path, monkeypatch):
    from app.config import get_settings

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "models").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(get_settings(), "storage_root", root)
    with pytest.raises(AppError, match="Unsafe storage path"):
        safe_path("models", str(uuid4()), ".dill")


def test_cancel_at_completion_boundary_is_not_overwritten(registered):
    from app.database import session_scope
    from app.jobs.manager import TrainingManager
    from app.storage.entities import Experiment, Job

    experiment_id, job_id = str(uuid4()), str(uuid4())
    with session_scope() as session:
        session.add(Experiment(id=experiment_id, dataset_id=registered.id, config={}, summary={}))
        session.flush()
        session.add(Job(id=job_id, experiment_id=experiment_id, status="cancel_requested"))
    TrainingManager()._finish(job_id, experiment_id, "succeeded", "Finished")
    with session_scope() as session:
        assert session.get(Job, job_id).status == "cancelled"
        assert session.get(Experiment, experiment_id).status == "cancelled"


def test_invalid_artifact_key_is_not_silently_replaced(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    key = tmp_path / ".artifact_key"
    key.write_bytes(b"invalid")
    with pytest.raises(AppError, match="invalid"):
        get_artifact_key()
    assert key.read_bytes() == b"invalid"


def test_concurrent_artifact_key_creation_uses_one_identity(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "storage_root", tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        keys = list(pool.map(lambda _: get_artifact_key(), range(8)))
    assert len(set(keys)) == 1
    assert keys[0] == (tmp_path / ".artifact_key").read_bytes()
