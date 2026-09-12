from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.analytics.calculations import epley_1rm, pct_change, set_volume
from app.models.profile import UserProfile
from app.progression.engine import recommend_strength
from app.program_generator.generator import generate_program


def auth(client: TestClient) -> str:
    res = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123", "name": "Test User"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_volume_and_1rm():
    assert set_volume(100, 5) == 500
    assert set_volume(None, 5) == 0
    assert epley_1rm(100, 1) == 100
    assert round(epley_1rm(100, 5) or 0, 2) == 116.67
    assert epley_1rm(100, 20) is None
    assert round(pct_change(107.2, 100) or 0, 1) == 7.2


def test_measurement_changes():
    assert pct_change(174.2, 175) is not None
    assert round(pct_change(174.2, 175) or 0, 2) == -0.46


def test_progression_increase_when_easy():
    result = recommend_strength(
        completed_reps=[8, 8, 8],
        target_reps=[8, 8, 8],
        actual_rpe=[6, 6, 6],
        target_rpe=[8, 8, 8],
        last_weight=80,
        increment=2.5,
    )
    assert result.suggested_weight == 82.5


def test_progression_deload_when_failing():
    result = recommend_strength(
        completed_reps=[4, 4, 3],
        target_reps=[8, 8, 8],
        actual_rpe=[9, 9, 10],
        target_rpe=[7, 7, 7],
        last_weight=80,
        increment=2.5,
    )
    assert result.suggested_weight == 77.5


def test_program_generation(db):
    from app.models.exercise import Exercise
    from app.models.user import User
    from app.lib.security import hash_password

    user = User(email="p@x.com", username="p", name="P", password_hash=hash_password("password123"))
    db.add(user)
    db.flush()
    profile = UserProfile(
        user_id=user.id,
        primary_goal="build_strength",
        experience="intermediate",
        days_per_week=4,
        preferred_days=[0, 1, 3, 5],
        typical_duration_minutes=60,
        available_locations=["gym"],
        available_equipment=["barbell", "dumbbells"],
    )
    db.add(profile)
    for name in ["Barbell Squat", "Barbell Deadlift", "Barbell Bench Press - Medium Grip", "Bent Over Barbell Row"]:
        db.add(
            Exercise(
                name=name,
                source="seed",
                source_id=name,
                exercise_type="strength",
                equipment=["barbell"],
                primary_muscles=["quadriceps"],
            )
        )
    db.commit()
    program = generate_program(db, user.id, profile)
    assert len(program.workouts) == 4
    assert program.workouts[0].exercises


def test_register_and_measurement_and_nutrition(client):
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/api/profile",
        headers=headers,
        json={
            "height": 70,
            "weight_unit": "lb",
            "length_unit": "in",
            "primary_goal": "build_strength",
            "experience": "intermediate",
            "days_per_week": 4,
            "preferred_days": [0, 1, 3, 5],
            "typical_duration_minutes": 60,
            "available_locations": ["gym"],
            "available_equipment": ["barbell"],
            "onboarding_completed": True,
        },
    )
    m1 = client.post("/api/body", headers=headers, json={"weight": 180, "waist": 34})
    assert m1.status_code == 200
    m2 = client.post("/api/body", headers=headers, json={"weight": 178, "waist": 33.5})
    assert m2.status_code == 200
    assert m2.json()["change"]["weight"] == -2
    client.put("/api/nutrition/target", headers=headers, json={"calories": 2400, "protein_g": 180, "carbs_g": 250, "fat_g": 70})
    day = client.post(
        "/api/nutrition/entries",
        headers=headers,
        json={"name": "Chicken", "calories": 400, "protein_g": 50, "carbs_g": 0, "fat_g": 8, "meal": "lunch"},
    )
    assert day.status_code == 200
    assert day.json()["totals"]["protein_g"] == 50
    assert day.json()["totals"]["calories"] == 400


def test_custom_exercise_workout_session_and_report(client, db):
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    from app.models.exercise import Exercise

    db.add(Exercise(name="Pullups", source="seed", source_id="Pullups", exercise_type="bodyweight", equipment=["body only"]))
    db.add(Exercise(name="Pushups", source="seed", source_id="Pushups", exercise_type="bodyweight", equipment=["body only"]))
    db.add(Exercise(name="Parallel Bar Dip", source="seed", source_id="Parallel_Bar_Dip", exercise_type="bodyweight", equipment=["other"]))
    db.commit()

    peloton = client.post(
        "/api/exercises",
        headers=headers,
        json={"name": "Peloton Ride", "exercise_type": "cardio", "equipment": ["peloton"], "primary_muscles": ["quadriceps"]},
    )
    assert peloton.status_code == 200
    pid = peloton.json()["id"]
    exercises = client.get("/api/exercises", headers=headers).json()
    pull = next(e for e in exercises if e["name"] == "Pullups")
    push = next(e for e in exercises if e["name"] == "Pushups")
    dip = next(e for e in exercises if e["name"] == "Parallel Bar Dip")

    workout = client.post(
        "/api/workouts",
        headers=headers,
        json={
            "name": "HOME UPPER BODY",
            "estimated_duration_minutes": 45,
            "exercises": [
                {
                    "exercise_id": pull["id"],
                    "rest_seconds": 90,
                    "sets": [
                        {"set_number": 1, "target_reps": 8, "min_reps": 6, "max_reps": 10, "target_effort": "medium", "target_rpe": 7, "rest_seconds": 90}
                    ]
                    * 0
                    + [
                        {"set_number": i, "target_reps": 8, "min_reps": 6, "max_reps": 10, "target_effort": "medium", "target_rpe": 7, "rest_seconds": 90}
                        for i in range(1, 5)
                    ],
                },
                {
                    "exercise_id": push["id"],
                    "sets": [{"set_number": i, "target_reps": 15, "rest_seconds": 60} for i in range(1, 5)],
                },
                {
                    "exercise_id": dip["id"],
                    "sets": [{"set_number": i, "target_reps": 10, "min_reps": 8, "max_reps": 12, "rest_seconds": 90} for i in range(1, 4)],
                },
                {
                    "exercise_id": pid,
                    "sets": [{"set_number": 1, "target_duration_seconds": 1200, "target_effort": "medium"}],
                },
            ],
        },
    )
    assert workout.status_code == 200, workout.text
    tid = workout.json()["id"]
    session = client.post("/api/sessions", headers=headers, json={"template_id": tid})
    assert session.status_code == 200, session.text
    sid = session.json()["id"]
    first_set = session.json()["exercises"][0]["sets"][0]
    patched = client.patch(
        f"/api/sessions/{sid}/sets/{first_set['id']}",
        headers=headers,
        json={"reps": 8, "rpe": 7, "completed": True},
    )
    assert patched.status_code == 200
    assert patched.json()["exercises"][0]["sets"][0]["completed"] is True
    cardio_ex = next(e for e in patched.json()["exercises"] if e["exercise"]["name"] == "Peloton Ride")
    client.patch(
        f"/api/sessions/{sid}/exercises/{cardio_ex['id']}/cardio",
        headers=headers,
        json={"duration_seconds": 1472, "distance_m": 12000, "rpe": 7, "completed": True},
    )
    done = client.post(f"/api/sessions/{sid}/finish", headers=headers)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    history = client.get("/api/sessions", headers=headers).json()
    assert history[0]["status"] == "completed"
    report = client.get("/api/reports/weekly", headers=headers)
    assert report.status_code == 200
    assert report.json()["training"]["completed"] >= 1
    assert any("completed" in s.lower() for s in report.json()["sentences"])


def test_delete_program_removes_its_workouts(client, db):
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    from app.models.exercise import Exercise

    db.add(
        Exercise(
            name="Squat",
            source="seed",
            source_id="Squat",
            exercise_type="strength",
            equipment=["barbell"],
            primary_muscles=["quadriceps"],
        )
    )
    db.commit()
    squat = next(e for e in client.get("/api/exercises", headers=headers).json() if e["name"] == "Squat")

    def make_workout(name: str) -> int:
        res = client.post(
            "/api/workouts",
            headers=headers,
            json={
                "name": name,
                "exercises": [{"exercise_id": squat["id"], "sets": [{"set_number": 1, "target_reps": 5}]}],
            },
        )
        assert res.status_code == 200, res.text
        return res.json()["id"]

    owned = make_workout("Program Day")
    shared = make_workout("Shared Day")
    leftover = make_workout("Keep Me")

    program = client.post(
        "/api/programs",
        headers=headers,
        json={
            "name": "Strength Block",
            "workouts": [
                {"template_id": owned, "weekday": 0, "position": 0},
                {"template_id": shared, "weekday": 2, "position": 1},
            ],
        },
    )
    assert program.status_code == 200, program.text
    pid = program.json()["id"]

    other = client.post(
        "/api/programs",
        headers=headers,
        json={
            "name": "Keep This Program",
            "is_active": False,
            "workouts": [{"template_id": shared, "weekday": 1, "position": 0}],
        },
    )
    assert other.status_code == 200, other.text

    session = client.post("/api/sessions", headers=headers, json={"template_id": owned, "program_id": pid})
    assert session.status_code == 200, session.text
    sid = session.json()["id"]

    deleted = client.delete(f"/api/programs/{pid}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert client.get(f"/api/programs/{pid}", headers=headers).status_code == 404
    assert client.get(f"/api/workouts/{owned}", headers=headers).status_code == 404
    assert client.get(f"/api/workouts/{shared}", headers=headers).status_code == 200
    assert client.get(f"/api/workouts/{leftover}", headers=headers).status_code == 200
    kept = client.get(f"/api/sessions/{sid}", headers=headers)
    assert kept.status_code == 200
    assert kept.json()["template_id"] is None
    assert kept.json()["program_id"] is None
    remaining = client.get("/api/programs", headers=headers).json()
    assert [p["name"] for p in remaining] == ["Keep This Program"]


def test_program_uses_workout_name_and_can_add_existing_workout(client, db):
    token = auth(client)
    headers = {"Authorization": f"Bearer {token}"}
    from app.models.exercise import Exercise

    db.add(
        Exercise(
            name="Row",
            source="seed",
            source_id="Row",
            exercise_type="strength",
            equipment=["dumbbells"],
            primary_muscles=["lats"],
        )
    )
    db.commit()
    row = next(e for e in client.get("/api/exercises", headers=headers).json() if e["name"] == "Row")

    def make_workout(name: str) -> tuple[int, dict]:
        res = client.post(
            "/api/workouts",
            headers=headers,
            json={
                "name": name,
                "exercises": [{"exercise_id": row["id"], "sets": [{"set_number": 1, "target_reps": 10}]}],
            },
        )
        assert res.status_code == 200, res.text
        return res.json()["id"], res.json()

    first_id, first = make_workout("Monday — Push")
    extra_id, _ = make_workout("Legs @ Home")
    program = client.post(
        "/api/programs",
        headers=headers,
        json={
            "name": "Home block",
            "workouts": [{"template_id": first_id, "weekday": 0, "position": 0, "name_override": "Monday — Push"}],
        },
    )
    assert program.status_code == 200, program.text
    pid = program.json()["id"]
    renamed = client.put(
        f"/api/workouts/{first_id}",
        headers=headers,
        json={
            "name": "Back + Biceps + Core @ Home",
            "notes": first.get("notes"),
            "estimated_duration_minutes": first.get("estimated_duration_minutes"),
            "exercises": [
                {"exercise_id": row["id"], "sets": [{"set_number": 1, "target_reps": 10}]}
            ],
        },
    )
    assert renamed.status_code == 200, renamed.text
    shown = client.get(f"/api/programs/{pid}", headers=headers).json()
    assert shown["workouts"][0]["name_override"] == "Monday — Push"
    assert shown["workouts"][0]["template"]["name"] == "Back + Biceps + Core @ Home"

    added = client.put(
        f"/api/programs/{pid}",
        headers=headers,
        json={
            "name": "Home block",
            "notes": None,
            "is_active": True,
            "workouts": [
                {"template_id": first_id, "weekday": 0, "position": 0},
                {"template_id": extra_id, "weekday": 2, "position": 1},
            ],
        },
    )
    assert added.status_code == 200, added.text
    names = [w["template"]["name"] for w in added.json()["workouts"]]
    assert names == ["Back + Biceps + Core @ Home", "Legs @ Home"]
    assert [w["weekday"] for w in added.json()["workouts"]] == [0, 2]
