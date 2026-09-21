from fastapi import APIRouter
from ..feature_engineering.pipeline import preview
from .schemas import TrainingConfig, PreviewOut

router = APIRouter(tags=["preprocessing and feature engineering"])

@router.post("/preprocessing/preview", response_model=PreviewOut)
@router.post("/feature-selection/preview", response_model=PreviewOut)
@router.post("/pca/preview", response_model=PreviewOut)
def preview_pipeline(config: TrainingConfig):
    return preview(config)
