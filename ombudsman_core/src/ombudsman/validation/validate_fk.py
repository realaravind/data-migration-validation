def validate_fk(sql_conn, snow_conn, metadata):
    res = {}
    for fact, dims in metadata.items():
        for dim, key in dims.items():
            # Escape column names to handle reserved keywords and special characters
            sql = sql_conn.fetch_one(f"""
                SELECT COUNT(*) FROM {fact} f
                LEFT JOIN {dim} d ON f.[{key}]=d.[{key}]
                WHERE d.[{key}] IS NULL
            """)
            snow = snow_conn.fetch_one(f"""
                SELECT COUNT(*) FROM {fact} f
                LEFT JOIN {dim} d ON f.{key}=d.{key}
                WHERE d.{key} IS NULL
            """)
            res[f"{fact}->{dim}"] = {"sql": sql, "snow": snow}
    return res