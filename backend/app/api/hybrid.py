from fastapi import APIRouter, Query

from ..hybrid_runtime import verify_hybrid_runtime

router = APIRouter(prefix="/hybrid", tags=["hybrid runtime verification"])


@router.get("/runtime-verification", response_model=dict)
def runtime_verification(force: bool = Query(False)):
    """Run or return the bounded flagship live hybrid runtime verification."""
    return verify_hybrid_runtime(force=force)
