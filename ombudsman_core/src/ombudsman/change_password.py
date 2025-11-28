# change_password.py
import sys
import getpass
from hashlib import sha256
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


def change_password(username: str, new_password: str):
    conn = get_snowflake_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE OMBUDSMAN_USERS
        SET PASSWORD_HASH=%s
        WHERE USERNAME=%s
    """, (hash_password(new_password), username))
    conn.commit()
    print(f"Password updated for user: {username}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        username = sys.argv[1]
        new_password = sys.argv[2]
    else:
        print("Usage: python change_password.py <username> <newpassword>")
        print("Or run without args for secure interactive mode\n")
        username = input("Username: ").strip()
        new_password = getpass.getpass("New Password: ").strip()

    change_password(username, new_password)