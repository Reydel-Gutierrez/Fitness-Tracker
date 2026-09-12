# Deployment

## Docker

```
cp .env.example .env
docker compose up -d --build
```

App: http://localhost:8080

Health: http://localhost:8080/api/health
OpenAPI: http://localhost:8080/docs

## Raspberry Pi

Use 64-bit Raspberry Pi OS. Install Docker Engine + Compose plugin. Then the
same `docker compose up -d --build` command. Images are debian bookworm based
and publish AMD64 and ARM64.

## Cloudflare Tunnel

Example `config.yml` ingress (credentials stay in your existing cloudflared
install, not in this repo):

```yaml
ingress:
  - hostname: fitness.example.com
    service: http://localhost:8080
  - service: http_status:404
```

LAN access continues to work at `http://<pi-ip>:8080`.

## Backups

Database file in Docker: `/data/fitness.db` on volume `fitness-data`.
Exercise images: `/data/exercise-images` on the same volume.

```
docker compose exec fitness python scripts/backup_db.py backup --db /data/fitness.db --file /data/backups/fitness.db
```

Restore with the `restore` action. The script uses `sqlite3.Connection.backup`.
