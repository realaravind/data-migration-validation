# ============================================================
# Ombudsman Migration Testing Framework — Makefile
# ============================================================
# Targets:
#   make all               → full build + validation
#   make build             → run all build_part*.sh
#   make part6-sql         → run Part 6 using SQL Server
#   make part6-sf          → run Part 6 using Snowflake
#   make validate          → validate output artifacts
#   make test              → run both SQL Server + Snowflake connection tests
#   make zip               → produce project ZIP
#   make clean             → remove generated output
# ============================================================

.PHONY: all build validate test sqlserver snowflake zip clean

all: build validate

# ------------------------------------------------------------
# Build — run all build parts 1–6
# ------------------------------------------------------------
build:
	bash build_part1.sh
	bash build_part2.sh
	bash build_part3.sh
	bash build_part4.sh
	bash build_part5.sh
	bash build_part6.sh

# ------------------------------------------------------------
# Direct metadata build for SQL Server
# ------------------------------------------------------------
part6-sql:
	bash build_part6.sh --sqlserver --conn-str="$(SQLSERVER_CONN_STR)"

# ------------------------------------------------------------
# Direct metadata build for Snowflake
# ------------------------------------------------------------
part6-sf:
	bash build_part6.sh --snowflake \
		--user="$(SNOWFLAKE_USER)" \
		--password="$(SNOWFLAKE_PASSWORD)" \
		--account="$(SNOWFLAKE_ACCOUNT)" \
		--database="$(SNOWFLAKE_DATABASE)" \
		--schema="$(SNOWFLAKE_SCHEMA)"

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
validate:
	bash validate_project.sh

# ------------------------------------------------------------
# Connectivity Tests
# ------------------------------------------------------------
test:
	python ombudsman/scripts/test_sqlserver.py
	python ombudsman/scripts/test_snowflake.py

sqlserver:
	python ombudsman/scripts/test_sqlserver.py

snowflake:
	python ombudsman/scripts/test_snowflake.py

# ------------------------------------------------------------
# Create ZIP (final deliverable)
# ------------------------------------------------------------
zip:
	bash ombudsman/finalize_project.sh

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
clean:
	rm -rf ombudsman/output/*