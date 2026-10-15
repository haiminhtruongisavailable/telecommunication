#!/usr/bin/env python3
"""Hand-placed schematics of the D2D hop adapter (hop_top). Every coordinate below is chosen by hand;
nothing is routed automatically. Widths / module heads come from spec.json (bind()).
Clock/reset stubs, 'unused' and 'no driver' stubs are placed at their pin from the spec net kind.
Writes layout_<view>.json + <view>.svg for every view, render_<view>.html, and index.html."""
import json
from schem import box, blk, dreg, const, op, mux, bind, emit

SPEC = json.load(open("spec.json"))
SV = {v["id"]: v for v in SPEC["views"]}

def ports(**kw):   # name=(side, y)
    return {n: dict(side=s, y=y, dir="in" if s == "L" else "out") for n, (s, y) in kw.items()}

# ================================================================== L1: inside hop_top
TOP = dict(name="top", W=1600, H=660, frame=dict(x0=250, y0=20, x1=1350, y1=640, title="hop_top"),
    ports=ports(clk=("L", 356), rst=("L", 380), panel_valid=("L", 420), panel_byte=("L", 444), tile_id=("L", 468),
                panel_sel=("L", 492), other_valid=("L", 532), other_flit=("L", 556), other_deadline=("L", 580),
                done=("R", 356), out_valid=("R", 460), out_flit=("R", 484), out_tile=("R", 508), out_panel_sel=("R", 532),
                t_last_bus=("R", 556)),
    inst={
        "u_pu": blk("hop_processing", "u_pu", 450, 180, 330, 430,
                    left=[("release_en", 220), ("W", 244), ("policy_id", 268), ("admit_limit", 292), ("send_en", 316),
                          ("clk", 356), ("rst", 380), ("panel_valid", 420), ("panel_byte", 444), ("tile_id", 468),
                          ("panel_sel", 492), ("other_valid", 532), ("other_flit", 556), ("other_deadline", 580)],
                    right=[("credit_count", 220), ("ready_count", 244), ("grant_idx", 268), ("grant_valid", 292),
                           ("first_done", 316), ("wave_done", 340), ("out_valid", 460), ("out_flit", 484),
                           ("out_tile", 508), ("out_panel_sel", 532), ("t_last_bus", 556)], link="pu"),
        "u_cu": blk("hop_control", "u_cu", 900, 180, 300, 230,
                    left=[("credit_count", 220), ("ready_count", 244), ("grant_idx", 268), ("grant_valid", 292),
                          ("first_done", 316), ("wave_done", 340), ("clk", 364), ("rst", 388)],
                    right=[("release_en", 220), ("W", 244), ("policy_id", 268), ("admit_limit", 292), ("send_en", 316),
                           ("done", 356)], link="cu"),
    },
    nets={
        "release_en": dict(lines=[[(1200, 220), (1220, 220), (1220, 150), (430, 150), (430, 220), (450, 220)]], labels=[(800, 145)]),
        "W": dict(lines=[[(1200, 244), (1240, 244), (1240, 130), (410, 130), (410, 244), (450, 244)]], labels=[(800, 125)]),
        "policy_id": dict(lines=[[(1200, 268), (1260, 268), (1260, 110), (390, 110), (390, 268), (450, 268)]], labels=[(800, 105)]),
        "admit_limit": dict(lines=[[(1200, 292), (1280, 292), (1280, 90), (370, 90), (370, 292), (450, 292)]], labels=[(800, 85)]),
        "send_en": dict(lines=[[(1200, 316), (1300, 316), (1300, 70), (350, 70), (350, 316), (450, 316)]], labels=[(800, 65)]),
        **{n: dict(lines=[[(780, y), (900, y)]]) for n, y in (("credit_count", 220), ("ready_count", 244), ("grant_idx", 268),
                                                             ("grant_valid", 292), ("first_done", 316), ("wave_done", 340))},
        **{n: dict(lines=[[(250, y), (450, y)]]) for n, y in (("panel_valid", 420), ("panel_byte", 444), ("tile_id", 468),
                                                             ("panel_sel", 492), ("other_valid", 532), ("other_flit", 556),
                                                             ("other_deadline", 580))},
        **{n: dict(lines=[[(780, y), (1350, y)]]) for n, y in (("out_valid", 460), ("out_flit", 484), ("out_tile", 508),
                                                              ("out_panel_sel", 532), ("t_last_bus", 556))},
        "done": dict(lines=[[(1200, 356), (1350, 356)]]),
    })

# ================================================================== L2: inside u_cu
CU = dict(name="cu", W=1600, H=730, frame=dict(x0=250, y0=20, x1=1350, y1=710, title="hop_control"),
    ports=ports(clk=("L", 80), rst=("L", 104), ready_count=("L", 440), grant_idx=("L", 470), credit_count=("L", 520),
                grant_valid=("L", 560), first_done=("L", 640), wave_done=("L", 670),
                release_en=("R", 132), W=("R", 156), policy_id=("R", 282), admit_limit=("R", 422), send_en=("R", 540), done=("R", 655)),
    inst={
        "u_fsm": blk("release_fsm", "u_fsm", 820, 80, 230, 110, left=[("clk", 132), ("rst", 156)],
                     right=[("release_en", 132), ("W", 156)], link="fsm"),
        "c_policy": const("c_policy", 560, 302),
        "u_pol": dreg("u_pol", 820, 210),
        "c_admit": const("c_admit", 530, 442, w=120),
        "u_adm": dreg("u_adm", 820, 350),
        "cmp_gt0": op("cmp_gt0", 560, 505, 90, 30, [("in", 520)], [("out", 520)]),
        "and_send": op("and_send", 820, 505, 80, 70, [("a", 520), ("b", 560)], [("y", 540)]),
        "cmp_nf": op("cmp_nf", 360, 422, 120, 36, [("in", 440)], [("out", 440)]),
        "and_rel": op("and_rel", 1100, 100, 100, 48, [("a", 116), ("b", 136)], [("y", 132)]),
        "done_cmb": op("done_cmb", 820, 620, 130, 70, [("first", 640), ("wave", 670)], [("y", 655)]),
    },
    nets={
        "rel_fsm": dict(lines=[[(1050, 132), (1075, 132), (1075, 116), (1100, 116)]]),
        "ready_count": dict(lines=[[(250, 440), (360, 440)]]),
        "not_full": dict(lines=[[(480, 440), (480, 196), (1070, 196), (1070, 136), (1100, 136)]]),
        "release_en": dict(lines=[[(1200, 132), (1350, 132)]]), "W": dict(lines=[[(1050, 156), (1350, 156)]]),
        "POLICY": dict(lines=[[(646, 302), (820, 302)]]), "policy_id": dict(lines=[[(970, 282), (1350, 282)]]),
        "ADMIT_LIMIT": dict(lines=[[(650, 442), (820, 442)]]), "admit_limit": dict(lines=[[(970, 422), (1350, 422)]]),
        "credit_count": dict(lines=[[(250, 520), (560, 520)]]),
        "gt0": dict(lines=[[(650, 520), (820, 520)]], labels=[(700, 514)]),
        "grant_valid": dict(lines=[[(250, 560), (820, 560)]]),
        "send_en": dict(lines=[[(900, 540), (1350, 540)]]),
        "first_done": dict(lines=[[(250, 640), (820, 640)]]), "wave_done": dict(lines=[[(250, 670), (820, 670)]]),
        "done": dict(lines=[[(950, 655), (1350, 655)]]),
    })

# ================================================================== L3: inside u_cu/u_fsm
FSM = dict(name="fsm", W=1600, H=600, frame=dict(x0=250, y0=20, x1=1350, y1=580, title="release_fsm"),
    ports=ports(clk=("L", 300), rst=("L", 324), release_en=("R", 167), W=("R", 520)),
    inst={
        "u_t": dreg("u_t", 700, 80),
        "inc_t": op("inc_t", 450, 157, 90, 30, [("a", 172)], [("y", 172)]),
        "cmp_t": op("cmp_t", 980, 137, 90, 60, [("t", 152), ("k", 182)], [("y", 167)]),
        "u_k_cnt": dreg("u_k_cnt", 700, 300, w=180),
        "mux_k": mux("mux_k", 560, 352),
        "add_c": op("add_c", 400, 377, 110, 30, [("a", 392)], [("y", 392)]),
        "c_W": const("c_W", 980, 520),
    },
    nets={
        "t": dict(lines=[[(850, 152), (980, 152)], [(880, 152), (880, 60), (420, 60), (420, 172), (450, 172)]], labels=[(600, 55)]),
        "t_next": dict(lines=[[(540, 172), (700, 172)]], labels=[(600, 166)]),
        "k_cnt": dict(lines=[[(880, 372), (950, 372), (950, 182), (980, 182)],
                             [(910, 372), (910, 450), (380, 450), (380, 392), (400, 392)], [(540, 450), (540, 412), (560, 412)]],
                      labels=[(700, 445)]),
        "k_plus": dict(lines=[[(510, 392), (560, 392)]]),
        "k_d": dict(lines=[[(632, 392), (700, 392)]]),
        "release_en": dict(lines=[[(1070, 167), (1350, 167)], [(1100, 167), (1100, 250), (530, 250), (530, 372), (560, 372)]],
                           labels=[(700, 245)]),
        "W": dict(lines=[[(1066, 520), (1350, 520)]]),
    })

# ================================================================== L2: inside u_pu
PU = dict(name="pu", W=2200, H=1140, frame=dict(x0=260, y0=20, x1=1960, y1=1120, title="hop_processing"),
    ports=ports(policy_id=("L", 64), release_en=("L", 140), W=("L", 164), admit_limit=("L", 188), clk=("L", 236), rst=("L", 260),
                panel_valid=("L", 360), panel_byte=("L", 384), tile_id=("L", 408), panel_sel=("L", 432),
                other_valid=("L", 548), other_flit=("L", 572), other_deadline=("L", 596), send_en=("L", 870),
                ready_count=("R", 84), grant_valid=("R", 158), grant_idx=("R", 238), first_done=("R", 560), wave_done=("R", 600),
                t_last_bus=("R", 640), out_tile=("R", 870), out_panel_sel=("R", 894), out_flit=("R", 1060), out_valid=("R", 1080),
                credit_count=("R", 1100)),
    inst={
        "u_release": blk("release", "u_release", 440, 100, 280, 200,
                         left=[("release_en", 140), ("W", 164), ("admit_limit", 188), ("square_finished", 212), ("clk", 252), ("rst", 276)],
                         right=[("let_square", 140)], link="release"),
        "u_packer": blk("packer", "u_packer", 440, 320, 280, 210,
                        left=[("let_square", 336), ("panel_valid", 360), ("panel_byte", 384), ("tile_id", 408),
                              ("panel_sel", 432), ("clk", 480), ("rst", 504)],
                        right=[("rec_valid", 360), ("rec_seq", 384), ("rec_tile", 408), ("rec_sel", 432), ("rec_payload", 456)], link="packer"),
        "u_ready": blk("ready_mem", "u_ready", 820, 320, 330, 420,
                       left=[("rec_valid", 360), ("rec_seq", 384), ("rec_tile", 408), ("rec_sel", 432), ("rec_payload", 456),
                             ("clk", 496), ("rst", 520), ("other_valid", 548), ("other_flit", 572), ("other_deadline", 596),
                             ("grant_idx", 640), ("consume", 664)],
                       right=[("ready_count", 344), ("record", 360), ("score_rec", 384)], link="ready"),
        **{f"u_{s}": blk(f"score_{s}", f"u_{s}", 1220, 110 + 80 * i, 220, 64, left=[("record", 158 + 80 * i)],
                         right=[("score", 158 + 80 * i)]) for i, s in enumerate(["fcfs", "edf", "firing", "shared", "row"])},
        "u_sched": blk("scheduler", "u_sched", 1520, 100, 280, 400,
                       left=[("policy_id", 134), ("score_fcfs", 158), ("score_edf", 238), ("score_firing", 318),
                             ("score_shared", 398), ("score_row", 478)],
                       right=[("grant_valid", 158), ("grant_idx", 238)], link="sched"),
        "u_credit": blk("credit", "u_credit", 440, 815, 280, 215,
                        left=[("send_en", 870), ("grant_valid", 894), ("credit_return", 918), ("clk", 980), ("rst", 1004)],
                        right=[("pass_en", 918), ("gt0", 942), ("credit_count", 966)], link="credit"),
        "u_phy": blk("phy_box", "u_phy", 820, 815, 280, 215, left=[("record", 870), ("pass_en", 918), ("clk", 980), ("rst", 1004)],
                     right=[("out_flit", 870), ("out_valid", 894)], link="phy"),
        "u_unpack": blk("unpack", "u_unpack", 1200, 815, 280, 215,
                        left=[("flit", 870), ("in_valid", 1018), ("clk", 980), ("rst", 1004)],
                        right=[("out_tile", 870), ("out_panel_sel", 894), ("panel_byte", 918)], link="unpack"),
    },
    nets={
        "policy_id": dict(lines=[[(260, 64), (1495, 64), (1495, 134), (1520, 134)]]),
        "release_en": dict(lines=[[(260, 140), (440, 140)]]), "W": dict(lines=[[(260, 164), (440, 164)]]),
        "admit_limit": dict(lines=[[(260, 188), (440, 188)]]),
        **{n: dict(lines=[[(260, y), (440, y)]]) for n, y in (("panel_valid", 360), ("panel_byte", 384), ("tile_id", 408), ("panel_sel", 432))},
        **{n: dict(lines=[[(720, y), (820, y)]]) for n, y in (("rec_valid", 360), ("rec_seq", 384), ("rec_tile", 408), ("rec_sel", 432),
                                                            ("rec_payload", 456))},
        **{n: dict(lines=[[(260, y), (820, y)]]) for n, y in (("other_valid", 548), ("other_flit", 572), ("other_deadline", 596))},
        "ready_count": dict(lines=[[(1150, 344), (1165, 344), (1165, 84), (1960, 84)]]),
        "score_rec": dict(lines=[[(1150, 384), (1185, 384)], [(1185, 158), (1185, 478)],
                                 [(1185, 158), (1220, 158)], [(1185, 238), (1220, 238)],
                                 [(1185, 318), (1220, 318)], [(1185, 398), (1220, 398)],
                                 [(1185, 478), (1220, 478)]]),
        "record": dict(lines=[[(1150, 360), (1175, 360), (1175, 800), (800, 800), (800, 870), (820, 870)]]),
        **{f"score_{s}": dict(lines=[[(1440, 158 + 80 * i), (1520, 158 + 80 * i)]], labels=[(1446, 152 + 80 * i)])
           for i, s in enumerate(["fcfs", "edf", "firing", "shared", "row"])},
        "grant_valid": dict(lines=[[(1800, 158), (1960, 158)], [(1840, 158), (1840, 780), (410, 780), (410, 894), (440, 894)]],
                            labels=[(1300, 775)]),
        "grant_idx": dict(lines=[[(1800, 238), (1960, 238)], [(1820, 238), (1820, 760), (790, 760), (790, 640), (820, 640)]],
                          labels=[(1300, 755)]),
        "send_en": dict(lines=[[(260, 870), (440, 870)]]),
        "pass_en": dict(lines=[[(720, 918), (820, 918)], [(760, 918), (760, 664), (820, 664)]], labels=[(713, 700)]),
        "credit_count": dict(lines=[[(720, 966), (740, 966), (740, 1100), (1960, 1100)]]),
        "out_flit": dict(lines=[[(1100, 870), (1200, 870)], [(1140, 870), (1140, 1060), (1960, 1060)]], labels=[(1148, 864)]),
        "out_valid": dict(lines=[[(1100, 894), (1120, 894), (1120, 1080), (1960, 1080)],
                                 [(1120, 1050), (320, 1050), (320, 918), (440, 918)],
                                 [(1120, 1018), (1200, 1018)]]),
        "let_square": dict(lines=[[(720, 140), (760, 140), (760, 80), (320, 80), (320, 336), (440, 336)]]),
        "out_tile": dict(lines=[[(1480, 870), (1960, 870)]]), "out_panel_sel": dict(lines=[[(1480, 894), (1960, 894)]]),
    })

# ================================================================== L3: inside u_pu/u_release
REL = dict(name="release", W=1600, H=560, frame=dict(x0=250, y0=20, x1=1350, y1=540, title="release"),
    ports=ports(admit_limit=("L", 185), clk=("L", 220), rst=("L", 244), W=("L", 300), release_en=("L", 382),
                square_finished=("L", 402), let_square=("R", 170)),
    inst={
        "min_cap": op("min_cap", 560, 150, 130, 60, [("a", 170), ("b", 185)], [("y", 176)]),
        "cmp_lt": op("cmp_lt", 820, 140, 80, 60, [("a", 155), ("b", 185)], [("y", 170)]),
        "u_admitted": dreg("u_admitted", 820, 300),
        "and_adm": op("and_adm", 400, 352, 70, 40, [("a", 362), ("b", 382)], [("y", 377)]),
        "addsub_adm": op("addsub_adm", 560, 362, 100, 80, [("inc", 377), ("dec", 402), ("a", 427)], [("y", 392)]),
    },
    nets={
        "admit_limit": dict(lines=[[(250, 185), (560, 185)]]),
        "W": dict(lines=[[(250, 300), (520, 300), (520, 170), (560, 170)]]),
        "cap": dict(lines=[[(690, 176), (780, 176), (780, 185), (820, 185)]]),
        "admitted": dict(lines=[[(970, 372), (990, 372), (990, 110), (800, 110), (800, 155), (820, 155)],
                                [(990, 372), (990, 500), (545, 500), (545, 427), (560, 427)]], labels=[(800, 495)]),
        "let_square": dict(lines=[[(900, 170), (1350, 170)], [(940, 170), (940, 250), (380, 250), (380, 362), (400, 362)]],
                           labels=[(600, 245)]),
        "release_en": dict(lines=[[(250, 382), (400, 382)]]),
        "admit_now": dict(lines=[[(470, 377), (560, 377)]], labels=[(478, 371)]),
        "square_finished": dict(lines=[[(250, 402), (560, 402)]]),
        "admitted_d": dict(lines=[[(660, 392), (820, 392)]], labels=[(700, 386)]),
    })

# ================================================================== L3: inside u_pu/u_packer
PK = dict(name="packer", W=1750, H=720, frame=dict(x0=250, y0=20, x1=1500, y1=700, title="packer"),
    ports=ports(panel_valid=("L", 300), panel_byte=("L", 352), clk=("L", 400), rst=("L", 424), tile_id=("L", 650), panel_sel=("L", 674),
                rec_valid=("R", 75), rec_payload=("R", 330), rec_seq=("R", 520), rec_tile=("R", 650), rec_sel=("R", 674),
                let_square=("L", 260)),
    inst={
        "u_cnt": dreg("u_cnt", 330, 70),
        "inc_cnt": op("inc_cnt", 540, 127, 70, 30, [("a", 142)], [("y", 142)]),
        "eq32": op("eq32", 740, 60, 90, 30, [("a", 75)], [("y", 75)]),
        "c_zero6": const("c_zero6", 640, 162, w=76),
        "cnt_mux": mux("cnt_mux", 740, 122),
        "word_mux": op("word_mux", 740, 250, 130, 170, [("fire", 270, dict(plain=True, nolabel=False)), ("valid", 300, dict(plain=True, nolabel=False)),
                       ("zero", 330, dict(plain=True, nolabel=False)), ("shifted", 360, dict(plain=True, nolabel=False)),
                       ("hold", 390, dict(plain=True, nolabel=False))], [("y", 350)], center_y=130),
        "u_word": dreg("u_word", 950, 258),
        "c_zero": const("c_zero", 640, 330, w=76),
        "shl": op("shl", 520, 340, 110, 45, [("byte", 352), ("word", 372)], [("y", 360)]),
        "and_let": op("and_let", 560, 268, 64, 56, [("a", 286), ("b", 304)], [("y", 294)]),
        "seq_mux": mux("seq_mux", 740, 500),
        "u_seq": dreg("u_seq", 950, 448),
        "inc_seq": op("inc_seq", 1160, 505, 70, 30, [("a", 520)], [("y", 520)]),
    },
    nets={
        "byte_cnt": dict(lines=[[(480, 142), (540, 142)]]),
        "cnt_inc": dict(lines=[[(610, 142), (625, 142), (625, 75), (740, 75)], [(625, 142), (625, 190), (725, 190), (725, 182), (740, 182)]]),
        "cnt_zero": dict(lines=[[(716, 162), (740, 162)]]),
        "cnt_d": dict(lines=[[(812, 162), (840, 162), (840, 215), (310, 215), (310, 162), (330, 162)]], labels=[(560, 210)]),
        "fire": dict(lines=[[(830, 75), (1500, 75)], [(880, 75), (880, 490), (725, 490), (725, 520), (740, 520)],
                            [(880, 105), (725, 105), (725, 142), (740, 142)], [(880, 235), (720, 235), (720, 270), (740, 270)]],
                     labels=[(950, 69)]),
        "let_square": dict(lines=[[(250, 260), (520, 260), (520, 286), (560, 286)]]),
        "panel_valid": dict(lines=[[(250, 300), (530, 300), (530, 304), (560, 304)]]),
        "pack_en": dict(lines=[[(624, 294), (700, 294), (700, 300), (740, 300)]]),
        "zero": dict(lines=[[(716, 330), (740, 330)]]),
        "panel_byte": dict(lines=[[(250, 352), (520, 352)]]),
        "shifted": dict(lines=[[(630, 360), (740, 360)]]),
        "word_d": dict(lines=[[(870, 350), (950, 350)]]),
        "rec_payload": dict(lines=[[(1100, 330), (1500, 330)], [(1130, 330), (1130, 440), (500, 440), (500, 372), (520, 372)],
                                   [(720, 440), (720, 390), (740, 390)]], labels=[(950, 435, "hold")]),
        "seq_d": dict(lines=[[(812, 540), (950, 540)]]),
        "seq": dict(lines=[[(1100, 520), (1160, 520)], [(1130, 520), (1130, 580), (715, 580), (715, 560), (740, 560)]], labels=[(950, 575)]),
        "seq_inc": dict(lines=[[(1230, 520), (1500, 520)], [(1260, 520), (1260, 600), (700, 600), (700, 540), (740, 540)]],
                        labels=[(950, 595, "seq+1")]),
        "tile_id": dict(lines=[[(250, 650), (1500, 650)]]), "panel_sel": dict(lines=[[(250, 674), (1500, 674)]]),
    })

# ================================================================== L3: inside u_pu/u_ready
P_ = dict(plain=True, nolabel=False)
RD = dict(name="ready", W=1800, H=920, frame=dict(x0=250, y0=20, x1=1550, y1=880, title="ready_mem"),
    ports=ports(grant_idx=("L", 70), rec_seq=("L", 110), rec_tile=("L", 134), rec_sel=("L", 158), rec_payload=("L", 182),
                rec_valid=("L", 206), other_valid=("L", 350), other_flit=("L", 374), other_deadline=("L", 398),
                clk=("L", 460), rst=("L", 484), consume=("L", 545), record=("R", 175), score_rec=("R", 230),
                ready_count=("R", 520)),
    inst={
        "cat_pk": op("cat_pk", 500, 90, 160, 190, [("seq", 110, P_), ("tile", 134, P_), ("sel", 158, P_), ("payload", 182, P_),
                     ("valid", 206, P_), ("rest", 240, P_)], [("y", 190)]),
        "shl4": op("shl4", 520, 660, 100, 40, [("a", 680)], [("y", 680)]),
        "c_extra": const("c_extra", 520, 740, w=70),
        "add_dk": op("add_dk", 700, 652, 120, 100, [("a", 672), ("b", 740)], [("y", 700)]),
        "c_tail": const("c_tail", 700, 800, w=110),
        "cat_rest": op("cat_rest", 900, 660, 140, 110, [("dl", 690, P_), ("tail", 760, P_)], [("y", 720)]),
        "c_ot": const("c_ot", 300, 470, w=90),
        "wr_or": op("wr_or", 370, 250, 50, 40, [("a", 260), ("b", 280)], [("y", 270)]),
        "cat_ot": op("cat_ot", 500, 330, 160, 120, [("valid", 350, P_), ("payload", 374, P_), ("deadline", 398, P_), ("rest", 430, P_)],
                     [("y", 390)]),
        "src_mux": op("src_mux", 760, 170, 110, 100, [("0", 190, P_), ("sel", 225, P_), ("1", 250, P_)], [("y", 210)]),
        "u_slot": dreg("u_slot", 920, 118, w=180),
        "sel8": op("sel8", 1140, 145, 70, 30, [("a", 160)], [("y", 160)]),
        "read_mux": op("read_mux", 1240, 140, 140, 70, [("sel", 160, P_), ("slot", 190, P_)], [("y", 175)]),
        "cnt_as": op("cnt_as", 920, 500, 100, 80, [("inc", 520), ("dec", 545), ("a", 565)], [("y", 540)]),
        "u_cnt": dreg("u_cnt", 1100, 448),
    },
    nets={
        **{n: dict(lines=[[(250, y), (500, y)]]) for n, y in (("rec_seq", 110), ("rec_sel", 158), ("rec_payload", 182),
                                                            ("other_flit", 374), ("other_deadline", 398))},
        "rec_tile": dict(lines=[[(250, 134), (500, 134)], [(490, 134), (490, 680), (520, 680)]]),
        "rec_valid": dict(lines=[[(250, 206), (500, 206)], [(340, 206), (340, 260), (370, 260)]]),
        "other_valid": dict(lines=[[(250, 350), (500, 350)], [(330, 350), (330, 280), (370, 280)],
                                   [(470, 350), (470, 305), (730, 305), (730, 225), (760, 225)]]),
        "wr": dict(lines=[[(420, 270), (450, 270), (450, 292), (880, 292), (880, 520), (920, 520)]], labels=[(884, 470)]),
        "rec_a": dict(lines=[[(660, 190), (760, 190)]], labels=[(680, 184)]),
        "rec_b": dict(lines=[[(660, 390), (740, 390), (740, 250), (760, 250)]], labels=[(680, 384)]),
        "wr_rec": dict(lines=[[(870, 210), (920, 210)]]),
        "slot": dict(lines=[[(1100, 190), (1240, 190)], [(1200, 190), (1200, 230), (1550, 230)]], labels=[(1124, 205)]),
        "tile16": dict(lines=[[(620, 680), (660, 680), (660, 672), (700, 672)]]),
        "extra": dict(lines=[[(590, 740), (700, 740)]]),
        "deadline": dict(lines=[[(820, 700), (860, 700), (860, 690), (900, 690)]]),
        "pk_tail": dict(lines=[[(810, 800), (860, 800), (860, 760), (900, 760)]]),
        "pk_rest": dict(lines=[[(1040, 720), (1040, 830), (442, 830), (442, 240), (500, 240)]]),
        "ot_rest": dict(lines=[[(390, 470), (450, 470), (450, 430), (500, 430)]]),
        "grant_idx": dict(lines=[[(250, 70), (1120, 70), (1120, 160), (1140, 160)]]),
        "gidx0": dict(lines=[[(1210, 160), (1240, 160)]]),
        "record": dict(lines=[[(1380, 175), (1550, 175)]]),
        "consume": dict(lines=[[(250, 545), (920, 545)]]),
        "cnt_d": dict(lines=[[(1020, 540), (1100, 540)]]),
        "ready_count": dict(lines=[[(1250, 520), (1550, 520)], [(1280, 520), (1280, 600), (900, 600), (900, 565), (920, 565)]]),
    })

# ================================================================== L3: inside u_pu/u_sched
SC = dict(name="sched", W=1550, H=320, frame=dict(x0=250, y0=20, x1=1300, y1=300, title="scheduler"),
    ports=ports(policy_id=("L", 100), score_fcfs=("L", 130), score_edf=("L", 160), score_firing=("L", 190), score_shared=("L", 220),
                score_row=("L", 250), grant_valid=("R", 160), grant_idx=("R", 200)),
    inst={
        "policy_mux": op("policy_mux", 600, 80, 140, 190, [("sel", 100, P_)] + [(f"in{i}", 130 + 30 * i, dict(P_)) for i in range(5)],
                         [("y", 185)]),
        "cmp_min": box("cmp_min", "cmp", "cmp_min", 880, 110, 220, 120, left=[("score", 185)], right=[("grant_valid", 160), ("grant_idx", 200)]),
    },
    nets={
        "policy_id": dict(lines=[[(250, 100), (600, 100)]]),
        **{s: dict(lines=[[(250, 130 + 30 * i), (600, 130 + 30 * i)]]) for i, s in
           enumerate(["score_fcfs", "score_edf", "score_firing", "score_shared", "score_row"])},
        "score_sel": dict(lines=[[(740, 185), (880, 185)]], labels=[(760, 179)]),
        "grant_valid": dict(lines=[[(1100, 160), (1300, 160)]]), "grant_idx": dict(lines=[[(1100, 200), (1300, 200)]]),
    })

# ================================================================== L3: inside u_pu/u_credit
CR = dict(name="credit", W=1750, H=500, frame=dict(x0=250, y0=20, x1=1500, y1=480, title="credit"),
    ports=ports(send_en=("L", 120), grant_valid=("L", 140), clk=("L", 200), rst=("L", 224), credit_return=("L", 305),
                gt0=("R", 250), credit_count=("R", 330), pass_en=("R", 440)),
    inst={
        "and_pass": op("and_pass", 480, 80, 70, 80, [("gt0", 100), ("send_en", 120), ("grant_valid", 140)], [("y", 120)]),
        "accept_ones": op("accept_ones", 640, 210, 110, 30, [("a", 225)], [("y", 225)]),
        "ret_count": op("ret_count", 640, 290, 110, 30, [("a", 305)], [("y", 305)]),
        "addsub": op("addsub", 830, 200, 110, 120, [("count", 210), ("accept", 225), ("returns", 305)], [("y", 275)]),
        "hold_eq": op("hold_eq", 830, 360, 110, 50, [("r", 375), ("a", 395)], [("y", 385)]),
        "cnt_mux": op("cnt_mux", 1000, 230, 72, 95, [("1", 245, P_), ("0", 275, P_), ("sel", 305, P_)], [("y", 270)],
                      center_small="mux", center_at=(0.62, 0.86)),
        "u_count": dreg("u_count", 1130, 178),
        "cmp_gt0": op("cmp_gt0", 1360, 235, 70, 30, [("a", 250)], [("y", 250)]),
    },
    nets={
        "send_en": dict(lines=[[(250, 120), (480, 120)]]), "grant_valid": dict(lines=[[(250, 140), (480, 140)]]),
        "gt0": dict(lines=[[(1430, 250), (1500, 250)], [(1460, 250), (1460, 60), (460, 60), (460, 100), (480, 100)]], labels=[(1200, 55)]),
        "pass_en": dict(lines=[[(550, 120), (600, 120), (600, 440), (1500, 440)], [(600, 225), (640, 225)]], labels=[(900, 435)]),
        "accept": dict(lines=[[(750, 225), (830, 225)], [(780, 225), (780, 395), (830, 395)]], labels=[(786, 219)]),
        "credit_return": dict(lines=[[(250, 305), (640, 305)]]),
        "returns": dict(lines=[[(750, 305), (830, 305)], [(800, 305), (800, 375), (830, 375)]]),
        "next": dict(lines=[[(940, 275), (1000, 275)]], labels=[(950, 269)]),
        "hold": dict(lines=[[(940, 385), (985, 385), (985, 305), (1000, 305)]], labels=[(946, 379)]),
        "cnt_d": dict(lines=[[(1072, 270), (1130, 270)]]),
        "credit_count": dict(lines=[[(1280, 250), (1360, 250)], [(1310, 250), (1310, 170), (810, 170), (810, 210), (830, 210)],
                                    [(970, 170), (970, 245), (1000, 245)], [(1330, 250), (1330, 330), (1500, 330)]], labels=[(1100, 165)]),
    })

# ================================================================== L3: inside u_pu/u_phy
PH = dict(name="phy", W=1700, H=500, frame=dict(x0=250, y0=20, x1=1450, y1=480, title="phy_box + gather"),
    ports=ports(pass_en=("L", 130), record=("L", 150), clk=("L", 360), rst=("L", 384), out_flit=("R", 285), out_valid=("R", 415)),
    inst={
        "c_bub": const("c_bub", 280, 170, w=70),
        "c_rr": const("c_rr", 280, 320, w=70),
        "load_mux": op("load_mux", 420, 110, 90, 80, [("sel", 130, P_), ("1", 150, P_), ("0", 170, P_)], [("y", 150)],
                       center_small="mux", center_at=(0.62, 0.8)),
        **{f"u_s{i}": dreg(f"u_s{i}", 560 + 210 * i, 58) for i in range(4)},
        "lane_mux": op("lane_mux", 420, 270, 120, 70, [("lane0", 290, P_), ("sel", 320, P_)], [("y", 305)]),
        "f_pay": op("f_pay", 640, 290, 100, 30, [("rec", 305)], [("y", 305)]),
        "f_val": op("f_val", 640, 420, 100, 30, [("rec", 435)], [("y", 435)]),
        "u_gflit": dreg("u_gflit", 820, 213),
        "u_gvalid": dreg("u_gvalid", 820, 343),
    },
    nets={
        "pass_en": dict(lines=[[(250, 130), (420, 130)]]), "record": dict(lines=[[(250, 150), (420, 150)]]),
        "prev": dict(lines=[[(350, 170), (420, 170)]]), "rr": dict(lines=[[(350, 320), (420, 320)]]),
        "s0_d": dict(lines=[[(510, 150), (560, 150)]]),
        "s0": dict(lines=[[(710, 130), (720, 130), (720, 150), (770, 150)]]),
        "s1": dict(lines=[[(920, 130), (930, 130), (930, 150), (980, 150)]]),
        "s2": dict(lines=[[(1130, 130), (1140, 130), (1140, 150), (1190, 150)]]),
        "arrived": dict(lines=[[(1340, 130), (1370, 130), (1370, 195), (400, 195), (400, 290), (420, 290)]], labels=[(1000, 190)]),
        "lane_rec": dict(lines=[[(540, 305), (640, 305)], [(590, 305), (590, 435), (640, 435)]], labels=[(548, 299)]),
        "pay": dict(lines=[[(740, 305), (820, 305)]]), "val": dict(lines=[[(740, 435), (820, 435)]]),
        "out_flit": dict(lines=[[(970, 285), (1450, 285)]]), "out_valid": dict(lines=[[(970, 415), (1450, 415)]]),
    })

# ================================================================== L3: inside u_pu/u_unpack
UP = dict(name="unpack", W=1550, H=420, frame=dict(x0=250, y0=20, x1=1300, y1=400, title="unpack"),
    ports=ports(flit=("L", 170), in_valid=("L", 200), clk=("L", 240), rst=("L", 264), panel_byte=("R", 150),
                out_tile=("R", 330), out_panel_sel=("R", 360)),
    inst={
        "byte_mux": op("byte_mux", 520, 130, 110, 80, [("sel", 150, P_), ("0", 170, P_), ("1", 190, P_)], [("y", 170)]),
        "u_word": dreg("u_word", 680, 78),
        "lo8": op("lo8", 950, 135, 70, 30, [("a", 150)], [("y", 150)]),
        "shr": op("shr", 950, 230, 80, 30, [("a", 245)], [("y", 245)]),
    },
    nets={
        "flit": dict(lines=[[(250, 170), (520, 170)]]),
        "take_byte": dict(lines=[[(250, 200), (480, 200), (480, 150), (520, 150)]]),
        "word_d": dict(lines=[[(630, 170), (680, 170)]]),
        "word": dict(lines=[[(830, 150), (950, 150)], [(880, 150), (880, 245), (950, 245)]], labels=[(890, 144)]),
        "panel_byte": dict(lines=[[(1020, 150), (1300, 150)]]),
        "shifted": dict(lines=[[(1030, 245), (1060, 245), (1060, 300), (490, 300), (490, 190), (520, 190)]], labels=[(700, 295)]),
    })

VIEWS = [TOP, CU, FSM, PU, REL, PK, RD, SC, CR, PH, UP]
TABS = [("top", "L1 hop_top"), ("cu", "L2 CU \u00b7 u_cu"), ("pu", "L2 PU \u00b7 u_pu"), ("fsm", "L3 u_fsm"),
        ("release", "L3 u_release"), ("packer", "L3 u_packer"), ("ready", "L3 u_ready"), ("sched", "L3 u_sched"),
        ("credit", "L3 u_credit"), ("phy", "L3 u_phy"), ("unpack", "L3 u_unpack")]

def autofill(V):
    """clock/reset stubs, unused and no-driver stubs sit at their pin; which pins = the spec net."""
    sv = SV[V["name"]]
    for n, d in sv["nets"].items():
        if d.get("stub"): V["nets"].setdefault(n, {})["stub"] = d["pins"]
        for k in ("unused", "nodriver"):
            if k in d: V["nets"].setdefault(n, {}).update({k: d["pins"], "finding": d[k]["finding"]})
    bind(V, sv, {i["inst"]: i for i in sv["instances"]}, SPEC["params"])

HTML = open("index_template.html").read()

if __name__ == "__main__":
    for V in VIEWS: autofill(V)
    inline = {V["name"]: emit(V) for V in VIEWS}
    parent = {v["id"]: v["parent"] for v in SPEC["views"]}
    nav = "".join(f'<a class="tab" href="#{k}">{t}</a>' for k, t in TABS)
    secs = []
    for k, t in TABS:
        sv = SV[k]
        up = f'<a class="up" href="#{parent[k][0]}">&uarr; up to {parent[k][0]} (box {parent[k][1]})</a>' if parent[k] else ""
        secs.append(f'<section id="v-{k}"><div class="bar"><b>{sv["title"]}</b>{up}</div>\n{inline[k]}\n</section>')
    open("index.html", "w").write(HTML.replace("%NAV%", nav).replace("%SECTIONS%", "\n".join(secs))
                                  .replace("%PARENTS%", json.dumps({k: (p[0] if p else None) for k, p in parent.items()})))
    for V in VIEWS:   # standalone page per view, used only for PNG rendering
        open(f"render_{V['name']}.html", "w").write(
            '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0}svg{display:block;width:100%;height:auto}</style>'
            f'</head><body>{open(V["name"] + ".svg").read()}</body></html>')
    print("wrote", len(VIEWS), "views + index.html")
