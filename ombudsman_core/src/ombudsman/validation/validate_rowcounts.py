def validate_rowcounts(sql_conn, snow_conn, tables):
    results = {}
    for t in tables:
        sql = sql_conn.fetch_one(f"SELECT COUNT(*) FROM {t}")
        snow = snow_conn.fetch_one(f"SELECT COUNT(*) FROM {t}")
        results[t] = {"sql": sql, "snow": snow, "match": sql == snow}
    return results