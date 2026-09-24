# V10 STACK AUDIT — SEPTEMBER 2026

**Audited:** 0.1c · 0.1d with Addendum A · 0.1e handover + Addenda A and B (the five files as uploaded 23 Sep 2026)
**Integrity:** byte-identical to the 5 August set (md5 match on all five). The stack has not changed in seven weeks. The corpus around it has.
**Method:** text comparison only. The five files against each other, against the two sister documents still on disk (V10-DAILY-CORE 0.3.2 and CHART-CONFIG PZ-0.4.1), and against the bench-run record since 5 August. No new classical retrieval this pass, so nothing here enters or leaves the corpus as classical authority. E20 is untouched.

---

## 1. WHAT STILL HOLDS

Checked, not assumed:

- **U12 十二長生 table:** all 96 cells re-derived by the forward/reverse rule. Clean.
- **§2.4 interaction pools:** 六沖, 六合, 三合, 三會, 刑, 自刑, 害, 破, 五合 all correct.
- **The located citations** (F3's 旺者沖衰 couplet, ch. 5's four mechanisms, ch. 35 論印, ch. 15 論相神緊要, ch. 6's opening): no later run has contradicted any of them.
- **The architecture:** Escalation Report, grade contingency, §7A.5 client register, the bridge-withholding rule. Every run since August has used these exactly as designed, and they are what surfaced everything below.

---

## 2. WHAT HAS BECOME LESS ACCURATE

### L-1 · LOCKED_PARTIAL is used by the stack and defined nowhere in it · Severity 1

U3, U4 and A2 all branch on `LOCKED_PARTIAL`. Nothing in the five files says what produces it. The one definition in the whole corpus is in the sister document, V10-DAILY-CORE 0.3.2, line 97:

> A branch 六合 that fails the U6 gate produces LOCKED_PARTIAL on both branches; one that meets the gate produces LOCKED_FULL.

The forensic stack's own practice is the opposite: digong's 午未 failed its gate and was ratified **LOCKED_FULL**, 3/3, in 0.1e Part One items 3–4. Every elimination made through an **ungated 六合** anywhere in the corpus rests on the forensic practice, against the only written definition. Known instances: digong 午未 (2026), Alice's August 巳申. Under the CORE definition, U3 turns each of those "ELIMINATED" clashes into **UNRESOLVED — ESCALATE**, and U4 turns the harms and destructions into **ATTENUATED**.

By elimination the CORE reading is probably what 0.1c meant: the only other candidate producer of a partial lock would be a half-三合, and §2.4 treats those as tendencies with no token at all. But the stack never says so, and the ratified practice went the other way.

### L-2 · U8 was not applied to the ratified field · Severity 1

U8: *a branch in an active standing clash cannot be captured by a combination.* E-8b's priority reading, the one the stack says to apply, restricts U8 to "a clash already standing in a senior layer."

On digong, decade 未 has stood in a full-force 丑未 clash with natal 丑 since the 辛未 decade began. When annual 午 arrives in 2026 and reaches for 未, that clash is standing in a senior layer. **U8 bars the capture on the priority reading, and on the pre-emption reading as well.** Because both E-8b readings agree, E-8b's own escalation condition never fires; U8 simply applies. The only reading that preserves the ratified lock is one where the single pool flattens every layer, and that reading makes U8 inoperative in every case, which E-8b's wording excludes by naming "a senior layer" at all.

Same shape on Alice: the August 巳申 captures natal 巳, which stands in the natal 巳亥 clash. Meanwhile the sara run did flag a July capture as E-8b. So the rule has been applied on one chart and skipped on two. Each run was locally reasonable, which is why the inconsistency only shows up when you put them side by side.

The root defect is that **layer seniority is never defined.** Nothing in the stack states that natal > decade > annual > monthly > daily, or whether a decade-with-natal clash counts as standing when an annual branch arrives.

### Joint consequence — the frozen digong field has three maps, not one

§2.5 requires both maps wherever an escalated condition would change the map. §C5 gives one.

| | 午未 | 丑未 沖 | 丑午 害 | 卯午 破 | 午 as root for 丙 |
|---|---|---|---|---|---|
| **As ratified** (LOCKED_FULL, U8 not applied) | LOCKED_FULL | ELIMINATED | ELIMINATED | ELIMINATED | E-4, open |
| **Under L-1** (CORE definition) | LOCKED_PARTIAL | UNRESOLVED | ATTENUATED | ATTENUATED | available under CORE's interim partial-lock rule |
| **Under L-2** (U8 applied) | does not form | FULL FORCE | FULL FORCE | FULL FORCE | FREE, 帝旺 root, E-4 moot |

The ratified map is the only one of the three that requires **both** an undefined token **and** a skipped rule. Under L-2 the picture inverts in both directions at once. The rescue is no longer bound, because the Day Master gets its first branch root of its life, unlocked. But "丑 shielded" is gone: the Officer's residence takes a clash and a harm, and the Seal, the month command itself, takes a full-force destruction from 午.

This audit does not re-grade digong. That would be a pass on a frozen chart. It records that **§C5's field is contingent on two definitional rulings nobody has made**, and it recommends marking §C5 so rather than re-running it.

### L-3 · U5's text contradicts a located source the stack itself relies on · Severity 2

U5 still reads: *transforms only if the month branch is the transformed element's 旺月.* F1 (三命通會 論十干化氣) established primary **and secondary** gate months, and 0.1e Part One item 6 already reasons with F1's secondary month (亥). The 5 August citation handover's own standing note said R1/Gate 2 needs the primary/secondary structure before it ships. **U5 was never amended.** An engine reading the stack literally will refuse secondary-month transformations that the stack's own ledger treats as valid.

Related: **the F1–F5 citation handover is not in the stack.** Source-ledger rows S12–S14 point at "per 5 Aug pass." The document that carries F1's text, including the 甲己 → 午, 乙庚 → 申 and 丙辛 → 亥 secondary clauses, is referenced and not included.

### L-4 · Two things the stack says it contains, and doesn't · Severity 2

- **The §2.6 hidden-stem table.** U14 says: *"The table is reproduced in §2.6 and is part of this specification."* It is not. 0.1d carries only the instruction to reproduce it. The complete twelve-row table is sitting in CHART-CONFIG PZ-0.4.1 (淵海子平 base). It never got moved.
- **Appendix B, the failure catalogue.** Patch 5 says to carry Categories A–G verbatim and add H onward. No category text exists anywhere in the five files, only references.

For a bench reader these are annoyances. For the PillarMind app, which loads the stack as a runtime prompt, they are two rules pointing at nothing.

### L-5 · §C3 is now about half the register · Severity 2

The consolidated register stops at E-22. Raised since, and living only in bench files:

- **Register items E-23 → E-38:** duplicate clash/destruction partners · root availability under clash · rooted-without-surface · transit branch matching the void pair · CRITICAL triggers undecidable when the formation halts · 沖提綱 with no trigger · symmetric multi-claimant 五合 · locked branch as a gate · hidden stems in a clashed branch · "the DM's root," any or principal · 剋 across distance · 用神 bound to the DM · 隔位 threshold · hidden stems in harmed/destroyed branches · same-element clash · 伏吟/反吟 absent · pool collision (寅亥 / 巳申 sit in both 六合 and 破).
- **Also:** the 從財格 Formation Gate candidacy (kris aquino, sara), G-4 (no monthly or annual strength apparatus), P-11 (decade-chain corroboration), P-12 (本氣 vs 透出 格局 derivation), P-14 (no cardinal rule for 三合), P-D1, P-D2, **Category M** (the production template emitting "Formation Force (七殺 Month Command) Fire" on four different Day Masters), and fixtures (l) through (o).

Anyone running from the five files sees none of this. The register has roughly doubled outside the stack.

### L-6 · §C7 no longer describes the practice in full · Severity 3

§C7 is unqualified. On 1 September the operator relaxed it for one business line (celebrity marriage-timing content, "nobody gets hurt" as the surviving boundary). The stack doesn't record the exception. Two notes:

- The Spouse Timing Report as designed (when the structure is active, never a favourability verdict) may already sit inside terrain language and not need an exception at all. Either way, it should be written down, because an undeclared scope change is exactly what Patch 14 exists to prevent.
- The 3 September retrieval located doctrine that bears on the stack directly: 沖 at the Day branch reads relative to 喜忌, per 滴天髓 任注 夫妻 and 三命通會 論妻妾. That makes spouse-palace reading 用神-dependent, which touches E-6. These are located citations the stack doesn't carry.

### L-7 · Two errors in this bench's own September digong addenda · corrected

Both files have correction ledgers appended.

- **The 酉月 seasonal table was swapped.** It read "Wood 囚, Fire 死." Correct is **Fire 囚, Wood 死**, derived from the relations: 當令 旺 / 我生 相 / 生我 休 / 剋我 囚 / 我剋 死. This is the **same swap, in the same season, that the dennis bench caught and corrected on 14 August for 申月.** A corrected error recurring is its own finding. It argues for making the seasonal table a show-your-derivation step, the way Patch 6 made void enumeration one.
- **The 16 September daily addendum skipped U8.** Its headline (巳酉丑 completes and silences the natal 卯酉 clash) does not survive. Both 酉 were standing in senior-layer clashes: natal 酉 in the natal 卯酉, monthly 酉 in the monthly 卯酉. Neither can be captured. The corrected day is in that file's ledger. This is L-2 committed by the auditor, the week before the audit.

---

## 3. WHAT IS MISSING — never in the stack

- **A definition of LOCKED_PARTIAL** (L-1).
- **A layer-seniority order for U8** (L-2).
- **A strength procedure** (E-19) and the **格 route tables** (P-1). Still the largest gap, unchanged since 5 August.
- **A strength apparatus at monthly and annual scope** (G-4). Four charts have needed it.
- **A 格局 derivation rule** (P-12). Kim, ces drilon and dennis each produced a different variant of the 本氣-vs-透出 split.
- **A cardinal / half-form rule for 三合** (P-14). §2.4 has one for 三會 only.
- **Birth-time offset intake.** Philippine DST windows (1936–37, 1954, 1978, 1990) and the ≈+4 min longitude correction. "Engine-verified" certifies pillar arithmetic, not the clock time fed to it.
- **The five §C6 operator rulings:** E-19 + P-2 jointly, E-12, F12, and the §9 refounding. All still pending since 5 August.
- **The transcription project:** the 官殺 chapter with 任注 (now first priority after dennis made E-17 load-bearing), the 格 chapters 31–47, ch. 6 in full, 論十干合. Not started.

---

## 4. RECOMMENDED ORDER

**First, two one-sentence operator rulings.** They are cheap and they change field maps corpus-wide, so they come before anything else.

> **R-DEF-1 (LOCKED_PARTIAL).** Either adopt CORE's definition into the forensic stack ("an ungated 六合 is LOCKED_PARTIAL on both branches"), or declare the forensic practice ("an ungated 六合 is LOCKED_FULL") as a labelled engine decision and patch CORE to match. The two documents may not disagree. The classical question (whether 合而不化 still binds enough to 忘沖) is unretrieved, so whichever is chosen enters as a declared decision, not doctrine.
>
> **R-DEF-2 (layer seniority).** "For U8, layers rank natal > decade > annual > monthly > daily. A clash between a senior-layer branch and any branch of equal or higher seniority is standing for every junior arrival." Or state the alternative. E-8b then reduces to the same-layer case, which is the only place its two readings actually diverge.

**Then a 0.1f** that is housekeeping, not doctrine: the two definitions, U5 rewritten to F1's primary/secondary structure with the F1 text attached, the §2.6 table actually inserted (copy from PZ-0.4.1), Appendix B written out, the register consolidated from the bench files, §C5 marked contingent on R-DEF-1/2, and the §C7 exception recorded.

**Then the transcription project**, as already queued.

**Do not re-run digong.** Mark it contingent. The chart that taught the corpus its gaps turns out to be carrying two more that it couldn't see, and that is the most useful thing it could have done.

---

*Text comparison only · no new classical claims · 23 September 2026*
