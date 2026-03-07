from snakes_and_foxes.domain.engine import (
    apply_action,
    compute_legal_moves,
    create_new_game,
    move_enemy_one_step,
    neighbors,
    shortest_path_distance,
)
from snakes_and_foxes.domain.models import (
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


def test_shortest_path_uses_board_graph():
    state = create_new_game(NewGameRequest(seed=11)).state
    start = NodeId(circle_index=5, node_index=5)
    goal = NodeId(circle_index=0, node_index=0)
    assert shortest_path_distance(state.board, start, goal) == 5


def test_compute_legal_moves_blocks_enemy_nodes():
    state = create_new_game(NewGameRequest(seed=3)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.moves_remaining = 1
    state.pieces[0].node = NodeId(circle_index=4, node_index=1)
    state.active_piece_id = "sun"
    state.enemies = [
        EnemyState(
            enemy_id="fox-1",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=5, node_index=1),
        )
    ]
    legal_moves = compute_legal_moves(state)
    assert NodeId(circle_index=5, node_index=1) not in legal_moves


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
    state.active_piece_id = "sun"
    state.pieces = [
        PieceState(
            piece_id="sun",
            label="Sun",
            node=NodeId(circle_index=3, node_index=0),
            reached_outer=True,
        ),
        PieceState(piece_id="moon", label="Moon", node=NodeId(circle_index=5, node_index=0)),
    ]
    state.enemies = [
        EnemyState(
            enemy_id="fox-1",
            enemy_type=EnemyType.FOX,
            node=NodeId(circle_index=5, node_index=1),
        )
    ]
    state.pending_enemy_moves = PendingEnemyMoves(foxes=1, snakes=0)
    state.legal_moves = [NodeId(circle_index=4, node_index=0)]
    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=4, node_index=0)),
    )
    assert result.state.pieces[1].alive is True
    assert result.state.enemies[0].node == NodeId(circle_index=4, node_index=1)


def test_active_piece_switches_after_roll_without_moves():
    state = create_new_game(NewGameRequest(seed=2)).state
    result = apply_action(state, RollAction(type="roll"))
    if result.state.phase == TurnPhase.PLAYER_MOVING:
        move_target = result.state.legal_moves[0]
        result = apply_action(result.state, MoveAction(type="move", destination=move_target))
        while result.state.phase == TurnPhase.PLAYER_MOVING:
            result = apply_action(
                result.state,
                MoveAction(type="move", destination=result.state.legal_moves[0]),
            )
    assert result.state.phase in {
        TurnPhase.WAITING_FOR_ROLL,
        TurnPhase.GAME_WON,
        TurnPhase.GAME_LOST,
    }
    if result.state.phase == TurnPhase.WAITING_FOR_ROLL:
        assert result.state.active_piece_id == "moon"


def test_either_piece_can_win():
    state = create_new_game(NewGameRequest(seed=17)).state
    state.phase = TurnPhase.PLAYER_MOVING
    state.moves_remaining = 1
    state.active_piece_id = "moon"
    state.pieces[1].node = NodeId(circle_index=1, node_index=0)
    state.pieces[1].reached_outer = True
    state.legal_moves = [NodeId(circle_index=0, node_index=0)]
    result = apply_action(
        state,
        MoveAction(type="move", destination=NodeId(circle_index=0, node_index=0)),
    )
    assert result.state.phase == TurnPhase.GAME_WON
    assert result.state.winner_piece_id == "moon"
