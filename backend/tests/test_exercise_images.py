import io

from PIL import Image
from fastapi.testclient import TestClient

from app.services.exercise_images import (
    archive_image_relpath,
    generate_thumbnails,
    normalize_stored_path,
    resolve_image_url,
    resolve_image_urls,
)
from app.services.exercise_seed import seed_exercises, seed_images_from_item, serialize_exercise
from app.models.exercise import Exercise


def _jpeg_bytes(color=(30, 80, 120), size=(24, 24)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def test_archive_paths_match_free_exercise_db_layout():
    assert archive_image_relpath("free-exercise-db-main/exercises/Barbell_Squat/0.jpg") == "Barbell_Squat/0.jpg"
    assert archive_image_relpath("free-exercise-db-main/exercises/Barbell_Bench_Press_-_Medium_Grip/1.jpg") == (
        "Barbell_Bench_Press_-_Medium_Grip/1.jpg"
    )
    assert archive_image_relpath("free-exercise-db-main/exercises/Pullups.json") is None
    assert archive_image_relpath("free-exercise-db-main/exercises/../secret/0.jpg") is None


def test_seed_keeps_dataset_relative_paths_not_github():
    images = seed_images_from_item(
        {
            "images": [
                "Barbell_Curl/0.jpg",
                "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Barbell_Curl/1.jpg",
            ]
        }
    )
    assert images == ["Barbell_Curl/0.jpg"]


def test_missing_files_serialize_without_remote_urls(db, tmp_path, monkeypatch):
    monkeypatch.setenv("EXERCISE_IMAGES_DIR", str(tmp_path))
    row = Exercise(
        name="Barbell Squat",
        source="seed",
        source_id="Barbell_Squat",
        images=["Barbell_Squat/0.jpg", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Barbell_Squat/0.jpg"],
    )
    db.add(row)
    db.commit()
    data = serialize_exercise(row)
    assert data["images"] == []
    assert data["thumbnail"] is None
    assert all("github" not in value for value in data["images"])


def test_local_files_become_media_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("EXERCISE_IMAGES_DIR", str(tmp_path))
    full = tmp_path / "Barbell_Squat" / "0.jpg"
    full.parent.mkdir(parents=True)
    full.write_bytes(_jpeg_bytes())
    generate_thumbnails(tmp_path)
    assert resolve_image_url("Barbell_Squat/0.jpg") == "/media/exercises/Barbell_Squat/0.jpg"
    assert resolve_image_url("Barbell_Squat/0.jpg", thumb=True) == "/media/exercises/thumbs/Barbell_Squat/0.jpg"
    assert resolve_image_url("https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Barbell_Squat/0.jpg") == (
        "/media/exercises/Barbell_Squat/0.jpg"
    )
    assert resolve_image_urls(["https://example.com/nope.jpg"]) == []
    assert normalize_stored_path("https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/Pushups/0.jpg") == "Pushups/0.jpg"


def test_serialize_uses_thumbs_in_list_and_full_images_in_detail(db, tmp_path, monkeypatch):
    monkeypatch.setenv("EXERCISE_IMAGES_DIR", str(tmp_path))
    folder = tmp_path / "Barbell_Squat"
    folder.mkdir()
    (folder / "0.jpg").write_bytes(_jpeg_bytes())
    (folder / "1.jpg").write_bytes(_jpeg_bytes())
    generate_thumbnails(tmp_path)
    row = Exercise(
        name="Barbell Squat",
        source="seed",
        source_id="Barbell_Squat",
        images=["Barbell_Squat/0.jpg", "Barbell_Squat/1.jpg"],
        instructions=["Stand with the bar"],
    )
    db.add(row)
    db.commit()
    compact = serialize_exercise(row, compact=True)
    detail = serialize_exercise(row, compact=False)
    assert compact["thumbnail"] == "/media/exercises/thumbs/Barbell_Squat/0.jpg"
    assert compact["images"] == []
    assert compact["instructions"] == []
    assert detail["images"] == [
        "/media/exercises/Barbell_Squat/0.jpg",
        "/media/exercises/Barbell_Squat/1.jpg",
    ]
    assert detail["instructions"] == ["Stand with the bar"]


def test_seed_and_custom_upload(client: TestClient, db, tmp_path, monkeypatch):
    monkeypatch.setenv("EXERCISE_IMAGES_DIR", str(tmp_path))
    added = seed_exercises(
        db,
        [
            {
                "id": "Barbell_Squat",
                "name": "Barbell Squat",
                "equipment": "barbell",
                "primaryMuscles": ["quadriceps"],
                "category": "strength",
                "images": ["Barbell_Squat/0.jpg", "Barbell_Squat/1.jpg"],
            }
        ],
    )
    assert added == 1
    row = db.query(Exercise).filter(Exercise.source_id == "Barbell_Squat").one()
    assert row.images == ["Barbell_Squat/0.jpg", "Barbell_Squat/1.jpg"]

    token_res = client.post(
        "/api/auth/register",
        json={"email": "img@example.com", "password": "password123", "name": "Img"},
    )
    headers = {"Authorization": f"Bearer {token_res.json()['access_token']}"}
    created = client.post(
        "/api/exercises",
        headers=headers,
        json={"name": "Sled Push", "exercise_type": "strength", "primary_muscles": ["quadriceps"]},
    )
    assert created.status_code == 200
    eid = created.json()["id"]
    uploaded = client.post(
        f"/api/exercises/{eid}/image",
        headers=headers,
        files={"file": ("sled.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["images"][0].startswith("/media/exercises/custom/")
    assert body["thumbnail"]
    assert "github" not in body["thumbnail"]
    assert (tmp_path / "custom" / str(eid) / "0.jpg").is_file()

    listed = client.get("/api/exercises", headers=headers)
    assert listed.status_code == 200
    squat = next(item for item in listed.json() if item["name"] == "Barbell Squat")
    assert squat["instructions"] == []
    assert squat["images"] == []  # compact list omits full-size paths
    assert squat["thumbnail"] is None  # files not imported in this test
    recent = client.get("/api/exercises/recent", headers=headers)
    assert recent.status_code == 200
    assert recent.json() == []
