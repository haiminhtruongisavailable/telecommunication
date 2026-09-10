# One-hop credit and EDF program

One bidirectional D2D hop. Credits then min D_k. Tiled INT8 GEMM. PR order P1, P2, P3, P4, P5. IEEE Xplore is the index, not the venue.

Grok bots start at `START-HERE.md`, then `golden/hop.py`, then `results/sweep.csv`.

## P1 docs freeze

T_k = T_0 + k * C_tile. D_k = T_k + extra. Same extra for FCFS and EDF.

## P2 golden and BookSim hop

Python method in `golden/hop.py`. BookSim `eval/hop_2node.cfg` is FCFS credits and K only. Clone with `scripts/clone_booksim.sh`. Do not commit the BookSim binary.

Success table is `results/sweep.csv`. EDF at K=16 miss 0. FCFS at K=16 still misses.

## P3 Verilog

`rtl/` copies the two checks. Match golden last-arrival cycles on a short seed. Review-gated.

## P4 Yosys

Area of `hop_top`. OpenROAD only after `results/area.txt` is nonzero.

## P5 slack baseline

Same hop. Add Aergia-style slack as a third policy. No mesh. Workshop or student IEEE, then Xplore indexes it.

## Out of scope

Photonics, HBM device, 8x8 mesh, BookSim EDF patch, analog PHY.
