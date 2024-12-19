[![Python Badge](https://img.shields.io/badge/Python-≥3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pixi Badge](https://img.shields.io/badge/🔌_Powered_by-Pixi-yellow?style=for-the-badge)](https://pixi.sh)
[![PostgreSQL Badge](https://img.shields.io/badge/PostgreSQL-≤16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License Badge](https://img.shields.io/badge/License-Apache%202.0-green.svg?style=for-the-badge&logo=apache&logoColor=white)](https://github.com/prefix-dev/pgsql-search/blob/main/LICENSE)


<div align="center">
    <img src="https://github.com/dnth/pgsql-search/blob/main/assets/logo.png" alt="pgsql-search" width="500">
</div>


## 🌟 Key Features
Currrent and planned features:
- [X] PostgreSQL Full Text Search
- [ ] Embedding based text search
- [ ] Embedding based image search
- [ ] Vector search
- [ ] Text-to-image search
- [ ] Image-to-text search
- [ ] Hybrid search


## 📦 Installation
> [!NOTE]
> If you are running on [Runpod](https://runpod.io/), please create a non root user before installing.

This project uses [Pixi](https://prefix.dev/) to manage dependencies and environments. 
First [install Pixi](https://pixi.sh/latest/). 

Clone the repository:

```bash
git clone https://github.com/dnth/pgsql-search.git

cd pgsql-search
```

Install the project:

```bash
pixi install
```

This should install all the dependencies of the project including PostgreSQL, CUDA, PyTorch, and pgvector into a virtual environment.


> [!TIP]
> Why pixi and not uv? \
> \
> We are using PostgreSQL database in this project and it's not installable directly via `uv` or `pip`. But PostgreSQL is installable via conda.
> Instead of using conda, we use Pixi to manage the environment and conda/pip dependencies. Plus, pixi uses `uv` under the hood to pull Python packages.

## 🚀 Quickstart

Start the local database server using `pixi` tasks:

```bash
pixi run configure-db
```

This initializes the database and starts the server. You should see a folder named `mylocal_db` in your current directory. This folder contains the database files.


Currentely, we only support Hugging Face datasets. Let's load a dataset with images and captions.

```python
from pgsql_search.loader import HuggingFaceDatasets

ds = HuggingFaceDatasets("UCSC-VLAA/Recap-COCO-30K")
ds.save_images("../data/images100")
ds = ds.select_columns(["image_filepath", "caption"])
```

`ds.dataset` is a Hugging Face `Dataset` object. You are free to perform any operations on it.

```python
ds.dataset
```

```
Dataset({
    features: ['image_filepath', 'caption'],
    num_rows: 30504
})
```

Create a database:

```python
from pgsql_search.database import PostgreSQLDatabase, ColumnType

PostgreSQLDatabase.create_database("my_database")
```

Insert the dataset into the database:

```python
df = ds.dataset.to_pandas()

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
    res = db.full_text_search(
        query="people", 
        table_name="image_metadata", 
        search_column="caption", 
        num_results=10
    )
```

`res` is a pandas `DataFrame`:

| id | image_filepath | caption | query | search_rank |
|----|----------------|---------|-------|-------------|
| 2 | ../data/images100/340089.jpg | A group of people who are sitting on couches i... | 'peopl' | 0.1 |
| 51 | ../data/images100/559012.jpg | some people walking on an orange carpet and a ... | 'peopl' | 0.1 |
| 83 | ../data/images100/348379.jpg | A man standing near a group of people with pic... | 'peopl' | 0.1 |
| 95 | ../data/images100/262274.jpg | Group of people walking in front of a white su... | 'peopl' | 0.1 |

Stop the database server:

```bash
pixi run stop-db
```

Remove the database:

```bash
pixi run remove-db
```

## Test

```bash
pixi run -e test pytest
```

