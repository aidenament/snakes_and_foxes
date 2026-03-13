from snakes_and_foxes.domain.engine import (
    _active_piece_has_enemy_bias,
    _decay_extra_black_pips,
    _rank_enemy_moves,
    _resolve_enemy_phase,
    _roll_face,
    apply_action,
    compute_legal_moves,
    create_new_game,
    move_enemy_one_step,
    neighbors,
    shortest_path_distance,
)
from snakes_and_foxes.domain.models import (
    DieFace,
    EnemyState,
    EnemyType,
    MoveAction,
    NewGameRequest,
    NodeId,
    PendingEnemyMoves,
    PieceState,
    RollAction,
    TurnPhase,
)


def test_center_neighbors_cover_first_ring():
    state = create_new_game(NewGameRequest(seed=7)).state
    neighbor_nodes = neighbors(state.board, NodeId(circle_index=0, node_index=0))
    assert len(neighbor_nodes) == state.board.nodes_per_circle
    assert neighbor_nodes[0] == NodeId(circle_index=1, node_index=0)
    assert neighbor_nodes[-1] == NodeId(circle_index=1, node_index=15)


def test_inner_ring_neighbors_follow_real_direction_rules():
    state = create_new_game(NewGameRequest(seed=11)).state
    neighbor_nodes = neighbors(state.board, NodeId(circle_index=1, node_index=0))
    assert neighbor_nodes == [
        NodeId(circle_index=1, node_index=15),
        NodeId(circle_index=0, node_index=0),
        NodeId(circle_index=2, node_index=0),
    ]


def test_outer_ring_is_bidirectional():
    state = create_new_game(NewGameRequest(seed=13)).state
    neighbor_nodes = neighbors(state.board, NodeId(circle_index=7, node_index=0))
    assert NodeId(circle_index=7, node_index=1) in neighbor_nodes
    assert NodeId(circle_index=7, node_index=15) in neighbor_nodes
    assert NodeId(circle_index=6, node_index=0) in neighbor_nodes


def test_shortest_path_uses_board_graph():
    state = create_new_game(NewGameRequest(seed=17)).state
    start = NodeId(circle_index=7, node_index=5)
    goal = NodeId(circle_index=0, node_index=0)
    assert shortest_path_distance(state.board, start, goal) == 7


def test_initial_enemy_layout_matches_outer_ring_setup():
    state = create_new_game(NewGameRequest(seed=23)).state
    assert len(state.enemies) == 16
    assert all(enemy.node.circle_index == 7 for enemy in state.enemies)
    for enemy in state.enemies:
        if enemy.node.node_index % 2 == 0:
            assert enemy.enemy_type == EnemyType.FOX
        else:
            assert enemy.enemy_type == EnemyType.SNAKE


def test_new_game_starts_with_white_active_and_both_pieces_in_hub():
    state = create_new_game(NewGameRequest(seed=101)).state
    assert state.active_piece_id == "white"
    assert state.phase == TurnPhase.WAITING_FOR_ROLL
    assert state.legal_moves == []
    assert [piece.node for piece in state.pieces] == [
        NodeId(circle_index=0, node_index=0),
        NodeId(circle_index=0, node_index=0),
    ]


def test_roll_faces_are_fair_before_any_piece_reaches_outer_ring():
    assert _roll_face(0.00, False).value == "black_pip"
    assert _roll_face(0.3332, False).value == "black_pip"
    assert _roll_face(0.3334, False).value == "green_squiggle"
    assert _roll_face(0.6665, False).value == "green_squiggle"
    assert _roll_face(0.6667, False).value == "red_triangle"


def test_roll_faces_favor_enemies_after_outer_ring_is_reached():
    assert _roll_face(0.00, True).value == "black_pip"
    assert _roll_face(0.2499, True).value == "black_pip"
    assert _roll_face(0.25, True).value == "green_squiggle"
    assert _roll_face(0.6249, True).value == "green_squiggle"
    assert _roll_face(0.625, True).value == "red_triangle"


class StubRandom:
    def __init__(self, values: list[float]):
        self._values = iter(values)

    def random(self) -> float:
        return next(self._values)


def test_extra_black_pips_decay_after_reaching_outer_ring():
    faces = [
        DieFace.BLACK_PIP,
        DieFace.BLACK_PIP,
        DieFace.BLACK_PIP,
        DieFace.GREEN_SQUIGGLE,
        DieFace.RED_TRIANGLE,
        DieFace.BLACK_PIP,
    ]
    result = _decay_extra_black_pips(faces, StubRandom([0.2, 0.95, 0.3, 0.99, 0.8]), 2)

    assert result == [
        DieFace.BLACK_PIP,
        DieFace.BLACK_PIP,
        DieFace.GREEN_SQUIGGLE,
        DieFace.GREEN_SQUIGGLE,
        DieFace.RED_TRIANGLE,
        DieFace.RED_TRIANGLE,
    ]


def test_enemy_bias_is_based_only_on_active_piece():
    state = create_new_game(NewGameRequest(seed=103)).state
    state.active_piece_id = "white"
    state.pieces[0].reached_outer = False
    state.pieces[1].reached_outer = True

    assert _active_piece_has_enemy_bias(state) is False

    state.active_piece_id = "black"
    assert _active_piece_has_enemy_bias(state) is True


def test_first_turn_rerolls_until_moves_exist():
    state = create_new_game(NewGameRequest(seed=2)).state
    result = apply_action(state, RollAction(type="roll"))
    assert result.state.phase == TurnPhase.PLAYER_MOVING
    assert result.state.moves_remaining > 0
    assert result.state.pieces[0].turns_taken == 1


def test_post_outer_roll_counter_advances_for_active_piece():
    state = create_new_game(NewGameRequest(seed=31)).state
    state.pieces[0].reached_outer = True
    state.pieces[0].turns_taken = 1

    result = apply_action(state, RollAction(type="roll"))

    assert result.state.pieces[0].post_outer_rolls == 1
    assert result.state.pieces[1].post_outer_rolls == 0


def test_player_can_reverse_on_spokes_but_not_against_ring_direction():
    state = create_new_game(NewGameRequest(seed=29)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.active_piece_id = "white"
    state.moves_remaining = 2
    state.pieces[0].node = NodeId(circle_index=2, node_index=1)
    state.pieces[1].node = NodeId(circle_index=2, node_index=8)
    state.turn_path = [NodeId(circle_index=1, node_index=1), NodeId(circle_index=2, node_index=1)]
    state.enemies = []

    legal_moves = compute_legal_moves(state)

    assert NodeId(circle_index=1, node_index=1) in legal_moves
    assert NodeId(circle_index=3, node_index=1) in legal_moves
    assert NodeId(circle_index=2, node_index=2) in legal_moves
    assert NodeId(circle_index=2, node_index=0) not in legal_moves


def test_enemy_capture_takes_priority():
    state = create_new_game(NewGameRequest(seed=5)).state
    target = NodeId(circle_index=4, node_index=1)
    enemy = EnemyState(
        enemy_id="fox-1",
        enemy_type=EnemyType.FOX,
        node=NodeId(circle_index=5, node_index=1),
    )
    destination, captured = move_enemy_one_step(state, enemy, target)
    assert captured is True
    assert destination == target


def test_enemy_targets_active_piece_only():
    state = create_new_game(NewGameRequest(seed=19)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.moves_remaining = 1
    state.active_piece_id = "white"
    state.pieces = [
        PieceState(
            piece_id="white",
            label="White",
            node=NodeId(circle_index=3, node_index=0),
            reached_outer=True,
        ),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=5, node_index=5)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-1",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=5, node_index=1),
        )
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=1, snakes=0)
    state.turn_path = [NodeId(circle_index=3, node_index=0)]
    state.legal_moves = [NodeId(circle_index=4, node_index=0)]

    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=4, node_index=0)),
    )

    assert result.state.pieces[1].alive is True
    assert result.state.enemies[0].node == NodeId(circle_index=5, node_index=0)


def test_enemy_cannot_step_onto_inactive_player_space():
    state = create_new_game(NewGameRequest(seed=53)).state
    state.active_piece_id = "white"
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=2, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=3, node_index=0)),
    ]
    enemy = EnemyState(
        enemy_id="snake-1",
        enemy_type=EnemyType.SNAKE,
        node=NodeId(circle_index=4, node_index=0),
    )

    destination, captured = move_enemy_one_step(state, enemy, state.pieces[0].node)

    assert captured is False
    assert destination == NodeId(circle_index=5, node_index=0)
    assert state.pieces[1].alive is True


def test_enemy_takes_required_detour_around_blockers():
    state = create_new_game(NewGameRequest(seed=61)).state
    state.active_piece_id = "white"
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=1, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=0, node_index=0)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-0",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=2),
        ),
        EnemyState(
            enemy_id="snake-1",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=1, node_index=1),
        ),
        EnemyState(
            enemy_id="fox-2",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=3),
        ),
    ]

    destination, captured = move_enemy_one_step(state, state.enemies[0], state.pieces[0].node)

    assert captured is False
    assert destination == NodeId(circle_index=2, node_index=2)


def test_enemy_order_uses_occupancy_aware_distance():
    state = create_new_game(NewGameRequest(seed=67)).state
    state.active_piece_id = "white"
    target = NodeId(circle_index=1, node_index=0)
    state.pieces = [
        PieceState(piece_id="white", label="White", node=target),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=0, node_index=0)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-a",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=3),
        ),
        EnemyState(
            enemy_id="fox-b",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=2, node_index=1),
        ),
    ]

    ranked_moves, blocked_enemy = _rank_enemy_moves(state, EnemyType.FOX, target, set())

    assert blocked_enemy is None
    assert ranked_moves[0][1].enemy_id == "fox-b"
    assert ranked_moves[0][2] == NodeId(circle_index=1, node_index=1)


def test_enemy_order_recalculates_after_each_move():
    state = create_new_game(NewGameRequest(seed=71)).state
    state.active_piece_id = "white"
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=2, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=0, node_index=0)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-0",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=1),
        ),
        EnemyState(
            enemy_id="fox-1",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=2),
        ),
        EnemyState(
            enemy_id="fox-2",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=13),
        ),
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=2, snakes=0)

    events = []
    _resolve_enemy_phase(state, events)

    move_events = [event for event in events if event.kind == "enemy_move"]

    assert [event.actor_id for event in move_events] == ["fox-0", "fox-2"]
    assert state.enemies[0].node == NodeId(circle_index=1, node_index=0)
    assert state.enemies[1].node == NodeId(circle_index=1, node_index=2)
    assert state.enemies[2].node == NodeId(circle_index=2, node_index=13)


def test_foxes_move_before_snakes_and_continue_after_capture():
    state = create_new_game(NewGameRequest(seed=37)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.active_piece_id = "white"
    state.moves_remaining = 1
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=4, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=1, node_index=8)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-0",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=7, node_index=0),
        ),
        EnemyState(
            enemy_id="snake-1",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=6, node_index=0),
        ),
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=1, snakes=1)
    state.turn_path = [NodeId(circle_index=4, node_index=0)]
    state.legal_moves = [NodeId(circle_index=5, node_index=0)]

    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=5, node_index=0)),
    )

    assert result.state.pieces[0].alive is False
    assert result.state.enemies[0].node == NodeId(circle_index=7, node_index=1)
    assert result.state.enemies[1].node == NodeId(circle_index=5, node_index=0)
    assert result.resolved_events[1].kind == "enemy_move"
    assert result.resolved_events[2].kind == "enemy_move"


def test_blocked_enemy_type_emits_one_hold_event_for_resolution_pass():
    state = create_new_game(NewGameRequest(seed=73)).state
    state.active_piece_id = "white"
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=1, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=0, node_index=0)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-0",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=1, node_index=2),
        ),
        EnemyState(
            enemy_id="snake-1",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=1, node_index=1),
        ),
        EnemyState(
            enemy_id="snake-2",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=2, node_index=2),
        ),
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=2, snakes=0)

    events = []
    _resolve_enemy_phase(state, events)

    hold_events = [event for event in events if event.kind == "enemy_hold"]

    assert len(hold_events) == 1
    assert hold_events[0].actor_id == "fox-0"


def test_only_one_enemy_can_capture_active_piece_on_same_turn():
    state = create_new_game(NewGameRequest(seed=59)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.active_piece_id = "white"
    state.moves_remaining = 1
    state.pieces = [
        PieceState(piece_id="white", label="White", node=NodeId(circle_index=3, node_index=0)),
        PieceState(piece_id="black", label="Black", node=NodeId(circle_index=1, node_index=8)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="snake-0",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=5, node_index=0),
        ),
        EnemyState(
            enemy_id="snake-1",
            enemy_type=EnemyType.SNAKE,
            node=NodeId(circle_index=6, node_index=0),
        ),
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=0, snakes=2)
    state.turn_path = [NodeId(circle_index=3, node_index=0)]
    state.legal_moves = [NodeId(circle_index=4, node_index=0)]

    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=4, node_index=0)),
    )

    capture_events = [event for event in result.resolved_events if event.kind == "capture"]

    assert result.state.pieces[0].alive is False
    assert result.state.enemies[0].node == NodeId(circle_index=4, node_index=0)
    assert result.state.enemies[1].node == NodeId(circle_index=5, node_index=0)
    assert len(capture_events) == 1


def test_either_piece_can_win():
    state = create_new_game(NewGameRequest(seed=41)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.moves_remaining = 2
    state.active_piece_id = "black"
    state.pieces[1].node = NodeId(circle_index=1, node_index=0)
    state.pieces[1].reached_outer = True
    state.pieces[0].node = NodeId(circle_index=5, node_index=3)
    state.enemies = []
    state.turn_path = [NodeId(circle_index=2, node_index=0), NodeId(circle_index=1, node_index=0)]

    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=0, node_index=0)),
    )

    assert result.state.phase == TurnPhase.GAME_WON
    assert result.state.winner_piece_id == "black"


def test_last_surviving_piece_remains_active():
    state = create_new_game(NewGameRequest(seed=43)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.active_piece_id = "white"
    state.moves_remaining = 1
    state.pieces[0].node = NodeId(circle_index=4, node_index=0)
    state.pieces[1].alive = False
    state.pieces[1].node = NodeId(circle_index=2, node_index=0)
    state.turn_path = [NodeId(circle_index=4, node_index=0)]
    state.enemies = []

    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=5, node_index=0)),
    )

    assert result.state.phase == TurnPhase.WAITING_FOR_ROLL
    assert result.state.active_piece_id == "white"


def test_active_piece_alternates_white_then_black_then_white():
    first_state = create_new_game(NewGameRequest(seed=47)).state
    first_state.phase = TurnPhase.PLAYER_MOVING
    first_state.active_piece_id = "white"
    first_state.moves_remaining = 1
    first_state.enemies = []
    first_state.turn_path = [NodeId(circle_index=0, node_index=0)]
    first_state.legal_moves = [NodeId(circle_index=1, node_index=0)]

    after_white = apply_action(
        first_state,
        MoveAction(type="move", destination=NodeId(circle_index=1, node_index=0)),
    ).state

    assert after_white.active_piece_id == "black"
    assert after_white.phase == TurnPhase.WAITING_FOR_ROLL

    after_white.phase = TurnPhase.PLAYER_MOVING
    after_white.moves_remaining = 1
    after_white.enemies = []
    after_white.turn_path = [NodeId(circle_index=0, node_index=0)]
    after_white.legal_moves = [NodeId(circle_index=1, node_index=1)]

    after_black = apply_action(
        after_white,
        MoveAction(type="move", destination=NodeId(circle_index=1, node_index=1)),
    ).state

    assert after_black.active_piece_id == "white"
    assert after_black.phase == TurnPhase.WAITING_FOR_ROLL
