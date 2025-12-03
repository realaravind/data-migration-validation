"""
Sample Workload Generator
Generates sample workloads based on schema templates
"""

from typing import List, Dict, Optional
import random
import pyodbc
import os
import yaml
from pathlib import Path


class WorkloadGenerator:
    """Generate sample workloads for different schema templates"""

    def __init__(self, db_connection = None):
        self.schemas = {
            "Retail": {
                "dimensions": ["Customer", "Product", "Store"],
                "facts": ["Sales", "Inventory"]
            },
            "Finance": {
                "dimensions": ["Account", "Transaction Type", "Merchant"],
                "facts": ["Transactions", "Balances"]
            },
            "Healthcare": {
                "dimensions": ["Patient", "Provider", "Diagnosis"],
                "facts": ["Visits", "Medications"]
            }
        }
        self.db_connection = db_connection
        self.table_columns = {}  # Cache for table columns

    def _get_table_columns(self, schema: str, table: str) -> List[str]:
        """Query database to get actual column names for a table"""
        if not self.db_connection:
            # Fallback to default column names if no DB connection
            return []

        cache_key = f"{schema}.{table}"
        if cache_key in self.table_columns:
            return self.table_columns[cache_key]

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, (schema, table))

            columns = [row[0] for row in cursor.fetchall()]
            self.table_columns[cache_key] = columns
            cursor.close()
            return columns
        except Exception as e:
            print(f"[WARN] Could not fetch columns for {schema}.{table}: {e}")
            return []

    def _find_column(self, columns: List[str], *patterns: str) -> Optional[str]:
        """Find first column matching any of the patterns (case-insensitive)"""
        if not columns:
            return None

        for pattern in patterns:
            pattern_lower = pattern.lower()
            for col in columns:
                if pattern_lower in col.lower():
                    return col
        return None

    def _get_sql_connection(self):
        """Establish connection to SQL Server"""
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('MSSQL_HOST', 'sqlserver')},{os.getenv('MSSQL_PORT', '1433')};"
            f"DATABASE={os.getenv('MSSQL_DATABASE', 'SampleDW')};"
            f"UID={os.getenv('MSSQL_USER', 'sa')};"
            f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
            f"TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)

    def _load_relationships(self, project_id: str = "dw_validation") -> Dict:
        """Load inferred relationships from project config"""
        try:
            # Get absolute path to relationships file
            script_dir = Path(__file__).parent
            relationships_path = script_dir / "projects" / project_id / "config" / "sql_relationships.yaml"

            if not relationships_path.exists():
                print(f"[WARN] Relationships file not found: {relationships_path}")
                return {}

            with open(relationships_path, 'r') as f:
                data = yaml.safe_load(f)
                relationships = {}

                # Build lookup: fact_table → {fk_column: (dim_table, dim_column)}
                for rel in data.get('relationships', []):
                    fact_table = rel['fact_table']
                    fk_column = rel['fk_column']
                    dim_table = rel['dim_table']
                    dim_column = rel['dim_column']

                    if fact_table not in relationships:
                        relationships[fact_table] = {}

                    relationships[fact_table][fk_column] = {
                        'dim_table': dim_table,
                        'dim_column': dim_column,
                        'confidence': rel.get('confidence', 'unknown')
                    }

                print(f"[INFO] Loaded {len(relationships)} fact table relationships")
                return relationships
        except Exception as e:
            print(f"[WARN] Could not load relationships: {e}")
            return {}

    def generate_workload(self, schema_name: str) -> List[Dict]:
        """Generate a comprehensive workload for the specified schema"""

        if schema_name not in self.schemas:
            raise ValueError(f"Unknown schema: {schema_name}")

        schema = self.schemas[schema_name]

        if schema_name == "Retail":
            return self._generate_retail_workload(schema)
        elif schema_name == "Finance":
            return self._generate_finance_workload(schema)
        elif schema_name == "Healthcare":
            return self._generate_healthcare_workload(schema)

        return []

    def _generate_retail_workload(self, schema: Dict) -> List[Dict]:
        """Generate Retail schema workload using actual database column names"""
        queries = []
        query_id = 1

        # Establish connection if not already connected
        if not self.db_connection:
            try:
                self.db_connection = self._get_sql_connection()
            except Exception as e:
                print(f"[WARN] Could not connect to database: {e}. Using fallback queries.")
                return self._generate_retail_workload_fallback(schema)

        # Load relationship metadata
        relationships = self._load_relationships()

        # Get actual column names from database
        customer_cols = self._get_table_columns("DIM", "dim_customer")
        product_cols = self._get_table_columns("DIM", "dim_product")
        store_cols = self._get_table_columns("DIM", "dim_store")
        sales_cols = self._get_table_columns("FACT", "fact_sales")

        # Find key columns using pattern matching for non-FK columns
        customer_id_col = self._find_column(customer_cols, "customer_id", "custid", "cust_id")
        customer_name_col = self._find_column(customer_cols, "customer_name", "custname", "name")

        product_id_col = self._find_column(product_cols, "product_id", "prodid", "prod_id")
        product_name_col = self._find_column(product_cols, "product_name", "prodname", "name")
        category_col = self._find_column(product_cols, "category", "cat")
        unit_price_col = self._find_column(product_cols, "unit_price", "price", "unitprice")

        store_id_col = self._find_column(store_cols, "store_id", "storeid")

        # Use relationship metadata to find FK→PK mappings
        fact_sales_key = "FACT.fact_sales"
        sales_customer_key_col = None
        sales_product_key_col = None
        sales_store_key_col = None
        customer_key_col = None
        product_key_col = None
        store_key_col = None

        if fact_sales_key in relationships:
            # Extract FK→PK relationships from metadata
            for fk_col, rel_info in relationships[fact_sales_key].items():
                dim_table = rel_info['dim_table']
                dim_column = rel_info['dim_column']

                if 'dim_customer' in dim_table.lower():
                    sales_customer_key_col = fk_col
                    customer_key_col = dim_column
                    print(f"[INFO] Using relationship: {fk_col} → {dim_table}.{dim_column}")
                elif 'dim_product' in dim_table.lower():
                    sales_product_key_col = fk_col
                    product_key_col = dim_column
                    print(f"[INFO] Using relationship: {fk_col} → {dim_table}.{dim_column}")
                elif 'dim_store' in dim_table.lower():
                    sales_store_key_col = fk_col
                    store_key_col = dim_column
                    print(f"[INFO] Using relationship: {fk_col} → {dim_table}.{dim_column}")
        else:
            print(f"[WARN] No relationships found for {fact_sales_key}, falling back to pattern matching")
            # Fallback to pattern matching if relationships not found
            sales_customer_key_col = self._find_column(sales_cols, "dim_customer_key", "customer_key", "customer_id", "custid")
            sales_product_key_col = self._find_column(sales_cols, "dim_product_key", "product_key", "product_id", "prodid")
            sales_store_key_col = self._find_column(sales_cols, "dim_store_key", "store_key", "store_id", "storeid")
            customer_key_col = self._find_column(customer_cols, "customer_key", "custkey") or customer_id_col
            product_key_col = self._find_column(product_cols, "product_key", "prodkey") or product_id_col
            store_key_col = self._find_column(store_cols, "store_key")

        quantity_col = self._find_column(sales_cols, "quantity", "qty")
        total_amount_col = self._find_column(sales_cols, "total_amount", "amount", "sales_amount", "totalamount")
        sale_date_col = self._find_column(sales_cols, "sale_date", "date", "saledate", "transaction_date")

        # Row count queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM DIM.dim_customer",
            "stats": {"total_executions": 1250, "avg_duration": 45.3, "last_execution_time": "2024-12-01T10:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM DIM.dim_product",
            "stats": {"total_executions": 980, "avg_duration": 38.7, "last_execution_time": "2024-12-01T11:15:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM DIM.dim_store",
            "stats": {"total_executions": 850, "avg_duration": 32.1, "last_execution_time": "2024-12-01T11:45:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM FACT.fact_sales",
            "stats": {"total_executions": 2100, "avg_duration": 125.5, "last_execution_time": "2024-12-01T12:00:00"}
        })
        query_id += 1

        # WHERE clause queries (only add if columns exist)
        if category_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT * FROM DIM.dim_product WHERE {category_col} = 'Electronics'",
                "stats": {"total_executions": 680, "avg_duration": 28.3, "last_execution_time": "2024-12-01T13:30:00"}
            })
            query_id += 1

        # Aggregation queries
        if unit_price_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT AVG({unit_price_col}) FROM DIM.dim_product",
                "stats": {"total_executions": 890, "avg_duration": 42.3, "last_execution_time": "2024-12-01T15:00:00"}
            })
            query_id += 1

        # JOIN queries
        if product_name_col and quantity_col and sales_product_key_col and product_key_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT p.{product_name_col}, s.{quantity_col} FROM DIM.dim_product p INNER JOIN FACT.fact_sales s ON p.{product_key_col} = s.{sales_product_key_col}",
                "stats": {"total_executions": 1350, "avg_duration": 223.4, "last_execution_time": "2024-12-01T16:30:00"}
            })
            query_id += 1

        # GROUP BY queries
        if category_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT {category_col}, COUNT(*) FROM DIM.dim_product GROUP BY {category_col}",
                "stats": {"total_executions": 650, "avg_duration": 56.8, "last_execution_time": "2024-12-01T18:00:00"}
            })
            query_id += 1

        # ORDER BY queries
        if unit_price_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT * FROM DIM.dim_product ORDER BY {unit_price_col} DESC",
                "stats": {"total_executions": 490, "avg_duration": 67.4, "last_execution_time": "2024-12-01T19:00:00"}
            })
            query_id += 1

        # Complex 3-way JOIN
        if customer_name_col and product_name_col and total_amount_col and customer_key_col and product_key_col:
            if sales_customer_key_col and sales_product_key_col:
                queries.append({
                    "query_id": query_id,
                    "raw_text": f"SELECT c.{customer_name_col}, p.{product_name_col}, s.{total_amount_col} FROM DIM.dim_customer c INNER JOIN FACT.fact_sales s ON c.{customer_key_col} = s.{sales_customer_key_col} INNER JOIN DIM.dim_product p ON s.{sales_product_key_col} = p.{product_key_col} WHERE s.{total_amount_col} > 1000",
                    "stats": {"total_executions": 890, "avg_duration": 312.8, "last_execution_time": "2024-12-01T20:00:00"}
                })
                query_id += 1

        # DISTINCT query
        if category_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT DISTINCT {category_col} FROM DIM.dim_product",
                "stats": {"total_executions": 420, "avg_duration": 48.2, "last_execution_time": "2024-12-01T20:30:00"}
            })
            query_id += 1

        # Range query
        if unit_price_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT * FROM DIM.dim_product WHERE {unit_price_col} > 100 AND {unit_price_col} < 500",
                "stats": {"total_executions": 580, "avg_duration": 52.1, "last_execution_time": "2024-12-01T21:00:00"}
            })
            query_id += 1

        # IN clause query
        if category_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT * FROM DIM.dim_product WHERE {category_col} IN ('Electronics', 'Clothing', 'Food')",
                "stats": {"total_executions": 460, "avg_duration": 43.5, "last_execution_time": "2024-12-01T22:00:00"}
            })
            query_id += 1

        # Aggregation with GROUP BY and LEFT JOIN
        if category_col and unit_price_col and quantity_col and product_key_col and sales_product_key_col:
            queries.append({
                "query_id": query_id,
                "raw_text": f"SELECT p.{category_col}, COUNT(*) AS ProductCount, AVG(p.{unit_price_col}) AS AvgPrice, SUM(ISNULL(s.{quantity_col}, 0)) AS TotalSold FROM DIM.dim_product p LEFT JOIN FACT.fact_sales s ON p.{product_key_col} = s.{sales_product_key_col} GROUP BY p.{category_col}",
                "stats": {"total_executions": 670, "avg_duration": 289.4, "last_execution_time": "2024-12-02T00:30:00"}
            })
            query_id += 1

        print(f"[INFO] Generated {len(queries)} Retail workload queries using actual database column names")
        return queries

    def _generate_retail_workload_fallback(self, schema: Dict) -> List[Dict]:
        """Fallback workload with basic COUNT queries only (no column-specific queries)"""
        print("[WARN] Using fallback workload - database connection not available")
        return [
            {"query_id": 1, "raw_text": "SELECT COUNT(*) FROM DIM.dim_customer", "stats": {"total_executions": 1250, "avg_duration": 45.3, "last_execution_time": "2024-12-01T10:30:00"}},
            {"query_id": 2, "raw_text": "SELECT COUNT(*) FROM DIM.dim_product", "stats": {"total_executions": 980, "avg_duration": 38.7, "last_execution_time": "2024-12-01T11:15:00"}},
            {"query_id": 3, "raw_text": "SELECT COUNT(*) FROM DIM.dim_store", "stats": {"total_executions": 850, "avg_duration": 32.1, "last_execution_time": "2024-12-01T11:45:00"}},
            {"query_id": 4, "raw_text": "SELECT COUNT(*) FROM FACT.fact_sales", "stats": {"total_executions": 2100, "avg_duration": 125.5, "last_execution_time": "2024-12-01T12:00:00"}},
        ]

    def _generate_finance_workload(self, schema: Dict) -> List[Dict]:
        """Generate Finance schema workload"""
        queries = []
        query_id = 1

        # Row counts
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_ACCOUNT",
            "stats": {"total_executions": 1100, "avg_duration": 42.1, "last_execution_time": "2024-12-01T10:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_TRANSACTION_TYPE",
            "stats": {"total_executions": 890, "avg_duration": 25.3, "last_execution_time": "2024-12-01T10:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_MERCHANT",
            "stats": {"total_executions": 950, "avg_duration": 38.7, "last_execution_time": "2024-12-01T11:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM fact.FACT_TRANSACTIONS",
            "stats": {"total_executions": 2300, "avg_duration": 145.2, "last_execution_time": "2024-12-01T11:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM fact.FACT_BALANCES",
            "stats": {"total_executions": 1650, "avg_duration": 98.4, "last_execution_time": "2024-12-01T12:00:00"}
        })
        query_id += 1

        # Account queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_ACCOUNT WHERE AccountType = 'Checking'",
            "stats": {"total_executions": 620, "avg_duration": 32.5, "last_execution_time": "2024-12-01T12:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_ACCOUNT WHERE AccountStatus = 'Active'",
            "stats": {"total_executions": 780, "avg_duration": 45.3, "last_execution_time": "2024-12-01T13:00:00"}
        })
        query_id += 1

        # Transaction analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT SUM(Amount) AS TotalTransactions FROM fact.FACT_TRANSACTIONS",
            "stats": {"total_executions": 1400, "avg_duration": 178.6, "last_execution_time": "2024-12-01T13:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AVG(Amount) AS AvgTransactionAmount FROM fact.FACT_TRANSACTIONS",
            "stats": {"total_executions": 980, "avg_duration": 156.2, "last_execution_time": "2024-12-01T14:00:00"}
        })
        query_id += 1

        # Join queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT a.AccountNumber, t.Amount FROM dim.DIM_ACCOUNT a INNER JOIN fact.FACT_TRANSACTIONS t ON a.AccountID = t.AccountID",
            "stats": {"total_executions": 1650, "avg_duration": 267.8, "last_execution_time": "2024-12-01T14:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT tt.TypeName, COUNT(*) AS TransactionCount FROM dim.DIM_TRANSACTION_TYPE tt INNER JOIN fact.FACT_TRANSACTIONS t ON tt.TypeID = t.TypeID GROUP BY tt.TypeName",
            "stats": {"total_executions": 1120, "avg_duration": 198.3, "last_execution_time": "2024-12-01T15:00:00"}
        })
        query_id += 1

        # Date-based transaction queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_TRANSACTIONS WHERE TransactionDate BETWEEN '2024-01-01' AND '2024-12-31'",
            "stats": {"total_executions": 890, "avg_duration": 212.4, "last_execution_time": "2024-12-01T15:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT MONTH(TransactionDate) AS Month, SUM(Amount) AS MonthlyTotal FROM fact.FACT_TRANSACTIONS WHERE YEAR(TransactionDate) = 2024 GROUP BY MONTH(TransactionDate) ORDER BY Month",
            "stats": {"total_executions": 760, "avg_duration": 245.6, "last_execution_time": "2024-12-01T16:00:00"}
        })
        query_id += 1

        # Merchant analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT m.MerchantName, SUM(t.Amount) AS TotalAmount FROM dim.DIM_MERCHANT m INNER JOIN fact.FACT_TRANSACTIONS t ON m.MerchantID = t.MerchantID GROUP BY m.MerchantName ORDER BY TotalAmount DESC",
            "stats": {"total_executions": 920, "avg_duration": 234.7, "last_execution_time": "2024-12-01T16:30:00"}
        })
        query_id += 1

        # Balance queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AccountID, CurrentBalance FROM fact.FACT_BALANCES WHERE CurrentBalance > 10000",
            "stats": {"total_executions": 680, "avg_duration": 123.5, "last_execution_time": "2024-12-01T17:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AVG(CurrentBalance) AS AvgBalance FROM fact.FACT_BALANCES",
            "stats": {"total_executions": 540, "avg_duration": 98.2, "last_execution_time": "2024-12-01T17:30:00"}
        })
        query_id += 1

        # Fraud detection patterns
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_TRANSACTIONS WHERE Amount > 5000",
            "stats": {"total_executions": 450, "avg_duration": 167.3, "last_execution_time": "2024-12-01T18:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AccountID, COUNT(*) AS TransactionCount FROM fact.FACT_TRANSACTIONS WHERE CAST(TransactionDate AS DATE) = CAST(GETDATE() AS DATE) GROUP BY AccountID HAVING COUNT(*) > 10",
            "stats": {"total_executions": 820, "avg_duration": 189.6, "last_execution_time": "2024-12-01T18:30:00"}
        })
        query_id += 1

        # Account balance reconciliation
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT a.AccountNumber, b.CurrentBalance, b.AvailableBalance FROM dim.DIM_ACCOUNT a INNER JOIN fact.FACT_BALANCES b ON a.AccountID = b.AccountID WHERE b.CurrentBalance != b.AvailableBalance",
            "stats": {"total_executions": 620, "avg_duration": 156.8, "last_execution_time": "2024-12-01T19:00:00"}
        })
        query_id += 1

        # DISTINCT transaction types
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT DISTINCT TypeID FROM fact.FACT_TRANSACTIONS",
            "stats": {"total_executions": 380, "avg_duration": 134.2, "last_execution_time": "2024-12-01T19:30:00"}
        })
        query_id += 1

        # Negative balance check
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_BALANCES WHERE CurrentBalance < 0",
            "stats": {"total_executions": 490, "avg_duration": 112.5, "last_execution_time": "2024-12-01T20:00:00"}
        })
        query_id += 1

        # Complex reporting query
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT a.AccountType, COUNT(DISTINCT a.AccountID) AS AccountCount, SUM(t.Amount) AS TotalTransactions, AVG(b.CurrentBalance) AS AvgBalance FROM dim.DIM_ACCOUNT a LEFT JOIN fact.FACT_TRANSACTIONS t ON a.AccountID = t.AccountID LEFT JOIN fact.FACT_BALANCES b ON a.AccountID = b.AccountID GROUP BY a.AccountType",
            "stats": {"total_executions": 710, "avg_duration": 312.4, "last_execution_time": "2024-12-01T20:30:00"}
        })
        query_id += 1

        # Merchant category analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT m.Category, COUNT(*) AS TransactionCount, SUM(t.Amount) AS TotalAmount FROM dim.DIM_MERCHANT m INNER JOIN fact.FACT_TRANSACTIONS t ON m.MerchantID = t.MerchantID GROUP BY m.Category",
            "stats": {"total_executions": 580, "avg_duration": 223.7, "last_execution_time": "2024-12-01T21:00:00"}
        })
        query_id += 1

        # NULL checks
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_TRANSACTIONS WHERE Description IS NOT NULL",
            "stats": {"total_executions": 340, "avg_duration": 145.8, "last_execution_time": "2024-12-01T21:30:00"}
        })
        query_id += 1

        # IN clause
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_ACCOUNT WHERE AccountType IN ('Checking', 'Savings', 'Investment')",
            "stats": {"total_executions": 520, "avg_duration": 48.3, "last_execution_time": "2024-12-01T22:00:00"}
        })
        query_id += 1

        # Date range with aggregation
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT tt.TypeName, COUNT(*) AS Count, SUM(t.Amount) AS Total FROM fact.FACT_TRANSACTIONS t INNER JOIN dim.DIM_TRANSACTION_TYPE tt ON t.TypeID = tt.TypeID WHERE t.TransactionDate >= DATEADD(month, -1, GETDATE()) GROUP BY tt.TypeName",
            "stats": {"total_executions": 890, "avg_duration": 267.9, "last_execution_time": "2024-12-01T22:30:00"}
        })
        query_id += 1

        # High-value accounts
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT a.AccountNumber, b.CurrentBalance FROM dim.DIM_ACCOUNT a INNER JOIN fact.FACT_BALANCES b ON a.AccountID = b.AccountID WHERE b.CurrentBalance > (SELECT AVG(CurrentBalance) * 2 FROM fact.FACT_BALANCES)",
            "stats": {"total_executions": 420, "avg_duration": 198.5, "last_execution_time": "2024-12-01T23:00:00"}
        })
        query_id += 1

        # Transaction velocity
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AccountID, COUNT(*) AS DailyTransactions, SUM(Amount) AS DailyTotal FROM fact.FACT_TRANSACTIONS WHERE CAST(TransactionDate AS DATE) = CAST(GETDATE() AS DATE) GROUP BY AccountID ORDER BY DailyTransactions DESC",
            "stats": {"total_executions": 960, "avg_duration": 212.3, "last_execution_time": "2024-12-01T23:30:00"}
        })
        query_id += 1

        return queries

    def _generate_healthcare_workload(self, schema: Dict) -> List[Dict]:
        """Generate Healthcare schema workload"""
        queries = []
        query_id = 1

        # Row counts
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_PATIENT",
            "stats": {"total_executions": 1350, "avg_duration": 48.7, "last_execution_time": "2024-12-01T08:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_PROVIDER",
            "stats": {"total_executions": 920, "avg_duration": 35.2, "last_execution_time": "2024-12-01T08:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM dim.DIM_DIAGNOSIS",
            "stats": {"total_executions": 1050, "avg_duration": 42.8, "last_execution_time": "2024-12-01T09:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM fact.FACT_VISITS",
            "stats": {"total_executions": 2200, "avg_duration": 156.3, "last_execution_time": "2024-12-01T09:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) FROM fact.FACT_MEDICATIONS",
            "stats": {"total_executions": 1780, "avg_duration": 123.6, "last_execution_time": "2024-12-01T10:00:00"}
        })
        query_id += 1

        # Patient queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PATIENT WHERE PatientID = 12345",
            "stats": {"total_executions": 560, "avg_duration": 18.4, "last_execution_time": "2024-12-01T10:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PATIENT WHERE Gender = 'F'",
            "stats": {"total_executions": 680, "avg_duration": 52.3, "last_execution_time": "2024-12-01T11:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PATIENT WHERE DateOfBirth BETWEEN '1960-01-01' AND '1980-12-31'",
            "stats": {"total_executions": 490, "avg_duration": 64.7, "last_execution_time": "2024-12-01T11:30:00"}
        })
        query_id += 1

        # Visit analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT COUNT(*) AS TotalVisits FROM fact.FACT_VISITS",
            "stats": {"total_executions": 1200, "avg_duration": 145.2, "last_execution_time": "2024-12-01T12:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT AVG(VisitDuration) AS AvgDuration FROM fact.FACT_VISITS",
            "stats": {"total_executions": 870, "avg_duration": 134.8, "last_execution_time": "2024-12-01T12:30:00"}
        })
        query_id += 1

        # JOIN queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT p.PatientName, v.VisitDate FROM dim.DIM_PATIENT p INNER JOIN fact.FACT_VISITS v ON p.PatientID = v.PatientID",
            "stats": {"total_executions": 1650, "avg_duration": 278.5, "last_execution_time": "2024-12-01T13:00:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT pr.ProviderName, COUNT(*) AS VisitCount FROM dim.DIM_PROVIDER pr INNER JOIN fact.FACT_VISITS v ON pr.ProviderID = v.ProviderID GROUP BY pr.ProviderName",
            "stats": {"total_executions": 1120, "avg_duration": 198.7, "last_execution_time": "2024-12-01T13:30:00"}
        })
        query_id += 1

        # Diagnosis analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT d.DiagnosisCode, d.DiagnosisName, COUNT(*) AS PatientCount FROM dim.DIM_DIAGNOSIS d INNER JOIN fact.FACT_VISITS v ON d.DiagnosisID = v.DiagnosisID GROUP BY d.DiagnosisCode, d.DiagnosisName ORDER BY PatientCount DESC",
            "stats": {"total_executions": 920, "avg_duration": 245.3, "last_execution_time": "2024-12-01T14:00:00"}
        })
        query_id += 1

        # Date-based visit queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_VISITS WHERE VisitDate BETWEEN '2024-01-01' AND '2024-12-31'",
            "stats": {"total_executions": 980, "avg_duration": 198.4, "last_execution_time": "2024-12-01T14:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT MONTH(VisitDate) AS Month, COUNT(*) AS MonthlyVisits FROM fact.FACT_VISITS WHERE YEAR(VisitDate) = 2024 GROUP BY MONTH(VisitDate) ORDER BY Month",
            "stats": {"total_executions": 780, "avg_duration": 223.6, "last_execution_time": "2024-12-01T15:00:00"}
        })
        query_id += 1

        # Medication queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT MedicationName, COUNT(*) AS PrescriptionCount FROM fact.FACT_MEDICATIONS GROUP BY MedicationName ORDER BY PrescriptionCount DESC",
            "stats": {"total_executions": 840, "avg_duration": 167.8, "last_execution_time": "2024-12-01T15:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_MEDICATIONS WHERE Dosage > 100",
            "stats": {"total_executions": 520, "avg_duration": 112.4, "last_execution_time": "2024-12-01T16:00:00"}
        })
        query_id += 1

        # Provider specialty analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT Specialty, COUNT(*) AS ProviderCount FROM dim.DIM_PROVIDER GROUP BY Specialty",
            "stats": {"total_executions": 610, "avg_duration": 45.7, "last_execution_time": "2024-12-01T16:30:00"}
        })
        query_id += 1

        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PROVIDER WHERE Specialty = 'Cardiology'",
            "stats": {"total_executions": 450, "avg_duration": 32.8, "last_execution_time": "2024-12-01T17:00:00"}
        })
        query_id += 1

        # Complex 3-way JOIN
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT p.PatientName, pr.ProviderName, d.DiagnosisName FROM dim.DIM_PATIENT p INNER JOIN fact.FACT_VISITS v ON p.PatientID = v.PatientID INNER JOIN dim.DIM_PROVIDER pr ON v.ProviderID = pr.ProviderID INNER JOIN dim.DIM_DIAGNOSIS d ON v.DiagnosisID = d.DiagnosisID",
            "stats": {"total_executions": 1050, "avg_duration": 334.6, "last_execution_time": "2024-12-01T17:30:00"}
        })
        query_id += 1

        # DISTINCT queries
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT DISTINCT DiagnosisID FROM fact.FACT_VISITS",
            "stats": {"total_executions": 420, "avg_duration": 145.3, "last_execution_time": "2024-12-01T18:00:00"}
        })
        query_id += 1

        # Age-based analysis
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT DATEDIFF(year, DateOfBirth, GETDATE()) AS Age, COUNT(*) AS PatientCount FROM dim.DIM_PATIENT GROUP BY DATEDIFF(year, DateOfBirth, GETDATE()) ORDER BY Age",
            "stats": {"total_executions": 580, "avg_duration": 98.6, "last_execution_time": "2024-12-01T18:30:00"}
        })
        query_id += 1

        # NULL checks
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PATIENT WHERE Email IS NOT NULL",
            "stats": {"total_executions": 340, "avg_duration": 52.4, "last_execution_time": "2024-12-01T19:00:00"}
        })
        query_id += 1

        # IN clause for multiple diagnoses
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_DIAGNOSIS WHERE DiagnosisCode IN ('E11', 'I10', 'J45')",
            "stats": {"total_executions": 490, "avg_duration": 43.2, "last_execution_time": "2024-12-01T19:30:00"}
        })
        query_id += 1

        # Patient medication history
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT p.PatientName, m.MedicationName, m.PrescribedDate FROM dim.DIM_PATIENT p INNER JOIN fact.FACT_MEDICATIONS m ON p.PatientID = m.PatientID ORDER BY m.PrescribedDate DESC",
            "stats": {"total_executions": 720, "avg_duration": 245.7, "last_execution_time": "2024-12-01T20:00:00"}
        })
        query_id += 1

        # High-frequency patients
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT p.PatientID, p.PatientName, COUNT(*) AS VisitCount FROM dim.DIM_PATIENT p INNER JOIN fact.FACT_VISITS v ON p.PatientID = v.PatientID GROUP BY p.PatientID, p.PatientName HAVING COUNT(*) > 10 ORDER BY VisitCount DESC",
            "stats": {"total_executions": 630, "avg_duration": 234.8, "last_execution_time": "2024-12-01T20:30:00"}
        })
        query_id += 1

        # Provider workload
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT pr.ProviderName, COUNT(DISTINCT v.PatientID) AS UniquePatients, COUNT(*) AS TotalVisits, AVG(v.VisitDuration) AS AvgDuration FROM dim.DIM_PROVIDER pr LEFT JOIN fact.FACT_VISITS v ON pr.ProviderID = v.ProviderID GROUP BY pr.ProviderName",
            "stats": {"total_executions": 890, "avg_duration": 298.5, "last_execution_time": "2024-12-01T21:00:00"}
        })
        query_id += 1

        # Recent visits
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM fact.FACT_VISITS WHERE VisitDate >= DATEADD(day, -30, GETDATE()) ORDER BY VisitDate DESC",
            "stats": {"total_executions": 1100, "avg_duration": 189.3, "last_execution_time": "2024-12-01T21:30:00"}
        })
        query_id += 1

        # Subquery for complex patient filtering
        queries.append({
            "query_id": query_id,
            "raw_text": "SELECT * FROM dim.DIM_PATIENT WHERE PatientID IN (SELECT DISTINCT PatientID FROM fact.FACT_VISITS WHERE DiagnosisID IN (SELECT DiagnosisID FROM dim.DIM_DIAGNOSIS WHERE DiagnosisCode LIKE 'E%'))",
            "stats": {"total_executions": 410, "avg_duration": 223.7, "last_execution_time": "2024-12-01T22:00:00"}
        })
        query_id += 1

        return queries
