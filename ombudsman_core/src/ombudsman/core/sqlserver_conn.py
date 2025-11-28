import pyodbc

class SQLServerConn:
    def __init__(self, conn_str):
        self.conn = pyodbc.connect(conn_str, autocommit=True)
        self.cur = self.conn.cursor()

    def fetch_one(self, q):
        self.cur.execute(q)
        r = self.cur.fetchone()
        return r[0] if r else None

    def fetch_many(self, q):
        self.cur.execute(q)
        return [tuple(x) for x in self.cur.fetchall()]

    def fetch_dicts(self, q):
        self.cur.execute(q)
        cols = [c[0] for c in self.cur.description]
        return [dict(zip(cols, row)) for row in self.cur.fetchall()]

    def execute(self, q):
        self.cur.execute(q)