#!/usr/bin/env python3
"""P3: RTL last-flit cycles must match golden/hop.py on N_tiles=8."""

import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "golden"))
from hop import simulate  # noqa: E402

TB = os.path.join(ROOT, "tb")
N = 8


def run_vvp(target):
    r = subprocess.run(["make", "-C", TB, target], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or "FAIL" in out:
        print(out)
        raise SystemExit("sim failed: " + target)
    return out


def read_tlast(path):
    rows = {}
    with open(path) as f:
        for rec in csv.DictReader(f):
            rows[int(rec["tile"])] = int(rec["t_last"])
    return rows


def match(policy, K, make_target):
    g = simulate(K=K, policy=policy, N_tiles=N, return_trace=True)
    out = run_vvp(make_target)
    if "PASS" not in out:
        print(out)
        raise SystemExit("no PASS in " + make_target)
    rtl = read_tlast(os.path.join(TB, "rtl_tlast.csv"))
    for k in range(N):
        if rtl.get(k) != g["t_last"][k]:
            print("mismatch tile", k, "golden", g["t_last"][k], "rtl", rtl.get(k))
            print(out)
            raise SystemExit("golden mismatch")
    print("MATCH", policy, "K", K, "miss", g["miss_rate"], "cycles", g["cycles"])
    return g, out


def main():
    g_edf, out_edf = match("edf", 16, "sim-edf")
    if g_edf["miss_rate"] != 0:
        raise SystemExit("EDF K=16 short seed must miss 0")
    g_fcfs, _ = match("fcfs", 16, "sim-fcfs")
    g_k1, out_k1 = match("edf", 1, "sim-k1")
    if g_k1["stall_cycles"] <= 0:
        raise SystemExit("K=1 stall must be > 0")

    run_vvp("sim-edf")
    a = open(os.path.join(TB, "rtl_tlast.csv")).read()
    run_vvp("sim-edf")
    b = open(os.path.join(TB, "rtl_tlast.csv")).read()
    if a != b:
        raise SystemExit("reset rerun not identical")

    print("PASS rtl matches golden on short seed")
    print("EDF miss", g_edf["miss_rate"], "FCFS miss", g_fcfs["miss_rate"])


if __name__ == "__main__":
    main()
