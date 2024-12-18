import pgsql_search as ps

# model = ps.models.CLIP()

# result = ps.search_fts(query="dog")
# print(result)


ps.load_hf_dataset(dataset_id="UCSC-VLAA/Recap-COCO-30K")
