# V10 — RETRIEVAL AUDIT HANDOVER FOR KIMI

**To:** Kimi (via API, web search enabled)
**From:** the operator and the bench
**Attached:** the operative stack (0.1c · 0.1d with Addendum A · 0.1e handover + Addenda A and B) and the September 2026 stack audit
**Rule in force:** E20. No classical claim enters the corpus without page-level retrieval.

---

## 0. WHAT THIS AUDIT IS, AND IS NOT

The V10 stack is the protocol an app will use to interpret BaZi charts. Before any app is built, we want the stack made more accurate. Right now the stack's accuracy is limited in two ways. You can help with one of them.

1. **Definitional gaps.** These are decisions the operator must make. You may supply evidence for them. You may not make them.
2. **Textual gaps.** These are places where the stack depends on classical text nobody has retrieved in full. This is where you can move the stack.

**You are not being asked** to re-audit rulings already closed, to rewrite the spec, to adopt or reject patches, to score other instruments, or to interpret any chart. A finding that says "the architecture is sound" adds nothing. A retrieved passage with a working URL adds a great deal.

---

## 1. THE RULES OF EVIDENCE

These are not formalities. Each one exists because an audit in this corpus failed without it.

- **Retrieve, don't recall.** Use web search for every item. If you cannot retrieve it, answer NOT FOUND. A correct-sounding recollection is worth zero here, and a fabricated one does damage.
- **Label 原文 vs 注.** Many editions interleave the original text with commentary (徐樂吾, 任鐵樵, and others). Say which one you are quoting. Commentary is useful, but it is a different tier.
- **Full chapter, or say so.** If you only saw a snippet, say "snippet." A snippet can narrow a question; it cannot close one. (Category K: a snippet once closed a register item that the rest of the chapter reversed.)
- **State the joint.** For every passage, write one sentence stating exactly what claim it supports, and one sentence stating what it does *not* establish. This is the most important rule. (Category L: real citation, real text, attached to a claim the text doesn't make. This happened three times in one earlier audit, including one of yours. Naming it here is not an accusation. The rule exists to stop it happening to anyone.)
- **Quote briefly.** The passage that bears on the question, not the chapter.

---

## 2. THE ITEMS, IN PRIORITY ORDER

### T-1 · Does an untransformed 六合 still bind? — evidence for operator ruling R-DEF-1

The stack uses a token, LOCKED_PARTIAL, and never defines it. The daily engine says an ungated 六合 is LOCKED_PARTIAL. The forensic stack treated one as LOCKED_FULL, eliminating clashes through it.

**Retrieve:** any classical treatment of 合而不化 at the branch layer, and of whether 貪合忘沖 applies when the combination does not transform. Also any text on 合絆. The candidate loci are 子平真詮 論刑沖會合解法 (ch. 7) and 滴天髓's 合/沖 passages with 任注.

### T-2 · Do luck layers have a precedence order? — evidence for operator ruling R-DEF-2

U8 says a branch in a standing clash cannot be captured by a combination. Whether a clash between a natal branch and a 大運 branch counts as "standing" when a 流年 branch arrives depends on an order the stack never defines.

**Retrieve:** any classical statement of how 大運 and 流年 interact with the natal chart and with each other, including 歲運並臨, the priority of 運 over 歲 or the reverse, and whether a 運 clash already in force is treated as settled when a 歲 arrives.

### T-3 · 滴天髓 官殺 chapter, 原文 plus 任注 — register E-17

The 原文 is short: 官殺混雜來問我，有可有不可. The conditions under which 混雜 is acceptable live in 任鐵樵's commentary.

**Retrieve:** the commentary in full, and list its conditions. This is now the corpus's first transcription priority.

### T-4 · 子平真詮 ch. 6, 論十干得時不旺失時不弱, full text — register E-19

Retrieved so far: only the opening, plus a root passage (是故十干不論月令休囚，只要四柱有根…). The stack has no procedure for deriving the Day Master's strength.

**Retrieve:** the full chapter. Mark every sentence that ranks roots, weights 得令 against 通根, or treats 透干. Do not propose a procedure. Transcription only.

### T-5 · How the 格局 is taken from the month command — register P-12

Two methods disagree on real charts. The 本氣 method takes the month branch's principal hidden stem. The 透出 method takes whichever hidden stem of the month branch appears on a heavenly stem.

**Retrieve:** 子平真詮's statements on 取格 from the month command, especially 論用神 (ch. 8) and 論用神變化 if present, including what happens when more than one hidden stem is transparent, or none.

### T-6 · Transit claimants and 隔位 — register E-21

子平真詮 ch. 5's proximity mechanisms (本身之合, 高太尉, 隔位太遠) all concern natal columns.

**Retrieve:** any classical text that places 大運 or 流年 stems in the proximity order for stem combinations. If none exists, answer NOT FOUND. That is a useful answer.

### T-7 · 丁壬 and 戊癸 secondary gate months

三命通會 論十干化氣 gives secondary months for 甲己 (午), 乙庚 (申) and 丙辛 (亥). Our retrieval did not find the clauses for 丁壬 and 戊癸.

**Retrieve:** those two clauses. The corpus conjecture is 寅 and 巳. Confirm or refute with text.

### T-8 · 三命通會 論十干合 — outstanding item G1

This chapter has been NOT FOUND by two instruments. If it exists, retrieve it. If you conclude the title is a phantom, say so and give your reason.

---

## 3. RETURN FORMAT

One block per item. Nothing outside the blocks except §4.

```
T-n:  FOUND / SNIPPET / NOT FOUND / VARIANT
      Source: <text, chapter>   URL: <url>   Tier: 原文 / 注 (whose)
      Passage: <brief quote>
      Supports: <one sentence>
      Does NOT establish: <one sentence>
      Bears on: <register item or ruling>
```

## 4. ONE PERMITTED OPINION

After the blocks, and only there, you may add at most three items the stack needs that are **not** on this list, each with the retrieved text that shows it. No text, no item.

---

*Your findings enter the corpus only through the operator. Retrieved text with a working URL is the one contribution that can change the specification. Everything else is commentary, and we already have a lot of that.*
