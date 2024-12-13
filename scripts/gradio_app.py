import json

import gradio as gr
import psycopg
from datasets import load_dataset
from loguru import logger

from pgsql_search.core import PostgresDB


def load_and_insert_dataset(dataset_name: str) -> str:
    """Load dataset from HuggingFace and insert into PostgreSQL"""
    try:
        # Load the dataset
        logger.info(f"Loading dataset: {dataset_name}")
        dataset = load_dataset(dataset_name, split="train")

        # Connect to the database
        conn_string = "dbname=retrieval_db user=retrieval_user"
        db = PostgresDB(conn_string)

        # Create table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS datasets (
            id SERIAL PRIMARY KEY,
            dataset_name TEXT,
            content JSONB
        );
        """
        with db.conn.cursor() as cur:
            cur.execute(create_table_sql)

        # Insert data
        inserted_count = 0
        for item in dataset:
            with db.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO datasets (dataset_name, content) VALUES (%s, %s)",
                    (dataset_name, json.dumps(item)),
                )
                inserted_count += 1

        db.conn.commit()
        return f"Successfully loaded and inserted {inserted_count} items from {dataset_name}"

    except Exception as e:
        return f"Error: {str(e)}"


def search_dataset(query: str) -> str:
    """Search the database using keywords"""
    try:
        conn_string = "dbname=retrieval_db user=retrieval_user"
        db = PostgresDB(conn_string)

        # Perform full-text search across all JSON content
        search_sql = """
        SELECT dataset_name, content
        FROM datasets
        WHERE content::text ILIKE %s
        LIMIT 5;
        """

        with db.conn.cursor() as cur:
            cur.execute(search_sql, (f"%{query}%",))
            results = cur.fetchall()

        if not results:
            return "No results found."

        # Format results
        output = []
        for dataset_name, content in results:
            output.append(f"Dataset: {dataset_name}")
            output.append(f"Content: {json.dumps(content, indent=2)}")
            output.append("-" * 50)

        return "\n".join(output)

    except Exception as e:
        return f"Error: {str(e)}"


# Create Gradio interface
with gr.Blocks() as app:
    gr.Markdown("# Dataset Search App")

    with gr.Tab("Load Dataset"):
        dataset_input = gr.Textbox(
            label="Enter HuggingFace Dataset Name (e.g., 'squad')", placeholder="squad"
        )
        load_button = gr.Button("Load Dataset")
        load_output = gr.Textbox(label="Loading Status")

        load_button.click(
            load_and_insert_dataset, inputs=[dataset_input], outputs=[load_output]
        )

    with gr.Tab("Search"):
        search_input = gr.Textbox(
            label="Enter Search Query", placeholder="Enter keywords to search..."
        )
        search_button = gr.Button("Search")
        search_output = gr.Textbox(label="Search Results")

        search_button.click(
            search_dataset, inputs=[search_input], outputs=[search_output]
        )

if __name__ == "__main__":
    app.launch()
