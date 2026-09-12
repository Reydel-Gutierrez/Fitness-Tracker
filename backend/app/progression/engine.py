"""Conservative deterministic progression recommendations. Never mutates workouts."""

from dataclasses import dataclass

from app.analytics.calculations import set_volume


@dataclass
class ProgressionResult:
    suggested_weight: float | None
    suggested_reps: int | None
    reason: str
    increment: float | None


def recommend_strength(
    *,
    completed_reps: list[int],
    target_reps: list[int | None],
    actual_rpe: list[float | None],
    target_rpe: list[float | None],
    last_weight: float | None,
    increment: float = 2.5,
) -> ProgressionResult:
    if last_weight is None or last_weight <= 0:
        return ProgressionResult(None, None, "Not enough data yet to calculate this trend.", None)
    if not completed_reps or not target_reps:
        return ProgressionResult(None, None, "Not enough data yet to calculate this trend.", None)

    paired = [
        (reps, tgt, rpe, trpe)
        for reps, tgt, rpe, trpe in zip(completed_reps, target_reps, actual_rpe, target_rpe)
        if tgt is not None
    ]
    if not paired:
        return ProgressionResult(last_weight, None, "Keep the same load until targets are defined.", 0)

    hit_all = all(reps >= tgt for reps, tgt, _, _ in paired)
    failed = sum(1 for reps, tgt, _, _ in paired if reps < tgt)
    rpes = [rpe for _, _, rpe, _ in paired if rpe is not None]
    target_rpes = [trpe for _, _, _, trpe in paired if trpe is not None]
    avg_rpe = sum(rpes) / len(rpes) if rpes else None
    avg_target_rpe = sum(target_rpes) / len(target_rpes) if target_rpes else None

    if hit_all and avg_rpe is not None and avg_target_rpe is not None and avg_rpe < avg_target_rpe - 0.4:
        nxt = round(last_weight + increment, 2)
        return ProgressionResult(
            nxt,
            None,
            f"All target reps were hit and average RPE ({avg_rpe:.1f}) was below target. Suggested next time: {nxt:g}.",
            increment,
        )
    if hit_all:
        nxt = round(last_weight + increment / 2, 2)
        return ProgressionResult(
            nxt,
            None,
            f"Target reps were achieved around the intended effort. Suggested next time: {nxt:g}.",
            increment / 2,
        )
    if failed >= max(1, len(paired) // 2):
        nxt = round(max(0, last_weight - increment), 2)
        return ProgressionResult(
            nxt,
            None,
            f"Target reps were missed on {failed} set(s). Suggested next time: {nxt:g}.",
            -increment,
        )
    return ProgressionResult(
        last_weight,
        None,
        f"Mixed results. Maintain {last_weight:g} next time.",
        0,
    )


def bodyweight_note(completed_reps: list[int], target_reps: list[int | None]) -> str:
    if not completed_reps or not target_reps:
        return "Not enough data yet to calculate this trend."
    hit = all(r >= (t or 0) for r, t in zip(completed_reps, target_reps) if t is not None)
    if hit:
        return "All target reps were achieved. Consider adding a small amount of load or 1–2 reps next time."
    return "Targets were not fully achieved. Repeat the same prescription next time."
