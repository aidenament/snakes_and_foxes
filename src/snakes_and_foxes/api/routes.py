from __future__ import annotations

from fastapi import APIRouter

from snakes_and_foxes.domain.engine import apply_action, create_new_game
from snakes_and_foxes.domain.models import (
    ActionRequest,
    ActionResponse,
    NewGameRequest,
    NewGameResponse,
)

router = APIRouter(prefix="/api")


@router.post("/game/new", response_model=NewGameResponse)
def new_game(request: NewGameRequest) -> NewGameResponse:
    result = create_new_game(request)
    return NewGameResponse(state=result.state, result=result)


@router.post("/game/action", response_model=ActionResponse)
def game_action(request: ActionRequest) -> ActionResponse:
    result = apply_action(request.state, request.action)
    return ActionResponse(state=result.state, result=result)
