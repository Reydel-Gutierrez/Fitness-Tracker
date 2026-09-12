# Data model

SQLAlchemy models in `backend/app/models`.

Core tables:

- `users`, `user_profiles`
- `body_measurements` — append-only history
- `goals`
- `exercises` — seed (`user_id` null) and custom (`source=custom`). Seed image paths are dataset-relative (`Barbell_Squat/0.jpg`); files live in `data/exercise-images` and are served from `/media/exercises`.
- `workout_templates`, `workout_template_exercises`, `prescribed_sets`
- `programs`, `program_workouts` — templates referenced by weekday
- `workout_sessions`, `performed_exercises`, `performed_sets`, `cardio_performances`
  Session rows snapshot prescription fields so later template edits never rewrite history.
- `foods`, `nutrition_entries`, `nutrition_targets`
- `weekly_checkins`, `weekly_reports`
- `progression_recommendations` — suggestions only; never auto-applied

Indexes exist on user + date fields used by history and analytics.
