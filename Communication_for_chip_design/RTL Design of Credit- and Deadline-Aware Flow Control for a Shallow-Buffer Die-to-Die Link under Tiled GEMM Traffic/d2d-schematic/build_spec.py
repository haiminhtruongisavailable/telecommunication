#!/usr/bin/env python3
"""Write spec.json: the netlist of every view, read by hand from the architecture doc.
Source of truth = source/architecture-ascii.md (A:Lnn) + source/workflow-scores-and-wires.md (W:Lnn).
There is no Verilog for this design (arch/*.v not written, A:L12). Old flat RTL in source/rtl/ is only
used for the pin comparison in rtl_pins.py.
Every instance and net carries 'src' (doc line). Anything the doc does not state but the drawing needs
is marked inferred=True with a reason. Every undriven / unread net is marked nodriver / unused with a
finding id (see FINDINGS)."""
import json

PARAMS = {"N_WIRES": 1, "W_FLIT": 256, "TILE_W": 8, "SEQ_W": 16, "DL_W": 32, "IDX_W": 8, "CW": 8,
          "TIME_W": 32, "POLICY_W": 3, "WAVE_W": 8, "N_TILES": 8, "SLOTS": 256, "D_PHY": 4, "K": 16,
          "REC_W": 336}
PARAM_SRC = {"N_TILES": "not in A:L18-29; value from rtl/hop_top.v:6 (finding F24)",
             "SLOTS": "A:L25 IDX_W '256 slots'", "D_PHY": "rtl/hop_top.v:5, W:L67 'D_phy = 4'",
             "K": "A:L26 'K = 16 fits', rtl/hop_top.v:4", "REC_W": "sum of the record table A:L67-78"}

def P(name, d, w, src=""):  # port
    return {"name": name, "dir": d, "width": str(w), "src": src}

# ------------------------------------------------------------------ module port lists
MOD = {}
MOD["hop_top"] = [P("clk", "in", 1, "A:L35"), P("rst", "in", 1, "A:L35"), P("panel_valid", "in", 1, "A:L36"),
    P("panel_byte", "in", 8, "A:L37"), P("tile_id", "in", 8, "A:L38"), P("panel_sel", "in", 1, "A:L39"),
    P("other_valid", "in", 1, "A:L40"), P("other_flit", "in", 256, "A:L41"), P("other_deadline", "in", 32, "A:L42"),
    P("out_valid", "out", 1, "A:L43"), P("out_flit", "out", 256, "A:L44"), P("out_tile", "out", 8, "A:L45"),
    P("out_panel_sel", "out", 1, "A:L46"), P("done", "out", 1, "A:L47"), P("t_last_bus", "out", "N_TILES*32", "A:L48")]
CU2PU = [("release_en", 1, "A:L54"), ("W", 8, "A:L55"), ("policy_id", 3, "A:L56"), ("admit_limit", 8, "A:L57"),
         ("send_en", "N_WIRES", "A:L58")]
PU2CU = [("credit_count", 8, "A:L59"), ("ready_count", 9, "A:L60"), ("grant_idx", "N_WIRES*8", "A:L61"),
         ("grant_valid", "N_WIRES", "A:L62"), ("first_done", 1, "A:L63"), ("wave_done", 1, "A:L63")]
MOD["hop_control"] = [P("clk", "in", 1, "A:L108"), P("rst", "in", 1, "A:L109")] + \
    [P(n, "in", w, s) for n, w, s in PU2CU] + [P(n, "out", w, s) for n, w, s in CU2PU] + [P("done", "out", 1, "A:L124")]
MOD["hop_processing"] = [P("clk", "in", 1, "A:L108"), P("rst", "in", 1, "A:L109")] + \
    [P(n, "in", w, s) for n, w, s in CU2PU] + \
    [P("panel_valid", "in", 1, "A:L178"), P("panel_byte", "in", 8, "A:L178"), P("tile_id", "in", 8, "A:L178"),
     P("panel_sel", "in", 1, "A:L178"), P("other_valid", "in", 1, "A:L189"), P("other_flit", "in", 256, "A:L189"),
     P("other_deadline", "in", 32, "A:L189")] + \
    [P(n, "out", w, s) for n, w, s in PU2CU] + \
    [P("out_valid", "out", 1, "A:L43"), P("out_flit", "out", 256, "A:L44"), P("out_tile", "out", 8, "A:L448"),
     P("out_panel_sel", "out", 1, "A:L448"), P("t_last_bus", "out", "N_TILES*32", "A:L48")]
MOD["release_fsm"] = [P("clk", "in", 1), P("rst", "in", 1), P("release_en", "out", 1, "A:L148"), P("W", "out", 8, "A:L149")]
MOD["release"] = [P("clk", "in", 1), P("rst", "in", 1), P("release_en", "in", 1, "A:L454"), P("W", "in", 8, "A:L454"),
    P("admit_limit", "in", 8, "A:L454"), P("square_finished", "in", 1, "A:L454"), P("let_square", "out", 1, "A:L463")]
MOD["packer"] = [P("clk", "in", 1), P("rst", "in", 1), P("let_square", "in", 1, "A:L463"),
    P("panel_valid", "in", 1, "A:L259"), P("panel_byte", "in", 8, "A:L259"),
    P("tile_id", "in", 8, "A:L259"), P("panel_sel", "in", 1, "A:L259"),
    P("rec_valid", "out", 1, "A:L288 fire"), P("rec_seq", "out", 16, "A:L288 seq+1"), P("rec_tile", "out", 8, "A:L288"),
    P("rec_sel", "out", 1, "A:L288"), P("rec_payload", "out", 256, "A:L280")]
MOD["ready_mem"] = [P("clk", "in", 1), P("rst", "in", 1), P("rec_valid", "in", 1, "A:L299"), P("rec_seq", "in", 16, "A:L299"),
    P("rec_tile", "in", 8, "A:L299"), P("rec_sel", "in", 1, "A:L299"), P("rec_payload", "in", 256, "A:L299"),
    P("other_valid", "in", 1, "A:L304"), P("other_flit", "in", 256, "A:L299"), P("other_deadline", "in", 32, "A:L299"),
    P("grant_idx", "in", "N_WIRES*8", "A:L316"), P("consume", "in", "N_WIRES", "A:L323 (inferred pin, F17)"),
    P("record", "out", "REC_W", "A:L319-320 granted flit"), P("score_rec", "out", "REC_W", "A:L309 slot register"),
    P("ready_count", "out", 9, "A:L323")]
SCORE = [P("record", "in", "REC_W", "A:L235-236"), P("score", "out", 32, "A:L248")]
for s in ("fcfs", "edf", "firing", "shared", "row"):
    MOD["score_" + s] = SCORE
SCORES = ["score_fcfs", "score_edf", "score_firing", "score_shared", "score_row"]
MOD["scheduler"] = [P("policy_id", "in", 3, "A:L336")] + [P(n, "in", 32, "A:L330") for n in SCORES] + \
    [P("grant_valid", "out", "N_WIRES", "A:L348"), P("grant_idx", "out", "N_WIRES*8", "A:L348")]
MOD["credit"] = [P("clk", "in", 1), P("rst", "in", 1), P("send_en", "in", "N_WIRES", "A:L357"),
    P("grant_valid", "in", "N_WIRES", "A:L357"), P("credit_return", "in", 1, "A:L357"),
    P("pass_en", "out", "N_WIRES", "A:L393"), P("credit_count", "out", 8, "A:L383"), P("gt0", "out", 1, "A:L389")]
MOD["phy_box"] = [P("clk", "in", 1), P("rst", "in", 1), P("record", "in", "REC_W", "A:L401 'payload, tile' / A:L320"),
    P("pass_en", "in", "N_WIRES", "A:L400"), P("out_flit", "out", 256, "A:L422"), P("out_valid", "out", 1, "A:L423 '+ valid'")]
MOD["unpack"] = [P("clk", "in", 1), P("rst", "in", 1), P("flit", "in", 256, "A:L432"),
    P("in_valid", "in", 1, "A:L423"),
    P("out_tile", "out", 8, "A:L448"), P("out_panel_sel", "out", 1, "A:L448"), P("panel_byte", "out", 8, "A:L447")]

def ports_of(mod):
    return [dict(p) for p in MOD[mod]]

# ------------------------------------------------------------------ leaf cells
def dreg(inst, w, src, head_extra="", inferred=None):
    d = {"inst": inst, "module": "dreg", "kind": "dreg", "src": src, "head_extra": head_extra,
         "ports": [P("clk", "in", 1), P("rst", "in", 1), P("d", "in", w), P("q", "out", w)]}
    if inferred: d["inferred"] = inferred
    return d
def op(inst, center, ins, outs, src, inferred=None, module="assign"):
    d = {"inst": inst, "module": module, "kind": "comb", "center": center, "src": src,
         "ports": [P(n, "in", w) for n, w in ins] + [P(n, "out", w) for n, w in outs]}
    if inferred: d["inferred"] = inferred
    return d
def const(inst, label, w, src, inferred=None):
    d = {"inst": inst, "module": "const", "kind": "const", "center": label, "src": src, "ports": [P("out", "out", w)]}
    if inferred: d["inferred"] = inferred
    return d
def block(inst, mod, src, link=None):
    d = {"inst": inst, "module": mod, "kind": "block", "src": src, "ports": ports_of(mod)}
    if link: d["link"] = link
    return d

def N(pins, src="", **kw):
    d = {"pins": pins, "src": src}; d.update(kw); return d
def CLK(insts):  # clk + rst nets for the given instances (and the frame port)
    return {"clk": N(["PORT.clk"] + [f"{i}.clk" for i in insts], "A:L476 dreg stores on clk", stub=True),
            "rst": N(["PORT.rst"] + [f"{i}.rst" for i in insts], "A:L35", stub=True)}

VIEWS = []
def view(id, module, level, title, parent, insts, nets):
    VIEWS.append({"id": id, "module": module, "level": level, "title": title, "parent": parent,
                  "ports": ports_of(module), "instances": insts, "nets": nets})

# ------------------------------------------------------------------ L1 top = inside hop_top
nets = CLK(["u_cu", "u_pu"])
for n, w, s in CU2PU: nets[n] = N([f"u_cu.{n}", f"u_pu.{n}"], s)
for n, w, s in PU2CU: nets[n] = N([f"u_pu.{n}", f"u_cu.{n}"], s)
for n in ("panel_valid", "panel_byte", "tile_id", "panel_sel", "other_valid", "other_flit", "other_deadline"):
    nets[n] = N([f"PORT.{n}", f"u_pu.{n}"], "A:L99-L101")
for n in ("out_valid", "out_flit", "out_tile", "out_panel_sel", "t_last_bus"):
    nets[n] = N([f"u_pu.{n}", f"PORT.{n}"], "A:L43-48")
nets["done"] = N(["u_cu.done", "PORT.done"], "A:L124")
view("top", "hop_top", 1, "L1 - inside hop_top", None,
     [block("u_cu", "hop_control", "A:L106", "cu"), block("u_pu", "hop_processing", "A:L106", "pu")], nets)

# ------------------------------------------------------------------ L2 CU = inside u_cu
insts = [block("u_fsm", "release_fsm", "A:L143-149", "fsm"),
         const("c_policy", "POLICY", 3, "A:L143-150", "policy_reg has no input pin anywhere (F11)"),
         dreg("u_pol", 3, "A:L143 policy_reg"),
         const("c_admit", "ADMIT_LIMIT", 8, "A:L153-154", "admit_limit_reg has no input pin anywhere (F11)"),
         dreg("u_adm", 8, "A:L153 admit_limit_reg"),
         op("cmp_gt0", "> 0", [("in", 8)], [("out", 1)], "A:L158 compare > 0"),
         op("and_send", "&", [("a", 1), ("b", "N_WIRES")], [("y", "N_WIRES")], "A:L158-159"),
         op("cmp_nf", "< 256", [("in", 9)], [("out", 1)], "A:L60 ready_count",
            inferred="release only while ready_count is below 256 slots"),
         op("and_rel", "&", [("a", 1), ("b", 1)], [("y", 1)], "A:L148",
            inferred="release_en leaves CU only when the fsm asks and ready is not full"),
         op("done_cmb", "done = ?", [("first", 1), ("wave", 1)], [("y", 1)], "A:L161 (operator not given, F10)")]
nets = CLK(["u_fsm", "u_pol", "u_adm"])
nets.update({
    "rel_fsm": N(["u_fsm.release_en", "and_rel.a"], "A:L148"),
    "ready_count": N(["PORT.ready_count", "cmp_nf.in"], "A:L60"),
    "not_full": N(["cmp_nf.out", "and_rel.b"], "A:L60"),
    "release_en": N(["and_rel.y", "PORT.release_en"], "A:L148"),
    "W": N(["u_fsm.W", "PORT.W"], "A:L149"),
    "POLICY": N(["c_policy.out", "u_pol.d"], "F11"), "policy_id": N(["u_pol.q", "PORT.policy_id"], "A:L150"),
    "ADMIT_LIMIT": N(["c_admit.out", "u_adm.d"], "F11"), "admit_limit": N(["u_adm.q", "PORT.admit_limit"], "A:L154"),
    "credit_count": N(["PORT.credit_count", "cmp_gt0.in"], "A:L157"),
    "gt0": N(["cmp_gt0.out", "and_send.a"], "A:L158"),
    "grant_valid": N(["PORT.grant_valid", "and_send.b"], "A:L159"),
    "send_en": N(["and_send.y", "PORT.send_en"], "A:L158"),
    "first_done": N(["PORT.first_done", "done_cmb.first"], "A:L161"),
    "wave_done": N(["PORT.wave_done", "done_cmb.wave"], "A:L161"),
    "done": N(["done_cmb.y", "PORT.done"], "A:L161"),
    "grant_idx": N(["PORT.grant_idx"], "A:L119", unused={"reason": "CU does not scan slots; the index stays inside PU", "finding": "F9"}),
})
view("cu", "hop_control", 2, "L2 - inside u_cu (hop_control)", ["top", "u_cu"], insts, nets)

# ------------------------------------------------------------------ L3 inside u_cu/u_fsm
INF_T = "a time counter is implied by 'cmp time' (A:L467) and TIME_W 'cycle count' (A:L27)"
insts = [dreg("u_t", 32, "A:L27 TIME_W cycle count", inferred=INF_T),
         op("inc_t", "+ 1", [("a", 32)], [("y", 32)], "A:L27", inferred=INF_T),
         dreg("u_k_cnt", 32, "A:L467 k_cnt dreg", head_extra="rst T_0"),
         op("add_c", "+ C_TILE", [("a", 32)], [("y", 32)], "A:L467 + C_TILE"),
         op("mux_k", "mux", [("sel", 1), ("1", 32), ("0", 32)], [("y", 32)], "A:L467",
            inferred="hold k_cnt until a release; the doc draws no enable"),
         op("cmp_t", ">=", [("t", 32), ("k", 32)], [("y", 1)], "A:L467 cmp time --> release_en"),
         const("c_W", "W", 8, "A:L146 'one wave of W', A:L29 WAVE_W")]
nets = CLK(["u_t", "u_k_cnt"])
nets.update({
    "t": N(["u_t.q", "inc_t.a", "cmp_t.t"], "A:L467"), "t_next": N(["inc_t.y", "u_t.d"], "inferred"),
    "k_cnt": N(["u_k_cnt.q", "add_c.a", "mux_k.0", "cmp_t.k"], "A:L467"),
    "k_plus": N(["add_c.y", "mux_k.1"], "A:L467"), "k_d": N(["mux_k.y", "u_k_cnt.d"], "inferred"),
    "release_en": N(["cmp_t.y", "PORT.release_en", "mux_k.sel"], "A:L467"),
    "W": N(["c_W.out", "PORT.W"], "A:L149"),
})
view("fsm", "release_fsm", 3, "L3 - inside u_cu/u_fsm (release_fsm)", ["cu", "u_fsm"], insts, nets)

# ------------------------------------------------------------------ L2 PU = inside u_pu
insts = [block("u_release", "release", "A:L181-187", "release"), block("u_packer", "packer", "A:L181-186", "packer"),
         block("u_ready", "ready_mem", "A:L189-191", "ready")] + \
        [block("u_" + s.split("_")[1], s, "A:L195-198 (closed, A:L232)") for s in SCORES] + \
        [block("u_sched", "scheduler", "A:L202-206", "sched"), block("u_credit", "credit", "A:L209-212", "credit"),
         block("u_phy", "phy_box", "A:L215-218", "phy"), block("u_unpack", "unpack", "A:L221-224", "unpack")]
nets = CLK(["u_release", "u_packer", "u_ready", "u_credit", "u_phy", "u_unpack"])
nets.update({
    "release_en": N(["PORT.release_en", "u_release.release_en"], "A:L172"),
    "W": N(["PORT.W", "u_release.W"], "A:L172"), "admit_limit": N(["PORT.admit_limit", "u_release.admit_limit"], "A:L183"),
    "square_finished": N(["u_release.square_finished"], "A:L454", nodriver={"reason": "no block produces it", "finding": "F3"}),
    "let_square": N(["u_release.let_square", "u_packer.let_square"], "A:L463"),
    "panel_valid": N(["PORT.panel_valid", "u_packer.panel_valid"], "A:L259"),
    "panel_byte": N(["PORT.panel_byte", "u_packer.panel_byte"], "A:L259"),
    "tile_id": N(["PORT.tile_id", "u_packer.tile_id"], "A:L259"),
    "panel_sel": N(["PORT.panel_sel", "u_packer.panel_sel"], "A:L259"),
    "other_valid": N(["PORT.other_valid", "u_ready.other_valid"], "A:L304"),
    "other_flit": N(["PORT.other_flit", "u_ready.other_flit"], "A:L189, A:L299"),
    "other_deadline": N(["PORT.other_deadline", "u_ready.other_deadline"], "A:L299"),
    "policy_id": N(["PORT.policy_id", "u_sched.policy_id"], "A:L336"),
    "send_en": N(["PORT.send_en", "u_credit.send_en"], "A:L357"),
    "grant_idx": N(["u_sched.grant_idx", "PORT.grant_idx", "u_ready.grant_idx"], "A:L316, A:L348"),
    "grant_valid": N(["u_sched.grant_valid", "PORT.grant_valid", "u_credit.grant_valid"], "A:L348, A:L357"),
    # one gather beat frees one RX slot; the same 1-bit out_valid is the return (F14 still: not N returns)
    "pass_en": N(["u_credit.pass_en", "u_phy.pass_en", "u_ready.consume"], "A:L393, A:L400, A:L323 (consume inferred, F17)"),
    "credit_count": N(["u_credit.credit_count", "PORT.credit_count"], "A:L211"),
    "gt0": N(["u_credit.gt0"], "A:L389", unused={"reason": "'gates send_en inside CU' but no PU->CU wire carries it", "finding": "F12"}),
    "score_rec": N(["u_ready.score_rec"] + [f"u_{s.split('_')[1]}.record" for s in SCORES], "A:L309 slot q, not the grant mux"),
    "record": N(["u_ready.record", "u_phy.record"], "A:L319-320 granted flit into the PHY"),
    "ready_count": N(["u_ready.ready_count", "PORT.ready_count"], "A:L323"),
    "out_flit": N(["u_phy.out_flit", "PORT.out_flit", "u_unpack.flit"], "A:L422, A:L432"),
    "out_valid": N(["u_phy.out_valid", "PORT.out_valid", "u_credit.credit_return", "u_unpack.in_valid"], "A:L423"),
    "out_tile": N(["u_unpack.out_tile", "PORT.out_tile"], "A:L448"),
    "out_panel_sel": N(["u_unpack.out_panel_sel", "PORT.out_panel_sel"], "A:L448"),
    "unpack_byte": N(["u_unpack.panel_byte"], "A:L447", unused={"reason": "hop_top has no byte output (A:L33-48)", "finding": "F21"}),
    "first_done": N(["PORT.first_done"], "A:L121", nodriver={"reason": "no PU block produces it", "finding": "F5"}),
    "wave_done": N(["PORT.wave_done"], "A:L122", nodriver={"reason": "no PU block produces it", "finding": "F5"}),
    "t_last_bus": N(["PORT.t_last_bus"], "A:L48", nodriver={"reason": "no PU block produces it", "finding": "F5"}),
})
for s in SCORES:
    nets[s] = N([f"u_{s.split('_')[1]}.score", f"u_sched.{s}"], "A:L330")
for n in ("rec_valid", "rec_seq", "rec_tile", "rec_sel", "rec_payload"):
    nets[n] = N([f"u_packer.{n}", f"u_ready.{n}"], "A:L182 records, A:L299")
view("pu", "hop_processing", 2, "L2 - inside u_pu (hop_processing)", ["top", "u_pu"], insts, nets)

# ------------------------------------------------------------------ L3 release
insts = [dreg("u_admitted", 8, "A:L460 admitted[7:0] -- dreg"),
         op("min_cap", "min", [("a", 8), ("b", 8)], [("y", 8)], "A:L468 lets W squares through",
            inferred="the comparator limit is min(W, admit_limit)"),
         op("cmp_lt", "<", [("a", 8), ("b", 8)], [("y", 1)], "A:L463 cmp < admit_limit"),
         op("and_adm", "&", [("a", 1), ("b", 1)], [("y", 1)], "A:L463", inferred="a square is admitted when let and release_en"),
         op("addsub_adm", "+ \u2212", [("a", 8), ("inc", 1), ("dec", 1)], [("y", 8)], "A:L465 admitted - 1",
            inferred="the +1 on admission is implied, not drawn")]
nets = CLK(["u_admitted"])
nets.update({
    "admitted": N(["u_admitted.q", "cmp_lt.a", "addsub_adm.a"], "A:L460"),
    "admit_limit": N(["PORT.admit_limit", "min_cap.b"], "A:L463"),
    "W": N(["PORT.W", "min_cap.a"], "A:L468"),
    "cap": N(["min_cap.y", "cmp_lt.b"], "A:L468"),
    "let_square": N(["cmp_lt.y", "PORT.let_square", "and_adm.a"], "A:L463"),
    "release_en": N(["PORT.release_en", "and_adm.b"], "A:L454"),
    "admit_now": N(["and_adm.y", "addsub_adm.inc"], "inferred"),
    "square_finished": N(["PORT.square_finished", "addsub_adm.dec"], "A:L465"),
    "admitted_d": N(["addsub_adm.y", "u_admitted.d"], "A:L465"),
})
view("release", "release", 3, "L3 - inside u_pu/u_release (release, 5g)", ["pu", "u_release"], insts, nets)

# ------------------------------------------------------------------ L3 packer
INF_SEQ = "seq register implied by 'seq+1' (A:L288); not drawn in 5a"
insts = [op("shl", "{lo,byte}", [("word", 256), ("byte", 8)], [("y", 256)], "A:L265-268"),
         op("and_let", "&", [("a", 1), ("b", 1)], [("y", 1)], "A:L463",
            inferred="a byte is shifted only when this square was admitted"),
         const("c_zero", "256'd0", 256, "A:L273 fire -> 0"),
         op("word_mux", "word_mux", [("fire", 1), ("valid", 1), ("zero", 256), ("shifted", 256), ("hold", 256)],
            [("y", 256)], "A:L272-275"),
         dreg("u_word", 256, "A:L280 dreg 256"),
         dreg("u_cnt", 6, "A:L283 byte_cnt[5:0]"),
         op("inc_cnt", "+ 1", [("a", 6)], [("y", 6)], "A:L283 +1"),
         op("eq32", "== 32", [("a", 6)], [("y", 1)], "A:L283 cmp == 32 -> fire"),
         const("c_zero6", "6'd0", 6, "A:L286"),
         op("cnt_mux", "mux", [("sel", 1), ("1", 6), ("0", 6)], [("y", 6)], "A:L286 cnt_mux (fire ? 0 : cnt+1)"),
         dreg("u_seq", 16, "A:L288", inferred=INF_SEQ),
         op("inc_seq", "+ 1", [("a", 16)], [("y", 16)], "A:L288 seq+1"),
         op("seq_mux", "mux", [("sel", 1), ("1", 16), ("0", 16)], [("y", 16)], "A:L288", inferred=INF_SEQ)]
nets = CLK(["u_word", "u_cnt", "u_seq"])
nets.update({
    "panel_byte": N(["PORT.panel_byte", "shl.byte"], "A:L267"),
    "let_square": N(["PORT.let_square", "and_let.a"], "A:L463"),
    "panel_valid": N(["PORT.panel_valid", "and_let.b"], "A:L272"),
    "pack_en": N(["and_let.y", "word_mux.valid"], "A:L272"),
    "shifted": N(["shl.y", "word_mux.shifted"], "A:L270"),
    "zero": N(["c_zero.out", "word_mux.zero"], "A:L273"),
    "word_d": N(["word_mux.y", "u_word.d"], "A:L278"),
    "rec_payload": N(["u_word.q", "PORT.rec_payload", "shl.word", "word_mux.hold"], "A:L265 hold, A:L280 payload"),
    "byte_cnt": N(["u_cnt.q", "inc_cnt.a"], "A:L283"),
    "cnt_inc": N(["inc_cnt.y", "eq32.a", "cnt_mux.0"], "A:L283-286"),
    "fire": N(["eq32.y", "word_mux.fire", "cnt_mux.sel", "seq_mux.sel", "PORT.rec_valid"], "A:L283, A:L288"),
    "cnt_zero": N(["c_zero6.out", "cnt_mux.1"], "A:L286"),
    "cnt_d": N(["cnt_mux.y", "u_cnt.d"], "A:L286 -> dreg 6"),
    "seq": N(["u_seq.q", "inc_seq.a", "seq_mux.0"], "A:L288"),
    "seq_inc": N(["inc_seq.y", "seq_mux.1", "PORT.rec_seq"], "A:L288 seq+1"),
    "seq_d": N(["seq_mux.y", "u_seq.d"], "inferred"),
    "tile_id": N(["PORT.tile_id", "PORT.rec_tile"], "A:L288"),
    "panel_sel": N(["PORT.panel_sel", "PORT.rec_sel"], "A:L288"),
})
view("packer", "packer", 3, "L3 - inside u_pu/u_packer (packer, 5a)", ["pu", "u_packer"], insts, nets)

# ------------------------------------------------------------------ L3 ready
insts = [op("shl4", "<< 4", [("a", 8)], [("y", 32)], "A:L71 D_k",
            inferred="C_tile is 16, so tile_id << 4 is tile_id * C_tile"),
         const("c_extra", "40", 32, "A:L71", inferred="baseline extra is 40, the same slack as the golden"),
         op("add_dk", "+", [("a", 32), ("b", 32)], [("y", 32)], "A:L71 D_k = T_k + extra",
            inferred="with T_0 = 0 the drawn deadline is tile_id * 16 + 40"),
         const("c_tail", "16,1,0,1", 22, "A:L74-77",
               inferred="flits_left 16, consumers 1, wave_id 0, is_gemm 1"),
         op("cat_rest", "{ }", [("dl", 32), ("tail", 22)], [("y", 54)], "A:L71-77"),
         const("c_ot", "flit=1", 47, "A:L74-77",
               inferred="other stack is one flit, not a GEMM square: seq tile sel 0, flits_left 1, is_gemm 0"),
         op("cat_pk", "{ }", [("valid", 1), ("seq", 16), ("tile", 8), ("sel", 1), ("payload", 256), ("rest", 54)],
            [("y", "REC_W")], "A:L299 packer record -> record fields A:L67-78"),
         op("cat_ot", "{ }", [("valid", 1), ("payload", 256), ("deadline", 32), ("rest", 47)], [("y", "REC_W")],
            "A:L299 other_flit + other_deadline"),
         op("src_mux", "src_mux", [("sel", 1), ("1", "REC_W"), ("0", "REC_W")], [("y", "REC_W")], "A:L304 sel = other_valid"),
         dreg("u_slot", "REC_W", "A:L309 slot dreg (one of 256 drawn, A:L296)", head_extra="\u00d7 256"),
         op("sel8", "[7:0]", [("a", "N_WIRES*8")], [("y", 8)], "A:L316 grant_idx[7:0]"),
         op("read_mux", "read_mux", [("sel", 8), ("slot", "REC_W")], [("y", "REC_W")], "A:L316"),
         op("wr_or", "|", [("a", 1), ("b", 1)], [("y", 1)], "A:L323 'a write'", inferred="a write = either source valid"),
         op("cnt_as", "+ \u2212", [("a", 9), ("inc", 1), ("dec", "N_WIRES")], [("y", 9)], "A:L323 plus one / minus one"),
         dreg("u_cnt", 9, "A:L323 separate dreg of 9 bits")]
nets = CLK(["u_slot", "u_cnt"])
nets.update({
    "rec_valid": N(["PORT.rec_valid", "cat_pk.valid", "wr_or.a"], "A:L299"),
    "rec_seq": N(["PORT.rec_seq", "cat_pk.seq"], "A:L299"),
    "rec_tile": N(["PORT.rec_tile", "cat_pk.tile", "shl4.a"], "A:L299"),
    "tile16": N(["shl4.y", "add_dk.a"], "A:L71"),
    "extra": N(["c_extra.out", "add_dk.b"], "A:L71 extra = 40"),
    "deadline": N(["add_dk.y", "cat_rest.dl"], "A:L71"),
    "pk_tail": N(["c_tail.out", "cat_rest.tail"], "A:L74-77"),
    "rec_sel": N(["PORT.rec_sel", "cat_pk.sel"], "A:L299"), "rec_payload": N(["PORT.rec_payload", "cat_pk.payload"], "A:L299"),
    "pk_rest": N(["cat_rest.y", "cat_pk.rest"], "A:L71-77"),
    "other_valid": N(["PORT.other_valid", "src_mux.sel", "wr_or.b", "cat_ot.valid"], "A:L304"),
    "other_flit": N(["PORT.other_flit", "cat_ot.payload"], "A:L299"),
    "other_deadline": N(["PORT.other_deadline", "cat_ot.deadline"], "A:L299"),
    "ot_rest": N(["c_ot.out", "cat_ot.rest"], "A:L74-77"),
    "rec_a": N(["cat_pk.y", "src_mux.0"], "A:L299"), "rec_b": N(["cat_ot.y", "src_mux.1"], "A:L299"),
    "wr_rec": N(["src_mux.y", "u_slot.d"], "A:L307"),
    "slot": N(["u_slot.q", "read_mux.slot", "PORT.score_rec"], "A:L309, A:L314"),
    "grant_idx": N(["PORT.grant_idx", "sel8.a"], "A:L316"), "gidx0": N(["sel8.y", "read_mux.sel"], "A:L316"),
    "record": N(["read_mux.y", "PORT.record"], "A:L319-320"),
    "wr": N(["wr_or.y", "cnt_as.inc"], "inferred"), "consume": N(["PORT.consume", "cnt_as.dec"], "A:L323"),
    "cnt_d": N(["cnt_as.y", "u_cnt.d"], "A:L323"), "ready_count": N(["u_cnt.q", "PORT.ready_count", "cnt_as.a"], "A:L323"),
})
view("ready", "ready_mem", 3, "L3 - inside u_pu/u_ready (ready, 5b)", ["pu", "u_ready"], insts, nets)

# ------------------------------------------------------------------ L3 scheduler
insts = [op("policy_mux", "policy_mux", [("sel", 3)] + [(f"in{i}", 32) for i in range(5)], [("y", 32)], "A:L336"),
         op("cmp_min", "cmp_min", [("score", 32)], [("grant_valid", "N_WIRES"), ("grant_idx", "N_WIRES*8")],
            "A:L341-349", module="cmp_min")]
nets = {"policy_id": N(["PORT.policy_id", "policy_mux.sel"], "A:L336"),
        "score_sel": N(["policy_mux.y", "cmp_min.score"], "A:L338"),
        "grant_valid": N(["cmp_min.grant_valid", "PORT.grant_valid"], "A:L348"),
        "grant_idx": N(["cmp_min.grant_idx", "PORT.grant_idx"], "A:L348")}
for i, s in enumerate(SCORES): nets[s] = N([f"PORT.{s}", f"policy_mux.in{i}"], "A:L330")
view("sched", "scheduler", 3, "L3 - inside u_pu/u_sched (scheduler, 5c)", ["pu", "u_sched"], insts, nets)

# ------------------------------------------------------------------ L3 credit
insts = [op("and_pass", "&", [("send_en", "N_WIRES"), ("grant_valid", "N_WIRES"), ("gt0", 1)], [("y", "N_WIRES")], "A:L393"),
         op("accept_ones", "count 1s", [("a", "N_WIRES")], [("y", 8)], "A:L362 accept_ones"),
         op("ret_count", "count", [("a", 1)], [("y", 8)], "A:L362 ret_count"),
         op("addsub", "\u2212 a + r", [("count", 8), ("accept", 8), ("returns", 8)], [("y", 8)], "A:L369-374 addsub"),
         op("hold_eq", "== 0", [("a", 8), ("r", 8)], [("y", 1)], "A:L378-379", inferred="select for 'hold if accept and returns are 0'"),
         op("cnt_mux", "mux", [("sel", 1), ("1", 8), ("0", 8)], [("y", 8)], "A:L377 cnt_mux"),
         dreg("u_count", 8, "A:L383 dreg 8", head_extra="rst K"),
         op("cmp_gt0", "> 0", [("a", 8)], [("y", 1)], "A:L389 cmp > 0")]
nets = CLK(["u_count"])
nets.update({
    "send_en": N(["PORT.send_en", "and_pass.send_en"], "A:L357"),
    "grant_valid": N(["PORT.grant_valid", "and_pass.grant_valid"], "A:L357"),
    "gt0": N(["cmp_gt0.y", "and_pass.gt0", "PORT.gt0"], "A:L389, A:L393"),
    "pass_en": N(["and_pass.y", "PORT.pass_en", "accept_ones.a"], "A:L393"),
    "accept": N(["accept_ones.y", "addsub.accept", "hold_eq.a"], "A:L362"),
    "credit_return": N(["PORT.credit_return", "ret_count.a"], "A:L357"),
    "returns": N(["ret_count.y", "addsub.returns", "hold_eq.r"], "A:L362"),
    "next": N(["addsub.y", "cnt_mux.0"], "A:L374"),
    "hold": N(["hold_eq.y", "cnt_mux.sel"], "A:L378"),
    "cnt_d": N(["cnt_mux.y", "u_count.d"], "A:L380"),
    "credit_count": N(["u_count.q", "PORT.credit_count", "addsub.count", "cnt_mux.1", "cmp_gt0.a"], "A:L383"),
})
view("credit", "credit", 3, "L3 - inside u_pu/u_credit (credit, 5d)", ["pu", "u_credit"], insts, nets)

# ------------------------------------------------------------------ L3 phy + gather
insts = [const("c_bub", "0", "REC_W", "A:L405", inferred="stage 0 loads a bubble, not its own q"),
         const("c_rr", "0", 1, "A:L423", inferred="N_WIRES is 1, so the gather has one lane"),
         op("load_mux", "load_mux", [("sel", 1), ("1", "REC_W"), ("0", "REC_W")], [("y", "REC_W")], "A:L403-405 sel = pass_en")] + \
        [dreg(f"u_s{i}", "REC_W", f"A:L409 dreg stage{i} (D_phy = 4, W:L67)") for i in range(4)] + \
        [op("lane_mux", "lane_mux", [("sel", 1), ("lane0", "REC_W")], [("y", "REC_W")], "A:L422 sel = rr"),
         op("f_pay", ".payload", [("rec", "REC_W")], [("y", 256)], "A:L422-424 dreg 256",
            inferred="field select of the 256-bit payload out of the record"),
         op("f_val", ".valid", [("rec", "REC_W")], [("y", 1)], "A:L424 + valid", inferred="field select of the valid bit"),
         dreg("u_gflit", 256, "A:L422 dreg 256"), dreg("u_gvalid", 1, "A:L424 + valid")]
nets = CLK(["u_s0", "u_s1", "u_s2", "u_s3", "u_gflit", "u_gvalid"])
nets.update({
    "pass_en": N(["PORT.pass_en", "load_mux.sel"], "A:L400, A:L404"),
    "record": N(["PORT.record", "load_mux.1"], "A:L401"),
    "prev": N(["c_bub.out", "load_mux.0"], "A:L405 bubble into stage 0"),
    "s0_d": N(["load_mux.y", "u_s0.d"], "A:L407"),
    "s0": N(["u_s0.q", "u_s1.d"], "A:L409"), "s1": N(["u_s1.q", "u_s2.d"], "A:L409"),
    "s2": N(["u_s2.q", "u_s3.d"], "A:L409"), "arrived": N(["u_s3.q", "lane_mux.lane0"], "A:L414"),
    "rr": N(["c_rr.out", "lane_mux.sel"], "A:L423 const 0 while one lane"),
    "lane_rec": N(["lane_mux.y", "f_pay.rec", "f_val.rec"], "A:L422"),
    "pay": N(["f_pay.y", "u_gflit.d"], "A:L422"), "val": N(["f_val.y", "u_gvalid.d"], "A:L424"),
    "out_flit": N(["u_gflit.q", "PORT.out_flit"], "A:L422"), "out_valid": N(["u_gvalid.q", "PORT.out_valid"], "A:L424"),
})
view("phy", "phy_box", 3, "L3 - inside u_pu/u_phy (phy_box + gather, 5e)", ["pu", "u_phy"], insts, nets)

# ------------------------------------------------------------------ L3 unpack
insts = [op("shr", ">> 8", [("a", 256)], [("y", 256)], "A:L436 shift >> 8",
            inferred="shift input taken from the dreg (doc arrow from out_flit would shift only once, F21)"),
         op("byte_mux", "byte_mux", [("sel", 1), ("1", 256), ("0", 256)], [("y", 256)], "A:L440 sel = take_byte"),
         dreg("u_word", 256, "A:L444 dreg 256"),
         op("lo8", "[7:0]", [("a", 256)], [("y", 8)], "A:L436 low byte is the next panel_byte")]
nets = CLK(["u_word"])
nets.update({
    "flit": N(["PORT.flit", "byte_mux.0"], "A:L432"),
    "take_byte": N(["PORT.in_valid", "byte_mux.sel"], "A:L440 shift when a flit arrives"),
    "shifted": N(["shr.y", "byte_mux.1"], "A:L438"), "word_d": N(["byte_mux.y", "u_word.d"], "A:L442"),
    "word": N(["u_word.q", "shr.a", "lo8.a"], "A:L446"),
    "panel_byte": N(["lo8.y", "PORT.panel_byte"], "A:L447"),
    "out_tile": N(["PORT.out_tile"], "A:L448", nodriver={"reason": "tile_id is dropped at the gather (A:L422-424)", "finding": "F21"}),
    "out_panel_sel": N(["PORT.out_panel_sel"], "A:L448", nodriver={"reason": "panel_sel is dropped at the gather", "finding": "F21"}),
})
view("unpack", "unpack", 3, "L3 - inside u_pu/u_unpack (unpack, 5f)", ["pu", "u_unpack"], insts, nets)

# ------------------------------------------------------------------ comb behaviour of leaf blocks with no inside view
LEAF_COMB = {"score_fcfs": [["record", "score"]], "score_edf": [["record", "score"]], "score_firing": [["record", "score"]],
             "score_shared": [["record", "score"]], "score_row": [["record", "score"]]}

# ------------------------------------------------------------------ known design issues that check.py must find (acknowledged)
KNOWN = [
    {"kind": "widen_width", "view": "phy", "key": "pass_en@N_WIRES=2", "finding": "F18"},
]

spec = {"title": "D2D hop adapter (hop_top) - schematic spec from the architecture doc",
        "source": {"kind": "doc-only", "why": "arch/*.v is not written (A:L12); no CU/PU Verilog on any branch",
                   "doc": "source/architecture-ascii.md", "doc2": "source/workflow-scores-and-wires.md",
                   "commit": open("source/SOURCE_COMMIT").read().strip()},
        "params": PARAMS, "param_src": PARAM_SRC, "leaf_comb": LEAF_COMB, "known": KNOWN,
        "views": VIEWS}
json.dump(spec, open("spec.json", "w"), indent=1)
print("spec.json:", len(VIEWS), "views,", sum(len(v["instances"]) for v in VIEWS), "instances,",
      sum(len(v["nets"]) for v in VIEWS), "nets")
