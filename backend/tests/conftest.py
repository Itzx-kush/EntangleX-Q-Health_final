"""Isolated test storage. These tests were generated, NOT executed in this task."""
import os
import shutil
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="qhealth-tests-"))
os.environ["QHEALTH_STORAGE_ROOT"] = str(_TEST_ROOT)
os.environ["QHEALTH_API_TOKEN"] = ""
from app.database import init_db, engine
from app.api.schemas import DatasetUploadMetadata, TrainingConfig
from app.data.service import register_csv

@pytest.fixture(scope="session", autouse=True)
def database():
    init_db()
    yield
    engine.dispose()
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)

@pytest.fixture
def biomedical_frame():
    # Synthetic fixtures test code properties; NEVER application benchmark results.
    rng = np.random.default_rng(19)
    frame = pd.DataFrame(rng.normal(size=(120, 6)), columns=[f"biomarker_{i}" for i in range(6)])
    latent = frame["biomarker_0"] + 0.5 * frame["biomarker_1"] + rng.normal(size=len(frame))
    frame["observed_class"] = np.where(latent > np.median(latent), "positive", "negative")
    frame.loc[3, "biomarker_2"] = np.nan
    return frame

@pytest.fixture
def registered(biomedical_frame):
    metadata = DatasetUploadMetadata(name="Synthetic test fixture", target="observed_class", positive_label="positive", deidentified=True)
    return register_csv(biomedical_frame.to_csv(index=False).encode(), "fixture.csv", metadata)

@pytest.fixture
def config(registered):
    return TrainingConfig(dataset_id=registered.id, models=["logistic_regression"], max_samples=None)

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as api:
        yield api
