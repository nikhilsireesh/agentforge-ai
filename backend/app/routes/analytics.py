from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents import AGENTS
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.services import analytics_service

router = APIRouter(prefix="/api", tags=["Analytics"])


@router.get("/analytics/overview")
def overview(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return analytics_service.overview(db)


@router.get("/analytics/agents")
def agents(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list:
    return analytics_service.agents(db)


@router.get("/analytics/executions")
def executions(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> dict:
    return analytics_service.executions(db)


@router.get("/agents", tags=["Agents"])
def agent_catalogue(_user: User = Depends(get_current_user)) -> list[dict]:
    """Static description of the six agents (name, role, output schema)."""
    return [{"name": a.name, "display_name": a.display_name, "description": a.description,
             "output_fields": list(a.output_model.model_fields)} for a in AGENTS.values()]
