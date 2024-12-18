from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

import pandas as pd
import psycopg
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
        default: Optional[Any] = None,
        vector_dim: Optional[int] = None,
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
        default: Optional[Any] = None,
        vector_dim: Optional[int] = None,
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

    def add_columns(self, *columns: Union[Column, tuple[str, ColumnType]]):
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
            logger.info(f"Added {len(columns)} new columns to {self.table_name}")
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
            table_columns = {row[0]: row[1] for row in self.cur.fetchall()}

            # Filter DataFrame to only include columns that exist in the table
            valid_columns = [col for col in df.columns if col in table_columns]
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
        self, query: str, table_name: str, search_column: str, num_results: int = 10
    ) -> pd.DataFrame:
        """
        Perform a full-text search on the table.

        Returns:
            pandas.DataFrame: Results with columns from the table plus a 'search_rank' column
        """
        try:
            self.cur.execute(
                f"""
                    SELECT *,
                        ts_rank_cd(to_tsvector('english', {search_column}), query) as search_rank
                    FROM {table_name}, plainto_tsquery('english', %(query)s) query
                    WHERE to_tsvector('english', {search_column}) @@ query
                    ORDER BY search_rank DESC
                    LIMIT {num_results}
                """,
                {"query": query},
            )

            # Get column names from cursor description
            columns = [desc[0] for desc in self.cur.description]
            results = self.cur.fetchall()

            # Convert to DataFrame with proper column names
            df_results = pd.DataFrame(results, columns=columns)

            logger.info(f"Found {len(results)} results for query: {query}")
            return df_results
        except Exception as e:
            logger.error(f"Error performing text search: {e}")
            raise
