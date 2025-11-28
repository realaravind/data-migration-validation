import os
import snowflake.connector

class SnowflakeConn:
    def __init__(self):
        self.schema = os.getenv("VALIDATION_SCHEMA", "VALIDATION")

        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        )
        self.cur = self.conn.cursor()

    def fetch_one(self, q):
        self.cur.execute(q)
        row = self.cur.fetchone()
        return row[0] if row else None

    def fetch_many(self, q):
        self.cur.execute(q)
        return [tuple(r) for r in self.cur.fetchall()]

    def fetch_dicts(self, q):
        self.cur.execute(q)
        cols = [c[0] for c in self.cur.description]
        return [dict(zip(cols, row)) for row in self.cur.fetchall()]

    def execute(self, q, params=None):
        self.cur.execute(q) if not params else self.cur.execute(q, params)