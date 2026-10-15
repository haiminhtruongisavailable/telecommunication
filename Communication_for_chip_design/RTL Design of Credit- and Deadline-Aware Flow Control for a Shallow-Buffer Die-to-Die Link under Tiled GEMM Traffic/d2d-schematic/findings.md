# Findings: D2D hop adapter (doc-only source)

Refs: **A:Lnnn** = source/architecture-ascii.md (= docs/architecture-ascii.md @ 8a0d7dd, byte-identical
to the attached .md); **W:Lnnn** = source/workflow-scores-and-wires.md; **G:Lnnn** =
source/grok/build_html.py (Grok CLI's drawing script); **rtl/x.v:n** = source/rtl (old flat design).
Every finding cited in spec.json is marked on the drawing (red "no driver · F#" / grey "unused · F#"
dashed stub, dashed box = inferred) and is checked by check.py.

The netlist below was revised in place. The page, tabs, colors, and click-into-block behavior are
the same. Closed on the drawing: F4 (let_square gates the packer), F6 (out_valid returns one
credit), F7 (scores read the slot register, not the grant mux), F16 (D_k = tile_id*16+40, tails
filled), F20 (new byte joins the low side), F22 (stage 0 loads 0), F23 (gather select is 0 at
N_WIRES=1), F26 (admission uses min(W, admit_limit)). F9 is half closed: ready_count blocks a
release when the 256 slots are full; grant_idx is still unread in CU. F21 is half closed:
take_byte follows in_valid. out_tile and out_panel_sel are still open.

## Source
### F1
No Verilog exists for the CU/PU design. Checked main, p1-freeze-and-pipeline and refs/pull/1/head
(855a123): no arch/ folder and no hop_control/hop_processing .v files; the only rtl/ is the old flat
design (credit.v, fifo_k.v, hop_top.v, packer.v, scheduler_edf.v). The source of truth is therefore
the doc. The branch head is now 8a0d7dd (two commits, b9d387d and 8a0d7dd, on top of c615672).

## Multiple drivers / undriven / unused
### F2
release_en has two drivers. CU draws release_fsm driving release_en (A:L143-149, a CU->PU wire,
A:L54), but PU 5g (A:L467) also builds "k_cnt dreg + C_TILE, cmp time -> release_en" inside PU. In
the drawing the timer is placed in CU only (view fsm); PU's release_en is an input.
### F3
square_finished (release input, A:L454) has no driver anywhere: nothing in PU produces it, and it
is not a hop_top pin.
### F4
Closed. let_square now ANDs with panel_valid before the packer word mux, so a byte shifts only
after the square is admitted. Panel bytes still enter the packer from the frame.
### F5
first_done, wave_done (CU inputs, A:L161) and t_last_bus (hop_top output, A:L48) have no driver
inside PU. No block computes them.
### F6
Closed for N_WIRES=1. credit_return is the same net as out_valid: one gather beat frees one RX
slot. It is not a hop_top pin. F14 remains, because the pin is still 1 bit.
### F9
ready_count now gates release_en: the fsm pulse leaves CU only while ready_count < 256.
grant_idx is still unused in CU (drawn "unused · F9"). Control does not scan slots.
### F11
policy_reg and admit_limit_reg (A:L143-154) have no input: there is no pin to load them. Drawn as
constants POLICY / ADMIT_LIMIT (dashed). Grok's script draws invented nets policy_next / admit_next
(G:L316, G:L326).
### F12
Credit gating is applied twice: pass_en = send_en & grant_valid, cleared when count==0 (A:L393),
and also "cmp > 0 gates send_en inside CU" (A:L389). The gt0 output that would carry that has no
PU->CU wire, so it is unused.
### F26
Closed. The release comparator sees min(W, admit_limit), so a wave cannot admit more squares
than W.

## Combinational loop
### F7
Closed. The five scores read score_rec, which is the slot register q. record is only the
grant-selected flit, and it goes to the PHY. grant_idx no longer feeds the score. The old
acknowledgement was removed from spec.known. F8 is still open: one drawn slot is not a min
over 256.
### F8
cmp_min receives one score (the selected record's) but must compare all slots: per-slot scores and
per-slot valid bits are missing from the doc. A single read port cannot feed a min over 256 slots.

## Widths / lanes
### F13
pass_en is only gated by count>0 (A:L393), not limited to min(credit_count, N_WIRES) as A:L86 says.
### F14
credit_return is 1 bit (A:L357) though up to N_WIRES credits can return per cycle at N>1.
### F18
ready has one read port (record, REC_W) but there are N_WIRES lanes; the phy load mux sel is 1 bit
while pass_en is N_WIRES wide, so the net breaks at N_WIRES=2 and 4 (check.py [widen], acknowledged).
### F23
Half closed. At N_WIRES=1 the gather select is the constant 0. out_flit is still 256 bits, so a
wider gather still overflows. F18 (pass_en wider than the load-mux select) is unchanged.

## Records / packer / unpack
### F15
credit cnt_mux (hold when nothing changes) is redundant: count + accepts - returns already equals
count when both are 0.
### F16
Closed as constants plus one adder. Packer deadline is tile_id*16+40 (C_tile=16, extra=40,
T_0=0). The 22-bit tail is flits_left=16, consumers=1, wave_id=0, is_gemm=1. The other-stack
tail is one non-GEMM flit (seq, tile, sel = 0, flits_left = 1). wave_id is still not a counter.
### F17
ready_mem has one write port: a packer record and an other-die record arriving together collide
(src_mux picks other_valid, the packer record is lost). No slot write address is given. The
"consume" pin that decrements ready_count is inferred (from pass_en).
### F19
Packer: byte_cnt==32 fires and resets the word to 0, so the 32nd byte is dropped; byte_cnt also
counts when panel_valid is low.
### F20
Closed on the drawing. The packer shift is {word[247:0], byte} (drawn "{lo,byte}"), so the new
byte is the low byte that unpack reads with [7:0]. The ==32 fire bug (F19) is unchanged.
### F21
Half closed. take_byte is in_valid, the same beat as out_valid, so the unpack shifts when a flit
arrives. out_tile and out_panel_sel are still undriven: gather still keeps only payload and valid.
panel_byte out of unpack is still unused, and the name still clashes with the hop_top input.
### F22
Closed. Stage 0 loads a constant 0 bubble when pass_en is low. It does not feed its own q back.

## Doc / script consistency
### F10
done is "first_done, wave_done -> done" (A:L161); the operator (AND/OR/select) is not given.
### F24
N_TILES sizes t_last_bus (A:L48) but is not in the parameter table (A:L18-29); value 8 taken from
rtl/hop_top.v:6.
### F25
Naming and Grok script errors: the score net is driven by all five score blocks into one net
(G:L94-98); grant_idx is wired to credit (G:L112); W is drawn from u_k (G:L307); unpack panel_byte
goes to the frame (G:L273); the L0 view lacks pins (G:L26-31).
### F27
W:L94 says "the same six scores"; the architecture has five (fcfs, edf, firing, shared, row).
### F28
The old rtl/hop_top.v pins (cycle, send_valid, credit_neg, stall_cycles ...) are entirely
different from the new hop_top pin table (A:L35-48); only clk, rst, done, t_last_bus match.
### F29
Reused rtl modules vs new pins (full list: rtl_pins.txt, made by rtl_pins.py):
credit.v has inc_n[CW-1:0]/dec/count/can_send (rtl/credit.v:8-11) vs credit_return/send_en/
grant_valid/credit_count/gt0/pass_en; only count~credit_count and can_send~gt0 correspond.
packer.v is combinational (no clk) with fire/do_pack/deadline/n_flits (rtl/packer.v:10-14); the new
packer is clocked, byte-serial, and has no deadline. scheduler_edf.v takes policy_edf (1 bit) and
per-slot valid/deadline/seq (rtl/scheduler_edf.v:8-11) vs policy_id[2:0] and five scores;
grant_idx is IDX_W (8) vs N_WIRES*8 (equal only at N=1). fifo_k.v (push/pop/occ/full/empty) has no
counterpart.
### F30
The K-slot buffer in front of unpack (W:L34) and rtl/fifo_k.v are missing from the new
architecture.
