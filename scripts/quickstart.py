from pgsql_search.database import ColumnType, PostgreSQLDatabase
from pgsql_search.loader import HuggingFaceDatasets

ds = HuggingFaceDatasets("UCSC-VLAA/Recap-COCO-30K")
# ds.dataset = ds.dataset.shuffle()
# ds = ds.select(list(range(100)))
ds.save_images("../data/images")
ds = ds.select_columns(["image_filepath", "caption"])

df = ds.dataset.to_pandas()
print(df.head())


PostgreSQLDatabase.create_database("my_database")

with PostgreSQLDatabase("my_database") as db:
    # First, create the table with just an ID column
    db.initialize_table("image_metadata")
    db.add_column("image_filepath", ColumnType.TEXT, nullable=False)
    db.add_column("caption", ColumnType.TEXT, nullable=True)
    db.insert_dataframe(df)


with PostgreSQLDatabase("my_database") as db:
    res = db.full_text_search(
        query="man in a yellow shirt",
        table_name="image_metadata",
        search_column="caption",
        num_results=10,
        interactive_output=False,
    )


print(res)
