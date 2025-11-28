def validate_entities(sql_conn, snow_conn, entities):
    res = {}
    for e, cfg in entities.items():
        sql = sql_conn.fetch_one(cfg["sql_query"])
        snow = snow_conn.fetch_one(cfg["snowflake_query"])
        res[e] = {"sql": sql, "snow": snow, "match": sql == snow}
    return res