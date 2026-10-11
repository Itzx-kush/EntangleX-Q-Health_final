# Optional Java Redis integration

This branch adds the custom Java Redis-compatible server from
[`Itzx-kush/redis-server-java`](https://github.com/Itzx-kush/redis-server-java)
as an optional service in EntangleX Q-Health. The source is vendored under
`backend/redis-server-java/src/main/java/`; the existing server implementation
is kept in its own folder rather than mixed into the Python backend.

## Design and non-goals

- The existing FastAPI backend, frontend, SQLite registries and artifacts,
  Supabase integration, Groq integration, and ML/quantum workflow remain.
- Redis is **disabled by default**. The ordinary `docker-compose.yml` is not
  changed; Redis is activated with the optional `docker-compose.redis.yml`
  overlay.
- Redis is a separate, optional demonstration service. This change does not
  move datasets, patient records, model artifacts, experiments, or durable
  research history into Redis.
- The UI calls FastAPI. It never connects directly to the raw Redis TCP port.
- The API adapter currently permits only `PING`, `ECHO`, `SET`, and `GET`
  and sends RESP2 arrays over a TCP socket. It is not intended as a general
  public Redis proxy.
- No Render blueprint changes are made by this feature branch. The local
  Compose setup is the first integration target; public deployment requires
  separate private networking and service configuration.

## Run the integrated app locally

From the repository root, with Docker Compose v2 installed:

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml up --build
```

Open the existing Q-Health frontend at http://127.0.0.1:8080 and choose
**Systems → Redis Lab** from the sidebar (or open `/redis`). The UI refreshes
server status every five seconds.

Try these commands in order:

```text
PING
ECHO hello
SET greeting "hello world"
GET greeting
```

The server only publishes its TCP port on the internal Compose network. The
FastAPI service connects to `redis-server:6380`; the browser sees the guarded
Q-Health REST API only.

Stop the stack with:

```bash
docker compose -f docker-compose.yml -f docker-compose.redis.yml down
```

The Redis persistence volume is named `qhealth_redis_data`. Do not pass
`--volumes` / `-v` to `down` unless you intentionally want to delete that
volume. Existing Q-Health data is held in its separate `qhealth_data` volume.

## Run the existing app without Redis

Keep using the original command:

```bash
docker compose up --build
```

Redis stays disabled in that configuration and Redis Lab explains how to
enable the optional service. For native Python development, the default
`QHEALTH_REDIS_ENABLED=false` also preserves the original behavior. To connect
to a server running on the host, set the documented `QHEALTH_REDIS_*`
environment variables in your local environment; do not expose the server to
untrusted networks.

## API endpoints

Both routes are included in Q-Health's existing API authentication boundary:

- `GET /api/redis/status` — disabled, online, or offline status and measured
  PING latency.
- `POST /api/redis/command` — request body example:
  `{"command":["SET","greeting","hello world"]}`.

Only the four commands above are accepted. The adapter bounds socket timeouts,
command argument sizes, and RESP response lengths. When Redis is offline, the
status endpoint returns an offline state and the existing research features
continue to operate.

## Verification boundary

The bridge has focused unit tests for RESP encoding/decoding and command
validation. The full Docker/Redis integration should be built and exercised in
the same environment used to run Q-Health before enabling it for other users.
This integration does not claim that every feature in the custom Redis server
is compatible with standard Redis clients or ready for production use.
