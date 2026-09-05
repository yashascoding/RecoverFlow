from __future__ import annotations

import uuid
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.agent import (
    AgentActionCreate,
    AgentActionResponse,
    AgentRunCreate,
    AgentRunResponse,
)
from app.services.agents.agent_service import AgentService

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_run(
    body: AgentRunCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    svc = AgentService(db)
    run = await svc.create_run(
        agent_type=body.agent_type.value,
        payment_id=body.payment_id,
        customer_id=body.customer_id,
        input_data=body.input_data,
    )
    await db.commit()
    return AgentRunResponse.model_validate(run)


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    run_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    svc = AgentService(db)
    run = await svc.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    if run.user_id and run.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    return AgentRunResponse.model_validate(run)


@router.get("/runs", response_model=dict)
async def list_agent_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = AgentService(db)
    items, total = await svc.list_runs(page=page, page_size=page_size, user_id=current_user.id)
    return {
        "items": [AgentRunResponse.model_validate(r) for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if total else 0,
    }


@router.post("/actions", response_model=AgentActionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_action(
    body: AgentActionCreate,
    db: AsyncSession = Depends(get_db),
) -> AgentActionResponse:
    svc = AgentService(db)
    run = await svc.get_run(body.run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    action = await svc.create_action(
        run_id=body.run_id,
        action_type=body.action_type.value,
        target=body.target,
        payload=body.payload,
    )
    await db.commit()
    return AgentActionResponse.model_validate(action)


@router.get("/actions/{action_id}", response_model=AgentActionResponse)
async def get_agent_action(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AgentActionResponse:
    svc = AgentService(db)
    action = await svc.get_action(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent action not found",
        )
    return AgentActionResponse.model_validate(action)


@router.get("/runs/{run_id}/actions", response_model=list[AgentActionResponse])
async def list_agent_actions_by_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AgentActionResponse]:
    svc = AgentService(db)
    run = await svc.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found",
        )
    actions = await svc.list_actions_by_run(run_id)
    return [AgentActionResponse.model_validate(a) for a in actions]
