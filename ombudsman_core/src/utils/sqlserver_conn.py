import pyodbc

class SQLServerConn:
    def __init__(self, conn_str):
        self.conn_str = conn_str
        self.conn = pyodbc.connect(self.conn_str, autocommit=True)
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