from fastapi import APIRouter
from ..alignment import alignment_contract
from .schemas import AlignmentContractOut

router = APIRouter(prefix="/alignment", tags=["SIH judge alignment"])

@router.get("", response_model=AlignmentContractOut)
def get_alignment_contract():
    """Deterministic capability, showcase and architecture metadata; never starts training."""
    return alignment_contract()
