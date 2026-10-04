# Rule book: Grok CLI → D2D (handoff)

This file is PR handoff only. Execution order lives in `docs/ieee-one-hop-program.md`. Student pipeline lives in `START-HERE.md`.

This file is for **Grok CLI**, not the student.
**Where it lives:** in the GitHub repo. CLI reads it from the tree. Do not rely on an external link alone.

Role split (frozen):
- **Grok CLI** = writes / edits / runs code (Python first; Verilog later), then opens or updates a PR.
- **D2D** = gets notified on that PR, verifies against the đồ án goal, explains to the student.
- The student talks to both; the PR is how CLI keeps D2D current.

Do **not** replace the student-facing rule book. That one still governs how ideas are taught. This one only governs how work reaches D2D.

---

## 0. Hard rules for CLI

1. After any meaningful change (new file, behavior change, new metric, new plot, claim of “done”), **open or update a PR**. That PR *is* the handoff. Do not wait for the student to forward chat logs.
2. PR title + body are **structured and short** (section 2). No full transcript. Enough that D2D can check goal alignment from the PR alone.
3. Never claim success to the student until D2D has reviewed the PR (or the student explicitly skips verification).
4. Stay in scope: one bidirectional D2D hop; compute die vs data die; packer / credit / K-slot FIFO / deadline (EDF / nearest D_k); K ∈ {1,2,4,16}; baselines FCFS deep vs FCFS shallow. BookSim is the FCFS hop check only (credits, K). EDF stays in golden then Verilog. Yosys before OpenROAD. No photonics, HBM device, or mesh SoC.
5. Low slack first. Never prioritize large slack. Never put matrix A on one die and matrix B on the other unless the student changes that freeze.
6. Python locks the idea; Verilog is the later chip-design deliverable. Say the layer in the PR body.
7. If the student is confused, stop coding. Point them (and D2D) at the idea, not a new file.
8. **Fallback only:** if GitHub/PR is unavailable, paste the section-2 block to the student to forward to D2D — same fields.

---

## 1. When you must open / update a PR

| Trigger | Why D2D needs the PR |
|--------|----------------------|
| New or renamed module (packer, credit, FIFO, scheduler, traffic, metrics) | Scope + interface check |
| Behavior change (credit rule, EDF vs FCFS, deadline math, stall/overflow) | Correctness vs freezes |
| New numbers (miss, tardiness, η_eff, B_useful, K sweep) | Goal check |
| New plot or table | Map to the story; not a substitute for explanation |
| Milestone “done” / “aligned” | External verify before student trusts it |
| Leaving frozen scope or adding BookSim / OpenROAD / new baseline | Student + D2D gate |
| Student asked for code while still fuzzy on teaching rule book 1.1–1.4 | D2D may pause / re-explain |

Skip only pure typo/format edits with **zero** behavior or metric change.

**PR hygiene:** one concern per PR when possible; push to the same PR for follow-ups on the same chunk so D2D sees a single thread.

---

## 2. PR body template (required every time)

Put this in the **PR description** (and refresh it on each push to that PR). Fill every field; use `n/a` only if truly not applicable.

```text
### D2D handoff
Goal: <one line — what this change is for>
Layer: Python idea-lock | Verilog FSM | eval/metrics | other:<name>
Files touched:
- path — <one-line job of file>
Behavior change:
- <before → after, or "none">
Frozen checks (yes/no/unknown + one clause each):
- no send at credit=0:
- payload conserved (what entered left or still queued):
- compute die vs data die unchanged:
- low-slack / min D_k first (if scheduler touched):
- K set still {1,2,4,16} (+ deep FCFS baseline if claimed):
Numbers (same hop, same traffic, same f_link if known):
- K=… | policy=FCFS|EDF | miss=… | tardiness=… | B_useful=… | η_eff=… | notes=
How to reproduce (≤5 lines):
- <cmd or entrypoint>
- <input / seed / config>
Open risks / unknowns:
- <overflow edge, deadline tie-break, …>
Ask D2D:
- verify | explain-to-student | gate-scope | other:<…>
```

If numbers are not ready: `Numbers: pending` + what run is next.

Optional on the PR: small CSV/log of the sweep, one plot. Not the entire tree.

---

## 3. What D2D must recover from the PR alone

1. **Intent** — which of packer / credits / K-FIFO / EDF / traffic / metrics moved.
2. **Invariant claims** — overflow, conservation, die roles, slack rule.
3. **Evidence** — diff + how to run + numbers or “not run yet.”
4. **Delta** — what changed since the last push on this PR (or first open).
5. **Ask** — verify / explain / gate scope.

---

## 4. Success criteria D2D will use

Same hop, same tiled INT8 GEMM traffic, same clock story:

- Never send when credit = 0.
- Payload conservation (arrived, queued, or model-defined drops only — default no silent loss).
- Ordering story: shallow FCFS worse on lateness/misses; EDF better at same K; deep FCFS baseline only.
- Miss rate / tardiness and B_useful (η_eff × B_peak) for K in {1,2,4,16}.
- No second invented objective (maximize slack, extra fairness theory, etc.).

If the run cannot speak to these, say so under Open risks — do not imply đồ án done.

---

## 5. Loop (do not cut D2D out)

1. Student asks for a change → CLI implements (subject to teaching rule book if still on ideas).
2. CLI **opens/updates PR** with section-2 body.
3. D2D is notified (GitHub watcher), reviews the PR, explains to the student.
4. Step is accepted only after that — unless the student explicitly overrides.

---

## 6. One-line reminder for CLI system prompt

> After every meaningful code or metric change, open/update a PR whose body is the D2D handoff template; D2D verifies goal (no overflow, conservation, miss/B_useful on same hop+traffic) and explains; do not claim done without that loop.
