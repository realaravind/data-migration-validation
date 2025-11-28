import json
import uuid
import datetime
import os

class ValidationWriter:
    def __init__(self, snow_conn):
        self.snow = snow_conn
        self.schema = os.getenv("VALIDATION_SCHEMA", "VALIDATION")
        self.run_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.utcnow()

        self.results = []

    def add_result(self, name, category, status, severity, details=None):
        self.results.append({
            "name": name,
            "category": category,
            "status": status,
            "severity": severity,
            "details": details
        })

    def write_json(self):
        out_path = "ombudsman/output/validation/"
        os.makedirs(out_path, exist_ok=True)
        json.dump({
            "run_id": self.run_id,
            "timestamp": str(self.timestamp),
            "results": self.results
        }, open(out_path + "results.json", "w"), indent=2)

    def write_to_snowflake(self):
        insert_run = f"""
            INSERT INTO {self.schema}.VALIDATION_RUNS
            (run_id, run_timestamp, total_checks, failed_checks, passed_checks)
            VALUES (%s, %s, %s, %s, %s)
        """

        total = len(self.results)
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        passed = total - failed

        self.snow.execute(insert_run, (
            self.run_id, self.timestamp, total, failed, passed
        ))

        insert_detail = f"""
            INSERT INTO {self.schema}.VALIDATION_RESULTS
            (run_id, validation_name, category, status, severity, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        for r in self.results:
            self.snow.execute(insert_detail, (
                self.run_id,
                r["name"],
                r["category"],
                r["status"],
                r["severity"],
                json.dumps(r["details"])
            ))