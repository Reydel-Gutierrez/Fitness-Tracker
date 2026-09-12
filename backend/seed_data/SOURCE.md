Exercise seed source
====================

Built-in exercises are imported from the public-domain
[free-exercise-db](https://github.com/yuhonas/free-exercise-db) dataset.

The JSON snapshot is vendored at `backend/seed_data/exercises.json` so the app
does not read GitHub at request time.

Image paths in that JSON are dataset-relative, for example:

    Barbell_Squat/0.jpg

In the upstream repo those files live at `exercises/Barbell_Squat/0.jpg`. The
import copies them into a persistent local directory and the API serves them
from `/media/exercises/...`. Thumbnails are stored under
`/media/exercises/thumbs/...`. The UI never uses GitHub or CDN URLs as `img`
sources.

Storage:

- Local: `data/exercise-images/`
- Docker: `/data/exercise-images` on the `fitness-data` volume (survives frontend rebuilds)
- Bundled in the Docker image at `/app/seed_data/exercise-images`, then copied into the volume on first start

Re-import metadata and images:

```
cd backend
.venv/Scripts/python scripts/seed_exercises.py
.venv/Scripts/python scripts/import_exercise_images.py
```
