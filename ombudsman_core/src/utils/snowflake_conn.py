import os
import snowflake.connector

class SnowflakeConn:
    def __init__(self):
        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        )
        self.cur = self.conn.cursor()

    def fetch_one(self, query):
        self.cur.execute(query)
        row = self.cur.fetchone()
        return row[0] if row else None

    def fetch_many(self, query):
        self.cur.execute(query)
        rows = self.cur.fetchall()
        return [tuple(r) for r in rows]

    def execute(self, query):
        self.cur.execute(query)
        return True