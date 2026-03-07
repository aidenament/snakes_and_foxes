from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoardConfig(StrictModel):
    circle_count: int = 6
    nodes_per_circle: int = 10

    @field_validator("circle_count")
    @classmethod
    def validate_circle_count(cls, value: int) -> int:
        if value < 2:
            raise ValueError("circle_count must be at least 2")
        return value

    @field_validator("nodes_per_circle")
    @classmethod
    def validate_nodes_per_circle(cls, value: int) -> int:
        if value < 3:
            raise ValueError("nodes_per_circle must be at least 3")
        return value


class NodeId(StrictModel):
    circle_index: int
    node_index: int = 0

    @field_validator("circle_index")
    @classmethod
    def validate_circle_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("circle_index must be non-negative")
        return value

    @field_validator("node_index")
    @classmethod
    def validate_node_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("node_index must be non-negative")
        return value

    @property
    def key(self) -> tuple[int, int]:
        return (self.circle_index, self.node_index)


class PieceState(StrictModel):
    piece_id: str
    label: str
    node: NodeId
    alive: bool = True
    reached_outer: bool = False


class EnemyType(StrEnum):
    FOX = "fox"
    SNAKE = "snake"


class EnemyState(StrictModel):
    enemy_id: str
    enemy_type: EnemyType
    node: NodeId
    active: bool = True


class DieFace(StrEnum):
    BLACK_PIP = "black_pip"
    RED_TRIANGLE = "red_triangle"
    GREEN_SQUIGGLE = "green_squiggle"


class DiceRoll(StrictModel):
    seed: int
    turn_number: int
    faces: list[DieFace]
    black_pips: int
    red_triangles: int
    green_squiggles: int


class TurnPhase(StrEnum):
    WAITING_FOR_ROLL = "waiting_for_roll"
    PLAYER_MOVING = "player_moving"
    GAME_WON = "game_won"
    GAME_LOST = "game_lost"


class EventLogEntry(StrictModel):
    kind: str
    message: str
    actor_id: str | None = None
    enemy_type: EnemyType | None = None
    source: NodeId | None = None
    destination: NodeId | None = None


class PendingEnemyMoves(StrictModel):
    foxes: int = 0
    snakes: int = 0


class GameState(StrictModel):
    board: BoardConfig = Field(default_factory=BoardConfig)
    seed: int
    turn_number: int = 1
    roll_index: int = 0
    phase: TurnPhase = TurnPhase.WAITING_FOR_ROLL
    active_piece_id: str = "sun"
    pieces: list[PieceState]
    enemies: list[EnemyState]
    dice_roll: DiceRoll | None = None
    moves_remaining: int = 0
    pending_enemy_moves: PendingEnemyMoves = Field(default_factory=PendingEnemyMoves)
    legal_moves: list[NodeId] = Field(default_factory=list)
    winner_piece_id: str | None = None
    event_log: list[EventLogEntry] = Field(default_factory=list)


class ActionResult(StrictModel):
    ok: bool
    state: GameState
    legal_moves: list[NodeId] = Field(default_factory=list)
    resolved_events: list[EventLogEntry] = Field(default_factory=list)
    message: str | None = None


class NewGameRequest(StrictModel):
    seed: int | None = None
    board: BoardConfig = Field(default_factory=BoardConfig)


class NewGameResponse(StrictModel):
    state: GameState
    result: ActionResult


class RollAction(StrictModel):
    type: Literal["roll"]


class MoveAction(StrictModel):
    type: Literal["move"]
    destination: NodeId


class RestartAction(StrictModel):
    type: Literal["restart"]


Action = Annotated[RollAction | MoveAction | RestartAction, Field(discriminator="type")]


class ActionRequest(StrictModel):
    state: GameState
    action: Action


class ActionResponse(StrictModel):
    state: GameState
    result: ActionResult
