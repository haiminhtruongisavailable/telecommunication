"""Generic drawing helpers for hand-placed schematics (no routing). Same look as the approved CORDIC kit.
A view V = dict(name, W, H, frame, ports, inst, nets). All coordinates are given by hand in layout.py.
Pin widths are NOT typed in layout.py: bind() copies them from spec.json (expression + value at base params)."""
import json, re

TIMES = "\u00d7"
FONT = "Arial, Helvetica, sans-serif"
PIN_FS, HEAD_FS, INST_FS, NET_FS, PORT_FS = 11, 11, 13, 10, 14
STUB_LEN = 14

def box(module, head, inst, x, y, w, h, left=(), right=(), **kw):
    """left/right: (pin, absolute_y[, opts]) -- inputs on the left edge, outputs on the right edge."""
    pins = {}
    for side, lst, d in (("L", left, "in"), ("R", right, "out")):
        for p in lst:
            name, py = p[:2]
            pins[name] = dict(side=side, dy=py - y, dir=d, **(p[2] if len(p) > 2 else {}))
    return dict(module=module, head=head, inst=inst, x=x, y=y, w=w, h=h, pins=pins, **kw)

def blk(module, inst, x, y, w, h, left, right, link=None):
    return box(module, module, inst, x, y, w, h, left, right, **({"link": "#" + link} if link else {}))

def dreg(inst, x, y, w=150):
    # clk +52, rst +72, d +92 ; q +72   (head filled from spec: 'dreg · <width> DFF')
    return box("dreg", "dreg", inst, x, y, w, 110, left=[("clk", y + 52), ("rst", y + 72), ("d", y + 92)], right=[("q", y + 72)])

def const(inst, x, y_out, w=86):
    return box("const", None, inst, x, y_out - 12, w, 24, right=[("out", y_out, dict(nolabel=True))])

def op(inst, x, y, w, h, left, right, labels=False, **kw):
    """assign / leaf cell box. labels=False hides pin names (center symbol says it all)."""
    o = {} if labels else dict(nolabel=True)
    L = [(p[0], p[1], dict(o, **(p[2] if len(p) > 2 else {}))) for p in left]
    R = [(p[0], p[1], dict(o, **(p[2] if len(p) > 2 else {}))) for p in right]
    return box("assign", None, inst, x, y, w, h, L, R, **kw)

def mux(inst, x, y, w=72):
    # sel / 1 / 0 on the left, y on the right (assign y = sel ? a1 : a0)
    return box("assign", None, inst, x, y, w, 80, left=[("sel", y + 20, dict(plain=True)), ("1", y + 40, dict(plain=True)),
               ("0", y + 60, dict(plain=True))], right=[("y", y + 40, dict(nolabel=True))], center_small="mux", center_at=(0.62, 0.78))

def wlabel(name, wexpr):
    w = str(wexpr)
    if w == "1": return name
    if w.isdigit(): return f"[{int(w)-1}:0] {name}"
    return f"[{w.replace('*', TIMES)}-1:0] {name}"

def evalw(expr, params):
    return int(eval(str(expr), {"__builtins__": {}}, dict(params)))

def bind(V, sv, spec_inst, params):
    """copy module type, widths and dirs of every drawn pin from the spec view (sv)."""
    for p, d in V["ports"].items():
        sp = next((q for q in sv["ports"] if q["name"] == p), None)
        if sp: d.update(wexpr=sp["width"], width=evalw(sp["width"], params))
        else: d.update(wexpr="?", width=-1)
    for n, b in V["inst"].items():
        si = spec_inst.get(n)
        for p, d in b["pins"].items():
            sp = next((q for q in si["ports"] if q["name"] == p), None) if si else None
            if sp: d.update(wexpr=sp["width"], width=evalw(sp["width"], params))
            else: d.update(wexpr="?", width=-1)
        if si:
            if si["kind"] in ("comb", "const") and not b.get("center") and not b.get("center_small") and not b.get("head"):
                b["center"] = si.get("center")
            if b["module"] == "dreg":
                qw = next(q["width"] for q in si["ports"] if q["name"] == "q")
                b["head"] = f"dreg \u00b7 {str(qw).replace('*', TIMES)} DFF" + (f" \u00b7 {si['head_extra']}" if si.get("head_extra") else "")
            if si.get("inferred"): b["inferred"] = True
    return V

def text_w(s, fs, bold=False):
    return len(s) * fs * (0.64 if bold else 0.58)

def pin_xy(V, ref):
    inst, pin = ref.split(".", 1)
    if inst == "PORT":
        p = V["ports"][pin]
        return (V["frame"]["x0"] if p["side"] == "L" else V["frame"]["x1"], p["y"])
    b = V["inst"][inst]; p = b["pins"][pin]
    return (b["x"] if p["side"] == "L" else b["x"] + b["w"], b["y"] + p["dy"])

def on_seg(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if x1 == x2 == x: return min(y1, y2) < y < max(y1, y2)
    if y1 == y2 == y: return min(x1, x2) < x < max(x1, x2)
    return False

def build(V):
    texts, stubs = [], []
    for n, b in V["inst"].items():
        cx = b["x"] + b["w"] / 2
        if b.get("head"):
            texts.append(dict(x=cx, y=b["y"] + 16, s=b["head"], fs=HEAD_FS, anchor="middle", owner=n))
            texts.append(dict(x=cx, y=b["y"] + 32, s=b["inst"], fs=INST_FS, anchor="middle", bold=True, owner=n))
        if b.get("center"):
            fs = 18 if len(b["center"]) <= 2 and b["h"] >= 30 else 12
            cy = b.get("center_y", b["h"] / 2)
            texts.append(dict(x=cx, y=b["y"] + cy + fs * 0.35, s=b["center"], fs=fs, anchor="middle", bold=True, owner=n))
        if b.get("center_small"):
            fx, fy = b["center_at"]
            texts.append(dict(x=b["x"] + b["w"] * fx, y=b["y"] + b["h"] * fy + 4, s=b["center_small"], fs=10, anchor="middle", bold=True, owner=n))
        for p, d in b["pins"].items():
            if d.get("nolabel"): continue
            x, y = pin_xy(V, f"{n}.{p}")
            texts.append(dict(x=x + 5 if d["side"] == "L" else x - 5, y=y + 4,
                              s=p if d.get("plain") else wlabel(p, d["wexpr"]), fs=PIN_FS,
                              anchor="start" if d["side"] == "L" else "end", owner=n, pin=p))
    for p, d in V["ports"].items():
        x, y = pin_xy(V, f"PORT.{p}")
        texts.append(dict(x=x - 10 if d["side"] == "L" else x + 10, y=y + 5, s=wlabel(p, d["wexpr"]), fs=PORT_FS,
                          anchor="end" if d["side"] == "L" else "start", owner="PORT"))
    F = V["frame"]
    texts.append(dict(x=(F["x0"] + F["x1"]) / 2, y=F["y0"] + 28, s=F["title"], fs=20, anchor="middle", bold=True, owner="FRAME"))
    for net, d in V["nets"].items():
        for ref in d.get("stub", []):
            x, y = pin_xy(V, ref)
            if ref.startswith("PORT."):
                stubs.append(dict(net=net, ref=ref, seg=[(x, y), (x + STUB_LEN, y)], circ=(x + STUB_LEN + 3, y)))
            else:
                stubs.append(dict(net=net, ref=ref, seg=[(x - STUB_LEN, y), (x, y)], circ=(x - STUB_LEN - 3, y)))
                texts.append(dict(x=x - STUB_LEN - 8, y=y + 3.5, s=net, fs=NET_FS, anchor="end", owner="stub", net=net, italic=True))
        for kind, word in (("unused", "unused"), ("nodriver", "no driver")):
            for ref in d.get(kind, []):
                x, y = pin_xy(V, ref)
                fid = d.get("finding", "")
                s = f"{word} \u00b7 {fid}" if fid else word
                inwards = (ref.startswith("PORT.") and V["ports"][ref[5:]]["side"] == "L") or \
                          (not ref.startswith("PORT.") and V["inst"][ref.split(".")[0]]["pins"][ref.split(".", 1)[1]]["side"] == "R")
                if inwards:   # stub goes to the right of the pin
                    stubs.append(dict(net=net, ref=ref, seg=[(x, y), (x + STUB_LEN, y)], **{kind: True}))
                    texts.append(dict(x=x + STUB_LEN + 4, y=y + 3.5, s=s, fs=NET_FS, anchor="start", owner="stub", net=net, italic=True, warn=True))
                else:
                    stubs.append(dict(net=net, ref=ref, seg=[(x - STUB_LEN, y), (x, y)], **{kind: True}))
                    texts.append(dict(x=x - STUB_LEN - 4, y=y + 3.5, s=s, fs=NET_FS, anchor="end", owner="stub", net=net, italic=True, warn=True))
        for lab in d.get("labels", []):
            lx, ly = lab[:2]; s = lab[2] if len(lab) > 2 else net
            texts.append(dict(x=lx, y=ly, s=s, fs=NET_FS, anchor="start", owner="net", net=net, italic=True))
    for t in texts:
        w = text_w(t["s"], t["fs"], t.get("bold"))
        x0 = t["x"] if t["anchor"] == "start" else (t["x"] - w if t["anchor"] == "end" else t["x"] - w / 2)
        t["bbox"] = [x0, t["y"] - t["fs"] * 0.78, x0 + w, t["y"] + t["fs"] * 0.22]
    return texts, stubs

def junctions(V):
    pts = []
    for net, d in V["nets"].items():
        segs = [(tuple(l[i]), tuple(l[i + 1])) for l in d.get("lines", []) for i in range(len(l) - 1)]
        for p in {p for s in segs for p in s}:
            deg = sum(1 if p in (a, b) else (2 if on_seg(p, a, b) else 0) for a, b in segs)
            if deg >= 3: pts.append(dict(net=net, p=p))
    return pts

def arrow(x, y, direction):
    s = 7 * direction
    return f'<path d="M{x},{y} L{x-s},{y-3.5} L{x-s},{y+3.5} Z" fill="#000"/>'

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg(V, texts, stubs, juncs, links=False):
    W, H, F = V["W"], V["H"], V["frame"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>',
         f'<rect x="{F["x0"]}" y="{F["y0"]}" width="{F["x1"]-F["x0"]}" height="{F["y1"]-F["y0"]}" fill="none" stroke="#000" stroke-width="1.6"/>']
    for n, b in V["inst"].items():
        dash = ' stroke-dasharray="5,3"' if b.get("inferred") else ""
        o.append(f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" fill="#fff" stroke="#000" stroke-width="1.3"{dash}/>')
    for net, d in V["nets"].items():
        for l in d.get("lines", []):
            o.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in l)}" fill="none" stroke="#000" stroke-width="1.3"/>')
    for s in stubs:
        a, b = s["seg"]
        dash = ' stroke-dasharray="3,2"' if (s.get("unused") or s.get("nodriver")) else ""
        col = "#c00" if s.get("nodriver") else "#000"
        o.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{col}" stroke-width="1.3"{dash}/>')
        if "circ" in s:
            o.append(f'<circle cx="{s["circ"][0]}" cy="{s["circ"][1]}" r="3" fill="#fff" stroke="#000" stroke-width="1.2"/>')
    for n, b in V["inst"].items():
        for p, d in b["pins"].items():
            if d["dir"] == "in":
                o.append(arrow(*pin_xy(V, f"{n}.{p}"), 1))
    for p, d in V["ports"].items():
        x, y = pin_xy(V, f"PORT.{p}")
        o.append(f'<rect x="{x-3}" y="{y-3}" width="6" height="6" fill="#000"/>')
    for j in juncs:
        o.append(f'<circle cx="{j["p"][0]}" cy="{j["p"][1]}" r="3.6" fill="#000"/>')
    for t in texts:
        st = ""
        if t.get("bold"): st += ' font-weight="bold"'
        if t.get("italic"): st += ' font-style="italic" fill="#c00"' if t.get("warn") else ' font-style="italic" fill="#444"'
        o.append(f'<text x="{t["x"]}" y="{t["y"]}" font-size="{t["fs"]}" text-anchor="{t["anchor"]}"{st}>{esc(t["s"])}</text>')
    if links:   # clickable instance boxes (index.html navigation)
        for n, b in V["inst"].items():
            if b.get("link"):
                o.append(f'<a href="{b["link"]}"><rect class="hot" x="{b["x"]}" y="{b["y"]}" width="{b["w"]}" height="{b["h"]}" '
                         f'fill="#1f6feb" fill-opacity="0" stroke="none" style="cursor:pointer"><title>open {b["inst"]}</title></rect></a>')
    o.append("</svg>")
    return "\n".join(o)

def emit(V):
    texts, stubs = build(V)
    juncs = junctions(V)
    pins = {}
    for n, b in V["inst"].items():
        for p, d in b["pins"].items():
            pins[f"{n}.{p}"] = dict(xy=pin_xy(V, f"{n}.{p}"), **d)
    for p, d in V["ports"].items():
        pins[f"PORT.{p}"] = dict(xy=pin_xy(V, f"PORT.{p}"), **d)
    out = dict(V, pins=pins, texts=texts, stubs=stubs, junctions=juncs)
    json.dump(out, open(f"layout_{V['name']}.json", "w"), indent=1)
    open(f"{V['name']}.svg", "w").write(svg(V, texts, stubs, juncs))
    return svg(V, texts, stubs, juncs, links=True)
