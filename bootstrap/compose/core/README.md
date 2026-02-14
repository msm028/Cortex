# Core Bootstrap Compose Stack

This stack defines internal-only core services (`postgres`, `minio`, `vaultwarden`) for deterministic config validation and controlled deployment.

Ports are intentionally not exposed by default (`ports:` is omitted).

Required environment variable names:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `VAULTWARDEN_DATABASE_URL`
- `VAULTWARDEN_ADMIN_TOKEN`
- `VAULTWARDEN_DOMAIN`
- `VAULTWARDEN_SIGNUPS_ALLOWED`
