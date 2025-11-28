# user_change_password.py
import sys
import getpass
from hashlib import sha256
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def hash_pw(p):
    return sha256(p.encode()).hexdigest()


def change_password(username, new_password):
    conn = get_snowflake_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    if cur.fetchone()[0] == 0:
        print(f"ERROR: User '{username}' does not exist.")
        return

    cur.execute("""
        UPDATE OMBUDSMAN_USERS
        SET PASSWORD_HASH=%s
        WHERE USERNAME=%s
    """, (hash_pw(new_password), username))

    conn.commit()
    print(f"Password for '{username}' updated.")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        change_password(sys.argv[1], sys.argv[2])
    else:
        u = input("Username: ")
        p = getpass.getpass("New Password: ")
        change_password(u, p)