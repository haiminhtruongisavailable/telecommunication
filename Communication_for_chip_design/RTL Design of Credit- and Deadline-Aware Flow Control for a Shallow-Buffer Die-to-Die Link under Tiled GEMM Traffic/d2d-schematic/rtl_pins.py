#!/usr/bin/env python3
"""Compare the pins of the old flat rtl/ modules (source/rtl, commit in source/SOURCE_COMMIT)
with the new-architecture modules in spec.json that reuse them.  Report only (exit 0);
the result is copied into findings.md (F29).  Widths are evaluated with each side's own
parameter defaults (rtl) / spec params at N_WIRES=1 (spec)."""
import re, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
S = json.load(open("spec.json")); P = dict(S["params"])
PAIRS = [("credit.v", "credit", "credit"), ("packer.v", "packer", "packer"),
         ("scheduler_edf.v", "scheduler_edf", "scheduler"), ("fifo_k.v", "fifo_k", "ready_mem"),
         ("hop_top.v", "hop_top", "hop_top")]

def ev(expr, env):
    e = expr
    for k in sorted(env, key=len, reverse=True): e = re.sub(rf"\b{k}\b", str(env[k]), e)
    return eval(e.replace("×", "*"))

def parse_rtl(path, mod):
    txt = open(path).read(); lines = txt.splitlines()
    env = {m.group(1): int(m.group(2)) for m in re.finditer(r"parameter\s+(?:integer\s+)?(\w+)\s*=\s*(\d+)", txt)}
    ports = {}
    for n, ln in enumerate(lines, 1):
        m = re.match(r"\s*(input|output)\s+(?:wire|reg)?\s*(\[([^:]+):0\])?\s*(\w+)", ln)
        if m:
            w = ev(m.group(3), env) + 1 if m.group(2) else 1
            ports[m.group(4)] = ("in" if m.group(1) == "input" else "out", w, (m.group(3) or "") , n)
        if re.match(r"\s*\);", ln) and ports: break
    return ports

def spec_ports(module):
    v = next((v for v in S["views"] if v["module"] == module), None)
    if v: return {p["name"]: (p["dir"], ev(p["width"], P), p["width"], p["src"]) for p in v["ports"]}

if __name__ == "__main__":
    for f, rmod, smod in PAIRS:
        r = parse_rtl(f"source/rtl/{f}", rmod); s = spec_ports(smod)
        print(f"== rtl/{f} ({rmod}) vs spec {smod}")
        both = sorted(set(r) & set(s))
        for n in both:
            ok = r[n][:2] == s[n][:2]
            print(f"   {'same' if ok else 'DIFF'} {n}: rtl {r[n][0]} {r[n][1]} (rtl/{f}:{r[n][3]})  spec {s[n][0]} {s[n][1]} ({s[n][3]})")
        for n in sorted(set(r) - set(s)): print(f"   rtl-only  {n}: {r[n][0]} {r[n][1]}  (rtl/{f}:{r[n][3]})")
        for n in sorted(set(s) - set(r)): print(f"   spec-only {n}: {s[n][0]} {s[n][2]}={s[n][1]}  ({s[n][3]})")
