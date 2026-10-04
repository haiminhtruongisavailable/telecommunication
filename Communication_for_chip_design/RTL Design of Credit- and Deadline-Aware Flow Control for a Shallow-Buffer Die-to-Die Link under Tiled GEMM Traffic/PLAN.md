# Plan: RTL of credit- and deadline-aware flow control on one shallow D2D hop

Python `golden/hop.py` locks EDF (min D_k if credit > 0). BookSim is the FCFS credit hop check only. Do not fork BookSim for EDF. SCALE-Sim is optional later for C_tile. Verilog copies the golden hop.

Read `START-HERE.md` first. PR order is `docs/ieee-one-hop-program.md`.

## Frozen object (do not grow)

- Two dies, one bidirectional Die-to-Die (D2D) hop.
- Traffic: tiled GEMM C = A x B, INT8. Die A computes. Die B holds a panel.
- Digital UCIe-style adapter only. Analog PHY is a delay box.
- RTL blocks: packer, credit counter, K-slot FIFO, EDF scheduler.
- Out of scope: analog PHY, photonic layout, HBM device, extra MAC array, mesh SoC.

## Method

- Tile k releases at T_k = T_0 + k * C_tile. Deadline is D_k = T_k + extra. Same extra for FCFS and EDF. Default extra=40.
- Send only if credit > 0. FCFS is queue order. EDF is min D_k.
- K in {1, 2, 4, 16}. Deep FCFS K=64 is baseline only.
- Metrics: eta_eff, B_useful = eta_eff * B_peak, L_k, miss rate.

## Tools

- `golden/hop.py` is the method.
- `eval/hop_2node.cfg` plus `scripts/clone_booksim.sh` is the FCFS hop check.
- Yosys after Verilog. OpenROAD only after Yosys writes `results/area.txt`.
- Clone BookSim. Do not commit the binary.

## Pass criterion

Same hop, same INT8 GEMM, same f_link. T = 16. K in {1, 2, 4, 16}.

- FCFS deep: B_useful near B_peak.
- FCFS shallow, K smaller than credit RTT: B_useful drops and/or miss rate rises.
- Credits plus nearest D_k: lower miss rate than shallow FCFS at the same K. B_useful may match.
- Verilog matches the golden hop (no overflow, payload conservation).

See `docs/ieee-one-hop-program.md` for P1 to P5.
