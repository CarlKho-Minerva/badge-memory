# Badge Memory — recording + submission run sheet

Database is WIPED CLEAN (smoke data deleted, indexes stay). Everything below
assumes a fresh start so the recording shows real ingest, live.

## 0. Setup (before hitting record)

```bash
cd ~/CODELocalProjects/badge-memory
export $(grep '^SANDBOX_MONGODB_URI=' ~/.config/carl-life-os/.env)
```

- Drop the filmed audio here as `alex.m4a` and `mongo-pm.m4a` (any format works,
  ffmpeg converts; if whisper mangles it, paste the transcript with
  `--text "..."` instead).
- Terminal: big font (Cmd+ +, 3 or 4 times), dark theme, full screen.
- Second browser tab open: Atlas → Data Explorer → `badge_memory` collections.
- Warm the model once so recording has no cold pauses (ha):
  `uv run python -c "import llm; llm.chat([{'role':'user','content':'hi'}])"`

## 1. Loom screen recording — one take, ~90s raw, cut to ~35s

Run these in order. The seconds are what survives the edit.

| # | Command | What to say / show | Keeps |
|---|---|---|---|
| 1 | `uv run python ingest.py --audio alex.m4a --context "walk with Mentra CTO, Build Fest"` | "The glasses caught my chat with Mentra's CTO. Watch the pipeline: transcribe, extract, embed, store — every step checkpoints to Atlas FIRST." | ~6s |
| 2 | **Ctrl-C while it thinks after** `transcript: N chars` **(the extract pause)** | "I just killed it mid-run." | ~2s |
| 3 | Press ↑, rerun the SAME command | Point at `resume point: extract` — "It resumes where it died. No cold start." | ~5s |
| 4 | `uv run python ingest.py --audio mongo-pm.m4a --context "MongoDB startups booth"` | "Second conversation." (can time-lapse this one) | ~3s |
| 5 | `uv run python recall.py "where is Mentra's office again?"` | Answer + cited chunks + similarity score on screen. "Semantic recall with receipts — Atlas Vector Search." | ~7s |
| 6 | `uv run python recall.py "what did the MongoDB startups team promise me?"` | (optional, cut if long) | ~4s |
| 7 | `uv run python recall.py --stats` | Point at strategy weights: "Every query logs which retrieval strategy won. The next query reorders itself. Stored state changes behavior — not just the prompt." | ~5s |
| 8 | `uv run python recall.py --followup "Alexander"` | "And it drafts the follow-up I promised him." | ~4s |
| 9 | Switch to Data Explorer tab, hover the 4 collections | "people, memories, checkpoints, retrieval_outcomes." | ~4s |

**Retake rule:** if a take flubs, wipe and go again:
```bash
uv run python - <<'EOF'
import store
for c in (store.memories, store.people, store.checkpoints, store.outcomes):
    c.delete_many({})
EOF
```

## 2. Edit order (60s total)

1. 0:00–0:08 — Shot 1: walk-up, zoom, "...what's his name again?", freeze.
   1s title card: **BADGE MEMORY — no cold start**
2. 0:08–0:15 — Shot 2: glasses on, mic B-roll, confident "Alex!" take.
   Caption: *same brain, warm memory.*
3. 0:15–0:50 — Loom cuts, rows 1→3→5→7→8 mandatory, 4/6/9 as time allows.
   Overlay the transcript text during row 1.
4. 0:50–0:60 — Data Explorer + end card: `github.com/CarlKho-Minerva/badge-memory`
   VO: "Vector search, Atlas Search, and state that changes behavior.
   Badge Memory — your agent already knows."

## 3. Submission (CV platform, DONE BY 4:45)

- [ ] Video uploaded, link opens in incognito (their #1 warning: Drive perms)
- [ ] Repo public: `github.com/CarlKho-Minerva/badge-memory` ✓ (already is)
- [ ] Commit + push DEMO.md and any final tweaks:
      `git add -A && git commit -m "demo run sheet + final tweaks" && git push`
- [ ] Project description, paste-ready:

> Badge Memory is a no-cold-start conference memory agent. Mentra Live glasses
> capture my real conversations; a checkpointed pipeline (whisper → LLM person
> cards → 768-d embeddings) lands them in four Atlas collections. Kill the
> process mid-ingest and it resumes from its Atlas checkpoint. Recall runs
> Atlas Vector Search and Atlas Search, cites its sources, and logs which
> strategy actually answered into retrieval_outcomes — future queries reorder
> their strategy by stored win-rate, so state changes behavior instead of just
> filling the prompt. Person cards accumulate across meetings ($addToSet), and
> the agent drafts the follow-ups I promised. Built solo, all inference local
> (gemma4:12b + nomic), all state in the event sandbox cluster.

- [ ] Backend blurb if asked: Python + pymongo only. Collections: people,
      memories, checkpoints, retrieval_outcomes. Indexes: vec_memories
      (vectorSearch, 768, cosine), fts_memories (Atlas Search). LLM/embeddings:
      local ollama, OpenAI-compatible, env-swappable.

## 4. After submitting

Imbue + errands. **Back at Embarcadero Stage entrance 6:45** for finalists.
If picked: the live demo is rows 5→7→8 plus the kill/restart — rehearse once
on hotspot before leaving (venue IP is on the access list; hotspot IP is NOT —
add it in Atlas Network Access if you'll demo off venue wifi).
