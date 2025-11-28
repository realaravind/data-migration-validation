# user_delete.py
import sys
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def user_delete(username):
    conn = get_snowflake_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    if cur.fetchone()[0] == 0:
        print(f"ERROR: User '{username}' does not exist.")
        return

    cur.execute("DELETE FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    conn.commit()
    print(f"User '{username}' deleted.")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        user_delete(sys.argv[1])
    else:
        u = input("Username to delete: ")
        user_delete(u)