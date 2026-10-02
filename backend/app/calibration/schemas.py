from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class CalibrationRequest(BaseModel):
    model_id: UUID
    dataset_id: UUID
    dataset_version_id: UUID | None = None
    calibration_method: Literal["sigmoid", "isotonic", "temperature_scaling", "none"] = Field(default="none")
    calibration_protocol: Literal["out_of_fold", "dedicated_split", "prefit_on_test"] = Field(default="dedicated_split")
    sampling_unit: Literal["independent_samples", "grouped_samples"] = Field(default="independent_samples")
    group_column: str | None = Field(default=None, max_length=200)
    split_seed: int = Field(default=42)
    test_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    calibration_size: float = Field(default=0.2, gt=0.0, lt=1.0) # size of calibration split when dedicated_split
    cv_folds: int = Field(default=3, ge=2, le=10) # used if protocol=out_of_fold
    bins: int = Field(default=10, ge=3, le=50)

class CalibrationPreflightResponse(BaseModel):
    feasible: bool
    limitations: list[str]
    method_support: dict[str, bool]
    configuration_fingerprint: str
