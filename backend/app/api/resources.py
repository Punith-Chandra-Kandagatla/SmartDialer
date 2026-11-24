from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_db
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.enums import AgentStatus
from app.schemas.agent import AgentCreate, AgentResponse, AgentStatusUpdate
from app.schemas.borrower import BorrowerCreate, BorrowerResponse
from app.services.state_machine import StateMachine, InvalidTransitionError

router = APIRouter(prefix="/api/v1", tags=["Resource Management"])


@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(data: AgentCreate, db: Session = Depends(get_db)):
    agent = Agent(name=data.name, email=str(data.email))

    db.add(agent)
    try:
        db.commit()
        db.refresh(agent)
        return agent
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Agent email already exists")


@router.get("/agents", response_model=list[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    return db.query(Agent).order_by(Agent.created_at.desc()).all()


@router.patch("/agents/{agent_id}/status", response_model=AgentResponse)
def update_agent_status(
    agent_id: str,
    data: AgentStatusUpdate,
    db: Session = Depends(get_db),
):
    agent = db.get(Agent, agent_id)

    if agent is None:
        raise HTTPException(404, "Agent not found")

    if data.status not in {
        AgentStatus.AVAILABLE,
        AgentStatus.OFFLINE,
        AgentStatus.PAUSED,
    }:
        raise HTTPException(400, "This status is controlled by the dialer")

    try:
        StateMachine.transition_agent(agent, data.status)
        db.commit()
        db.refresh(agent)
        return agent
    except InvalidTransitionError as exc:
        db.rollback()
        raise HTTPException(409, str(exc))


@router.post("/borrowers", response_model=BorrowerResponse, status_code=201)
def create_borrower(data: BorrowerCreate, db: Session = Depends(get_db)):
    borrower = Borrower(**data.model_dump())

    db.add(borrower)
    try:
        db.commit()
        db.refresh(borrower)
        return borrower
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Borrower reference already exists")


@router.get("/borrowers", response_model=list[BorrowerResponse])
def list_borrowers(db: Session = Depends(get_db)):
    return db.query(Borrower).order_by(Borrower.created_at.desc()).all()