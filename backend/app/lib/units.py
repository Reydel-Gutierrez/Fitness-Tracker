LB_PER_KG = 2.2046226218
IN_PER_CM = 1 / 2.54


def kg_to_display(kg: float | None, unit: str) -> float | None:
    if kg is None:
        return None
    return round(kg * LB_PER_KG, 2) if unit == "lb" else round(kg, 2)


def display_to_kg(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    return value / LB_PER_KG if unit == "lb" else value


def cm_to_display(cm: float | None, unit: str) -> float | None:
    if cm is None:
        return None
    return round(cm * IN_PER_CM, 2) if unit == "in" else round(cm, 2)


def display_to_cm(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    return value / IN_PER_CM if unit == "in" else value


def m_to_display_km(meters: float | None) -> float | None:
    if meters is None:
        return None
    return round(meters / 1000, 3)


def pace_sec_per_km(duration_seconds: int | None, distance_m: float | None) -> float | None:
    if not duration_seconds or not distance_m or distance_m <= 0:
        return None
    return duration_seconds / (distance_m / 1000)
