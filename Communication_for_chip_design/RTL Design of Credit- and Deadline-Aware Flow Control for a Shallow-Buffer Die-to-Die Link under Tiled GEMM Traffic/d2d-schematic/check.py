#!/usr/bin/env python3
"""Verify the D2D hop schematics.  exit 0 = every rule PASS, exit 1 = any FAIL.
usage: check.py                          -> all views
       check.py <view> [layout.json]     -> one view (optionally a different, e.g. broken, layout file)
       env SPEC=<file>                   -> use another spec.json (break_demo uses this)
Parts: [doc] spec vs the architecture doc tables   [net] netlist sanity of every view
       [loop]/[widen] design checks (each hit must be acknowledged in spec.known with a finding)
       [draw] drawing vs spec (CORDIC rules: pins, wires, boxes, junctions, labels)   [xview] frame = parent box."""
import json, re, sys, os, itertools
from collections import defaultdict

SPEC = json.load(open(os.environ.get("SPEC", "spec.json")))
VIEWS = {v["id"]: v for v in SPEC["views"]}
PARAMS = SPEC["params"]
DOC = open("source/architecture-ascii.md").read().splitlines()
FINDINGS = open("findings.md").read()

def ev(expr, **over):
    return int(eval(str(expr), {"__builtins__": {}}, dict(PARAMS, **over)))
def norm(w):
    w = str(w).replace("`", "").replace(" x ", "*").replace(" ", "")
    return w

# ================================================================== [doc] spec vs doc tables
def doc_table(start_pat):
    i = next(k for k, l in enumerate(DOC) if re.search(start_pat, l))
    rows = []
    for k in range(i + 2, len(DOC)):
        l = DOC[k]
        if not l.startswith("|"): break
        if set(l.replace("|", "").strip()) <= set("- "): continue
        rows.append((k + 1, [c.strip() for c in l.strip().strip("|").split("|")]))
    return rows

def check_doc():
    errs = []
    top = VIEWS["top"]; tp = {p["name"]: p for p in top["ports"]}
    seen = set()
    for ln, (pin, width, dirn) in doc_table(r"^\| Pin \| Width \| Direction"):
        names = re.findall(r"`(\w+)`", pin); widths = [norm(w) for w in width.split(",")]
        if len(widths) == 1: widths *= len(names)
        d = dirn.split(".")[0].strip()
        for n, w in zip(names, widths):
            seen.add(n)
            if n not in tp: errs.append(f"[doc] A:L{ln} hop_top pin {n} missing from spec"); continue
            if (tp[n]["dir"], norm(tp[n]["width"])) != (d, w):
                errs.append(f"[doc] A:L{ln} hop_top pin {n}: spec {tp[n]['dir']}/{tp[n]['width']} != doc {d}/{w}")
    for n in tp:
        if n not in seen: errs.append(f"[doc] spec hop_top pin {n} is not in the doc pin table")
    # CU<->PU wires: width from the table, direction from the layer-1 drawing arrows
    l1 = DOC[next(k for k, l in enumerate(DOC) if l.startswith("## Layer 1")):next(k for k, l in enumerate(DOC) if l.startswith("## Layer 2"))]
    cu2pu = {m.group(1) for l in l1 for m in [re.search(r"\| (\w+)(\[\*\])?\s*<-+\+", l)] if m and m.group(1) not in ("clk", "rst")}
    pu2cu = {m.group(1) for l in l1 for m in [re.search(r"\| (\w+)(\[\*\])? -+\+-->\|", l)] if m}
    blocks = {i["inst"]: {p["name"]: p for p in i["ports"]} for i in top["instances"]}
    tnets = top["nets"]
    wires = 0
    for ln, (wire, width, grow) in doc_table(r"^\| Wire \| Width \| Grows"):
        names = re.findall(r"`(\w+)`", wire); widths = [norm(w) for w in width.split(",")]
        if len(widths) == 1: widths *= len(names)
        for n, w in zip(names, widths):
            wires += 1
            if n in cu2pu: src, dst = "u_cu", "u_pu"
            elif n in pu2cu: src, dst = "u_pu", "u_cu"
            else: errs.append(f"[doc] A:L{ln} wire {n} has no arrow in the layer-1 drawing"); continue
            for inst, d in ((src, "out"), (dst, "in")):
                p = blocks[inst].get(n)
                if not p: errs.append(f"[doc] A:L{ln} wire {n}: no pin on {inst}"); continue
                if (p["dir"], norm(p["width"])) != (d, w): errs.append(f"[doc] A:L{ln} {inst}.{n}: {p['dir']}/{p['width']} != doc {d}/{w}")
            if ("yes" in grow) != ("N_WIRES" in w): errs.append(f"[doc] A:L{ln} wire {n}: 'grows' column disagrees with width {w}")
            if set(tnets.get(n, {}).get("pins", [])) != {f"{src}.{n}", f"{dst}.{n}"}:
                errs.append(f"[doc] wire {n} is not a net {src}.{n} -> {dst}.{n} in view top")
    rec = doc_table(r"^\| Field \| Width")
    rw = sum(int(re.match(r"\d+", c[1]).group()) for ln, c in rec if not c[0].startswith("`score`"))
    if rw != PARAMS["REC_W"]: errs.append(f"[doc] REC_W {PARAMS['REC_W']} != sum of record table {rw}")
    for ln, (par, val, _) in doc_table(r"^\| Parameter \| Value"):
        n = par.strip("`"); v = int(re.match(r"\d+", val).group())
        if PARAMS.get(n) != v: errs.append(f"[doc] A:L{ln} parameter {n}={v} but spec has {PARAMS.get(n)}")
    for v in SPEC["views"]:
        for i in v["instances"]:
            if not i.get("src"): errs.append(f"[doc] {v['id']}.{i['inst']} has no doc source")
            if "inferred" in i and len(i["inferred"]) < 10: errs.append(f"[doc] {v['id']}.{i['inst']} inferred without a reason")
        for n, d in v["nets"].items():
            if not d.get("src"): errs.append(f"[doc] net {v['id']}.{n} has no doc source")
            for k in ("unused", "nodriver"):
                if k in d:
                    f = d[k].get("finding", "")
                    if not d[k].get("reason") or not re.search(rf"^### {f}\b", FINDINGS, re.M):
                        errs.append(f"[doc] net {v['id']}.{n} {k} needs a reason and a finding in findings.md (got {f!r})")
    return errs, f"{len(tp)} hop_top pins, {wires} CU<->PU wires, record {rw} bits"

# ================================================================== [net] netlist of each view
def pins_of(v):
    out = {f"PORT.{p['name']}": dict(p, dir="out" if p["dir"] == "in" else "in", port=True) for p in v["ports"]}  # seen from inside
    for i in v["instances"]:
        for p in i["ports"]: out[f"{i['inst']}.{p['name']}"] = p
    return out

def comb_arcs(module, memo={}):
    """in-port -> set(out-ports) combinational paths through a module."""
    if module in memo: return memo[module]
    if module in SPEC["leaf_comb"]:
        r = defaultdict(set)
        for a, b in SPEC["leaf_comb"][module]: r[a].add(b)
        memo[module] = r; return r
    v = next((x for x in SPEC["views"] if x["module"] == module), None)
    r = defaultdict(set)
    if v:
        g = graph(v)
        for p in v["ports"]:
            if p["dir"] != "in": continue
            seen, st = set(), [f"PORT.{p['name']}"]
            while st:
                n = st.pop()
                for m in g.get(n, ()):
                    if m not in seen: seen.add(m); st.append(m)
            r[p["name"]] = {m[5:] for m in seen if m.startswith("PORT.") and m[5:] != p["name"]}
    memo[module] = r; return r

def graph(v):
    g = defaultdict(set)
    P = pins_of(v)
    for n, d in v["nets"].items():
        drv = [p for p in d["pins"] if P[p]["dir"] == "out"]
        for a in drv:
            for b in d["pins"]:
                if b != a: g[a].add(b)
    for i in v["instances"]:
        ins = [p["name"] for p in i["ports"] if p["dir"] == "in"]; outs = [p["name"] for p in i["ports"] if p["dir"] == "out"]
        if i["kind"] == "dreg": continue
        if i["kind"] in ("comb", "const"):
            for a in ins:
                for b in outs: g[f"{i['inst']}.{a}"].add(f"{i['inst']}.{b}")
        else:
            for a, bs in comb_arcs(i["module"]).items():
                for b in bs: g[f"{i['inst']}.{a}"].add(f"{i['inst']}.{b}")
    return g

def find_loops(v):
    g = graph(v); loops = []; color = {}; stack = []
    def dfs(n):
        color[n] = 1; stack.append(n)
        for m in sorted(g.get(n, ())):
            if color.get(m) == 1: loops.append(stack[stack.index(m):] + [m])
            elif not color.get(m): dfs(m)
        stack.pop(); color[n] = 2
    for n in sorted(list(g)):
        if not color.get(n): dfs(n)
    P = pins_of(v)
    net_of = {p: n for n, d in v["nets"].items() for p in d["pins"]}
    out = []
    for L in loops:
        nets = sorted({net_of[p] for p in L if p in net_of})
        out.append((nets, L))
    return out

def check_nets(vid):
    v = VIEWS[vid]; errs, notes = [], []
    P = pins_of(v)
    cnt = defaultdict(list)
    for n, d in v["nets"].items():
        for p in d["pins"]:
            if p not in P: errs.append(f"[net] {vid}: net {n} names unknown pin {p}")
            cnt[p].append(n)
    for p in P:
        if len(cnt[p]) != 1: errs.append(f"[net] {vid}: pin {p} is on {len(cnt[p])} nets {cnt[p]}")
    known = SPEC["known"]
    for n, d in v["nets"].items():
        pins = [p for p in d["pins"] if p in P]
        drv = [p for p in pins if P[p]["dir"] == "out"]; rd = [p for p in pins if P[p]["dir"] == "in"]
        if "nodriver" in d:
            if drv: errs.append(f"[net] {vid}: net {n} marked no-driver but driven by {drv}")
            notes.append(f"no driver: {vid}.{n} ({d['nodriver']['finding']})")
        elif len(drv) != 1: errs.append(f"[net] {vid}: net {n} has {len(drv)} drivers {drv}")
        if "unused" in d:
            if rd: errs.append(f"[net] {vid}: net {n} marked unused but read by {rd}")
            notes.append(f"unused: {vid}.{n} ({d['unused']['finding']})")
        elif not rd: errs.append(f"[net] {vid}: net {n} is read by nobody")
        ws = {p: ev(P[p]["width"]) for p in pins}
        if len(set(ws.values())) > 1: errs.append(f"[net] {vid}: width mismatch on net {n} at base params: {ws}")
        for nw in (2, 4):
            w2 = {p: ev(P[p]["width"], N_WIRES=nw) for p in pins}
            if len(set(w2.values())) > 1:
                key = f"{n}@N_WIRES={nw}"
                k = [x for x in known if x["kind"] == "widen_width" and x["view"] == vid and x["key"] in (key, f"{n}@N_WIRES=2")]
                if not k: errs.append(f"[widen] {vid}: net {n} mismatches when N_WIRES={nw}: {w2} (not acknowledged)")
                else: notes.append(f"widen: {vid}.{n} breaks at N_WIRES={nw} ({k[0]['finding']})")
    for x in known:
        if x["kind"] == "widen_width" and x["view"] == vid:
            n = x["key"].split("@")[0]
            if n not in v["nets"] or len({ev(P[p]["width"], N_WIRES=2) for p in v["nets"][n]["pins"]}) < 2:
                errs.append(f"[widen] stale acknowledgement {x}")
    loops = find_loops(v)
    keys, used = set(), set()
    for nets, L in loops:
        key = ">".join(nets); keys.add(key)
        k = [x for x in known if x["kind"] == "comb_loop" and x["view"] == vid and set(nets) <= set(x["nets"])]
        if k: used.add(id(k[0]))
        if not k: errs.append(f"[loop] {vid}: combinational loop with no register through nets {nets} (not acknowledged)")
        else: notes.append(f"loop: {vid} {' -> '.join(nets)} ({k[0]['finding']})")
    for x in known:
        if x["kind"] == "comb_loop" and x["view"] == vid and id(x) not in used:
            errs.append(f"[loop] stale acknowledgement {x}")
    if v["parent"]:
        pv, pi = v["parent"]
        inst = next((i for i in VIEWS[pv]["instances"] if i["inst"] == pi), None)
        if not inst or inst["module"] != v["module"]: errs.append(f"[net] {vid}: parent {pv}.{pi} is not a {v['module']}")
        else:
            a = {p["name"]: (p["dir"], norm(p["width"])) for p in v["ports"]}
            b = {p["name"]: (p["dir"], norm(p["width"])) for p in inst["ports"]}
            if a != b: errs.append(f"[net] {vid}: frame ports {a} != parent pins {b}")
    for i in v["instances"]:
        child = next((x for x in SPEC["views"] if x["module"] == i["module"]), None)
        if child and i.get("link") != child["id"]: errs.append(f"[net] {vid}.{i['inst']}: has inside view {child['id']} but no link")
    return errs, notes

# ================================================================== [draw] drawing vs spec (CORDIC geometry rules)
def on_seg(p, a, b, closed=True):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    lo = (lambda u, v, w: min(v, w) <= u <= max(v, w)) if closed else (lambda u, v, w: min(v, w) < u < max(v, w))
    if x1 == x2 == x: return lo(y, y1, y2)
    if y1 == y2 == y: return lo(x, x1, x2)
    return False
def seg_hits_rect(a, b, r, pad=0):
    x0, y0, x1, y1 = r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad
    sx0, sx1 = sorted((a[0], b[0])); sy0, sy1 = sorted((a[1], b[1]))
    return sx0 < x1 and sx1 > x0 and sy0 < y1 and sy1 > y0
def ov(r1, r2, pad=0):
    return r1[0] < r2[2] + pad and r1[2] > r2[0] - pad and r1[1] < r2[3] + pad and r1[3] > r2[1] - pad
def segs_of(lines):
    return [(tuple(l[i]), tuple(l[i + 1])) for l in lines for i in range(len(l) - 1)]

def check_draw(vid, L):
    v = VIEWS[vid]; errors = []; err = errors.append
    LI, F = L["inst"], L["frame"]
    SI = {i["inst"]: i for i in v["instances"]}
    for inst in SI:
        if inst not in LI: err(f"[draw] instance {inst} missing from drawing")
    for inst in LI:
        if inst not in SI: err(f"[draw] drawn instance {inst} not in spec")
    for inst, si in SI.items():
        if inst not in LI: continue
        b = LI[inst]; sp = {p["name"]: p for p in si["ports"]}
        want_mod = "assign" if si["module"] in ("assign",) else si["module"]
        if b["module"] != want_mod: err(f"[draw] {inst}: drawn module {b['module']} != spec {want_mod}")
        if set(b["pins"]) != set(sp): err(f"[draw] {inst}: pins drawn {sorted(b['pins'])} != spec {sorted(sp)}")
        for pn, d in b["pins"].items():
            if pn in sp:
                if (d["dir"], d["width"]) != (sp[pn]["dir"], ev(sp[pn]["width"])):
                    err(f"[draw] {inst}.{pn}: dir/width {d['dir']}/{d['width']} != spec {sp[pn]['dir']}/{sp[pn]['width']}")
                if d["side"] != ("L" if d["dir"] == "in" else "R"): err(f"[draw] {inst}.{pn}: {d['dir']} pin on side {d['side']}")
        if si.get("link") and b.get("link") != "#" + si["link"]: err(f"[draw] {inst}: box does not open view {si['link']}")
    sp = {p["name"]: p for p in v["ports"]}
    if set(L["ports"]) != set(sp): err(f"[draw] module ports drawn {sorted(L['ports'])} != spec {sorted(sp)}")
    for p, d in L["ports"].items():
        if p in sp and (d["dir"], d["width"]) != (sp[p]["dir"], ev(sp[p]["width"])):
            err(f"[draw] port {p}: {d['dir']}/{d['width']} != spec {sp[p]['dir']}/{sp[p]['width']}")
        if d["side"] != ("L" if d["dir"] == "in" else "R"): err(f"[draw] port {p} on wrong frame side")
    pins = {k: (tuple(x["xy"]), x) for k, x in L["pins"].items() if k.split(".")[0] in LI or k.startswith("PORT.")}
    for ref, (xy, d) in pins.items():
        inst, pn = ref.split(".", 1)
        if inst == "PORT":
            if xy[0] != (F["x0"] if d["side"] == "L" else F["x1"]) or not F["y0"] < xy[1] < F["y1"]: err(f"[draw] {ref} not on frame edge")
            continue
        b = LI[inst]
        ex = b["x"] if d["side"] == "L" else b["x"] + b["w"]
        m = 8 if b["h"] > 30 else 4
        if xy[0] != ex or not b["y"] + m <= xy[1] <= b["y"] + b["h"] - m: err(f"[draw] {ref} not on its box edge")
    by_side = defaultdict(list)
    for ref, (xy, d) in pins.items(): by_side[(ref.split(".")[0], d["side"])].append(xy[1])
    for k, ys in by_side.items():
        ys.sort()
        for a, c in zip(ys, ys[1:]):
            if c - a < 14: err(f"[draw] pins on {k} closer than 14px ({a},{c})")
    all_segs = []
    for net, d in L["nets"].items():
        for li, l in enumerate(d.get("lines", [])):
            for a, b in segs_of([l]): all_segs.append((net, f"{net}#{li}", a, b))
    for s in L["stubs"]:
        all_segs.append((s["net"], f"stub:{s['ref']}", tuple(s["seg"][0]), tuple(s["seg"][1])))
    for net, pid, a, b in all_segs:
        if a[0] != b[0] and a[1] != b[1]: err(f"[draw] {pid}: segment {a}-{b} not orthogonal")
        if a == b: err(f"[draw] {pid}: zero-length segment")
    drawn, want = set(L["nets"]), set(v["nets"])
    if drawn != want: err(f"[draw] nets drawn-only {sorted(drawn-want)}, spec-only {sorted(want-drawn)}")
    pin_at = defaultdict(list)
    for ref, (xy, d) in pins.items(): pin_at[xy].append(ref)
    for net, d in L["nets"].items():
        sn = v["nets"].get(net)
        if not sn: continue
        wantp = set(sn["pins"]); got = set()
        kind = "unused" if "unused" in sn else ("nodriver" if "nodriver" in sn else ("stub" if sn.get("stub") else "wire"))
        if kind in ("unused", "nodriver"):
            if kind not in d: err(f"[draw] net {net} must be drawn as a '{kind}' stub")
            for k in ("unused", "nodriver", "stub", "lines"):
                if k != kind and d.get(k): err(f"[draw] {kind} net {net} must have no '{k}'")
            got = set(d.get(kind, []))
            for ref in got:   # the dashed stub itself must be drawn on that pin, with its finding tag
                st = [s for s in L["stubs"] if s["net"] == net and s["ref"] == ref]
                if not st or ref not in pins or not any(tuple(q) == pins[ref][0] for q in st[0]["seg"]):
                    err(f"[draw] {kind} net {net}: dashed stub at {ref} not drawn")
                elif not any(sn[kind]["finding"] in t["s"] for t in L["texts"] if t.get("net") == net or t.get("stub") == ref or sn[kind]["finding"] in t["s"]):
                    err(f"[draw] {kind} net {net}: tag '{sn[kind]['finding']}' not drawn")
            if d.get("finding") != sn[kind]["finding"]: err(f"[draw] {kind} stub of {net} must show finding {sn[kind]['finding']}")
        elif kind == "stub":
            got = set(d.get("stub", []))
            if d.get("lines"): err(f"[draw] clock/reset net {net} must be stubs, not wires")
            for s in L["stubs"]:
                if s["net"] == net and not any(tuple(p) == pins[s["ref"]][0] for p in s["seg"]): err(f"[draw] stub {s['ref']} not on its pin")
        else:
            if d.get("unused") or d.get("nodriver") or d.get("stub"): err(f"[draw] net {net} is a real wire in the spec, drawn as a stub")
            lines = d.get("lines", []); parent = list(range(len(lines)))
            def find(i):
                while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
                return i
            if not lines: err(f"[draw] net {net} has no wire")
            for li, l in enumerate(lines):
                for end in (tuple(l[0]), tuple(l[-1])):
                    if pin_at.get(end): got.update(pin_at[end]); continue
                    hit = False
                    for lj, m in enumerate(lines):
                        if lj != li and any(on_seg(end, tuple(m[i]), tuple(m[i + 1])) for i in range(len(m) - 1)):
                            parent[find(li)] = find(lj); hit = True
                    if not hit: err(f"[draw] net {net}: dangling wire end at {end}")
                for xy, refs in pin_at.items():
                    if xy in (tuple(l[0]), tuple(l[-1])): continue
                    if any(on_seg(xy, tuple(l[i]), tuple(l[i + 1])) for i in range(len(l) - 1)):
                        err(f"[draw] net {net}: wire passes through pin(s) {refs}")
            if lines and len({find(i) for i in range(len(lines))}) != 1: err(f"[draw] net {net}: not one connected wire tree")
        if got != wantp: err(f"[draw] net {net}: missing {sorted(wantp-got)} extra {sorted(got-wantp)}")
    crossings = 0
    for (n1, p1, a1, b1), (n2, p2, a2, b2) in itertools.combinations(all_segs, 2):
        h1, h2 = a1[1] == b1[1], a2[1] == b2[1]
        if h1 == h2:
            if (a1[1] == a2[1]) if h1 else (a1[0] == a2[0]):
                k = 0 if h1 else 1
                lo = max(min(a1[k], b1[k]), min(a2[k], b2[k])); hi = min(max(a1[k], b1[k]), max(a2[k], b2[k]))
                if hi > lo: err(f"[draw] overlapping parallel segments: {p1} {a1}-{b1} and {p2} {a2}-{b2}")
                elif hi == lo and n1 != n2: err(f"[draw] nets {n1}/{n2} touch end-to-end")
            continue
        if n1 != n2:
            for e in (a1, b1):
                if on_seg(e, a2, b2): err(f"[draw] short: {p1} end {e} touches net {n2}")
            for e in (a2, b2):
                if on_seg(e, a1, b1): err(f"[draw] short: {p2} end {e} touches net {n1}")
            hs, vs = ((a1, b1), (a2, b2)) if h1 else ((a2, b2), (a1, b1))
            c = (vs[0][0], hs[0][1])
            if on_seg(c, *hs, closed=False) and on_seg(c, *vs, closed=False): crossings += 1
    boxes = {n: (b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]) for n, b in LI.items()}
    for net, pid, a, b in all_segs:
        for n, r in boxes.items():
            if seg_hits_rect(a, b, r): err(f"[draw] {pid} segment {a}-{b} crosses box {n}")
        for p in (a, b):
            if not (F["x0"] <= p[0] <= F["x1"] and F["y0"] <= p[1] <= F["y1"]): err(f"[draw] {pid} leaves the frame at {p}")
    for n1, n2 in itertools.combinations(boxes, 2):
        if seg_hits_rect(boxes[n1][:2], boxes[n1][2:], boxes[n2], pad=10): err(f"[draw] boxes {n1} and {n2} overlap / closer than 10px")
    for n, r in boxes.items():
        if not (F["x0"] < r[0] and r[2] < F["x1"] and F["y0"] < r[1] and r[3] < F["y1"]): err(f"[draw] box {n} outside frame")
    want_j = set()
    for net, d in L["nets"].items():
        segs = segs_of(d.get("lines", []))
        for p in {p for s in segs for p in s}:
            if sum(1 if p in (a, b) else (2 if on_seg(p, a, b, closed=False) else 0) for a, b in segs) >= 3: want_j.add((net, p))
    got_j = {(j["net"], tuple(j["p"])) for j in L["junctions"]}
    if want_j != got_j: err(f"[draw] junction dots wrong: missing {want_j-got_j} extra {got_j-want_j}")
    for t in L["texts"]:
        bb = t["bbox"]
        if t["owner"] in boxes:
            r = boxes[t["owner"]]
            if not (bb[0] >= r[0] + 2 and bb[2] <= r[2] - 2 and bb[1] >= r[1] + 2 and bb[3] <= r[3] - 2):
                err(f"[draw] label {t['s']!r} does not fit inside {t['owner']}")
        else:
            for n, r in boxes.items():
                if ov(bb, r, 2): err(f"[draw] label {t['s']!r} overlaps box {n}")
        for net, pid, a, b in all_segs:
            if seg_hits_rect(a, b, bb, pad=1): err(f"[draw] label {t['s']!r} is crossed by wire {pid}")
        if t["owner"] == "net" and not any(seg_hits_rect(a, b, bb, pad=8) for n, pid, a, b in all_segs if n == t["net"]):
            err(f"[draw] net label {t['s']!r} is not next to net {t['net']}")
        if bb[0] < 0 or bb[2] > L["W"] or bb[1] < 0 or bb[3] > L["H"]: err(f"[draw] label {t['s']!r} off canvas")
    for t1, t2 in itertools.combinations(L["texts"], 2):
        if ov(t1["bbox"], t2["bbox"], 2): err(f"[draw] labels {t1['s']!r} and {t2['s']!r} overlap")
    return errors, f"{len(LI)} boxes, {len(all_segs)} wire segments, {len(L['junctions'])} junction dots, {crossings} plain crossings, {len(L['texts'])} labels"

def check_xview(vid, L):
    """the drawn frame of a view = the drawn box of its parent instance (names, dirs, widths)."""
    v = VIEWS[vid]; errs = []
    if not v["parent"]: return errs
    pv, pi = v["parent"]
    try: PL = json.load(open(f"layout_{pv}.json"))
    except FileNotFoundError: return [f"[xview] layout_{pv}.json missing"]
    b = PL["inst"].get(pi)
    if not b: return [f"[xview] parent box {pv}.{pi} not drawn"]
    a = {p: (d["dir"], d["width"]) for p, d in L["ports"].items()}
    c = {p: (d["dir"], d["width"]) for p, d in b["pins"].items()}
    if a != c: errs.append(f"[xview] frame of {vid} {sorted(set(a.items()) ^ set(c.items()))} differs from box {pv}.{pi}")
    if b.get("link") != f"#{vid}": errs.append(f"[xview] box {pv}.{pi} does not link to #{vid}")
    return errs

def check(vid, layfile=None, doc=True):
    L = json.load(open(layfile or f"layout_{vid}.json"))
    e1, notes = check_nets(vid)
    e2, stats = check_draw(vid, L)
    e3 = check_xview(vid, L)
    errs = e1 + e2 + e3
    v = VIEWS[vid]
    print(f"[{vid}] spec: {len(v['instances'])} instances, {len(v['nets'])} nets; drawing: {stats}")
    for n in notes: print(f"   . {n}")
    if errs:
        print(f"[{vid}] FAIL: {len(errs)} problem(s)")
        for e in errs: print("   -", e)
        return False
    print(f"[{vid}] PASS")
    return True

if __name__ == "__main__":
    ok = True
    derr, dstat = check_doc()
    print(f"[doc] {dstat}")
    if derr:
        ok = False; print(f"[doc] FAIL: {len(derr)} problem(s)"); [print("   -", e) for e in derr]
    else: print("[doc] PASS")
    if len(sys.argv) > 1:
        ok = check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None) and ok
    else:
        ok = all([check(v) for v in VIEWS]) and ok
    print("ALL PASS" if ok else "CHECK FAILED")
    sys.exit(0 if ok else 1)
