# Badge Memory

A conference-memory agent with **no cold start**. I wear Mentra Live camera
glasses and a mic at an event; conversations become person cards and embedded
memories in MongoDB Atlas. Kill the process, restart it, it comes back knowing
everyone I met. Ask it "who did I meet from Mentra and what did we talk about"
and it answers with receipts, then drafts the follow-up I promised.

Built solo at **MongoDB.local Build Fest — The Persistent Context Sprint**,
2026-08-13, 1:30–5:00 PM, on the event's Atlas Sandbox cluster.

## Why it isn't a cold-start agent

Stored state changes what the system does next, three different ways:

1. **Checkpointed ingest** (`checkpoints` collection): every pipeline step
   (transcribe → extract → embed → store) checkpoints to Atlas first. A crash
   mid-ingest resumes at the failed step. Demo: `Ctrl-C` during embedding,
   rerun, watch it skip straight to where it died.
2. **Adaptive retrieval** (`retrieval_outcomes` collection): every query logs
   which strategy ($vectorSearch vs Atlas $search) actually produced the used
   answer. The next query reads the aggregate win-rate and reorders its
   strategy. The pipeline you run at 5 PM is not the pipeline you ran at 2 PM.
3. **Accumulating person cards** (`people` collection): meeting someone twice
   deepens their card (`$addToSet` topics/promises/quotes) instead of
   overwriting it. The agent greets returning people with the delta.

## MongoDB used

- **Atlas Vector Search** (`$vectorSearch`, 768-d nomic embeddings with correct
  asymmetric task prefixes) for semantic recall
- **Atlas Search** (`$search`) for exact-name/keyword recall
- **Aggregation** for strategy win-rates (Laplace-smoothed) and stats
- Four collections: `people`, `memories`, `checkpoints`, `retrieval_outcomes`

## Run it

```bash
export SANDBOX_MONGODB_URI='mongodb+srv://...'
uv sync                     # pymongo only
uv run python ingest.py --text "transcript here" --context "booth chat"
uv run python setup_indexes.py          # once
uv run python recall.py "who did I promise an intro to?"
uv run python recall.py --followup "Alexander"
uv run python recall.py --stats
```

LLM + embeddings default to local ollama (`gemma4:12b`, `nomic-embed-text`) —
the whole demo runs with zero external API calls. Any OpenAI-compatible
endpoint works via `LLM_BASE_URL` / `LLM_MODEL`.

## Provenance

All code in this repo was written during the hack window (first commit
timestamp is the receipt). The conversations ingested are my own, recorded
today at Build Fest with the other person's consent. The glasses capture the
audio; the pipeline doesn't care which microphone wrote the file.
