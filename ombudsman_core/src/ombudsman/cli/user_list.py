# user_list.py
from ombudsman.connections.snowflake_conn import get_snowflake_conn


def list_users():
    conn = get_snowflake_conn()
    cur = conn.cursor()

    cur.execute("SELECT USERNAME, ROLE FROM OMBUDSMAN_USERS ORDER BY USERNAME")
    rows = cur.fetchall()

    print("\nUsers:")
    print("-------")
    for u, r in rows:
        print(f"{u}  ({r})")
    print("-------")


if __name__ == "__main__":
    list_users()