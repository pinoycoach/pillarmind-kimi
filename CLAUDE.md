# CLAUDE.md — PillarMind × Kimi, Phase 1

Read this before writing any code. Per the Build Standard, facts live here in one place — don't
re-derive them from chat scrollback, and don't ask the user to repeat them.

## What this phase is, and is not

**Phase 1 builds the resolver. Nothing else.** Input: a birth datetime + city + sex (or a birth
date alone, in hour-unknown mode). Output: a Resolved Field Map — pillars, void, hidden stems,
every combination/clash/harm/destruction/punishment resolved per the V10 rules — as a JSON object.
Deterministic. No LLM call anywhere in this phase. No Kimi, no Claude API, nothing. If a function
in this phase calls out to a language model, that's a sign the phase boundary broke.

Kimi's actual job — writing an interpretation from a Resolved Field Map — is Phase 3, and it needs
none of the resolver's internals, only its JSON output. Don't build toward it yet.

## Facts, in one place

- **Pillar derivation engine:** `lunar-python`. Never derive pillars, void, or hidden-stem tables
  by any other method. This is V10 U1 / U14 — closed taxonomies, no inference.
- **The rule text lives in:** `stack/v10_0_1c.md`, `v10_0_1d_with_addendum_A.md`,
  `v10_0_1e_1_handover.md` + Addenda A, B, `v10_0_1f_reconciliation_ledger.md`,
  `v10_0_1f_addendum_A.md` — read in that order; later documents amend earlier ones,
  nothing is rewritten in place.
- **Open decisions and their status:** `DECISIONS.md`, same folder. Read it now. Nothing in it is
  BLOCKING. Operator rulings recorded there override the stack's own escalation defaults.
- **Environment (Build Standard pt 8), N3 resolved:** builder OS Windows, runner OS Windows,
  deploy target Linux (Railway). `pathlib` only, no hard-coded separators; multiprocessing behind
  `if __name__ == "__main__":`; files read and written as UTF-8 explicitly.

## N1 and N2 — ruled 23 Sep 2026

Both are the operator's rulings, recorded in `DECISIONS.md` (Resolved) with their basis. Apply
them; don't reopen them.

- **N1 / R-DEF-1:** an ungated 六合 is **LOCKED_FULL**. Located: 子平真詮 ch. 7 原文
  「有戌，則卯與戌合而不沖」, with no 化 condition in the chapter.
- **N2 / R-DEF-2:** a clash standing across layers does **not** block a later capture of one of its
  legs (capture allowed). This is a declared engine decision, inference tier: ch. 25 「逢沖而不沖」,
  applied by analogy. Same-layer cases are E-8b and still escalate.

**The seam.** Both live in `resolver/rulings.py` as `resolve_six_harmony_lock()` and
`check_layer_seniority()`, each opening with a single unruled branch that returns the escalation
object. The rulings are the constants `R_DEF_1_RULING` and `R_DEF_2_RULING`. Setting either back to
`None` restores the escalation, with no change downstream. The `unruled` fixture in
`tests/test_rules.py` keeps that path tested. Don't delete the unruled branches.

**Everything else still escalates, never guesses.** Unruled conditions (E-21, E-8b, E-5, U5's two
readings of 旺月, L-3's missing gate months, E-23-scope, and others) come back ESCALATED in the
JSON with every candidate, exactly as the V10 texts escalate in prose. Where an escalation changes
downstream resolution, the engine runs one world per candidate and reports each differing field
with its pending ruling (0.1c §2.5, "give both maps"). A new operator ruling lands the same way:
record it in `DECISIONS.md`, then change only the function that escalates on it.

## Verification, per Build Standard pt 14

The bench has already hand-derived Resolved Field Maps for real charts, with documented findings.
They are golden cases in `golden/`, one JSON expected-output file per chart, checked by
`tests/test_golden.py`. Per Build Standard pt 9 that test calls the real pipeline
(derive → resolve), never already-computed fixtures in memory. Expected values come from the
bench's findings and the operator's rulings, never from the resolver's own output.

- **digong** (1945-03-28 02:20, Maasin, male; 乙酉/己卯/丙申/己丑, decade 辛未, annual 丙午 2026) —
  under N1/N2, the 0.1e ratified map: 午未 LOCKED_FULL with 丑未 / 丑午 / 卯午 ELIMINATED, 卯酉
  at full force, void 辰巳. The 丙/丙/辛 stem contest stays ESCALATED on E-21.
- **sara** (戊午/丁巳/癸巳, void 午未, **hour unknown** — hour-unknown mode, no birth time
  assumed). Her real birth data lives only in `golden_local/` (git-ignored); the committed
  `golden/sara_2026_08.json` uses a placeholder date that reproduces the same pillars — August 2026 layer (丙申 month): a 巳申 六合 under
  E-5's gate-divergence finding.
- **AA** (庚戌/甲申/甲申/丙寅) — the E-23 duplicate-branch clash: natal alone, no clash; in the 庚寅
  decade, the clash returns. **Optional.** Its two golden files skip until birth data is supplied.
  That's not a blocker, and they stay skipped until the operator provides it.

## Definition of done for Phase 1

- Resolver takes a birth datetime + city + sex (or a birth date in hour-unknown mode), returns a
  Resolved Field Map JSON.
- The digong and sara golden cases match on the real pipeline. AA's are optional and may stay
  skipped.
- Zero network calls, zero LLM calls, anywhere in this phase's code path.
- `DECISIONS.md` current: N1 and N2 resolved with their basis, N16 recording the seam
  (`resolver/rulings.py`), and every other open item matching what the resolver escalates.
- A three-part phase report per the original Build Standard, plus the retro line for this specific
  phase: what a bench-hand-derivation catches that a golden-case JSON diff wouldn't (worth naming
  honestly — probably prose-quality and citation accuracy, neither of which this phase produces).

## What's explicitly out of scope here

Kimi API calls of any kind. The interpretation prompt. The runtime-prompt compile question (N6).
Anything about which Kimi model to use (N5) — that's a Phase 3 decision made on output quality,
not needed to build a resolver.

## Standing rules

Per `DECISIONS.md` N32 (which amends N30):

- No commit reaches `main` without an operator decision. Never push to or merge into `main`
  without the operator's explicit "merge".
- All work, local or cloud, happens on a branch named for the session; the operator merges.
  Commit and push every session, to the session branch.
- `nap_*.json` and `dennis_*.json` are never committed, recreated, or faked.
- Run `git pull` before reading `DECISIONS.md` (N30).
