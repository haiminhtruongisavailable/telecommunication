#!/usr/bin/env python3
"""Same hop, same tiles: FCFS vs EDF, sweep K. Prints the success table."""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hop import simulate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results")
os.makedirs(OUT, exist_ok=True)

rows = []
jobs = [("fcfs", 64)]
for K in (1, 2, 4, 16):
    jobs.append(("fcfs", K))
    jobs.append(("edf", K))

print("%-6s %4s %8s %10s %10s %8s" % ("policy", "K", "eta_eff", "B_useful", "miss_rate", "mean_L"))
for policy, K in jobs:
    r = simulate(K=K, policy=policy)
    rows.append(r)
    print("%-6s %4d %8.3f %10.3f %10.3f %8.1f" % (
        r["policy"], r["K"], r["eta_eff"], r["B_useful_GBps"], r["miss_rate"], r["mean_L"]))

path = os.path.join(OUT, "sweep.csv")
with open(path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print("wrote", path)
