# user_add.py
import sys
import getpass
from hashlib import sha256
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def hash_pw(p):
    return sha256(p.encode()).hexdigest()


def user_add(username, password, role):
    conn = get_snowflake_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    if cur.fetchone()[0] > 0:
        print(f"ERROR: User '{username}' already exists.")
        return

    cur.execute("""
        INSERT INTO OMBUDSMAN_USERS (USERNAME, PASSWORD_HASH, ROLE)
        VALUES (%s, %s, %s)
    """, (username, hash_pw(password), role))

    conn.commit()
    print(f"User '{username}' created with role '{role}'.")


if __name__ == "__main__":
    if len(sys.argv) == 4:
        user_add(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Interactive mode:")
        u = input("Username: ")
        p = getpass.getpass("Password: ")
        r = input("Role (admin/operator/viewer): ")
        user_add(u, p, r)