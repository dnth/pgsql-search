# pgsql-search

Simplify PostgreSQL search using Python.


Input a text or image, and get a list of similar items from a PostgreSQL database.

## Features
- [ ] PostgreSQL Full Text Search
- [ ] Embedding based text search
- [ ] Embedding based image search
- [ ] Vector search
- [ ] Text-to-image search
- [ ] Image-to-text search


## Installation


## Usage

Start the local database server:

```bash
initdb -D mylocal_db
pg_ctl -D mylocal_db -l logfile start
```

This initializes the database and starts the server. You should see a folder named `mylocal_db` in your current directory.
Replace `mylocal_db` with your own database name. 
