"""Recall + follow-up agent with ADAPTIVE retrieval.

    uv run python recall.py "who did I meet from Mentra and what did we discuss?"
    uv run python recall.py --followup "Alexander Israelov"
    uv run python recall.py --stats

Strategy order is chosen from the retrieval_outcomes collection: the system
prefers whichever of $vectorSearch / $search has actually produced used answers
so far. Stored outcomes change the next run's behavior — no cold start, and no
static pipeline either.
"""
import argparse
import json

import llm
import store

ANSWER_PROMPT = """Answer from the retrieved memory below. Cite people by name.
If the memory doesn't contain the answer, say so plainly. 3 sentences max."""

FOLLOWUP_PROMPT = """Write a 3-sentence follow-up message from Carl to this
person. Reference what they discussed and any promise made. Warm, direct, no
corporate filler, no exclamation marks."""


def vector_search(query, k=5):
    qv = llm.embed(query, kind="search_query")
    return list(store.memories.aggregate([
        {"$vectorSearch": {"index": "vec_memories", "path": "embedding",
                           "queryVector": qv, "numCandidates": 200, "limit": k}},
        {"$project": {"_id": 0, "text": 1, "people": 1, "context": 1,
                      "score": {"$meta": "vectorSearchScore"}}}]))


def keyword_search(query, k=5):
    return list(store.memories.aggregate([
        {"$search": {"index": "fts_memories",
                     "text": {"query": query, "path": ["text", "people",
                                                       "context"]}}},
        {"$limit": k},
        {"$project": {"_id": 0, "text": 1, "people": 1, "context": 1}}]))


def ask(query):
    weights = store.strategy_weights()
    order = sorted(["vector", "keyword"],
                   key=lambda s: -weights.get(s, 0.5))
    print(f"strategy weights {weights or '(no history yet)'} -> order {order}")
    hits, strategy_used = [], None
    for strat in order:
        fn = vector_search if strat == "vector" else keyword_search
        try:
            hits = fn(query)
        except Exception as exc:
            print(f"  {strat} failed: {exc}")
            continue
        print(f"  {strat}: {len(hits)} hits")
        if hits:
            strategy_used = strat
            break
    if not hits:
        print("no memory found")
        return
    ctx = "\n---\n".join(f"[{h.get('context','')}] {h['text']}" for h in hits)
    answer = llm.chat([{"role": "system", "content": ANSWER_PROMPT},
                       {"role": "user", "content": f"Q: {query}\n\nMEMORY:\n{ctx}"}])
    print("\n" + answer + "\n")
    for h in hits[:3]:
        tag = f" ({h['score']:.3f})" if "score" in h else ""
        print(f"  source{tag}: {h['text'][:90]}")
    for strat in order:
        store.log_outcome(query, strat, len(hits),
                          used=(strat == strategy_used))


def followup(name):
    card = store.people.find_one({"name_key": name.lower()})
    if not card:
        # fuzzy: partial match
        card = store.people.find_one(
            {"name_key": {"$regex": name.lower().split()[0]}})
    if not card:
        print(f"no person card for {name!r}")
        return
    msg = llm.chat([{"role": "system", "content": FOLLOWUP_PROMPT},
                    {"role": "user", "content": json.dumps(
                        {k: card.get(k) for k in
                         ("name", "company", "role", "topics", "promises",
                          "quotes")}, default=str)}])
    print(f"\n--- follow-up to {card['name']} ---\n{msg}\n")


def stats():
    print("people:", store.people.count_documents({}))
    print("memories:", store.memories.count_documents({}))
    print("checkpoints:", store.checkpoints.count_documents({}))
    print("outcomes:", store.outcomes.count_documents({}))
    print("strategy weights:", store.strategy_weights())
    for p in store.people.find({}, {"_id": 0, "name": 1, "company": 1,
                                    "topics": 1}):
        print(" ", p.get("name"), "|", p.get("company", "?"),
              "|", ", ".join((p.get("topics") or [])[:4]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*")
    ap.add_argument("--followup")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats:
        stats()
    elif args.followup:
        followup(args.followup)
    elif args.query:
        ask(" ".join(args.query))
    else:
        print(__doc__)
