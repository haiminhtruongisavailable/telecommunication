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
