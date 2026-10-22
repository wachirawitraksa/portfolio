#!/bin/sh
# Proves that a backup can be restored, WITHOUT touching the running system.
#
#   sh ops/verify-backup.sh [BACKUP_DIR/portfolio-...]      (default: the newest backup)
#
# It checks the checksums, restores the dump into a throw-away PostgreSQL container, counts the rows of the main
# tables there and (when the stack is running) compares them with the live database, and lists the file archive.
# A backup nobody has restored is a hope, not a backup: run this after setting backups up, and now and then after.
set -eu
. "$(dirname "$0")/lib.sh"

backup_dir=$(cfg BACKUP_DIR /var/backups/portfolio)
target="${1:-$(ls -1d "$backup_dir"/portfolio-* 2>/dev/null | sort | tail -n 1)}"
[ -n "$target" ] && [ -d "$target" ] || { echo "No backup found. Run: sh ops/backup.sh" >&2; exit 1; }
echo "Verifying $target"

(cd "$target" && sha256sum -c SHA256SUMS) || { echo "FAIL: the checksums do not match (the backup is damaged)." >&2; exit 1; }

# The tables whose row counts are compared.
tables="project project_image work_entry education_entry article tag category kind profile contact_link glossary_entry rag_chunk"
counts_sql=""
for t in $tables; do
  counts_sql="$counts_sql select '$t', count(*) from $t union all"
done
counts_sql="${counts_sql% union all} order by 1;"

name="pf-verify-$$"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "Starting a temporary PostgreSQL ..."
docker run -d --name "$name" -e POSTGRES_USER=verify -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=verify pgvector/pgvector:pg16 >/dev/null
tries=0
until docker exec "$name" pg_isready -U verify -d verify >/dev/null 2>&1; do
  tries=$((tries + 1)); [ "$tries" -lt 60 ] || { echo "FAIL: the temporary database did not start." >&2; exit 1; }
  sleep 1
done
sleep 2 # pg_isready answers a moment before the init scripts finish

echo "Restoring the dump ..."
docker exec -i "$name" pg_restore -U verify -d verify --no-owner --no-privileges < "$target/db.dump" 2>"$target/.restore.log" || true
errors=$(grep -c "error" "$target/.restore.log" || true)
rm -f "$target/.restore.log"
restored=$(docker exec "$name" psql -U verify -d verify -tAF'|' -c "$counts_sql") || { echo "FAIL: the restored database cannot be queried." >&2; exit 1; }
migration=$(docker exec "$name" psql -U verify -d verify -tAc "select version_num from alembic_version" | tr -d '\r\n ')

echo
echo "Restored copy (database migration $migration):"
echo "$restored" | sed 's/|/ = /; s/^/  /'

status=ok
if docker compose ps --status running db 2>/dev/null | grep -q db; then
  live=$(docker compose exec -T db psql -U "$db_user" -d "$db_name" -tAF'|' -c "$counts_sql" | tr -d '\r')
  if [ "$live" = "$(echo "$restored" | tr -d '\r')" ]; then
    echo "The live database has the same counts: nothing changed since this backup."
  else
    echo "Note: the live database differs from this backup (expected if content changed since it was taken):"
    echo "$live" | sed 's/|/ = /; s/^/  live /'
  fi
fi

[ "$errors" = "0" ] || { echo "Restore reported $errors error line(s)." >&2; status=check; }

echo
echo "Files archive:"
# Read it from stdin: GNU tar takes "C:\..." (a Windows path) for a remote host name.
listing=$(tar tzf - < "$target/storage.tar.gz") || { echo "FAIL: the files archive cannot be read." >&2; exit 1; }
files=$(printf '%s
' "$listing" | grep -vc '/$' || true)
echo "  $files file(s) in storage.tar.gz"

echo
if [ "$status" = ok ]; then
  echo "PASS: the backup restores into a working database and the file archive reads."
else
  echo "CHECK: the backup restored but reported errors above."
  exit 1
fi
