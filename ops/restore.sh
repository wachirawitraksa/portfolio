#!/bin/sh
# Restores a backup into the running stack. THIS REPLACES the current database and uploaded files.
#
#   sh ops/restore.sh BACKUP_DIR/portfolio-...  [--yes]
#
# What it does: checks the checksums, stops the web, api and proxy containers, replaces the database content with the
# dump and the uploaded files with the archive, then starts everything again. The api container applies any newer
# database migrations when it starts, so a backup from an older version restores fine.
#
# Try it on a copy first (verify-backup.sh restores into a throw-away database and touches nothing).
set -eu
. "$(dirname "$0")/lib.sh"

target="${1:-}"
[ -n "$target" ] && [ -d "$target" ] || { echo "Usage: sh ops/restore.sh BACKUP_DIR/portfolio-... [--yes]" >&2; exit 1; }
yes="${2:-}"

(cd "$target" && sha256sum -c SHA256SUMS) || { echo "The checksums do not match; refusing to restore a damaged backup." >&2; exit 1; }
[ -f "$target/manifest.txt" ] && cat "$target/manifest.txt"

if [ "$yes" != "--yes" ]; then
  printf 'This replaces the current database and uploaded files with the backup above. Type "restore" to continue: '
  read -r answer
  [ "$answer" = "restore" ] || { echo "Cancelled."; exit 1; }
fi

echo "Stopping the web, api and proxy ..."
docker compose stop caddy web api >/dev/null 2>&1 || docker compose stop web api

echo "Restoring the database ..."
docker compose up -d db >/dev/null
tries=0
until docker compose exec -T db pg_isready -U "$db_user" -d "$db_name" >/dev/null 2>&1; do
  tries=$((tries + 1)); [ "$tries" -lt 60 ] || { echo "The database did not start." >&2; exit 1; }
  sleep 1
done
docker compose exec -T db pg_restore -U "$db_user" -d "$db_name" --clean --if-exists --no-owner --no-privileges < "$target/db.dump" \
  || echo "pg_restore printed warnings (usually harmless messages about objects that did not exist); check the result below."

echo "Restoring the uploaded files ..."
docker compose up -d storage >/dev/null
volume=$(storage_volume)
docker compose stop storage >/dev/null
docker run --rm -v "$volume":/data -v "$(native "$target")":/backup:ro alpine:3 sh -c 'find /data -mindepth 1 -delete && tar xzf /backup/storage.tar.gz -C /data'

echo "Starting everything ..."
docker compose up -d

echo
echo "Restored. Database content now:"
docker compose exec -T db psql -U "$db_user" -d "$db_name" -tAc \
  "select 'projects: ' || (select count(*) from project) || ', work: ' || (select count(*) from work_entry) || ', articles: ' || (select count(*) from article) || ', images: ' || (select count(*) from project_image)"
echo "Open the site and the admin to check it, then rebuild the search data in the admin (Question box) if the content changed."
