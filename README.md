# pgsql-search

Simplify PostgreSQL search using Python.


Input a text or image, and get a list of matching items from a PostgreSQL database.

## Features
- [ ] PostgreSQL Full Text Search
- [ ] Embedding based text search
- [ ] Embedding based image search
- [ ] Vector search
- [ ] Text-to-image search
- [ ] Image-to-text search
- [ ] Hybrid search


## Installation
This project uses [Pixi](https://prefix.dev/) to manage dependencies and environments. 
First [install Pixi](https://pixi.sh/latest/). 

Install the project:

```bash
pixi install
```


> [!TIP]
> Why pixi and not uv? \
> \
> We are using PostgreSQL database in this project and it's not installable directly via `uv` or `pip`. But PostgreSQL is installable via conda.
> Instead of using conda, we use Pixi to manage the environment and conda/pip dependencies. Plus, pixi uses `uv` under the hood to pull Python packages.

## Usage

Start the local database server:

```bash
initdb -D mylocal_db
pg_ctl -D mylocal_db -l logfile start

createuser retrieval_user
createdb retrieval_db -O retrieval_user
```

Or using `pixi` tasks:

```bash
pixi run configure-db
```

This initializes the database and starts the server. You should see a folder named `mylocal_db` in your current directory. Also creates a user and database.
Replace `mylocal_db` with your own database name. 

Load a dataset:

```python
from pgsql_search.loader import HuggingFaceDatasets

ds = HuggingFaceDatasets("UCSC-VLAA/Recap-COCO-30K")
ds.save_images("../data/images100")
ds = ds.select_columns(["image_filepath", "caption"])
```


Create a database:

```python
from pgsql_search.database import PostgreSQLDatabase, ColumnType

PostgreSQLDatabase.create_database("my_database")
```

Insert the dataset into the database:

```python
with PostgreSQLDatabase("my_database") as db:
    db.initialize_table("image_metadata")
    db.add_column("image_filepath", ColumnType.TEXT, nullable=False)
    db.add_column("caption", ColumnType.TEXT, nullable=True)

    db.insert_dataframe(df)
```

Run a full text search:

```python
from pgsql_search.database import PostgreSQLDatabase

with PostgreSQLDatabase("my_database") as db:
    res = db.full_text_search("elephant", "image_metadata", "caption", num_results=10)
```

```
| id | image_filepath | caption | query | search_rank |
|----|----------------|---------|-------|-------------|
| 2 | ../data/images100/477389.jpg | The baby elephant is walking with a small obje... | 'eleph' | 0.1 |
```


## Test

```bash
pixi run -e test pytest
```

