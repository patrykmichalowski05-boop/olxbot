PostgreSQL development environment.

This configuration is not started automatically.

Required:
- Docker Compose
- A test-only database password

Set FLIP_TEST_PG_PASSWORD, then execute:

docker compose -f ops/dev/docker-compose.postgres.yml up -d

The container binds only to 127.0.0.1:55432.

Never point this environment at production data.
