#!/bin/sh
# Prints fresh values for the secrets in .env, ready to paste. Nothing is written to any file.
#
#   sh ops/gen-secrets.sh
#
# POSTGRES_PASSWORD and the password inside DATABASE_URL are printed together so they cannot drift apart.
set -eu

random() { # random() <bytes>: lowercase hex from the system's random source
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

password=$(random 24)
echo "POSTGRES_PASSWORD=$password"
echo "DATABASE_URL=postgresql+asyncpg://portfolio:$password@db:5432/portfolio"
echo "S3_ACCESS_KEY=$(random 10)"
echo "S3_SECRET_KEY=$(random 24)"
echo "ASK_IP_SALT=$(random 24)"
