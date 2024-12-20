from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd
import psycopg
from itables import show
from loguru import logger
from pgvector.psycopg import register_vector


class ColumnType(Enum):
    TEXT = "TEXT"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    TIMESTAMP = "TIMESTAMP"
    BOOLEAN = "BOOLEAN"
    VECTOR = "VECTOR"


class Column:
    def __init__(
        self,
        name: str,
        type: ColumnType,
        default: Any | None = None,
        vector_dim: int | None = None,
        nullable: bool = True,
    ):
        self.name = name
        self.type = type
        self.default = default
        self.vector_dim = vector_dim
        self.nullable = nullable

    def get_sql_definition(self) -> str:
        if self.type == ColumnType.VECTOR:
            if not self.vector_dim:
                raise ValueError(
                    "Vector dimension must be specified for vector columns"
                )
            type_str = f"vector({self.vector_dim})"
        else:
            type_str = self.type.value

        sql = f"{self.name} {type_str}"
        if not self.nullable:
            sql += " NOT NULL"
        if self.default is not None:
            if isinstance(self.default, str):
                sql += f" DEFAULT '{self.default}'"
            elif isinstance(self.default, (bool, int, float)):
                sql += f" DEFAULT {self.default}"
            elif isinstance(self.default, datetime):
                sql += f" DEFAULT TIMESTAMP '{self.default}'"
            else:
                sql += f" DEFAULT {self.default}"
        return sql


@dataclass
class SearchResult:
    id: int
    image_filepath: str
    caption: str
    user_query: str
    parsed_query: str
    search_rank: float
    # add other relevant fields

    @classmethod
    def from_db_row(cls, row: tuple, columns: list[str]) -> "SearchResult":
        return cls(**dict(zip(columns, row)))

    @staticmethod
    def to_dataframe(results: list["SearchResult"]) -> pd.DataFrame:
        return pd.DataFrame([vars(result) for result in results])

    @staticmethod
    def to_itables(results: list["SearchResult"]) -> pd.DataFrame:
        """Convert a list of SearchResults to a pandas DataFrame"""
        import base64
        import os
        from pathlib import Path

        def get_image_data_url(filepath: str) -> str:
            try:
                with open(filepath, "rb") as f:
                    data = base64.b64encode(f.read()).decode()
                    ext = Path(filepath).suffix[1:]  # Remove the dot from extension
                    return f"data:image/{ext};base64,{data}"
            except Exception:
                return ""

        def get_file_link(filepath: str) -> str:
            # Check if running in JupyterLab
            if os.environ.get("JPY_PARENT_PID"):
                return f'<a href="files/{filepath}" target="_blank">{filepath}</a>'
            # VS Code or other environments
            return f'<a href="file://{filepath}" target="_blank">{filepath}</a>'

        df = pd.DataFrame([vars(result) for result in results])
        # Add HTML img tag column and make filepath a clickable link
        if "image_filepath" in df.columns:
            df["image"] = df["image_filepath"].apply(
                lambda x: f'<img src="{get_image_data_url(x)}" style="max-height: 150px; max-width: 300px; object-fit: contain;"/>'
            )
            df["image_filepath"] = df["image_filepath"].apply(get_file_link)
        return df


class PostgreSQLDatabase:
    """
    A class to interact with the PostgreSQL database.
    """

    def __init__(self, database_name: str) -> None:
        self.database_name = database_name
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.connect()
        self.setup_pgvector_extension()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        if exc_type:
            logger.error(f"Error: {exc_type} - {exc_val}")
            return False
        return True

    def connect(self):
        try:
            self.conn = psycopg.connect(dbname=self.database_name)
            self.cur = self.conn.cursor()
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        try:
            self.cur.close()
            self.conn.close()
            logger.info("Disconnected from database")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")

    def setup_pgvector_extension(self):
        try:
            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(self.conn)
            logger.info("pgvector extension initialized")
        except Exception as e:
            logger.error(f"Error creating pgvector extension: {e}")

    def initialize_table(self, table_name: str, id_column: str = "id"):
        """
        Initialize a new table with just an ID column.

        Args:
            table_name: Name of the table to create
            id_column: Name of the ID column (defaults to 'id')
        """
        try:
            self.table_name = table_name  # Store table name for future operations
            self.cur.execute(f"""
            DROP TABLE IF EXISTS {table_name};

            CREATE TABLE {table_name} (
                {id_column} SERIAL PRIMARY KEY
            )
            """)
            self.conn.commit()
            logger.info(
                f"Initialized table '{table_name}' with ID column '{id_column}'"
            )
        except Exception as e:
            logger.error(f"Error initializing table: {e}")
            raise

    def add_column(
        self,
        name: str,
        type: ColumnType,
        default: Any | None = None,
        vector_dim: int | None = None,
        nullable: bool = True,
    ):
        """
        Add a single column to the table.

        Examples:
            db.add_column("source", ColumnType.TEXT, default="unknown")
            db.add_column("confidence", ColumnType.FLOAT, default=1.0)
            db.add_column("embedding", ColumnType.VECTOR, vector_dim=512)
        """
        self.add_columns(Column(name, type, default, vector_dim, nullable))

    def add_columns(self, *columns: Column | tuple[str, ColumnType]):
        """
        Add multiple columns to the table.

        Examples:
            db.add_columns(
                Column("source", ColumnType.TEXT, default="unknown"),
                Column("confidence", ColumnType.FLOAT, default=1.0),
                Column("embedding", ColumnType.VECTOR, vector_dim=512),
                ("simple_column", ColumnType.TEXT)  # Simple tuple syntax
            )
        """
        if not hasattr(self, "table_name"):
            raise RuntimeError("Table not initialized. Call initialize_table first.")

        try:
            for col in columns:
                if isinstance(col, tuple):
                    col = Column(col[0], col[1])

                alter_sql = f"ALTER TABLE {self.table_name} ADD COLUMN {col.get_sql_definition()}"
                self.cur.execute(alter_sql)

            self.conn.commit()
            logger.info(
                f"Added {len(columns)} new columns [{', '.join([col.name for col in columns])}] to {self.table_name}"
            )
        except Exception as e:
            logger.error(f"Error adding columns: {e}")
            raise

    def insert_dataframe(self, df: pd.DataFrame, batch_size: int = 1000):
        """
        Insert data from a pandas DataFrame into the table.
        Automatically matches DataFrame columns with table columns.

        Args:
            df: pandas DataFrame containing the data
            batch_size: Number of rows to insert in each batch (default: 1000)
        """
        if not hasattr(self, "table_name"):
            raise RuntimeError("Table not initialized. Call initialize_table first.")

        try:
            # Get existing table columns and their types
            self.cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{self.table_name}'
            """)
            table_columns = {
                row[0].decode() if isinstance(row[0], bytes) else row[0]: row[
                    1
                ].decode()
                if isinstance(row[1], bytes)
                else row[1]
                for row in self.cur.fetchall()
            }

            # Filter DataFrame to only include columns that exist in the table
            valid_columns = [col for col in df.columns if col in table_columns]
            logger.info(f"Table columns: {table_columns}")
            logger.info(f"DataFrame columns: {df.columns}")
            logger.info(f"Valid columns to insert: {valid_columns}")
            if not valid_columns:
                raise ValueError(
                    "No matching columns found between DataFrame and table"
                )

            df_filtered = df[valid_columns]

            # Prepare the insert statement
            columns_str = ", ".join(valid_columns)
            placeholders = ", ".join(["%s"] * len(valid_columns))
            insert_sql = f"""
                INSERT INTO {self.table_name} ({columns_str})
                VALUES ({placeholders})
            """

            # Convert DataFrame to list of tuples
            data = df_filtered.values.tolist()

            # Insert data in batches
            total_rows = len(data)
            for i in range(0, total_rows, batch_size):
                batch = data[i : i + batch_size]
                self.cur.executemany(insert_sql, batch)
                self.conn.commit()
                logger.info(
                    f"Inserted batch {i//batch_size + 1} ({min(i + batch_size, total_rows)}/{total_rows} rows)"
                )

            logger.info(
                f"Successfully inserted {total_rows} rows into {self.table_name}"
            )

            # Log any columns that were in DataFrame but not in table
            skipped_columns = set(df.columns) - set(valid_columns)
            if skipped_columns:
                logger.warning(f"Skipped columns not in table: {skipped_columns}")

        except Exception as e:
            logger.error(f"Error inserting data: {e}")
            raise

    def full_text_search(
        self,
        query: str,
        table_name: str,
        search_column: str,
        num_results: int = 10,
    ) -> pd.DataFrame:
        """
        Perform a full-text search on the table.

        Args:
            query: Search query string
            table_name: Name of the table to search
            search_column: Column to perform the search on
            num_results: Maximum number of results to return
            return_dataframe: If True, returns results as pandas DataFrame

        Returns:
            Either List[SearchResult] or pd.DataFrame depending on return_dataframe parameter
        """
        try:
            self.cur.execute(
                f"""
                    SELECT *,
                        %(query)s as user_query,
                        ts_rank_cd(to_tsvector('english', {search_column}), parsed_query) as search_rank
                    FROM {table_name}, plainto_tsquery('english', %(query)s) parsed_query
                    WHERE to_tsvector('english', {search_column}) @@ parsed_query
                    ORDER BY search_rank DESC
                    LIMIT {num_results}
                """,
                {"query": query},
            )

            # Get column names from cursor description
            columns = [desc[0] for desc in self.cur.description]
            results = self.cur.fetchall()

            results = [SearchResult.from_db_row(row, columns) for row in results]

            df = SearchResult.to_itables(results)

            show(
                df,
                classes="display",
                style="width:100%;margin:auto",
                columnDefs=[{"className": "dt-left", "targets": "_all"}],
            )

            return SearchResult.to_dataframe(results)

        except Exception as e:
            logger.error(f"Error performing text search: {e}")
            raise

    @staticmethod
    def create_database(database_name: str) -> None:
        """
        Creates a new PostgreSQL database if it doesn't exist.

        Args:
            database_name: Name of the database to create
        """
        try:
            with psycopg.connect(dbname="postgres") as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    # Check if database exists
                    cur.execute(
                        "SELECT 1 FROM pg_database WHERE datname = %s", (database_name,)
                    )
                    if not cur.fetchone():
                        cur.execute(f"CREATE DATABASE {database_name}")
                        logger.info(f"Created database '{database_name}'")
                    else:
                        logger.info(f"Database '{database_name}' already exists")
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
