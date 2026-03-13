from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable
from functools import cache

from snakes_and_foxes.domain.models import (
    ActionResult,
    BoardConfig,
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
    "white": "White",
    "black": "Black",
}
NodeKey = tuple[int, int]
CANONICAL_BOARD = BoardConfig()
POST_OUTER_BLACK_PIP_CHANCE = 1 / 4
POST_OUTER_EXTRA_BLACK_PIP_DECAY = 0.85


def create_new_game(request: NewGameRequest) -> ActionResult:
    seed = (
        request.seed if request.seed is not None else random.SystemRandom().randint(1, 999_999_999)
    )
    state = GameState(
        board=CANONICAL_BOARD.model_copy(deep=True),
        seed=seed,
        pieces=[
            PieceState(piece_id="white", label="White", node=NodeId(circle_index=0, node_index=0)),
            PieceState(piece_id="black", label="Black", node=NodeId(circle_index=0, node_index=0)),
        ],
        enemies=_initial_enemies(CANONICAL_BOARD),
        turn_path=[NodeId(circle_index=0, node_index=0)],
        event_log=[
            EventLogEntry(
                kind="intro",
                message=(
                    "A fresh board is laid: White and Black begin in the hub, "
                    "with foxes and snakes alternating around the outer ring."
                ),
            )
        ],
    )
    return ActionResult(
        ok=True,
        state=state,
        legal_moves=[],
        resolved_events=state.event_log,
        message="New game created.",
    )


def apply_action(state: GameState, action: RollAction | MoveAction | RestartAction) -> ActionResult:
    if isinstance(action, RestartAction):
        return create_new_game(NewGameRequest(seed=state.seed))

    if state.phase in {TurnPhase.GAME_WON, TurnPhase.GAME_LOST}:
        return _error_result(state, "The game is over. Start a new game to continue.")

    if isinstance(action, RollAction):
        return _apply_roll(state)

    if isinstance(action, MoveAction):
        return _apply_move(state, action.destination)

    return _error_result(state, "Unsupported action.")


def ring_direction(circle_index: int) -> int:
    if circle_index <= 0:
        raise ValueError("Ring direction is only defined for board rings.")
    return -1 if circle_index % 2 == 1 else 1


def _board_signature(board: BoardConfig) -> tuple[int, int]:
    return (board.circle_count, board.nodes_per_circle)


@cache
def _cached_neighbor_keys(
    circle_count: int,
    nodes_per_circle: int,
) -> dict[NodeKey, tuple[NodeKey, ...]]:
    outer_ring = circle_count - 1
    graph: dict[NodeKey, tuple[NodeKey, ...]] = {
        (0, 0): tuple((1, index) for index in range(nodes_per_circle))
    }

    for circle_index in range(1, circle_count):
        for node_index in range(nodes_per_circle):
            options: list[NodeKey] = []
            if circle_index == outer_ring:
                options.append((circle_index, (node_index + 1) % nodes_per_circle))
                options.append((circle_index, (node_index - 1) % nodes_per_circle))
            else:
                options.append(
                    (
                        circle_index,
                        (node_index + ring_direction(circle_index)) % nodes_per_circle,
                    )
                )

            if circle_index == 1:
                options.append((0, 0))
            else:
                options.append((circle_index - 1, node_index))

            if circle_index < outer_ring:
                options.append((circle_index + 1, node_index))

            graph[(circle_index, node_index)] = tuple(_dedupe_keys(options))

    return graph


@cache
def _cached_distances(
    circle_count: int,
    nodes_per_circle: int,
) -> dict[NodeKey, dict[NodeKey, int]]:
    graph = _cached_neighbor_keys(circle_count, nodes_per_circle)
    distances: dict[NodeKey, dict[NodeKey, int]] = {}

    for start in graph:
        queue = deque([(start, 0)])
        visited = {start}
        shortest: dict[NodeKey, int] = {start: 0}
        while queue:
            current, distance = queue.popleft()
            for nxt in graph[current]:
                if nxt in visited:
                    continue
                visited.add(nxt)
                shortest[nxt] = distance + 1
                queue.append((nxt, distance + 1))
        distances[start] = shortest

    return distances


@cache
def _cached_reverse_neighbor_keys(
    circle_count: int,
    nodes_per_circle: int,
) -> dict[NodeKey, tuple[NodeKey, ...]]:
    graph = _cached_neighbor_keys(circle_count, nodes_per_circle)
    reverse_graph: dict[NodeKey, list[NodeKey]] = {node: [] for node in graph}

    for source, destinations in graph.items():
        for destination in destinations:
            reverse_graph[destination].append(source)

    return {
        node: tuple(_dedupe_keys(predecessors))
        for node, predecessors in reverse_graph.items()
    }


def neighbors(board, node: NodeId) -> list[NodeId]:
    graph = _cached_neighbor_keys(*_board_signature(board))
    return [
        NodeId(circle_index=circle_index, node_index=node_index)
        for circle_index, node_index in graph.get(node.key, ())
    ]


def shortest_path_distance(board, start: NodeId, goal: NodeId) -> int | None:
    return _cached_distances(*_board_signature(board)).get(start.key, {}).get(goal.key)


def _build_enemy_distance_map(
    board: BoardConfig,
    target: NodeId,
    blocked_keys: frozenset[NodeKey],
) -> dict[NodeKey, int]:
    reverse_graph = _cached_reverse_neighbor_keys(*_board_signature(board))
    queue = deque([target.key])
    distances: dict[NodeKey, int] = {target.key: 0}

    while queue:
        current = queue.popleft()
        for predecessor in reverse_graph.get(current, ()):
            if predecessor in distances:
                continue
            if predecessor in blocked_keys and predecessor != target.key:
                continue
            distances[predecessor] = distances[current] + 1
            queue.append(predecessor)

    return distances


def compute_legal_moves(state: GameState) -> list[NodeId]:
    if state.phase != TurnPhase.PLAYER_MOVING or state.moves_remaining <= 0:
        return []

    active_piece = get_active_piece(state)
    if active_piece is None or not active_piece.alive:
        return []

    occupied = _occupied_player_and_enemy_keys(state, active_piece.piece_id)
    moves: list[NodeId] = []
    for candidate in neighbors(state.board, active_piece.node):
        if candidate.key in occupied:
            continue

        candidate_reached_outer = active_piece.reached_outer or _is_outer_ring(
            state.board, candidate
        )
        if candidate_reached_outer and candidate.circle_index == 0:
            moves.append(candidate)
            continue

        if state.moves_remaining == 1 or _can_finish_exact_move(
            board=state.board,
            current=candidate,
            steps_remaining=state.moves_remaining - 1,
            reached_outer=candidate_reached_outer,
            occupied=occupied,
        ):
            moves.append(candidate)

    return _sorted_nodes(moves)


def move_enemy_one_step(state: GameState, enemy: EnemyState, target: NodeId) -> tuple[NodeId, bool]:
    distance_map = _build_enemy_distance_map(
        state.board,
        target,
        _enemy_blocked_path_keys(state),
    )
    move_option = _enemy_move_option(state, enemy, target, distance_map)
    if move_option is None:
        return enemy.node, False

    _, destination, _ = move_option
    return destination, destination == target


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
    active_piece = get_active_piece(next_state)
    if active_piece is None or not active_piece.alive:
        return _error_result(next_state, "No active piece is available.")

    rerolled_opening_turn = False
    while True:
        roll = _generate_roll(next_state)
        next_state.roll_index += 1
        if active_piece.turns_taken > 0 or roll.black_pips > 0:
            break
        rerolled_opening_turn = True

    active_piece.turns_taken += 1
    if active_piece.reached_outer:
        active_piece.post_outer_rolls += 1
    next_state.dice_roll = roll
    next_state.moves_remaining = roll.black_pips
    next_state.pending_enemy_moves = PendingEnemyMoves(
        foxes=roll.red_triangles,
        snakes=roll.green_squiggles,
    )

    events: list[EventLogEntry] = []
    if rerolled_opening_turn:
        events.append(
            EventLogEntry(
                kind="reroll",
                actor_id=active_piece.piece_id,
                message=(
                    f"{active_piece.label} rerolled because the opening throw "
                    "had no move symbols."
                ),
            )
        )

    events.append(
        EventLogEntry(
            kind="roll",
            actor_id=active_piece.piece_id,
            message=(
                f"{active_piece.label} rolled {roll.black_pips} moves, "
                f"{roll.red_triangles} fox activations, and "
                f"{roll.green_squiggles} snake activations."
            ),
        )
    )

    next_state.turn_path = [active_piece.node]
    if roll.black_pips > 0:
        next_state.phase = TurnPhase.PLAYER_MOVING
        next_state.legal_moves = compute_legal_moves(next_state)
        if not next_state.legal_moves:
            next_state.moves_remaining = 0
            events.append(
                EventLogEntry(
                    kind="warning",
                    actor_id=active_piece.piece_id,
                    message=(
                        "No legal path fits the full move total, so the hunt "
                        "advances immediately."
                    ),
                )
            )
            _resolve_enemy_phase(next_state, events)
    else:
        events.append(
            EventLogEntry(
                kind="skip",
                actor_id=active_piece.piece_id,
                message="No move symbols were rolled, so only the snakes and foxes advance.",
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
    if active_piece is None or not active_piece.alive:
        return _error_result(next_state, "No active piece is available.")

    source = active_piece.node
    active_piece.node = destination
    next_state.turn_path.append(destination)
    if _is_outer_ring(next_state.board, destination):
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
                message=f"{active_piece.label} returned to the hub after touching the outer ring.",
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
        if not next_state.legal_moves:
            next_state.moves_remaining = 0
            events.append(
                EventLogEntry(
                    kind="warning",
                    message=(
                        "No legal continuation remains for the exact move count, "
                        "so the enemy phase begins."
                    ),
                )
            )
            _resolve_enemy_phase(next_state, events)
            _finalize_events(next_state, events)
            return ActionResult(
                ok=True,
                state=next_state,
                legal_moves=next_state.legal_moves,
                resolved_events=events,
                message="Player movement ended early.",
            )

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
    if active_piece is None:
        _advance_turn(state, events)
        return

    target_node = active_piece.node.model_copy(deep=True)

    for enemy_type, limit in (
        (EnemyType.FOX, state.pending_enemy_moves.foxes),
        (EnemyType.SNAKE, state.pending_enemy_moves.snakes),
    ):
        moved_enemy_ids: set[str] = set()
        moves_completed = 0
        while moves_completed < limit:
            ranked_moves, blocked_enemy = _rank_enemy_moves(
                state,
                enemy_type,
                target_node,
                moved_enemy_ids,
            )
            if not ranked_moves:
                if blocked_enemy is not None:
                    source = blocked_enemy.node
                    events.append(
                        EventLogEntry(
                            kind="enemy_hold",
                            actor_id=blocked_enemy.enemy_id,
                            enemy_type=blocked_enemy.enemy_type,
                            source=source,
                            destination=source,
                            message=(
                                f"{blocked_enemy.enemy_type.value.title()} {blocked_enemy.enemy_id} "
                                "could not move closer and held its ground."
                            ),
                        )
                    )
                break
            _, enemy, destination, captured_target = ranked_moves[0]
            moved_enemy_ids.add(enemy.enemy_id)
            source = enemy.node
            enemy.node = destination
            moves_completed += 1
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

            for captured_piece in _capture_active_piece_on_node(state, destination):
                events.append(
                    EventLogEntry(
                        kind="capture",
                        message=(
                            f"{enemy.enemy_type.value.title()} captured "
                            f"{captured_piece.label}."
                        ),
                        actor_id=enemy.enemy_id,
                        enemy_type=enemy.enemy_type,
                        source=source,
                        destination=destination,
                    )
                )

    state.pending_enemy_moves = PendingEnemyMoves()
    if not any(piece.alive for piece in state.pieces):
        state.phase = TurnPhase.GAME_LOST
        state.legal_moves = []
        events.append(
            EventLogEntry(
                kind="defeat",
                message="Both pieces were captured. The board belongs to the hunt.",
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
        state.active_piece_id = "black" if state.active_piece_id == "white" else "white"
        if state.active_piece_id not in living_piece_ids:
            state.active_piece_id = living_piece_ids[0]

    state.turn_number += 1
    state.phase = TurnPhase.WAITING_FOR_ROLL
    state.moves_remaining = 0
    state.pending_enemy_moves = PendingEnemyMoves()
    state.legal_moves = []
    active_piece = get_active_piece(state)
    state.turn_path = [active_piece.node] if active_piece else []
    if active_piece is not None:
        events.append(
            EventLogEntry(
                kind="turn_end",
                message=f"The next active piece is {PLAYER_COLORS[state.active_piece_id]}.",
                actor_id=state.active_piece_id,
            )
        )


def _generate_roll(state: GameState) -> DiceRoll:
    rng = random.Random(f"{state.seed}:{state.turn_number}:{state.roll_index}")
    active_piece = get_active_piece(state)
    use_enemy_bias = bool(active_piece and active_piece.reached_outer)
    faces = [_roll_face(rng.random(), use_enemy_bias) for _ in range(6)]
    if use_enemy_bias and active_piece is not None:
        faces = _decay_extra_black_pips(
            faces,
            rng,
            active_piece.post_outer_rolls + 1,
        )
    return DiceRoll(
        seed=state.seed,
        turn_number=state.turn_number,
        faces=faces,
        black_pips=sum(face == DieFace.BLACK_PIP for face in faces),
        red_triangles=sum(face == DieFace.RED_TRIANGLE for face in faces),
        green_squiggles=sum(face == DieFace.GREEN_SQUIGGLE for face in faces),
    )


def _roll_face(value: float, use_enemy_bias: bool) -> DieFace:
    if not use_enemy_bias:
        if value < (1 / 3):
            return DieFace.BLACK_PIP
        if value < (2 / 3):
            return DieFace.GREEN_SQUIGGLE
        return DieFace.RED_TRIANGLE

    if value < POST_OUTER_BLACK_PIP_CHANCE:
        return DieFace.BLACK_PIP
    if value < (5 / 8):
        return DieFace.GREEN_SQUIGGLE
    return DieFace.RED_TRIANGLE


def _active_piece_has_enemy_bias(state: GameState) -> bool:
    active_piece = get_active_piece(state)
    return bool(active_piece and active_piece.reached_outer)


def _decay_extra_black_pips(
    faces: list[DieFace],
    rng: random.Random,
    post_outer_roll_number: int,
) -> list[DieFace]:
    black_indices = [index for index, face in enumerate(faces) if face == DieFace.BLACK_PIP]
    if len(black_indices) <= 1:
        return faces

    survival_chance = POST_OUTER_EXTRA_BLACK_PIP_DECAY**post_outer_roll_number
    adjusted_faces = faces.copy()
    for index in black_indices[1:]:
        if rng.random() < survival_chance:
            continue
        adjusted_faces[index] = _enemy_face(rng.random())

    return adjusted_faces


def _enemy_face(value: float) -> DieFace:
    if value < 0.5:
        return DieFace.GREEN_SQUIGGLE
    return DieFace.RED_TRIANGLE


def _initial_enemies(board) -> list[EnemyState]:
    outer_ring = board.circle_count - 1
    enemies: list[EnemyState] = []
    for node_index in range(board.nodes_per_circle):
        enemy_type = EnemyType.FOX if node_index % 2 == 0 else EnemyType.SNAKE
        enemies.append(
            EnemyState(
                enemy_id=f"{enemy_type.value}-{node_index}",
                enemy_type=enemy_type,
                node=NodeId(circle_index=outer_ring, node_index=node_index),
            )
        )
    return enemies


def _occupied_player_and_enemy_keys(
    state: GameState, active_piece_id: str
) -> frozenset[tuple[int, int]]:
    occupied = {
        piece.node.key
        for piece in state.pieces
        if piece.alive and piece.piece_id != active_piece_id
    }
    occupied.update(enemy.node.key for enemy in state.enemies if enemy.active)
    return frozenset(occupied)


def _can_finish_exact_move(
    board,
    current: NodeId,
    steps_remaining: int,
    reached_outer: bool,
    occupied: frozenset[tuple[int, int]],
) -> bool:
    @cache
    def search(
        circle_index: int,
        node_index: int,
        remaining_steps: int,
        has_reached_outer: bool,
    ) -> bool:
        if remaining_steps == 0:
            return True

        node = NodeId(circle_index=circle_index, node_index=node_index)
        for candidate in neighbors(board, node):
            if candidate.key in occupied:
                continue

            candidate_reached_outer = has_reached_outer or _is_outer_ring(board, candidate)
            if candidate_reached_outer and candidate.circle_index == 0:
                return True

            if search(
                candidate.circle_index,
                candidate.node_index,
                remaining_steps - 1,
                candidate_reached_outer,
            ):
                return True

        return False

    return search(
        current.circle_index,
        current.node_index,
        steps_remaining,
        reached_outer,
    )


def _rank_enemy_moves(
    state: GameState,
    enemy_type: EnemyType,
    target: NodeId,
    moved_enemy_ids: set[str],
) -> tuple[
    list[tuple[tuple[int, int, int, int, int, str], EnemyState, NodeId, bool]],
    EnemyState | None,
]:
    candidates = [
        enemy
        for enemy in state.enemies
        if enemy.active and enemy.enemy_type == enemy_type and enemy.enemy_id not in moved_enemy_ids
    ]
    if not candidates:
        return [], None

    distance_map = _build_enemy_distance_map(
        state.board,
        target,
        _enemy_blocked_path_keys(state),
    )
    ranked_moves: list[tuple[tuple[int, int, int, int, int, str], EnemyState, NodeId, bool]] = []
    blocked_candidates: list[tuple[tuple[int, int, int, int, int, str], EnemyState]] = []

    for enemy in candidates:
        move_option = _enemy_move_option(state, enemy, target, distance_map)
        if move_option is None:
            blocked_candidates.append((_enemy_selection_key(enemy, target, None), enemy))
            continue

        total_distance, destination, captured_target = move_option
        ranked_moves.append(
            (
                _enemy_selection_key(enemy, target, total_distance),
                enemy,
                destination,
                captured_target,
            )
        )

    ranked_moves.sort(key=lambda item: item[0])
    blocked_candidates.sort(key=lambda item: item[0])
    blocked_enemy = blocked_candidates[0][1] if blocked_candidates else None
    return ranked_moves, blocked_enemy


def _enemy_selection_key(
    enemy: EnemyState,
    target: NodeId,
    distance: int | None,
) -> tuple[int, int, int, int, int, str]:
    if distance is None:
        distance = 1_000_000

    return (
        distance,
        0 if _same_spoke(enemy.node, target) else 1,
        0 if enemy.node.circle_index == target.circle_index and target.circle_index > 0 else 1,
        enemy.node.circle_index,
        enemy.node.node_index,
        enemy.enemy_id,
    )


def _enemy_move_option(
    state: GameState,
    enemy: EnemyState,
    target: NodeId,
    distance_map: dict[NodeKey, int],
) -> tuple[int, NodeId, bool] | None:
    occupied_enemy_keys = {
        other.node.key
        for other in state.enemies
        if other.active and other.enemy_id != enemy.enemy_id
    }
    blocked_player_keys = _inactive_player_keys(state)
    active_piece = get_active_piece(state)
    active_target_is_live = (
        active_piece is not None and active_piece.alive and active_piece.node == target
    )
    best_option: tuple[tuple[int, int, int, int, int, int, int], int, NodeId, bool] | None = None

    for candidate in neighbors(state.board, enemy.node):
        if candidate.key in occupied_enemy_keys:
            continue

        capture_target = active_target_is_live and candidate == target
        if candidate.key in blocked_player_keys and not capture_target:
            continue

        remaining_distance = 0 if capture_target else distance_map.get(candidate.key)
        if remaining_distance is None:
            continue

        total_distance = remaining_distance + 1
        option = (
            (
                0 if capture_target else 1,
                remaining_distance,
                0 if _same_spoke(candidate, target) else 1,
                0 if candidate.circle_index < enemy.node.circle_index else 1,
                0 if candidate.circle_index == enemy.node.circle_index else 1,
                candidate.circle_index,
                candidate.node_index,
            ),
            total_distance,
            candidate,
            capture_target,
        )
        if best_option is None or option[0] < best_option[0]:
            best_option = option

    if best_option is None:
        return None

    _, total_distance, destination, captured_target = best_option
    return total_distance, destination, captured_target


def _capture_active_piece_on_node(state: GameState, destination: NodeId) -> list[PieceState]:
    active_piece = get_active_piece(state)
    if active_piece is None or not active_piece.alive or active_piece.node != destination:
        return []

    active_piece.alive = False
    return [active_piece]


def _same_spoke(node: NodeId, target: NodeId) -> bool:
    return (
        node.circle_index > 0 and target.circle_index > 0 and node.node_index == target.node_index
    )


def _inactive_player_keys(state: GameState) -> frozenset[NodeKey]:
    return frozenset(
        piece.node.key
        for piece in state.pieces
        if piece.alive and piece.piece_id != state.active_piece_id
    )


def _enemy_blocked_path_keys(state: GameState) -> frozenset[NodeKey]:
    blocked_keys = set(_inactive_player_keys(state))
    blocked_keys.update(enemy.node.key for enemy in state.enemies if enemy.active)
    return frozenset(blocked_keys)


def _is_outer_ring(board, node: NodeId) -> bool:
    return node.circle_index == board.circle_count - 1


def _finalize_events(state: GameState, events: Iterable[EventLogEntry]) -> None:
    combined = state.event_log + list(events)
    state.event_log = combined[-14:]


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


def _dedupe_nodes(nodes: Iterable[NodeId]) -> list[NodeId]:
    ordered: list[NodeId] = []
    seen: set[tuple[int, int]] = set()
    for node in nodes:
        if node.key in seen:
            continue
        seen.add(node.key)
        ordered.append(node)
    return ordered


def _dedupe_keys(nodes: Iterable[NodeKey]) -> list[NodeKey]:
    ordered: list[NodeKey] = []
    seen: set[NodeKey] = set()
    for node in nodes:
        if node in seen:
            continue
        seen.add(node)
        ordered.append(node)
    return ordered


_cached_neighbor_keys(*_board_signature(CANONICAL_BOARD))
_cached_reverse_neighbor_keys(*_board_signature(CANONICAL_BOARD))
_cached_distances(*_board_signature(CANONICAL_BOARD))
