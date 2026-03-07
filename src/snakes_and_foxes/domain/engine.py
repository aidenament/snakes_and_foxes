from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable

from snakes_and_foxes.domain.models import (
    ActionResult,
    DiceRoll,
    DieFace,
    EnemyState,
    EnemyType,
    EventLogEntry,
    GameState,
    MoveAction,
    NewGameRequest,
    NodeId,
    PendingEnemyMoves,
    PieceState,
    RestartAction,
    RollAction,
    TurnPhase,
)

PLAYER_COLORS = {
    "sun": "Sun",
    "moon": "Moon",
}


def create_new_game(request: NewGameRequest) -> ActionResult:
    seed = (
        request.seed
        if request.seed is not None
        else random.SystemRandom().randint(1, 999_999_999)
    )
    state = GameState(
        board=request.board,
        seed=seed,
        pieces=[
            PieceState(piece_id="sun", label="Sun", node=NodeId(circle_index=0, node_index=0)),
            PieceState(piece_id="moon", label="Moon", node=NodeId(circle_index=0, node_index=0)),
        ],
        enemies=_initial_enemies(request.board),
        event_log=[
            EventLogEntry(
                kind="intro",
                message="Guide either piece to the outer ring and return to the center.",
            )
        ],
    )
    state.legal_moves = []
    return ActionResult(
        ok=True,
        state=state,
        legal_moves=[],
        resolved_events=state.event_log,
        message="New game created.",
    )


def apply_action(state: GameState, action: RollAction | MoveAction | RestartAction) -> ActionResult:
    if isinstance(action, RestartAction):
        return create_new_game(NewGameRequest(seed=state.seed, board=state.board))

    if state.phase in {TurnPhase.GAME_WON, TurnPhase.GAME_LOST}:
        return _error_result(state, "The game is over. Start a new game to continue.")

    if isinstance(action, RollAction):
        return _apply_roll(state)

    if isinstance(action, MoveAction):
        return _apply_move(state, action.destination)

    return _error_result(state, "Unsupported action.")


def ring_direction(circle_index: int) -> int:
    return -1 if circle_index % 2 == 0 else 1


def neighbors(board, node: NodeId) -> list[NodeId]:
    if node.circle_index == 0:
        return [NodeId(circle_index=1, node_index=index) for index in range(board.nodes_per_circle)]

    options = [
        NodeId(
            circle_index=node.circle_index,
            node_index=(
                node.node_index + ring_direction(node.circle_index)
            )
            % board.nodes_per_circle,
        )
    ]

    if node.circle_index == 1:
        options.append(NodeId(circle_index=0, node_index=0))
    else:
        options.append(NodeId(circle_index=node.circle_index - 1, node_index=node.node_index))

    if node.circle_index < board.circle_count - 1:
        options.append(NodeId(circle_index=node.circle_index + 1, node_index=node.node_index))

    return options


def shortest_path_distance(board, start: NodeId, goal: NodeId) -> int | None:
    if start == goal:
        return 0

    queue = deque([(start, 0)])
    visited = {start.key}

    while queue:
        current, distance = queue.popleft()
        for nxt in neighbors(board, current):
            if nxt.key in visited:
                continue
            if nxt == goal:
                return distance + 1
            visited.add(nxt.key)
            queue.append((nxt, distance + 1))

    return None


def compute_legal_moves(state: GameState) -> list[NodeId]:
    if state.phase != TurnPhase.PLAYER_MOVING or state.moves_remaining <= 0:
        return []

    active_piece = get_active_piece(state)
    if active_piece is None or not active_piece.alive:
        return []

    occupied_by_players = {
        piece.node.key
        for piece in state.pieces
        if piece.alive and piece.piece_id != active_piece.piece_id and piece.node.circle_index != 0
    }
    occupied_by_enemies = {enemy.node.key for enemy in state.enemies if enemy.active}

    moves: list[NodeId] = []
    for candidate in neighbors(state.board, active_piece.node):
        if candidate.key in occupied_by_enemies:
            continue
        if candidate.key in occupied_by_players:
            continue
        moves.append(candidate)
    return _sorted_nodes(moves)


def select_enemies_to_move(
    state: GameState,
    enemy_type: EnemyType,
    limit: int,
    target: NodeId,
) -> list[str]:
    distances: list[tuple[int, str]] = []
    for enemy in state.enemies:
        if not enemy.active or enemy.enemy_type != enemy_type:
            continue
        distance = shortest_path_distance(state.board, enemy.node, target)
        if distance is None:
            continue
        distances.append((distance, enemy.enemy_id))
    distances.sort(key=lambda item: (item[0], item[1]))
    return [enemy_id for _, enemy_id in distances[:limit]]


def move_enemy_one_step(state: GameState, enemy: EnemyState, target: NodeId) -> tuple[NodeId, bool]:
    candidate_nodes = neighbors(state.board, enemy.node)
    occupied = {
        other.node.key
        for other in state.enemies
        if other.active and other.enemy_id != enemy.enemy_id
    }

    if any(candidate == target for candidate in candidate_nodes):
        return target, True

    scored: list[tuple[int, int, tuple[int, int], NodeId]] = []
    for candidate in candidate_nodes:
        if candidate.key in occupied:
            continue
        distance = shortest_path_distance(state.board, candidate, target)
        if distance is None:
            continue
        if candidate.circle_index < enemy.node.circle_index:
            move_priority = 0
        elif candidate.circle_index == enemy.node.circle_index:
            move_priority = 1
        else:
            move_priority = 2
        scored.append((distance, move_priority, candidate.key, candidate))

    if not scored:
        return enemy.node, False

    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return scored[0][3], False


def get_active_piece(state: GameState) -> PieceState | None:
    for piece in state.pieces:
        if piece.piece_id == state.active_piece_id:
            return piece
    return None


def get_piece(state: GameState, piece_id: str) -> PieceState | None:
    for piece in state.pieces:
        if piece.piece_id == piece_id:
            return piece
    return None


def _apply_roll(state: GameState) -> ActionResult:
    if state.phase != TurnPhase.WAITING_FOR_ROLL:
        return _error_result(state, "Rolls are only allowed at the start of a turn.")

    next_state = state.model_copy(deep=True)
    roll = _generate_roll(next_state)
    next_state.roll_index += 1
    next_state.dice_roll = roll
    next_state.moves_remaining = roll.black_pips
    next_state.pending_enemy_moves = PendingEnemyMoves(
        foxes=roll.red_triangles,
        snakes=roll.green_squiggles,
    )

    events = [
        EventLogEntry(
            kind="roll",
            message=(
                f"Rolled {roll.black_pips} black pips, "
                f"{roll.red_triangles} fox activations, and "
                f"{roll.green_squiggles} snake activations."
            ),
        )
    ]

    if roll.black_pips > 0:
        next_state.phase = TurnPhase.PLAYER_MOVING
        next_state.legal_moves = compute_legal_moves(next_state)
        if not next_state.legal_moves:
            events.append(
                EventLogEntry(
                    kind="warning",
                    message="No safe moves are available. Enemies advance immediately.",
                )
            )
            next_state.moves_remaining = 0
            _resolve_enemy_phase(next_state, events)
    else:
        events.append(
            EventLogEntry(
                kind="skip",
                message="No black pips. The enemies move instead.",
            )
        )
        _resolve_enemy_phase(next_state, events)

    _finalize_events(next_state, events)
    return ActionResult(
        ok=True,
        state=next_state,
        legal_moves=next_state.legal_moves,
        resolved_events=events,
        message="Dice resolved.",
    )


def _apply_move(state: GameState, destination: NodeId) -> ActionResult:
    if state.phase != TurnPhase.PLAYER_MOVING:
        return _error_result(state, "You can only move after rolling black pips.")

    next_state = state.model_copy(deep=True)
    next_state.legal_moves = compute_legal_moves(next_state)
    if destination not in next_state.legal_moves:
        return _error_result(next_state, "That node is not a legal move.")

    active_piece = get_active_piece(next_state)
    if active_piece is None:
        return _error_result(next_state, "No active piece is available.")

    source = active_piece.node
    active_piece.node = destination
    if destination.circle_index == next_state.board.circle_count - 1:
        active_piece.reached_outer = True

    next_state.moves_remaining -= 1
    events = [
        EventLogEntry(
            kind="player_move",
            message=f"{active_piece.label} moved.",
            actor_id=active_piece.piece_id,
            source=source,
            destination=destination,
        )
    ]

    if active_piece.reached_outer and destination.circle_index == 0:
        next_state.phase = TurnPhase.GAME_WON
        next_state.winner_piece_id = active_piece.piece_id
        next_state.moves_remaining = 0
        next_state.legal_moves = []
        events.append(
            EventLogEntry(
                kind="victory",
                message=f"{active_piece.label} returned to the center and won the game.",
                actor_id=active_piece.piece_id,
                destination=destination,
            )
        )
        _finalize_events(next_state, events)
        return ActionResult(
            ok=True,
            state=next_state,
            legal_moves=[],
            resolved_events=events,
            message="Victory.",
        )

    if next_state.moves_remaining > 0:
        next_state.legal_moves = compute_legal_moves(next_state)
        _finalize_events(next_state, events)
        return ActionResult(
            ok=True,
            state=next_state,
            legal_moves=next_state.legal_moves,
            resolved_events=events,
            message=f"{next_state.moves_remaining} move(s) remain.",
        )

    _resolve_enemy_phase(next_state, events)
    _finalize_events(next_state, events)
    return ActionResult(
        ok=True,
        state=next_state,
        legal_moves=next_state.legal_moves,
        resolved_events=events,
        message="Move resolved.",
    )


def _resolve_enemy_phase(state: GameState, events: list[EventLogEntry]) -> None:
    active_piece = get_active_piece(state)
    if active_piece is None or not active_piece.alive:
        _advance_turn(state, events)
        return

    for enemy_type, limit in (
        (EnemyType.FOX, state.pending_enemy_moves.foxes),
        (EnemyType.SNAKE, state.pending_enemy_moves.snakes),
    ):
        if limit <= 0:
            continue
        target_piece = get_active_piece(state)
        if target_piece is None or not target_piece.alive:
            break
        enemy_ids = select_enemies_to_move(state, enemy_type, limit, target_piece.node)
        for enemy_id in enemy_ids:
            target_piece = get_active_piece(state)
            if target_piece is None or not target_piece.alive:
                break
            enemy = next(
                (
                    item
                    for item in state.enemies
                    if item.enemy_id == enemy_id and item.active
                ),
                None,
            )
            if enemy is None:
                continue
            source = enemy.node
            destination, captured = move_enemy_one_step(state, enemy, target_piece.node)
            enemy.node = destination
            events.append(
                EventLogEntry(
                    kind="enemy_move",
                    message=f"{enemy.enemy_type.value.title()} moved.",
                    actor_id=enemy.enemy_id,
                    enemy_type=enemy.enemy_type,
                    source=source,
                    destination=destination,
                )
            )
            if captured:
                target_piece.alive = False
                events.append(
                    EventLogEntry(
                        kind="capture",
                        message=f"{enemy.enemy_type.value.title()} captured {target_piece.label}.",
                        actor_id=enemy.enemy_id,
                        enemy_type=enemy.enemy_type,
                        source=source,
                        destination=destination,
                    )
                )
                if not any(piece.alive for piece in state.pieces):
                    state.phase = TurnPhase.GAME_LOST
                    state.legal_moves = []
                    events.append(
                        EventLogEntry(
                            kind="defeat",
                            message="Both pieces were captured. The game is lost.",
                        )
                    )
                    return

    _advance_turn(state, events)


def _advance_turn(state: GameState, events: list[EventLogEntry]) -> None:
    if state.phase in {TurnPhase.GAME_LOST, TurnPhase.GAME_WON}:
        state.legal_moves = []
        return

    living_piece_ids = [piece.piece_id for piece in state.pieces if piece.alive]
    if not living_piece_ids:
        state.phase = TurnPhase.GAME_LOST
        state.legal_moves = []
        return

    if len(living_piece_ids) == 1:
        state.active_piece_id = living_piece_ids[0]
    else:
        state.active_piece_id = "moon" if state.active_piece_id == "sun" else "sun"
        if state.active_piece_id not in living_piece_ids:
            state.active_piece_id = living_piece_ids[0]

    state.turn_number += 1
    state.phase = TurnPhase.WAITING_FOR_ROLL
    state.moves_remaining = 0
    state.pending_enemy_moves = PendingEnemyMoves()
    state.legal_moves = []
    events.append(
        EventLogEntry(
            kind="turn_end",
            message=f"The next active piece is {PLAYER_COLORS[state.active_piece_id]}.",
            actor_id=state.active_piece_id,
        )
    )


def _generate_roll(state: GameState) -> DiceRoll:
    rng = random.Random(f"{state.seed}:{state.turn_number}:{state.roll_index}")
    faces = [rng.choice(list(DieFace)) for _ in range(6)]
    return DiceRoll(
        seed=state.seed,
        turn_number=state.turn_number,
        faces=faces,
        black_pips=sum(face == DieFace.BLACK_PIP for face in faces),
        red_triangles=sum(face == DieFace.RED_TRIANGLE for face in faces),
        green_squiggles=sum(face == DieFace.GREEN_SQUIGGLE for face in faces),
    )


def _initial_enemies(board) -> list[EnemyState]:
    outer_ring = board.circle_count - 1
    enemies: list[EnemyState] = []
    for node_index in range(board.nodes_per_circle):
        enemy_type = EnemyType.SNAKE if node_index % 2 == 0 else EnemyType.FOX
        enemies.append(
            EnemyState(
                enemy_id=f"{enemy_type.value}-{node_index}",
                enemy_type=enemy_type,
                node=NodeId(circle_index=outer_ring, node_index=node_index),
            )
        )
    return enemies


def _finalize_events(state: GameState, events: Iterable[EventLogEntry]) -> None:
    combined = state.event_log + list(events)
    state.event_log = combined[-12:]


def _error_result(state: GameState, message: str) -> ActionResult:
    error_event = EventLogEntry(kind="error", message=message)
    next_state = state.model_copy(deep=True)
    _finalize_events(next_state, [error_event])
    return ActionResult(
        ok=False,
        state=next_state,
        legal_moves=next_state.legal_moves,
        resolved_events=[error_event],
        message=message,
    )


def _sorted_nodes(nodes: Iterable[NodeId]) -> list[NodeId]:
    return sorted(nodes, key=lambda node: (node.circle_index, node.node_index))
