"""Deterministic training calculations. Epley 1RM: weight * (1 + reps / 30)."""

EPLEY_MAX_REPS = 12


def set_volume(weight: float | None, reps: int | None) -> float:
    if weight is None or reps is None or weight < 0 or reps < 0:
        return 0.0
    return weight * reps


def epley_1rm(weight: float, reps: int) -> float | None:
    """Estimated 1RM using Epley. Returns None when reps are outside a reliable range."""
    if weight <= 0 or reps <= 0 or reps > EPLEY_MAX_REPS:
        return None
    if reps == 1:
        return float(weight)
    return weight * (1 + reps / 30)


def change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return current - previous


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / previous) * 100


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < min(3, window):
        return None
    sample = values[-window:]
    return sum(sample) / len(sample)


def linear_trend(values: list[float]) -> float | None:
    """Simple slope of y over equally spaced x. Positive = increasing."""
    n = len(values)
    if n < 2:
        return None
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return None
    return num / den
