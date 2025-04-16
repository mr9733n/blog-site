# backend/migrations/initialize_columns.py
import sqlite3
import os
import sys
import json
from datetime import datetime, timezone

# Add parent directory to path so we can import from backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.config import get_config


def execute_query(conn, query, params=None):
    """Execute a query safely, catching column already exists errors"""
    try:
        if params:
            conn.execute(query, params)
        else:
            conn.execute(query)
        return True
    except sqlite3.OperationalError as e:
        # If it's a "column already exists" error, just log and continue
        if "duplicate column name" in str(e) or "already exists" in str(e):
            print(f"Note: {e}")
            return True
        # Otherwise re-raise the exception
        print(f"Error: {e}")
        return False


def initialize_empty_columns(database_path):
    """
    Initialize columns that might be empty with default values
    This helps avoid errors when accessing columns that exist but have NULL values
    """
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row

    print(f"Connected to database at {database_path}")
    print(f"Starting column initialization at {datetime.now(timezone.utc).isoformat()}")

    try:
        # Check if columns exist and initialize them if they're empty
        columns_to_initialize = [
            {
                "name": "ip_network_hash",
                "default": None,
                "table": "user_sessions"
            },
            {
                "name": "activity_times",
                "default": "[]",  # Empty JSON array
                "table": "user_sessions"
            },
            {
                "name": "request_counter",
                "default": 0,
                "table": "user_sessions"
            },
            {
                "name": "last_counter_update",
                "default": datetime.now(timezone.utc).isoformat(),
                "table": "user_sessions"
            }
        ]

        for column in columns_to_initialize:
            # Check if column exists
            try:
                conn.execute(f"SELECT {column['name']} FROM {column['table']} LIMIT 1")
                print(f"Column {column['name']} exists in table {column['table']}")

                # Update NULL values to default values
                if column['default'] is not None:
                    default_value = column['default']
                    if isinstance(default_value, (dict, list)):
                        default_value = json.dumps(default_value)

                    print(f"Initializing empty {column['name']} values with {default_value}")
                    conn.execute(
                        f"UPDATE {column['table']} SET {column['name']} = ? WHERE {column['name']} IS NULL",
                        [default_value]
                    )
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                print(f"Column {column['name']} doesn't exist in {column['table']}, adding it")

                default_clause = ""
                if column['default'] is not None:
                    if isinstance(column['default'], (int, float)):
                        default_clause = f" DEFAULT {column['default']}"
                    else:
                        default_clause = f" DEFAULT '{column['default']}'"

                column_type = "INTEGER" if isinstance(column['default'], int) else "TEXT"
                conn.execute(f"ALTER TABLE {column['table']} ADD COLUMN {column['name']} {column_type}{default_clause}")

        # Commit all changes
        conn.commit()
        print("Column initialization completed successfully")

    except Exception as e:
        print(f"Error during initialization: {e}")
    finally:
        conn.close()

    print(f"Column initialization finished at {datetime.now(timezone.utc).isoformat()}")


def main():
    # Get database path from config
    config = get_config()
    database_path = config.DATABASE_PATH

    # Initialize columns
    initialize_empty_columns(database_path)


if __name__ == "__main__":
    main()