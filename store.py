"""Badge Memory — MongoDB Atlas Sandbox store layer.

Collections:
    people             one card per person met (name, role, topics, promises)
    memories           conversation chunks with 768-d embeddings
    checkpoints        pipeline + agent state; the no-cold-start backbone
    retrieval_outcomes which retrieval strategy actually answered each query

Built live at MongoDB.local Build Fest, 2026-08-13, for the Persistent Context
Sprint ("No Cold Start"). Everything runs on the event's Atlas Sandbox cluster.
"""
import os
import sys
import time

from pymongo import MongoClient, ReturnDocument

URI = os.environ.get("SANDBOX_MONGODB_URI")
if not URI:
    sys.exit("SANDBOX_MONGODB_URI not set — export the sandbox SRV string")

client = MongoClient(URI, serverSelectionTimeoutMS=15000)
db = client["badge_memory"]
people = db["people"]
memories = db["memories"]
checkpoints = db["checkpoints"]
outcomes = db["retrieval_outcomes"]


def checkpoint(run_id, step, state=None):
    """Persist pipeline progress. A crashed run resumes instead of restarting —
    state changes what happens next, it doesn't just fill a prompt."""
    checkpoints.find_one_and_update(
        {"run_id": run_id},
        {"$set": {"step": step, "state": state or {}, "at": time.time()},
         "$push": {"history": {"step": step, "at": time.time()}}},
        upsert=True, return_document=ReturnDocument.AFTER)


def resume_point(run_id):
    doc = checkpoints.find_one({"run_id": run_id})
    return (doc["step"], doc.get("state") or {}) if doc else (None, {})


def upsert_person(card):
    """Merge-don't-overwrite: topics/promises/quotes accumulate across
    conversations, so meeting someone twice deepens the card."""
    name = card["name"].strip()
    update = {
        "$setOnInsert": {"name": name, "first_met": time.time()},
        "$set": {k: v for k, v in card.items()
                 if k in ("company", "role") and v},
        "$addToSet": {},
    }
    for field in ("topics", "promises", "quotes"):
        if card.get(field):
            update["$addToSet"][field] = {"$each": card[field]}
    if not update["$addToSet"]:
        update.pop("$addToSet")
    return people.find_one_and_update(
        {"name_key": name.lower()},
        {**update, "$set": {**update.get("$set", {}), "name_key": name.lower(),
                            "last_seen": time.time()}},
        upsert=True, return_document=ReturnDocument.AFTER)


def add_memory(doc):
    memories.update_one({"chunk_key": doc["chunk_key"]},
                        {"$set": doc}, upsert=True)


def log_outcome(query, strategy, hit_count, used):
    """The learning loop: every query records which strategy produced the
    documents the answer actually used. recall.py reads the aggregate to decide
    strategy order on the NEXT query."""
    outcomes.insert_one({"query": query, "strategy": strategy,
                         "hit_count": hit_count, "used": bool(used),
                         "at": time.time()})


def strategy_weights():
    pipe = [{"$group": {"_id": "$strategy",
                        "wins": {"$sum": {"$cond": ["$used", 1, 0]}},
                        "runs": {"$sum": 1}}}]
    stats = {d["_id"]: (d["wins"] + 1) / (d["runs"] + 2)   # Laplace smoothing
             for d in outcomes.aggregate(pipe)}
    return stats
