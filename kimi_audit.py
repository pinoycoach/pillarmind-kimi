"""Phase 0 — Kimi API smoke test + V10 retrieval audit.

Usage (Windows PowerShell):
    $env:MOONSHOT_API_KEY = "sk-..."          # never paste the key into this file
    pip install openai
    python kimi_audit.py --list-models         # step 1: confirm the live model list on YOUR account
    python kimi_audit.py --stack ./stack       # step 2: run the audit

./stack must contain the five V10 files plus v10_stack_audit_2026-09.md.
Output is written to kimi_audit_result.md as UTF-8. It is not printed, because
the Windows console mangles Chinese text.
"""
import argparse
import json
import os
import pathlib
import sys

from openai import OpenAI

BASE_URL = "https://api.moonshot.ai/v1"          # international platform; .cn keys will not work here
DEFAULT_MODEL = "kimi-k2.6"                       # see DECISIONS N4: $web_search reported failing on kimi-k3
WEB_SEARCH = {"type": "builtin_function", "function": {"name": "$web_search"}}
MAX_ROUNDS = 40                                   # hard stop so a search loop cannot run up a bill


def client() -> OpenAI:
    key = os.environ.get("MOONSHOT_API_KEY")
    if not key:
        sys.exit("MOONSHOT_API_KEY is not set in this shell.")
    return OpenAI(api_key=key, base_url=BASE_URL)


def list_models() -> None:
    for m in client().models.list().data:
        print(m.id)


def load_stack(folder: pathlib.Path) -> str:
    files = sorted(folder.glob("*.md"))
    if not files:
        sys.exit(f"No .md files found in {folder}")
    parts = [f"\n\n===== FILE: {f.name} =====\n\n" + f.read_text(encoding="utf-8") for f in files]
    return "".join(parts)


def run_audit(folder: pathlib.Path, model: str) -> None:
    here = pathlib.Path(__file__).parent
    handover = (here / "KIMI-AUDIT-HANDOVER.md").read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": handover},
        {"role": "user", "content": "The operative V10 stack and the September audit follow. "
                                    "Carry out the handover exactly.\n" + load_stack(folder)},
    ]
    c = client()
    searches, total_tokens, nudged = [], 0, False
    for round_no in range(1, MAX_ROUNDS + 1):
        resp = c.chat.completions.create(
            model=model,
            messages=messages,
            tools=[WEB_SEARCH],
            # no temperature: Kimi models enforce their own fixed value and reject anything else
            extra_body={"thinking": {"type": "disabled"}},   # required when $web_search is declared
        )
        total_tokens += resp.usage.total_tokens if resp.usage else 0
        choice = resp.choices[0]
        if choice.finish_reason != "tool_calls" and not searches and not nudged:
            # The model answered from memory. Refuse that answer once and demand retrieval.
            nudged = True
            messages.append({"role": "assistant", "content": choice.message.content or ""})
            messages.append({"role": "user", "content":
                "You made zero web searches, so every item above is recollection-tier and "
                "inadmissible under §1. Discard that answer. Call $web_search for each item "
                "T-1 to T-8 before writing any block, then produce the return format again."})
            print("Round 1 had zero searches: rejected, demanding retrieval...")
            continue
        if choice.finish_reason != "tool_calls":
            header = (
                f"<!-- PROVENANCE  model: {model} | rounds: {round_no} | "
                f"web searches: {len(searches)} | total tokens: {total_tokens} -->\n"
                + "".join(f"<!-- search {i}: {q} -->\n" for i, q in enumerate(searches, 1))
                + "\n"
            )
            out = here / "kimi_audit_result.md"
            out.write_text(header + (choice.message.content or ""), encoding="utf-8")
            print(f"Done. Written to {out}")
            print(f"Rounds: {round_no} | web searches: {len(searches)} | total tokens: {total_tokens}")
            if not searches:
                print("WARNING: zero web searches. Every finding in this result is recollection-tier (E20).")
            return
        messages.append(choice.message)
        for call in choice.message.tool_calls:
            # For $web_search, Kimi runs the search server-side; we echo the arguments back verbatim.
            args = json.loads(call.function.arguments)
            searches.append(json.dumps(args, ensure_ascii=False)[:200])
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": json.dumps(args, ensure_ascii=False),
            })
    sys.exit(f"Stopped after {MAX_ROUNDS} rounds without a final answer.")


if __name__ == "__main__":                         # required on Windows (spawn, not fork)
    p = argparse.ArgumentParser()
    p.add_argument("--list-models", action="store_true")
    p.add_argument("--stack", type=pathlib.Path, default=pathlib.Path("./stack"))
    p.add_argument("--model", default=DEFAULT_MODEL)
    a = p.parse_args()
    list_models() if a.list_models else run_audit(a.stack, a.model)