#!/usr/bin/env python3
"""BookSim = realistic hop (credits, K, FCFS).
   golden/hop.py = our method (EDF vs FCFS, D_k).
   Writes results/booksim_k.csv, results/sweep.csv, results/figures/performance.png
"""

import csv
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hop import simulate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = os.path.join(ROOT, "third_party", "booksim2", "src", "booksim")
CFG = os.path.join(ROOT, "eval", "hop_2node.cfg")
OUT = os.path.join(ROOT, "results")
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

K_LIST = [1, 2, 4, 16, 64]
W_FLIT = 32
F_LINK = 1e9
B_PEAK = W_FLIT * F_LINK / 1e9  # 32 GB/s


def last_float(log, pattern):
    vals = re.findall(pattern, log)
    return float(vals[-1]) if vals else None


def run_booksim(K):
    p = subprocess.run(
        [BS, CFG, "vc_buf_size=%d" % K],
        cwd=os.path.dirname(BS),
        capture_output=True,
        text=True,
        check=False,
    )
    log = p.stdout + p.stderr
    log_path = os.path.join(OUT, "booksim_K%d.log" % K)
    with open(log_path, "w") as f:
        f.write(log)
    acc = last_float(log, r"Accepted flit rate average\s*=\s*([0-9.]+)")
    inj = last_float(log, r"Injected flit rate average\s*=\s*([0-9.]+)")
    plat = last_float(log, r"Packet latency average\s*=\s*([0-9.]+)")
    return {
        "K": K,
        "accepted_flit_rate": acc,
        "injected_flit_rate": inj,
        "packet_latency": plat,
        "B_useful_GBps": (acc * B_PEAK) if acc is not None else None,
    }


print("BookSim hop (FCFS / credits / K)")
bs_rows = []
for K in K_LIST:
    r = run_booksim(K)
    bs_rows.append(r)
    print("  K=%2d  accepted_flit=%s  B_useful=%s GB/s  pkt_lat=%s" % (
        K, r["accepted_flit_rate"], r["B_useful_GBps"], r["packet_latency"]))

bs_csv = os.path.join(OUT, "booksim_k.csv")
with open(bs_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(bs_rows[0].keys()))
    w.writeheader()
    w.writerows(bs_rows)
print("wrote", bs_csv)

print("Golden method (FCFS vs EDF, D_k)")
gold = []
jobs = [("fcfs", 64)]
for K in (1, 2, 4, 16):
    jobs.append(("fcfs", K))
    jobs.append(("edf", K))
for policy, K in jobs:
    r = simulate(K=K, policy=policy)
    gold.append(r)
    print("  %-5s K=%2d  B_useful=%.3f  miss=%.3f  mean_L=%.1f" % (
        r["policy"], r["K"], r["B_useful_GBps"], r["miss_rate"], r["mean_L"]))

g_csv = os.path.join(OUT, "sweep.csv")
with open(g_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(gold[0].keys()))
    w.writeheader()
    w.writerows(gold)
print("wrote", g_csv)

import matplotlib.pyplot as plt

fig, ax = plt.subplots(1, 3, figsize=(11.2, 3.5))

ks_bs = [r["K"] for r in bs_rows]
ax[0].plot(ks_bs, [r["B_useful_GBps"] for r in bs_rows], "o-", color="0.2")
ax[0].set_title("BookSim hop (FCFS)")
ax[0].set_xlabel("K (flit slots)")
ax[0].set_ylabel("accepted x B_peak (GB/s)")
ax[0].set_xticks(K_LIST)

for pol, mk in (("fcfs", "o"), ("edf", "s")):
    sub = [r for r in gold if r["policy"] == pol and r["K"] != 64]
    ax[1].plot([r["K"] for r in sub], [r["B_useful_GBps"] for r in sub], mk + "-", label=pol)
    ax[2].plot([r["K"] for r in sub], [r["miss_rate"] for r in sub], mk + "-", label=pol)
ax[1].set_title("Our method: B_useful")
ax[1].set_xlabel("K")
ax[1].set_ylabel("GB/s")
ax[1].legend(fontsize=8)
ax[2].set_title("Our method: GEMM miss rate")
ax[2].set_xlabel("K")
ax[2].set_ylabel("miss rate")
ax[2].legend(fontsize=8)
fig.suptitle("Left: BookSim credit hop. Mid/right: EDF = min D_k if credit>0.", fontsize=9)
fig.tight_layout()
fig_path = os.path.join(FIG, "performance.png")
fig.savefig(fig_path, dpi=130)
print("wrote", fig_path)
