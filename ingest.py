"""Ingest a conversation into Badge Memory — checkpointed at every step.

    uv run python ingest.py --text "..." --context "walk with Mentra CTO"
    uv run python ingest.py --audio path/to/convo.wav --context "booth chat"

Steps (each lands in the checkpoints collection before it runs):
    1. transcribe   (whisper-cli, only for --audio)
    2. extract      (LLM -> person cards + summary as JSON)
    3. embed        (chunk + nomic embeddings)
    4. store        (person cards merged, memory chunks upserted)

Kill it at any step and rerun with the same --run-id: it resumes from the
checkpoint instead of starting cold. That's the point.
"""
import argparse
import hashlib
import subprocess
import sys
import tempfile
import time

import llm
import store

EXTRACT_PROMPT = """You turn a conversation transcript into structured memory.
Return ONLY JSON:
{"people": [{"name": "...", "company": "...", "role": "...",
             "topics": ["..."], "promises": ["what the user promised or was promised"],
             "quotes": ["short memorable lines"]}],
 "summary": "3 sentences, past tense, names included",
 "chunks": ["self-contained 2-4 sentence passages preserving who said what"]}
Only include people who actually speak or are described. The user is Carl —
NEVER include Carl himself in "people"; cards are for the people he meets."""


def transcribe(audio_path):
    wav = audio_path
    if not audio_path.endswith(".wav"):
        wav = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-ar", "16000",
                        "-ac", "1", wav], check=True, capture_output=True)
    out = subprocess.run(
        ["/opt/homebrew/bin/whisper-cli", "-f", wav, "-np", "-nt"],
        check=True, capture_output=True, text=True)
    return out.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--audio")
    ap.add_argument("--context", default="", help="where/when this happened")
    ap.add_argument("--run-id")
    args = ap.parse_args()
    if not (args.text or args.audio):
        sys.exit("need --text or --audio")

    src = args.text or args.audio
    run_id = args.run_id or "ing-" + hashlib.sha1(src.encode()).hexdigest()[:10]
    step, state = store.resume_point(run_id)
    print(f"[{run_id}] resume point: {step or 'fresh start'}")

    if step in (None,):
        store.checkpoint(run_id, "transcribe", {})
        text = args.text or transcribe(args.audio)
        state = {"text": text, "context": args.context}
        store.checkpoint(run_id, "extract", state)
        step = "extract"
        print(f"  transcript: {len(state['text'])} chars")

    if step == "extract":
        raw = llm.chat([{"role": "system", "content": EXTRACT_PROMPT},
                        {"role": "user", "content":
                         f"Context: {state['context']}\n\n{state['text']}"}])
        state["extracted"] = llm.extract_json(raw)
        store.checkpoint(run_id, "embed", state)
        step = "embed"
        ppl = [p["name"] for p in state["extracted"].get("people", [])]
        print(f"  extracted people: {ppl}")

    if step == "embed":
        vecs = []
        for chunk in state["extracted"].get("chunks", []):
            vecs.append((chunk, llm.embed(chunk)))
        state["n_vecs"] = len(vecs)
        # store immediately; embedding is the slow step worth crash-protecting
        now = time.time()
        for i, (chunk, vec) in enumerate(vecs):
            store.add_memory({
                "chunk_key": f"{run_id}:{i}",
                "run_id": run_id, "text": chunk, "embedding": vec,
                "context": state["context"], "at": now,
                "people": [p["name"] for p in
                           state["extracted"].get("people", [])],
                "summary": state["extracted"].get("summary", "")})
        store.checkpoint(run_id, "store", state)
        step = "store"
        print(f"  embedded + stored {len(vecs)} chunks")

    if step == "store":
        for card in state.get("extracted", {}).get("people", []):
            doc = store.upsert_person(card)
            print(f"  person card: {doc['name']} "
                  f"(topics: {len(doc.get('topics', []))}, "
                  f"promises: {len(doc.get('promises', []))})")
        store.checkpoint(run_id, "done", {"finished": time.time()})
        print(f"[{run_id}] done — memory persists; next run starts warm")


if __name__ == "__main__":
    main()
