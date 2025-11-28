'''
python userctl.py add admin hello123 admin
python userctl.py delete alice
python userctl.py passwd bob newpass
python userctl.py role charlie operator
python userctl.py list

'''
#  userctl.py
import sys
import getpass
from hashlib import sha256
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def hash_pw(p):
    return sha256(p.encode()).hexdigest()


def conn():
    return get_snowflake_conn().cursor()


def add_user(username, password, role):
    c = conn()
    c.execute("SELECT COUNT(*) FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    if c.fetchone()[0] > 0:
        print("User already exists.")
        return

    c.execute("""
        INSERT INTO OMBUDSMAN_USERS (USERNAME, PASSWORD_HASH, ROLE)
        VALUES (%s, %s, %s)
    """, (username, hash_pw(password), role))
    c.connection.commit()
    print("User created.")


def delete_user(username):
    c = conn()
    c.execute("DELETE FROM OMBUDSMAN_USERS WHERE USERNAME=%s", (username,))
    c.connection.commit()
    print("User deleted.")


def update_role(username, role):
    c = conn()
    c.execute("UPDATE OMBUDSMAN_USERS SET ROLE=%s WHERE USERNAME=%s", (role, username))
    c.connection.commit()
    print("Role updated.")


def change_pw(username, pw):
    c = conn()
    c.execute("UPDATE OMBUDSMAN_USERS SET PASSWORD_HASH=%s WHERE USERNAME=%s", (hash_pw(pw), username))
    c.connection.commit()
    print("Password updated.")


def list_users():
    c = conn()
    c.execute("SELECT USERNAME, ROLE FROM OMBUDSMAN_USERS ORDER BY USERNAME")
    rows = c.fetchall()
    for u, r in rows:
        print(f"{u} ({r})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
Usage:
  python userctl.py add <username> <password> <role>
  python userctl.py delete <username>
  python userctl.py passwd <username> <newpass>
  python userctl.py role <username> <role>
  python userctl.py list
""")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "add":
        add_user(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "delete":
        delete_user(sys.argv[2])
    elif cmd == "passwd":
        change_pw(sys.argv[2], sys.argv[3])
    elif cmd == "role":
        update_role(sys.argv[2], sys.argv[3])
    elif cmd == "list":
        list_users()