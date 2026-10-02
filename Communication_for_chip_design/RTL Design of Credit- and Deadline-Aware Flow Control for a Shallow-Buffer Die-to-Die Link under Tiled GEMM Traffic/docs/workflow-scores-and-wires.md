# Workflow, scores, and the widen zone

One note for the whole adapter: what moves, which score picks the flit, and which pins are allowed to grow later.

This is a specification. `golden/hop.py` still releases one square on `T_k = T_0 + k * C_tile` and still compares first-come-first-served with earliest `D_k`. The Verilog in `rtl/` is the older one-policy reference. The next hardware build follows `i05_cordic`: one block per file, and a later pin change stays inside the block that owns that pin.

## What the machine is

Two dies. One hop in the base machine. The data die holds A and B. The compute die multiplies.

A tile and a square are the same job: output square `k` of `C`. The golden size is `16 x 16`. One tile carries the A panel and the B panel for that square, not all of A and not all of B. Those two panels become 16 flits, and every flit of that tile shares `D_k`. The square of `C` is computed after the flits arrive. It is not sent into the multiplier.

```text
DATA DIE
  release (one square, or a wave of W squares)
       |
       v
  packer  -- cuts A/B bytes into flit records
       |
       v
  ready  <-- other stack also appends here (already one flit)
       |
       v
  score, then scheduler  -- looks at every waiting record, emits winners
       |
       v
  credit gate  -- send only while credit > 0
       |
       v
  PHY delay box  -- D_phy cycles, base width 1 flit
       |
       v
COMPUTE DIE
  K-slot buffer --> unpack --> MAC
       |
       +--> credit return (arrives at the data die after 2 * D_phy)
```

`K` is the number of flits the compute die can hold. It is not a wire count. `credit = 0` means the hop sends nothing that cycle. A credit return is an empty slot coming back, not GEMM data.

## Where parallel is allowed

| Place | What happens | Wires |
| --- | --- | --- |
| Release into the packer | A wave of width `W` may enter in one cycle. `W * 16` records can be appended to `ready` together. Today's baseline still uses `T_k = T_0 + k * C_tile`, with the next square allowed in one tile-time early. | No extra wires. `ready` is a buffer and accepts a burst. |
| `ready` to the scheduler | The scheduler already reads every valid slot. That full set is the scheduling space. | No extra wires. More wires here would be extra outputs, not a wider view. |
| Scheduler to the hop | Base machine: one winner leaves per cycle. | This is the widen zone. Parameter `N_WIRES`. |
| Inside one flit | A real UCIe flit is already a wide word. Here that width is the 32-byte flit. | Parameter `W_FLIT`. This one does touch the packer, because the packer cuts bytes into flits. |

A second path from the packer into `ready` is not part of the design. The other stack joins at `ready`, after the GEMM packer, never at packer input and never inside the PHY.

## Scores

The scheduler still emits indexes. The thing that changes is the score on each waiting record. Earliest `D` remains the baseline. On a wave, many records share one deadline, so earliest `D` ties and falls back to sequence number, which is packer order.

Each record carries: `seq`, `tile_id`, `panel` (A or B), flits still missing on that panel, how many squares are stuck on that panel, `wave_id`, `is_gemm`, and `D_k`.

| Score | Rule | What it is for |
| --- | --- | --- |
| First-come-first-served | Smallest `seq`. | Baseline. Packer order. |
| Earliest `D` | Smallest `D_k`, tie on `seq`. | Baseline. Frozen low-slack rule for the one-array workload. |
| Closest to firing | Prefer the flit that finishes a square whose other panel is already complete, and whose own panel has the fewest flits left. | Time until the first square can multiply. |
| Shared panel first | Prefer the panel with the most waiting squares. After that shared A is complete, use closest-to-firing on the private B panels. | One A serves the whole wave. Needs the reused-A workload, not a private A copied into every square. |
| Finish the row | Prefer the square with the most flits left, or rotate across the wave. | Time until every square in the wave can multiply. This rule can send a flit that earliest `D` would call large slack. It is a wave experiment, not a replacement of the frozen low-slack claim. |
| Admission | Let only as many squares into `ready` as `K` and one flit per cycle can finish. Hold the rest until one square completes. | Keeps the shallow buffer from opening the whole wave and finishing none. This is a rule in the release block, not a new stage on the wire. |

Same machine for every row: one hop, send only when `credit > 0`, `K` in `{1, 2, 4, 16}`, `D_phy = 4`. The other stack still offers one flit into `ready`.

Report, for each score:

- cycle when the first square has both panels
- cycle when every square in the wave has both panels
- share of grants that are GEMM versus the other stack
- miss rate, mean lateness `L_k`, mean `t_last`, and `B_useful = eta_eff * B_peak`

Two workloads sit on that plot. The sequential release stays. The wave is added beside it. For shared-panel-first, run both a private A per square and one reused A per wave, so a better score is not only a smaller byte count.

## Widen zone, and the blocks it must not touch

`i05_cordic` puts control in `cordic_control` and arithmetic in `cordic_processing`. The top file only wires `load`, `run`, `i`, `x`, and `y`. Changing the adder inside block A does not change those pins.

This adapter uses the same split. `N_WIRES` is a parameter on three blocks only:

| Block | Grows with `N_WIRES` | Pins that stay put |
| --- | --- | --- |
| Scheduler output | Emits `N_WIRES` indexes, or fewer when `ready` or credit runs out. | Score inputs. One integer score per slot. The score modules do not grow. |
| Credit | May accept up to `N_WIRES` sends in one cycle, and never more than the current credit. | `credit > 0` before any send. Packer and `ready` do not see `N_WIRES`. |
| PHY | `N_WIRES` delay lanes, each of `D_phy` cycles. | A gather on the compute side hands unpack one arrived record at a time. Unpack, the MAC, and the K-slot record format stay one flit wide. |

Blocks with no `N_WIRES` port: release, packer, other-stack offer, `ready` storage, every score module, unpack, MAC.

`W_FLIT` is the other knob, and it is not isolated. A wider flit changes how many flits the packer emits per panel. Do not hide that inside the PHY parameter.

Later sweep, after the one-wire golden matches: `N_WIRES` in `{1, 2, 4}` with the same six scores. At `N_WIRES = 1` the scores should separate. As the pipe widens they should move closer, because more of the wave leaves in the same cycle.

## Next hardware tree

Build this only after the golden scores exist. Do not retarget today's `rtl/hop_top.v` in place. New files, same pattern as `cordic.v` beside `cordic_control.v` and `cordic_processing.v`:

```text
arch/hop_top.v            wires only
arch/release.v            sequential clock or wave W; admission hold lives here
arch/packer.v             panel bytes to records; no other-stack input
arch/other_stack.v        one offered flit into ready
arch/ready_mem.v          the records, no policy
arch/score_fcfs.v
arch/score_edf.v
arch/score_firing.v
arch/score_shared.v
arch/score_row.v
arch/scheduler.v          argmin, parameter N_WIRES, output indexes only
arch/credit.v             parameter N_WIRES on the accept count
arch/phy_box.v            parameter N_WIRES, plus the one-flit gather
arch/unpack.v             one record in, panels out
```

Adding a wire later means raising `N_WIRES` on the scheduler output, the credit accept count, and the PHY lanes. Release, packer, `ready`, the score files, and unpack stay at the same ports.

## What is still true underneath

- One bidirectional hop in the base machine. PHY is a delay box.
- Two checks: `credit > 0`, then the chosen score.
- Tile `k` deadline on the baseline is `D_k = T_k + extra`, with the same `extra` for first-come-first-served and earliest `D`.
- Miss uses `L_k = max(0, t_last(k) - D_k)` after the run. First-come-first-served does not read `D_k` when it picks.
- Other-stack deadline stays finite and tighter than "wait until the matrix ends." The stored golden still uses the far tag until that knob is edited on purpose.
- BookSim remains the first-come-first-served hop check. No EDF fork there.
- Verilog, Yosys, and OpenROAD stay parked until this golden exists and a later step allows them.
