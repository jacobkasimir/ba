#!/bin/sh
set -eu

# Run SQL as the initialization administrator.
# psql safely quotes the password through :'role_password'.
psql \
  -v ON_ERROR_STOP=1 \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -v database_name="$POSTGRES_DB" \
  -v role_password="$QUERY_RO_PASSWORD" <<'SQL'

CREATE ROLE user
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    PASSWORD :'role_password';

-- Explicitly allow only the required database and table access.
GRANT CONNECT ON DATABASE :"database_name" TO user;
GRANT USAGE ON SCHEMA public TO user;
GRANT SELECT ON public.patient_dimension TO user;

-- Additional defaults, not replacements for privilege enforcement.
ALTER ROLE user SET default_transaction_read_only = on;
ALTER ROLE user SET statement_timeout = '5s';
ALTER ROLE user SET lock_timeout = '1s';

SQL
