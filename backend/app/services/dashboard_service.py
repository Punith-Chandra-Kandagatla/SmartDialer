from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.campaign import Campaign


class DashboardService:

    @staticmethod
    def _count_by_status(db: Session, model):
        rows = db.execute(
            select(model.status, func.count(model.id))
            .group_by(model.status)
        ).all()

        return {
            status.value: count
            for status, count in rows
        }

    @staticmethod
    def get_overview(db: Session) -> dict:

        return {
            "campaigns": {
                "total": db.scalar(
                    select(func.count(Campaign.id))
                ) or 0,
                "by_status": DashboardService._count_by_status(
                    db, Campaign
                ),
            },
            "agents": {
                "total": db.scalar(
                    select(func.count(Agent.id))
                ) or 0,
                "by_status": DashboardService._count_by_status(
                    db, Agent
                ),
            },
            "borrowers": {
                "total": db.scalar(
                    select(func.count(Borrower.id))
                ) or 0,
                "by_status": DashboardService._count_by_status(
                    db, Borrower
                ),
            },
            "calls": {
                "total": db.scalar(
                    select(func.count(Call.id))
                ) or 0,
                "by_status": DashboardService._count_by_status(
                    db, Call
                ),
            },
        }