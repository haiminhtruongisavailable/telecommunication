#!/usr/bin/env python3
"""Prove check.py catches real mistakes: each break mutates a COPY of spec.json or of one
layout_<view>.json (files written to breaks/), runs check.py on that view and requires
exit 1 plus the expected message.  Covers every view/level (L1 top .. L3 leaves).
exit 0 = every break was caught; also re-runs the clean check, which must exit 0."""
import json, copy, subprocess, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
SPEC = json.load(open("spec.json"))
def V(s, vid): return next(v for v in s["views"] if v["id"] == vid)
def L(vid): return json.load(open(f"layout_{vid}.json"))

def b_top_wire(s, l):            # top: delete a CU<->PU wire
    del l["nets"]["send_en"]
def b_top_doc(s, l):             # top: drop a pin the doc pin table lists
    v = V(s, "top"); v["ports"] = [p for p in v["ports"] if p["name"] != "done"]
    v["nets"]["done"]["pins"] = [p for p in v["nets"]["done"]["pins"] if p != "PORT.done"]
def b_cu_offpin(s, l):           # cu: wire end misses its pin by 10 px
    l["nets"]["policy_id"]["lines"][0][0][0] -= 10
def b_fsm_junction(s, l):        # fsm: forget the junction dots of a fan-out
    l["junctions"] = [j for j in l["junctions"] if j["net"] != "k_cnt"]
def b_pu_swap(s, l):             # pu: two pins swapped on the scheduler box
    for p in (l["inst"]["u_sched"]["pins"], {k[8:]: v for k, v in l["pins"].items() if k.startswith("u_sched.")}):
        for k in ("dy", "xy"):
            if k in p["score_fcfs"]: p["score_fcfs"][k], p["score_edf"][k] = p["score_edf"][k], p["score_fcfs"][k]
def b_pu_loop(s, l):             # pu: scores read the grant mux again, so the loop returns
    v = V(s, "pu")
    moved = [p for p in v["nets"]["score_rec"]["pins"] if p.endswith(".record")]
    v["nets"]["score_rec"]["pins"] = [p for p in v["nets"]["score_rec"]["pins"] if p not in moved]
    v["nets"]["record"]["pins"].extend(moved)
def b_release_2drv(s, l):        # release: second driver on a net
    V(s, "release")["nets"]["let_square"]["pins"].append("u_admitted.q")
def b_packer_width(s, l):        # packer: width mismatch on word_d
    for i in V(s, "packer")["instances"]:
        if i["inst"] == "u_word":
            for p in i["ports"]:
                if p["name"] == "d": p["width"] = "128"
def b_ready_noreader(s, l):      # ready: net with a driver but no reader
    V(s, "ready")["nets"]["wr"]["pins"] = ["wr_or.y"]
def b_sched_frame(s, l):         # sched: frame pin set no longer = parent box pins
    v = V(s, "sched"); v["ports"] = [p for p in v["ports"] if p["name"] != "score_row"]
    del v["nets"]["score_row"]
def b_credit_thru(s, l):         # credit: wire drawn straight through a box
    l["nets"]["gt0"]["lines"].append([[1150, 150], [1150, 330]])
def b_phy_widen(s, l):           # phy: width break at N_WIRES=2 no longer acknowledged
    s["known"] = [k for k in s["known"] if k["kind"] != "widen_width"]
def b_unpack_stub(s, l):         # unpack: the 'no driver' marker for out_tile removed
    l["stubs"] = [t for t in l["stubs"] if t["net"] != "out_tile"]
def b_sched_stale(s, l):         # sched: acknowledgement for a loop that does not exist (stale)
    s["known"].append({"kind": "comb_loop", "view": "sched", "nets": ["score_sel"], "finding": "F7"})

BREAKS = [  # (view, level, what, function, expected text in check output)
    ("top", 1, "CU<->PU wire send_en deleted", b_top_wire, "send_en"),
    ("top", 1, "doc pin 'done' dropped from hop_top", b_top_doc, "[doc] FAIL"),
    ("cu", 2, "policy_id wire end moved 10px off its pin", b_cu_offpin, "policy_id"),
    ("fsm", 3, "k_cnt fan-out junction dots removed", b_fsm_junction, "junction"),
    ("pu", 2, "u_sched score_fcfs/score_edf pins swapped", b_pu_swap, "score_"),
    ("pu", 2, "scores tied back onto the granted record", b_pu_loop, "loop"),
    ("release", 3, "second driver on let_square", b_release_2drv, "driver"),
    ("packer", 3, "u_word.d width 256 -> 128", b_packer_width, "width"),
    ("ready", 3, "net wr loses its reader", b_ready_noreader, "read by nobody"),
    ("sched", 3, "frame pin score_row removed (frame != parent box)", b_sched_frame, "score_row"),
    ("sched", 3, "stale comb-loop acknowledgement", b_sched_stale, "stale"),
    ("credit", 3, "wire routed through u_count box", b_credit_thru, "gt0"),
    ("phy", 3, "N_WIRES=2 width break no longer acknowledged", b_phy_widen, "widen"),
    ("unpack", 3, "'no driver' stub for out_tile removed", b_unpack_stub, "out_tile"),
]

def run(view, spec_file=None, layout_file=None):
    env = dict(os.environ); 
    if spec_file: env["SPEC"] = spec_file
    args = [sys.executable, "check.py", view] + ([layout_file] if layout_file else [])
    r = subprocess.run(args, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr

if __name__ == "__main__":
    os.makedirs("breaks", exist_ok=True); allok = True
    for n, (view, lvl, what, fn, expect) in enumerate(BREAKS, 1):
        s, l = copy.deepcopy(SPEC), L(view)
        fn(s, l)
        sf, lf = f"breaks/b{n:02d}_spec.json", f"breaks/b{n:02d}_layout_{view}.json"
        json.dump(s, open(sf, "w"), indent=1); json.dump(l, open(lf, "w"))
        rc, out = run(view, sf, lf)
        msgs = [x.strip() for x in out.splitlines() if x.strip().startswith("-") or "FAIL" in x]
        hit = rc == 1 and expect.lower() in out.lower()
        allok &= hit
        print(f"B{n:02d} L{lvl} {view:8s} {what}\n     -> exit {rc} {'CAUGHT' if hit else 'MISSED!'}: "
              + " | ".join(m for m in msgs if expect.lower() in m.lower())[:300])
    rc, out = run("top"); rc_all = subprocess.run([sys.executable, "check.py"], capture_output=True).returncode
    print(f"clean check.py -> exit {rc_all}")
    allok &= rc_all == 0
    print("ALL BREAKS CAUGHT" if allok else "BREAK DEMO FAILED"); sys.exit(0 if allok else 1)
