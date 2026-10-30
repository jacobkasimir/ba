import os

import psycopg


def open_database():
    """Create a short-lived connection using gateway-only credentials."""

    settings = {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ["DB_PORT"]),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "sslmode": os.environ["DB_SSLMODE"],
        "connect_timeout": 5,
        # Fixed application name helps identify sessions during debugging.
        "application_name": "aktin-query-gateway",
    }

    # Required when the selected TLS configuration uses a custom CA.
    ca_file = os.getenv("DB_SSLROOTCERT")
    if ca_file:
        settings["sslrootcert"] = ca_file

    return psycopg.connect(**settings)