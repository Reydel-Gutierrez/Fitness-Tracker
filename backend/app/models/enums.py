from enum import StrEnum


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT = "prefer_not_to_say"


class PrimaryGoal(StrEnum):
    LOSE_FAT = "lose_fat"
    BUILD_MUSCLE = "build_muscle"
    BUILD_STRENGTH = "build_strength"
    RECOMPOSITION = "body_recomposition"
    ENDURANCE = "improve_endurance"
    GENERAL = "general_fitness"


class Experience(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class WeightUnit(StrEnum):
    LB = "lb"
    KG = "kg"


class LengthUnit(StrEnum):
    IN = "in"
    CM = "cm"


class ExerciseType(StrEnum):
    STRENGTH = "strength"
    BODYWEIGHT = "bodyweight"
    CARDIO = "cardio"
    TIMED = "timed"
    DISTANCE = "distance"


class GoalType(StrEnum):
    WEIGHT = "weight"
    BODY_MEASUREMENT = "body_measurement"
    WORKOUT_FREQUENCY = "workout_frequency"
    STRENGTH = "strength"
    CARDIO = "cardio"
    NUTRITION = "nutrition"
    CUSTOM = "custom"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SetType(StrEnum):
    WARMUP = "warmup"
    WORKING = "working"
    DROP = "drop"
    FAILURE = "failure"
    BACKOFF = "backoff"


class Effort(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class SessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SessionSource(StrEnum):
    SCHEDULED = "scheduled"
    QUICK = "quick"
    EXTRA = "extra"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class RecommendationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IGNORED = "ignored"
