"""Create the sandbox search indexes programmatically. Run once after first ingest.

    uv run python setup_indexes.py
"""
import time

from pymongo.operations import SearchIndexModel

import store

# ensure collection exists before index creation
if store.memories.count_documents({}) == 0:
    store.memories.insert_one({"chunk_key": "_seed", "text": "seed",
                               "people": [], "context": "seed"})

existing = {ix["name"] for ix in store.memories.list_search_indexes()}
if "vec_memories" not in existing:
    store.memories.create_search_index(SearchIndexModel(
        name="vec_memories", type="vectorSearch",
        definition={"fields": [
            {"type": "vector", "path": "embedding", "numDimensions": 768,
             "similarity": "cosine"},
            {"type": "filter", "path": "people"}]}))
if "fts_memories" not in existing:
    store.memories.create_search_index(SearchIndexModel(
        name="fts_memories", type="search",
        definition={"mappings": {"dynamic": False, "fields": {
            "text": {"type": "string"}, "people": {"type": "string"},
            "context": {"type": "string"}}}}))

for _ in range(30):
    states = {ix["name"]: ix.get("queryable")
              for ix in store.memories.list_search_indexes()}
    print(states)
    if all(states.values()):
        print("indexes queryable")
        break
    time.sleep(10)
store.memories.delete_one({"chunk_key": "_seed"})
