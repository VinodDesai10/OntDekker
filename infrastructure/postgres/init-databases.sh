#!/usr/bin/env bash
# =============================================================================
# OntDekker — PostgreSQL database bootstrap
#
# Mounted into the postgres container via docker-entrypoint-initdb.d/.
# Executed automatically by the postgres image on a fresh volume.
# Idempotently creates databases for all microservices in the monorepo.
# =============================================================================
set -e

echo "[init-databases] Creating application databases..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE auth_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db')\gexec
    SELECT 'CREATE DATABASE user_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_db')\gexec
    SELECT 'CREATE DATABASE feed_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'feed_db')\gexec
    SELECT 'CREATE DATABASE community_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'community_db')\gexec
    SELECT 'CREATE DATABASE trip_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'trip_db')\gexec
    SELECT 'CREATE DATABASE guide_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'guide_db')\gexec
    SELECT 'CREATE DATABASE recommendation_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'recommendation_db')\gexec
    SELECT 'CREATE DATABASE chat_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chat_db')\gexec
    SELECT 'CREATE DATABASE notification_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'notification_db')\gexec
    SELECT 'CREATE DATABASE moderation_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'moderation_db')\gexec
EOSQL

echo "[init-databases] All service databases created successfully."
