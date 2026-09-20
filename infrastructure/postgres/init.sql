-- OntDekker — PostgreSQL initialization script
--
-- This script is executed by the postgres:16 container on FIRST DATA VOLUME
-- INITIALIZATION ONLY (via /docker-entrypoint-initdb.d).
--
-- IMPORTANT: If the Docker volume already contains initialized PostgreSQL data,
-- this script will NOT run again. To re-initialize (e.g. to add these databases
-- to an existing volume), you must remove the volume first:
--
--   docker compose down
--   docker volume rm <project>_postgres_data
--   docker compose up
--
-- Databases created here:
--   auth_db  — owned by Authentication Service (Developer 1)
--   user_db  — owned by User Service (Developer 1)
--
-- All other service databases are provisioned by their respective owners.
-- Each CREATE DATABASE uses IF NOT EXISTS for idempotency within a single
-- initialization run (e.g. if this script is ever re-run manually via psql).

SELECT 'CREATE DATABASE auth_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db')\gexec

SELECT 'CREATE DATABASE user_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'user_db')\gexec

SELECT 'CREATE DATABASE community_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'community_db')\gexec

SELECT 'CREATE DATABASE feed_db'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'feed_db')\gexec
