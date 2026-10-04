"""HTTP boundary for bounded selection checks."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from missiongen import Recipe
from missiongen.readiness import selection_report
from .artifact_service import USER_ERRORS
from .generation import capacity

router = APIRouter()

class ReadinessRequest(BaseModel):
    recipe: dict


@router.post('/api/readiness')
def readiness(req: ReadinessRequest):
    try:
        with capacity.slot():
            return selection_report(Recipe.from_dict(req.recipe))
    except USER_ERRORS as exc:
        raise HTTPException(400, str(exc)) from exc
