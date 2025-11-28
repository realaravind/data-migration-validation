import os
from ombudsman.connections.snowflake_conn import get_snowflake_conn
from hashlib import sha256


def hash_password(password):
    return sha256(password.encode()).hexdigest()


def setup_snowflake():
    conn = get_snowflake_conn()
    cursor = conn.cursor()

    # Results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OMBUDSMAN_RESULTS (
        ID INTEGER AUTOINCREMENT PRIMARY KEY,
        PIPELINE_NAME STRING,
        STEP_NAME STRING,
        STATUS STRING,
        MESSAGE STRING,
        RUN_TIMESTAMP TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Pipelines table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OMBUDSMAN_PIPELINES (
        ID INTEGER AUTOINCREMENT PRIMARY KEY,
        NAME STRING,
        YAML_CONTENT STRING,
        UPLOADED_BY STRING,
        UPLOADED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Roles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OMBUDSMAN_ROLES (
        ROLE STRING PRIMARY KEY
    );
    """)

    # Insert standard roles
    cursor.execute("INSERT INTO OMBUDSMAN_ROLES (ROLE) SELECT 'admin' WHERE NOT EXISTS (SELECT 1 FROM OMBUDSMAN_ROLES WHERE ROLE='admin');")
    cursor.execute("INSERT INTO OMBUDSMAN_ROLES (ROLE) SELECT 'operator' WHERE NOT EXISTS (SELECT 1 FROM OMBUDSMAN_ROLES WHERE ROLE='operator');")
    cursor.execute("INSERT INTO OMBUDSMAN_ROLES (ROLE) SELECT 'viewer' WHERE NOT EXISTS (SELECT 1 FROM OMBUDSMAN_ROLES WHERE ROLE='viewer');")

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS OMBUDSMAN_USERS (
        USERNAME STRING PRIMARY KEY,
        PASSWORD_HASH STRING,
        ROLE STRING REFERENCES OMBUDSMAN_ROLES(ROLE)
    );
    """)

    # Read default admin from environment variables
    admin_user = os.getenv("OMBUDSMAN_ADMIN_USER", "admin")
    admin_pass = os.getenv("OMBUDSMAN_ADMIN_PASSWORD", "admin123")

    cursor.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (admin_user,))
    exists = cursor.fetchone()[0]

    if exists == 0:
        print(f"Creating default admin user '{admin_user}' in Snowflake...")
        cursor.execute("""
            INSERT INTO OMBUDSMAN_USERS (USERNAME, PASSWORD_HASH, ROLE)
            VALUES (%s, %s, %s)
        """, (admin_user, hash_password(admin_pass), "admin"))

    conn.commit()