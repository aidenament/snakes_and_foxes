from __future__ import annotations

from statistics import mean
from time import perf_counter

from snakes_and_foxes.domain.engine import apply_action, create_new_game
from snakes_and_foxes.domain.models import MoveAction, NewGameRequest, RollAction, TurnPhase

RUNS = 200


def play_opening_turn(seed: int) -> float:
    state = create_new_game(NewGameRequest(seed=seed)).state
    started = perf_counter()
    result = apply_action(state, RollAction(type="roll"))
    while result.state.phase == TurnPhase.PLAYER_MOVING and result.state.legal_moves:
        result = apply_action(
            result.state,
            MoveAction(type="move", destination=result.state.legal_moves[0]),
        )
    return (perf_counter() - started) * 1000


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * ratio))
    return ordered[index]


def main() -> None:
    samples = [play_opening_turn(seed) for seed in range(1, RUNS + 1)]
    print(f"runs={RUNS}")
    print(f"mean_ms={mean(samples):.3f}")
    print(f"p50_ms={percentile(samples, 0.50):.3f}")
    print(f"p95_ms={percentile(samples, 0.95):.3f}")
    print(f"max_ms={max(samples):.3f}")


if __name__ == "__main__":
    main()
