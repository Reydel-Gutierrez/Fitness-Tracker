FROM node:22-bookworm-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app
COPY backend/seed_data /app/seed_data
# Import dataset images into the image at build time so runtime does not hit GitHub.
RUN python scripts/import_exercise_images.py --dest /app/seed_data/exercise-images
COPY --from=frontend /src/dist /app/static
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////data/fitness.db
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8080/api/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
