#!/usr/bin/env python3
"""Layer drawings for the hop. Same page shape as i05_cordic/rtl-blocks/dist/index.html.

No port table and no meaning column. A box is a block. An arrow is a connection.
Policy blocks have no deeper view.
"""
import html
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "index.html")

DATA = "#2563eb"
CTRL = "#ea580c"
MONO = "ui-monospace, 'DejaVu Sans Mono', Menlo, Consolas, monospace"
SANS = "system-ui, 'DejaVu Sans', 'Segoe UI', Arial, sans-serif"

# lanes: rows of boxes. A box is (id, name, module, opens or None).
# edges: (src, dst, net, "data"|"control"). src/dst may be "L" or "R" for the frame.
VIEWS = [
    {
        "id": "top",
        "tab": "L0 top",
        "title": "L0 - hop_top",
        "lanes": [[("hop", "hop_top", "hop_top", "inside_top")]],
        "edges": [
            ("L", "hop", "panel_byte", "data"),
            ("L", "hop", "other_flit", "data"),
            ("hop", "R", "out_flit", "data"),
            ("hop", "R", "done", "control"),
        ],
    },
    {
        "id": "inside_top",
        "tab": "L1 CU + PU",
        "title": "L1 - inside hop_top",
        "lanes": [[
            ("u_pu", "u_pu", "hop_processing", "inside_pu"),
            ("u_cu", "u_cu", "hop_control", "inside_cu"),
        ]],
        "edges": [
            ("u_cu", "u_pu", "release_en", "control"),
            ("u_cu", "u_pu", "W", "control"),
            ("u_cu", "u_pu", "policy_id", "control"),
            ("u_cu", "u_pu", "admit_limit", "control"),
            ("u_cu", "u_pu", "send_en", "control"),
            ("u_pu", "u_cu", "credit_count", "data"),
            ("u_pu", "u_cu", "ready_count", "data"),
            ("u_pu", "u_cu", "grant_idx", "data"),
            ("u_pu", "u_cu", "grant_valid", "control"),
            ("u_pu", "u_cu", "first_done", "control"),
            ("u_pu", "u_cu", "wave_done", "control"),
        ],
    },
    {
        "id": "inside_pu",
        "tab": "L2 PU path",
        "title": "L2 - inside u_pu, the path",
        "lanes": [[
            ("u_release", "u_release", "release", "inside_release"),
            ("u_packer", "u_packer", "packer", "inside_packer"),
            ("u_ready", "u_ready", "ready_mem", "inside_ready"),
            ("u_sched", "u_sched", "scheduler", "inside_sched"),
        ]],
        "edges": [
            ("L", "u_release", "release_en", "control"),
            ("L", "u_packer", "panel_byte", "data"),
            ("L", "u_ready", "other_flit", "data"),
            ("u_release", "u_packer", "square", "control"),
            ("u_packer", "u_ready", "record", "data"),
            ("u_ready", "u_sched", "record", "data"),
            ("u_ready", "R", "to_scores", "data"),
            ("L", "u_sched", "policy_id", "control"),
            ("u_sched", "R", "grant_idx", "data"),
        ],
    },
    {
        "id": "inside_scores",
        "tab": "L2 scores",
        "title": "L2 - score blocks, ports only",
        "lanes": [[
            ("s0", "u_fcfs", "score_fcfs", None),
            ("s1", "u_edf", "score_edf", None),
            ("s2", "u_firing", "score_firing", None),
            ("s3", "u_shared", "score_shared", None),
            ("s4", "u_row", "score_row", None),
        ]],
        "edges": [
            ("L", "s0", "record", "data"),
            ("L", "s1", "record", "data"),
            ("L", "s2", "record", "data"),
            ("L", "s3", "record", "data"),
            ("L", "s4", "record", "data"),
            ("s0", "R", "score", "data"),
            ("s1", "R", "score", "data"),
            ("s2", "R", "score", "data"),
            ("s3", "R", "score", "data"),
            ("s4", "R", "score", "data"),
        ],
    },
    {
        "id": "inside_grant",
        "tab": "L2 grant path",
        "title": "L2 - inside u_pu, grant to unpack",
        "lanes": [[
            ("u_credit", "u_credit", "credit", "inside_credit"),
            ("u_phy", "u_phy", "phy_box", "inside_phy"),
            ("u_gather", "u_gather", "gather", "inside_gather"),
            ("u_unpack", "u_unpack", "unpack", "inside_unpack"),
        ]],
        "edges": [
            ("L", "u_credit", "grant_idx", "data"),
            ("L", "u_credit", "send_en", "control"),
            ("u_credit", "u_phy", "pass_en", "control"),
            ("u_credit", "R", "credit_count", "data"),
            ("u_phy", "u_gather", "arrived", "data"),
            ("u_gather", "u_unpack", "out_flit", "data"),
            ("u_unpack", "R", "panel_byte", "data"),
            ("L", "u_credit", "credit_return", "control"),
        ],
    },
    {
        "id": "inside_cu",
        "tab": "L2 CU",
        "title": "L2 - inside u_cu",
        "lanes": [[
            ("u_fsm", "u_fsm", "release_fsm", "inside_fsm"),
            ("u_pol", "u_pol", "policy_reg", "inside_pol"),
            ("u_adm", "u_adm", "admit_reg", "inside_adm"),
            ("u_gate", "u_gate", "send_gate", "inside_gate"),
        ]],
        "edges": [
            ("u_fsm", "R", "release_en", "control"),
            ("u_fsm", "R", "W", "control"),
            ("u_pol", "R", "policy_id", "control"),
            ("u_adm", "R", "admit_limit", "control"),
            ("L", "u_gate", "credit_count", "data"),
            ("L", "u_gate", "grant_valid", "control"),
            ("u_gate", "R", "send_en", "control"),
        ],
    },
    {
        "id": "inside_packer",
        "tab": "L3 packer",
        "title": "L3 - inside u_packer",
        "lanes": [
            [("sh", "u_shift", "shift_l8", None),
             ("mx", "u_word_mux", "mux", None),
             ("rg", "u_word", "dreg", None)],
            [("ct", "u_cnt", "addsub", None),
             ("cm", "u_fire", "cmp", None)],
        ],
        "edges": [
            ("L", "sh", "panel_byte", "data"),
            ("sh", "mx", "shifted", "data"),
            ("rg", "mx", "hold", "data"),
            ("mx", "rg", "d", "data"),
            ("ct", "cm", "byte_cnt", "data"),
            ("cm", "mx", "fire", "control"),
            ("rg", "R", "payload", "data"),
        ],
    },
    {
        "id": "inside_ready",
        "tab": "L3 ready",
        "title": "L3 - inside u_ready",
        "lanes": [[
            ("sm", "u_src_mux", "mux", None),
            ("sl", "u_slot", "dreg", None),
            ("rm", "u_read_mux", "mux", None),
        ]],
        "edges": [
            ("L", "sm", "record", "data"),
            ("L", "sm", "other_flit", "data"),
            ("sm", "sl", "d", "data"),
            ("sl", "rm", "q", "data"),
            ("L", "rm", "grant_idx", "control"),
            ("rm", "R", "record", "data"),
        ],
    },
    {
        "id": "inside_sched",
        "tab": "L3 scheduler",
        "title": "L3 - inside u_sched",
        "lanes": [[
            ("pm", "u_policy_mux", "mux", None),
            ("cp", "u_cmp_min", "cmp", None),
        ]],
        "edges": [
            ("L", "pm", "score_fcfs", "data"),
            ("L", "pm", "score_edf", "data"),
            ("L", "pm", "score_firing", "data"),
            ("L", "pm", "score_shared", "data"),
            ("L", "pm", "score_row", "data"),
            ("L", "pm", "policy_id", "control"),
            ("pm", "cp", "score", "data"),
            ("cp", "R", "grant_idx", "data"),
            ("cp", "R", "grant_valid", "control"),
        ],
    },
    {
        "id": "inside_credit",
        "tab": "L3 credit",
        "title": "L3 - inside u_credit",
        "lanes": [[
            ("as", "u_addsub", "addsub", None),
            ("mx", "u_cnt_mux", "mux", None),
            ("rg", "u_count", "dreg", None),
            ("cm", "u_nz", "cmp", None),
        ]],
        "edges": [
            ("L", "as", "accept", "control"),
            ("L", "as", "credit_return", "control"),
            ("rg", "as", "count", "data"),
            ("as", "mx", "next", "data"),
            ("rg", "mx", "hold", "data"),
            ("mx", "rg", "d", "data"),
            ("rg", "cm", "count", "data"),
            ("rg", "R", "credit_count", "data"),
            ("cm", "R", "gt0", "control"),
        ],
    },
    {
        "id": "inside_phy",
        "tab": "L3 phy",
        "title": "L3 - inside u_phy, one lane",
        "lanes": [[
            ("mx", "u_load_mux", "mux", None),
            ("d0", "u_s0", "dreg", None),
            ("d1", "u_s1", "dreg", None),
            ("d2", "u_s2", "dreg", None),
            ("d3", "u_s3", "dreg", None),
        ]],
        "edges": [
            ("L", "mx", "payload", "data"),
            ("L", "mx", "pass_en", "control"),
            ("d0", "mx", "hold", "data"),
            ("mx", "d0", "d", "data"),
            ("d0", "d1", "q", "data"),
            ("d1", "d2", "q", "data"),
            ("d2", "d3", "q", "data"),
            ("d3", "R", "arrived", "data"),
        ],
    },
    {
        "id": "inside_gather",
        "tab": "L3 gather",
        "title": "L3 - inside u_gather",
        "lanes": [[
            ("mx", "u_lane_mux", "mux", None),
            ("rg", "u_out", "dreg", None),
        ]],
        "edges": [
            ("L", "mx", "lane", "data"),
            ("mx", "rg", "d", "data"),
            ("rg", "R", "out_flit", "data"),
        ],
    },
    {
        "id": "inside_unpack",
        "tab": "L3 unpack",
        "title": "L3 - inside u_unpack",
        "lanes": [[
            ("sh", "u_shift", "shift_r8", None),
            ("mx", "u_byte_mux", "mux", None),
            ("rg", "u_word", "dreg", None),
        ]],
        "edges": [
            ("L", "sh", "out_flit", "data"),
            ("sh", "mx", "shifted", "data"),
            ("rg", "mx", "hold", "data"),
            ("mx", "rg", "d", "data"),
            ("sh", "R", "panel_byte", "data"),
        ],
    },
    {
        "id": "inside_release",
        "tab": "L3 release",
        "title": "L3 - inside u_release",
        "lanes": [[
            ("k", "u_k", "dreg", None),
            ("cm", "u_admit_cmp", "cmp", None),
            ("ad", "u_admitted", "dreg", None),
        ]],
        "edges": [
            ("L", "cm", "admit_limit", "control"),
            ("ad", "cm", "admitted", "data"),
            ("cm", "R", "let_square", "control"),
            ("k", "R", "k", "data"),
            ("L", "ad", "square_finished", "control"),
        ],
    },
    {
        "id": "inside_fsm",
        "tab": "L3 release_fsm",
        "title": "L3 - inside u_fsm",
        "lanes": [[
            ("nx", "u_next", "ctrl_next", None),
            ("st", "u_state", "dreg", None),
            ("kk", "u_k", "dreg", None),
        ]],
        "edges": [
            ("st", "nx", "state", "control"),
            ("nx", "st", "state_next", "control"),
            ("nx", "kk", "k_next", "data"),
            ("st", "R", "release_en", "control"),
            ("kk", "R", "W", "control"),
        ],
    },
    {
        "id": "inside_pol",
        "tab": "L3 policy_reg",
        "title": "L3 - inside u_pol",
        "lanes": [[("rg", "u_policy", "dreg", None)]],
        "edges": [
            ("L", "rg", "policy_next", "control"),
            ("rg", "R", "policy_id", "control"),
        ],
    },
    {
        "id": "inside_adm",
        "tab": "L3 admit_reg",
        "title": "L3 - inside u_adm",
        "lanes": [[("rg", "u_admit", "dreg", None)]],
        "edges": [
            ("L", "rg", "admit_next", "control"),
            ("rg", "R", "admit_limit", "control"),
        ],
    },
    {
        "id": "inside_gate",
        "tab": "L3 send_gate",
        "title": "L3 - inside u_gate",
        "lanes": [[
            ("cm", "u_nz", "cmp", None),
            ("mx", "u_and", "mux", None),
        ]],
        "edges": [
            ("L", "cm", "credit_count", "data"),
            ("cm", "mx", "gt0", "control"),
            ("L", "mx", "grant_valid", "control"),
            ("mx", "R", "send_en", "control"),
        ],
    },
]


def esc(s):
    return html.escape(s, quote=True)


def draw(view):
    lanes = view["lanes"]
    bw, bh, gap_x, gap_y = 168, 64, 88, 36
    left_m, top_m = 132, 28
    pos = {}
    max_n = max(len(r) for r in lanes)
    width = left_m + max_n * bw + (max_n - 1) * gap_x + 150
    for ri, row in enumerate(lanes):
        y = top_m + ri * (bh + gap_y + 28)
        row_w = len(row) * bw + (len(row) - 1) * gap_x
        x0 = left_m + (max_n * bw + (max_n - 1) * gap_x - row_w) / 2
        for i, (bid, name, mod, opens) in enumerate(row):
            x = x0 + i * (bw + gap_x)
            pos[bid] = (x, y, bw, bh, name, mod, opens)
    back_n = 0
    for src, dst, _net, _kind in view["edges"]:
        if src in pos and dst in pos and pos[src][0] > pos[dst][0]:
            back_n += 1
    row_bottom = top_m + len(lanes) * bh + (len(lanes) - 1) * (gap_y + 28)
    bus_y0 = row_bottom + 22
    height = bus_y0 + max(back_n, 1) * 18 + 16

    vid = view["id"]
    parts = [
        f'<svg class="diagram" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="{esc(view["title"])}">',
        f'<defs><marker id="ah-d-{vid}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{DATA}"/></marker>'
        f'<marker id="ah-c-{vid}" viewBox="0 0 10 10" refX="9" refY="5" '
        f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{CTRL}"/></marker></defs>',
    ]

    def port_y(node, slot, nslots):
        _x, y, _w, h, *_ = pos[node]
        if nslots <= 1:
            return y + h / 2
        return y + 14 + slot * min(16, (h - 28) / max(nslots - 1, 1))

    into = {}
    outof = {}
    for e in view["edges"]:
        into.setdefault(e[1], []).append(e)
        outof.setdefault(e[0], []).append(e)

    drawn = []
    back_i = 0
    for src, dst, net, kind in view["edges"]:
        color = DATA if kind == "data" else CTRL
        marker = f"ah-d-{vid}" if kind == "data" else f"ah-c-{vid}"
        si = outof[src].index((src, dst, net, kind))
        di = into[dst].index((src, dst, net, kind))
        if src == "L":
            x2, y2 = pos[dst][0], port_y(dst, di, len(into[dst]))
            x1, y1 = 12, y2
            pts = f"{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f}"
            lx, ly = (x1 + x2) / 2, y1 - 7
        elif dst == "R":
            x1 = pos[src][0] + pos[src][2]
            y1 = port_y(src, si, len(outof[src]))
            x2, y2 = width - 12, y1
            pts = f"{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f}"
            lx, ly = (x1 + x2) / 2, y1 - 7
        elif pos[src][0] < pos[dst][0]:
            x1 = pos[src][0] + pos[src][2]
            y1 = port_y(src, si, len(outof[src]))
            x2 = pos[dst][0]
            y2 = port_y(dst, di, len(into[dst]))
            if abs(y1 - y2) < 3:
                pts = f"{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f}"
                lx, ly = (x1 + x2) / 2, y1 - 7
            else:
                mid = (x1 + x2) / 2
                pts = f"{x1:.1f},{y1:.1f} {mid:.1f},{y1:.1f} {mid:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
                lx, ly = mid, min(y1, y2) - 7
        else:
            # return wire under the row, so it does not cross the boxes
            x1 = pos[src][0]
            y1 = pos[src][1] + pos[src][3]
            x2 = pos[dst][0] + pos[dst][2]
            y2 = pos[dst][1] + pos[dst][3]
            yb = bus_y0 + back_i * 18
            back_i += 1
            pts = (
                f"{x1:.1f},{y1:.1f} {x1:.1f},{yb:.1f} {x2:.1f},{yb:.1f} {x2:.1f},{y2:.1f}"
            )
            lx, ly = (x1 + x2) / 2, yb - 4
        drawn.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.7" '
            f'marker-end="url(#{marker})"/>'
        )
        drawn.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="12" fill="{color}">{esc(net)}</text>'
        )

    # boxes after wires so the frame covers the wire ends cleanly
    box_svg = []
    for bid, (x, y, w, h, name, mod, opens) in pos.items():
        stroke = DATA if opens else "#94a3b8"
        fill = "#eff6ff" if opens else "#ffffff"
        inner = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="10" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            f'<text x="{x + w/2:.1f}" y="{y + 28:.1f}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="13.5" font-weight="700" fill="#0f172a">{esc(name)}</text>'
            f'<text x="{x + w/2:.1f}" y="{y + 48:.1f}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="12" fill="#334155">{esc(mod)}</text>'
        )
        if opens:
            box_svg.append(f'<a href="#{esc(opens)}" class="open">{inner}</a>')
        else:
            box_svg.append(inner)
    parts.extend(drawn)
    parts.extend(box_svg)
    parts.append("</svg>")
    return "\n".join(parts)


def page():
    css = f"""
*{{box-sizing:border-box}}
body{{margin:0;font-family:{SANS};color:#0f172a;background:#f8fafc}}
header{{padding:14px 24px 0}}
h1{{font-size:19px;margin:0 0 4px}}
.note{{font-size:13px;color:#475569;margin:0 0 10px}}
nav{{display:flex;gap:6px;padding:0 24px 8px;border-bottom:1px solid #cbd5e1;flex-wrap:wrap}}
nav a{{padding:7px 14px;font-size:14px;text-decoration:none;color:#1e293b;border:1px solid #cbd5e1;
  border-bottom:none;border-radius:8px 8px 0 0;background:#e2e8f0}}
section.view{{display:none;padding:14px 24px 30px}}
section.view:target{{display:block}}
body:not(:has(section.view:target)) section.view:first-of-type{{display:block}}
h2{{font-size:16px;margin:4px 0 2px}}
.legend{{font-size:12.5px;color:#475569;margin:0 0 8px}}
.legend .d{{color:{DATA};font-weight:700}}.legend .c{{color:{CTRL};font-weight:700}}
.diagram{{display:block;background:#fff;border:1px solid #e2e8f0;border-radius:10px;max-width:100%;height:auto}}
a.open{{cursor:pointer}}
a.open:hover rect{{fill:#dbeafe}}
"""
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Hop adapter - layer diagram</title>",
        f"<style>{css}</style></head><body>",
        "<header><h1>Hop adapter - layer diagram</h1>",
        '<p class="note">One view per depth. A blue frame opens the next layer. '
        "A grey frame is a leaf. Score blocks do not open. "
        "Arrow text is the connection name.</p></header><nav>",
    ]
    for v in VIEWS:
        parts.append(f'<a href="#{esc(v["id"])}">{esc(v["tab"])}</a>')
    parts.append("</nav>")
    for v in VIEWS:
        parts.append(f'<section class="view" id="{esc(v["id"])}">')
        parts.append(f'<h2>{esc(v["title"])}</h2>')
        parts.append(
            '<p class="legend"><span class="d">Blue</span> = data, '
            '<span class="c">orange</span> = control. '
            "Blue frame opens the next depth.</p>"
        )
        parts.append(draw(v))
        parts.append("</section>")
    parts.append("</body></html>\n")
    return "\n".join(parts)


def main():
    text = page()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print(OUT, len(text))


if __name__ == "__main__":
    main()
