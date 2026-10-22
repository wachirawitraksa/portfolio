#!/bin/sh
# Shared helpers for the scripts in ops/. Sourced, never run on its own.
#
# Everything is read from .env in the project folder, the same file docker compose uses, so there is one place to
# configure. The scripts run `docker compose` from that folder, so COMPOSE_FILE in .env (the production overrides)
# applies to them too.

cd "$(dirname "$0")/.."
# Git Bash on Windows rewrites paths that start with "/" before handing them to docker; stop it.
export MSYS_NO_PATHCONV=1

# cfg NAME [DEFAULT]: NAME from the environment, else from .env (the last assignment wins), else DEFAULT.
cfg() {
  value=$(printenv "$1" 2>/dev/null || true) # an environment variable wins over .env
  if [ -z "$value" ] && [ -f .env ]; then
    value=$(grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '\r')
  fi
  if [ -n "$value" ]; then printf '%s' "$value"; else printf '%s' "${2:-}"; fi
}

# native DIR: DIR as a path docker understands (a Windows path under Git Bash, unchanged elsewhere).
native() {
  (cd "$1" && (pwd -W 2>/dev/null || pwd))
}

# storage_volume: the name of the volume that holds the uploaded files (mounted at /data in the storage container).
storage_volume() {
  container=$(docker compose ps -aq storage | head -n 1)
  [ -n "$container" ] || { echo "The storage container does not exist. Start the stack first." >&2; exit 1; }
  docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}' "$container"
}

db_user=$(cfg POSTGRES_USER portfolio)
db_name=$(cfg POSTGRES_DB portfolio)
