import pgsql_search as ps

print(f"Loaded pgsql_search version {ps.__version__}")
ps.search_fts()
