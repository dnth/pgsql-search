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
```

This initializes the database and starts the server. You should see a folder named `mylocal_db` in your current directory.
Replace `mylocal_db` with your own database name. 

## Quickstart
To run the quickstart script, you need to activate the environment first. The pixi shell command will open a shell in the environment where you can run the script like you would in a normal Python environment.

```bash
pixi shell
python scripts/quickstart.py
```

Alternatively by using the `pixi run` command, you can run the script in the environment automatically:

```bash
pixi run python scripts/quickstart.py
```

Or even better you can run this as a pixi task:

```bash
pixi run quickstart
```

Assuming you've already activated the environment, you can run other scripts directly.

Load datasets into the database:

```bash
python scripts/load_datasets.py
```

Insert images into the database:

```bash
python scripts/insert_into_db.py
```

Query the database:

```bash
python scripts/query.py
```



## Test

```bash
pixi run -e test pytest
```

