# Start here (one hop)

You work this folder one step at a time. Do not skip to Verilog. Do not add photonics or a mesh.

## What this chip does

Two dies, one D2D hop. Compute die vs data die. Tiles of INT8 GEMM, not extra silicon.

Each cycle, two checks. Credit greater than 0, then send the flit with the soonest D_k (EDF). FCFS is queue order. It is the baseline.

Tile k is released at T_k = T_0 + k * C_tile. Deadline is D_k = T_k + extra. Same extra for FCFS and EDF.

## Files by job

`golden/hop.py` is the method. `eval/hop_2node.cfg` is BookSim FCFS hop check. `docs/ieee-one-hop-program.md` is PR order P1 to P5. `RULEBOOK-GROK-CLI-TO-D2D.md` is how Grok CLI writes a PR for D2D. `results/sweep.csv` is the current numbers.

## Your loop this week (P1 then P2)

1. Read this page and the freeze in `description.txt`.
2. Run `python3 golden/run_sweep.py`. Look at miss_rate, not only B_useful.
3. Check that EDF at K=16 has miss 0 and FCFS at K=16 still misses. That is the success of the idea, not a faster wire.
4. Stop. Next code is P2 (publish golden + BookSim cfg). Verilog is P3.

## If a number looks wrong

Do not add a new policy. Ask whether credit was 0, or whether bulk sat at the head of FCFS.
