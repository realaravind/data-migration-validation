# user_set_role.py
import sys
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def set_role(username, role):
    conn = get_snowflake_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    if cur.fetchone()[0] == 0:
        print(f"ERROR: User '{username}' does not exist.")
        return

    cur.execute("UPDATE OMBUDSMAN_USERS SET ROLE=%s WHERE USERNAME=%s", (role, username))
    conn.commit()
    print(f"Role for '{username}' updated to '{role}'.")
    

if __name__ == "__main__":
    if len(sys.argv) == 3:
        set_role(sys.argv[1], sys.argv[2])
    else:
        u = input("Username: ")
        r = input("New role (admin/operator/viewer): ")
        set_role(u, r)