import hashlib
import json
import logging
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from typing import Any

from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..storage.entities import ConditionTask, DatasetVersion, Dataset, ModelRecord
from .schemas import ReadinessResult, ConditionTaskResponse, ConditionTaskCreate
from .capabilities import get_model_capabilities
from ..data.splitting import _validate_group_column
from ..data.quality import quality_report, validate_target
from ..data.service import load_versioned_frame

logger = logging.getLogger(__name__)

def evaluate_condition_task_readiness(session: Session, task_id: str) -> ReadinessResult:
    task = session.get(ConditionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="ConditionTask not found")

    ds = session.get(Dataset, task.dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    try:
        ds, ds_version, frame = load_versioned_frame(str(task.dataset_id), str(task.dataset_version_id) if task.dataset_version_id else None)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    status = "READY"
    blockers = []
    warnings = []
    limitations = []
    
    # 1. TASK DEFINITION
    task_def = {
        "target": task.target_column,
        "positive_label": task.positive_label,
        "negative_label": task.negative_label,
        "task_type": task.task_type
    }
    
    if not task.target_column or not task.positive_label or not task.negative_label:
        blockers.append("Incomplete task configuration: target or labels missing.")
        status = "INCOMPLETE_CONFIGURATION"
        
    if task.target_column not in frame.columns:
        blockers.append(f"Target column '{task.target_column}' is missing from the dataset.")
        
    # 2. TARGET VALIDITY & LABELS
    labels_info = {}
    quality = {}
    target_info = {}
    if task.target_column in frame.columns:
        target_str = frame[task.target_column].astype(str)
        counts = target_str.value_counts().to_dict()
        
        pos = counts.get(task.positive_label, 0)
        neg = counts.get(task.negative_label, 0)
        total = len(frame)
        
        labels_info = {
            "total_samples": total,
            "positive_samples": pos,
            "negative_samples": neg,
            "positive_fraction": float(pos/total) if total > 0 else 0,
            "negative_fraction": float(neg/total) if total > 0 else 0,
            "observed_classes": list(counts.keys())
        }
        
        if pos == 0:
            blockers.append(f"Positive label '{task.positive_label}' not found in target.")
        if neg == 0:
            blockers.append(f"Negative label '{task.negative_label}' not found in target.")
            
        if len(counts) > 2:
            warnings.append(f"Target column contains {len(counts)} classes. Only the specified positive/negative labels will be used for binary classification.")
            
        if (pos > 0 and pos < 20) or (neg > 0 and neg < 20):
            limitations.append("Extremely small class size detected. Validation folds may be unstable or unstratifiable.")
            status = "READY_WITH_LIMITATIONS" if status == "READY" else status
            
        if pos > 0 and neg > 0 and (pos/total < 0.05 or neg/total < 0.05):
            warnings.append("Severe class imbalance detected (< 5%).")
            status = "READY_WITH_LIMITATIONS" if status == "READY" else status

        try:
            quality = quality_report(frame, task.target_column, task.positive_label)
            if quality.get("blockers"):
                blockers.extend(quality["blockers"])
            if quality.get("warnings"):
                warnings.extend(quality["warnings"])
        except Exception as e:
            blockers.append(f"Data quality report failed: {str(e)}")

    # 3. GROUP READINESS (Advisory / Feasibility)
    # We do not enforce a group column unless configured in TrainingConfig, but readiness 
    # can flag candidate group columns.
    group_info = {}
    # Find candidate columns that end in '_id' or have high cardinality but low uniqueness
    candidates = []
    for c in frame.columns:
        if c == task.target_column: continue
        uniques = frame[c].nunique(dropna=True)
        # If it's an ID column with repeated rows per ID
        if ('_id' in c.lower() or 'patient' in c.lower() or 'subject' in c.lower()) and 1 < uniques < len(frame):
             candidates.append(c)
             
    group_info["candidate_groups"] = candidates

    # 4. CAPABILITIES
    capabilities = get_model_capabilities()
    
    if blockers and status != "INCOMPLETE_CONFIGURATION":
        status = "BLOCKED"
    elif limitations and status == "READY":
        status = "READY_WITH_LIMITATIONS"
        
    fingerprint = hashlib.sha256(json.dumps({
        "dataset_version_id": ds_version.id,
        "target": task.target_column,
        "positive": task.positive_label,
        "negative": task.negative_label,
        "task_type": task.task_type
    }, sort_keys=True).encode()).hexdigest()

    result = ReadinessResult(
        condition_task={
            "id": task.id,
            "condition_name": task.condition_name,
            "metadata": task.metadata_
        },
        dataset={
            "id": ds.id,
            "name": ds.name,
            "version_id": ds_version.id,
            "content_sha256": ds_version.content_sha256,
            "rows": len(frame),
            "columns": len(frame.columns)
        },
        task_type=task.task_type,
        status=status,
        checks={
            "task_definition": task_def,
            "labels": labels_info,
            "quality": quality,
            "groups": group_info,
            "validation": {
                 "holdout_feasible": labels_info.get("positive_samples", 0) > 10 and labels_info.get("negative_samples", 0) > 10,
                 "calibration_feasible": labels_info.get("positive_samples", 0) > 30 and labels_info.get("negative_samples", 0) > 30,
                 "threshold_analysis_feasible": labels_info.get("positive_samples", 0) > 20 and labels_info.get("negative_samples", 0) > 20
            }
        },
        blockers=list(set(blockers)),
        warnings=list(set(warnings)),
        limitations=list(set(limitations)),
        supported_models=list(capabilities.values()) if status not in ("BLOCKED", "INCOMPLETE_CONFIGURATION") else [],
        configuration_fingerprint=fingerprint
    )
    
    task.readiness_status = status
    task.readiness_report = result.model_dump(mode="json")
    task.readiness_updated_at = datetime.now(timezone.utc)
    session.add(task)
    
    return result

def create_condition_task(session: Session, req: ConditionTaskCreate) -> ConditionTask:
    import uuid
    task_id = str(uuid.uuid4())
    
    task = ConditionTask(
        id=task_id,
        condition_name=req.condition_name,
        task_type=req.task_type,
        target_column=req.target_column,
        positive_label=req.positive_label,
        negative_label=req.negative_label,
        dataset_id=str(req.dataset_id),
        dataset_version_id=str(req.dataset_version_id) if req.dataset_version_id else None,
        metadata_=req.metadata_.model_dump() if req.metadata_ else {},
        status="draft",
        created_at=datetime.now(timezone.utc)
    )
    session.add(task)
    session.flush()
    
    # Assess readiness synchronously upon creation
    try:
        evaluate_condition_task_readiness(session, task_id)
        task.status = "ready" if task.readiness_status in ["READY", "READY_WITH_LIMITATIONS"] else "blocked"
    except Exception as e:
        logger.exception("Readiness evaluation failed")
        task.readiness_status = "BLOCKED"
        task.readiness_report = {"error": str(e)}
        task.status = "blocked"
        
    return task
