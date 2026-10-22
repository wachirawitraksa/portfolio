#!/bin/sh
# Backs up the two things that cannot be rebuilt: the database and the uploaded files (images, CVs).
#
#   sh ops/backup.sh
#
# Writes BACKUP_DIR/portfolio-<UTC time>/ containing
#   db.dump          PostgreSQL custom-format dump (pg_dump -Fc)
#   storage.tar.gz   the uploaded files
#   SHA256SUMS       checksums, checked again by restore.sh and verify-backup.sh
#   manifest.txt     when, from which commit, which database migration
# keeps the newest BACKUP_KEEP of them, and copies the new one to BACKUP_REMOTE if that is set (needs rclone).
#
# Run it from cron, for example every night at 03:15:
#   15 3 * * * cd /srv/portfolio && sh ops/backup.sh >> /var/log/portfolio-backup.log 2>&1
#
# A backup on the same disk does not survive a dead disk. Set BACKUP_REMOTE, or copy BACKUP_DIR somewhere else.
set -eu
. "$(dirname "$0")/lib.sh"

backup_dir=$(cfg BACKUP_DIR /var/backups/portfolio)
keep=$(cfg BACKUP_KEEP 14)
remote=$(cfg BACKUP_REMOTE)

umask 077 # the backup holds personal data and the CV: readable by this user only
mkdir -p "$backup_dir"
out="$backup_dir/portfolio-$(date -u +%Y%m%d-%H%M%S)"
mkdir "$out"
# A half-written backup is worse than none: remove it unless everything below succeeded.
finished=no
cleanup() { [ "$finished" = yes ] || { echo "Backup failed; removing $out" >&2; rm -rf "$out"; }; }
trap cleanup EXIT

echo "Dumping the database ..."
docker compose exec -T db pg_dump -U "$db_user" -Fc "$db_name" > "$out/db.dump"
[ -s "$out/db.dump" ] || { echo "The database dump is empty." >&2; exit 1; }

echo "Archiving the uploaded files ..."
volume=$(storage_volume)
[ -n "$volume" ] || { echo "Could not find the storage volume." >&2; exit 1; }
docker run --rm -v "$volume":/data:ro -v "$(native "$out")":/backup alpine:3 tar czf /backup/storage.tar.gz -C /data .
[ -s "$out/storage.tar.gz" ] || { echo "The files archive is empty." >&2; exit 1; }

(cd "$out" && sha256sum db.dump storage.tar.gz > SHA256SUMS)
migration=$(docker compose exec -T db psql -U "$db_user" -d "$db_name" -tAc "select version_num from alembic_version" | tr -d '\r\n ')
{
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
  echo "alembic_revision=$migration"
  echo "db_dump_bytes=$(wc -c < "$out/db.dump" | tr -d ' ')"
  echo "storage_archive_bytes=$(wc -c < "$out/storage.tar.gz" | tr -d ' ')"
} > "$out/manifest.txt"
finished=yes

# Rotation: keep the newest $keep (names sort by time).
count=$(ls -1d "$backup_dir"/portfolio-* | wc -l | tr -d ' ')
if [ "$count" -gt "$keep" ]; then
  ls -1d "$backup_dir"/portfolio-* | sort | head -n "$((count - keep))" | while read -r old; do
    echo "Removing the old backup $old"
    rm -rf "$old"
  done
fi

if [ -n "$remote" ]; then
  if command -v rclone >/dev/null 2>&1; then
    echo "Copying to $remote ..."
    rclone copy "$out" "$remote/$(basename "$out")"
  else
    echo "BACKUP_REMOTE is set but rclone is not installed: the backup stays on this machine only." >&2
  fi
fi

echo "Backup written to $out"
cat "$out/manifest.txt"
