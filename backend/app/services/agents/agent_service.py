from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.agent_run import AgentRun, AgentRunStatus

logger = get_logger(__name__)


class AgentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_run(
        self,
        agent_type: str,
        payment_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        input_data: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AgentRun:
        run = AgentRun(
            agent_type=agent_type,
            payment_id=payment_id,
            customer_id=customer_id,
            input_data=input_data,
            user_id=user_id,
            status=AgentRunStatus.PENDING.value,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.refresh(run)
        logger.info(
            "agent_run_created",
            extra={"run_id": str(run.id), "agent_type": agent_type},
        )
        return run

    async def get_run(self, run_id: uuid.UUID) -> AgentRun | None:
        result = await self.db.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(
        self, page: int = 1, page_size: int = 20, user_id: uuid.UUID | None = None
    ) -> tuple[Sequence[AgentRun], int]:
        count_query = select(func.count()).select_from(AgentRun)
        query = select(AgentRun)

        if user_id:
            count_query = count_query.where(AgentRun.user_id == user_id)
            query = query.where(AgentRun.user_id == user_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            query
            .order_by(AgentRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def create_action(
        self,
        run_id: uuid.UUID,
        action_type: str,
        target: str | None = None,
        payload: dict | None = None,
    ) -> AgentAction:
        action = AgentAction(
            run_id=run_id,
            action_type=action_type,
            target=target,
            payload=payload,
            status=AgentActionStatus.PENDING.value,
        )
        self.db.add(action)
        await self.db.flush()
        await self.db.refresh(action)
        logger.info(
            "agent_action_created",
            extra={"action_id": str(action.id), "run_id": str(run_id)},
        )
        return action

    async def get_action(self, action_id: uuid.UUID) -> AgentAction | None:
        result = await self.db.execute(
            select(AgentAction).where(AgentAction.id == action_id)
        )
        return result.scalar_one_or_none()

    async def list_actions_by_run(self, run_id: uuid.UUID) -> Sequence[AgentAction]:
        result = await self.db.execute(
            select(AgentAction)
            .where(AgentAction.run_id == run_id)
            .order_by(AgentAction.created_at.asc())
        )
        return result.scalars().all()
