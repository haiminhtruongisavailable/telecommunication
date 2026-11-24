`default_nettype none
`timescale 1ns/1ps

// Four waiting slots. A GEMM record and an other-stack record that arrive
// in the same cycle take two slots. Each other-stack record takes the next
// sequence number. flits_left on a GEMM record is 16 minus the flits of
// that tile already sent.
module ready_mem #(
    parameter integer W_FLIT  = 256,
    parameter integer TILE_W  = 8,
    parameter integer SEQ_W   = 16,
    parameter integer DL_W    = 32,
    parameter integer N_SLOTS = 4,
    parameter integer POLICY  = 0
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    rec_valid,
    input  wire                    rec_sel,
    input  wire [TILE_W-1:0]       rec_tile,
    input  wire [7:0]              rec_wave,
    input  wire [W_FLIT-1:0]       rec_payload,
    input  wire                    other_valid,
    input  wire [W_FLIT-1:0]       other_flit,
    input  wire [DL_W-1:0]         other_deadline,
    // consumers is 1 on the teacher path. Wave mode passes the panel fanout.
    // rec2_* is the second GEMM flit. Tied invalid, it does not change admission.
    input  wire [7:0]              rec_consumers,
    input  wire                    use_wave_dl,
    input  wire [7:0]              wave_w,
    input  wire                    rec2_valid,
    input  wire                    rec2_sel,
    input  wire [TILE_W-1:0]       rec2_tile,
    input  wire [7:0]              rec2_wave,
    input  wire [W_FLIT-1:0]       rec2_payload,
    input  wire [7:0]              rec2_consumers,
    input  wire                    grant_valid,
    input  wire [7:0]              grant_idx,
    input  wire                    consume,
    output wire                    square_finished,
    output wire [8:0]              ready_count,
    output wire                    v0,
    output wire                    v1,
    output wire                    v2,
    output wire                    v3,
    output wire [335:0]            r0,
    output wire [335:0]            r1,
    output wire [335:0]            r2,
    output wire [335:0]            r3,
    output wire [335:0]            score_rec,
    output wire [335:0]            record,
    output wire                    gemm_accept,
    output wire                    gemm_accept2,
    output wire                    other_accept
);
    // {valid, is_gemm, wave_id[7:0], consumers[7:0], flits_left[4:0],
    //  deadline[31:0], seq[15:0], panel_sel, tile_id[7:0], payload[255:0]}
    localparam integer REC_W = 336;

    reg [REC_W-1:0] slot_q [0:N_SLOTS-1];
    reg [N_SLOTS-1:0] occ;
    reg [SEQ_W-1:0] issue_q;
    reg [REC_W-1:0] last_q;
    reg [4:0] sent_cnt [0:255];
    reg [8:0] count_q;
    // 1 after a contested single-slot admit of GEMM. Reset favors GEMM next.
    reg        last_admit;
    integer si;

    wire [1:0] gix = grant_idx[1:0];
    // Constant bit selects. occ[gix] in one continuous assign stays stale
    // when grant_valid rises and the index does not change.
    wire slot_occ = (gix == 2'd0) ? occ[0] :
                    (gix == 2'd1) ? occ[1] :
                    (gix == 2'd2) ? occ[2] : occ[3];
    wire grant_occ = grant_valid && slot_occ;
    wire [REC_W-1:0] held = (gix == 2'd0) ? slot_q[0] :
                            (gix == 2'd1) ? slot_q[1] :
                            (gix == 2'd2) ? slot_q[2] : slot_q[3];
    wire       held_gemm = held[334];
    wire [4:0] held_left = held[317:313];

    // Free the granted slot, then GEMM, an optional second GEMM, then other.
    // rec2_valid tied off leaves one GEMM. Two or more free slots take both
    // sources. One free slot with both pending:
    // FCFS alternates (last_admit). EDF, shortest, most-consumers, and
    // longest take the earlier deadline and give a tie to GEMM.
    // A refused record stays on its input.
    wire       grant_take = consume && grant_occ;
    wire [N_SLOTS-1:0] occ_after;
    wire [2:0] n_after;
    wire       one_free;
    wire       contested;
    wire       other_earlier;
    wire       give_other;
    wire       deadline_admit;
    wire [31:0] gemm_deadline;
    wire [31:0] gemm_deadline2;
    wire [7:0]  wave_mask;
    wire [7:0]  base_tile;
    wire [7:0]  base_tile2;
    wire [31:0] tile_deadline;
    wire [31:0] wave_deadline;
    assign occ_after[0] = occ[0] & ~(grant_take & (gix == 2'd0));
    assign occ_after[1] = occ[1] & ~(grant_take & (gix == 2'd1));
    assign occ_after[2] = occ[2] & ~(grant_take & (gix == 2'd2));
    assign occ_after[3] = occ[3] & ~(grant_take & (gix == 2'd3));
    assign n_after = {2'b0, occ_after[0]} + {2'b0, occ_after[1]}
                   + {2'b0, occ_after[2]} + {2'b0, occ_after[3]};
    // Teacher deadline is 16*tile+40. Wave mode stores T_wave+40, with
    // T_wave = 16 * (tile aligned down to wave_w). The same value is
    // what admission compares against the other-stack deadline.
    assign tile_deadline = {20'b0, rec_tile, 4'b0} + 32'd40;
    assign wave_mask = wave_w - 8'd1;
    assign base_tile = rec_tile & ~wave_mask;
    assign base_tile2 = rec2_tile & ~wave_mask;
    assign wave_deadline = {20'b0, base_tile, 4'b0} + 32'd40;
    assign gemm_deadline = use_wave_dl ? wave_deadline : tile_deadline;
    assign gemm_deadline2 = use_wave_dl
        ? ({20'b0, base_tile2, 4'b0} + 32'd40)
        : ({20'b0, rec2_tile, 4'b0} + 32'd40);
    assign one_free   = (n_after == 3'd3);
    assign contested  = rec_valid && other_valid && one_free;
    assign other_earlier = other_deadline < gemm_deadline;
    assign deadline_admit = (POLICY == 1) || (POLICY == 2)
                         || (POLICY == 3) || (POLICY == 4);
    assign give_other = contested && (deadline_admit ? other_earlier : last_admit);
    assign gemm_accept  = rec_valid && (n_after < 3'd4) && !give_other;
    // The second GEMM flit enters only after the first, and only while a
    // slot remains. Other-stack then takes whatever is left.
    assign gemm_accept2 = rec2_valid && gemm_accept && ((n_after + 3'd1) < 3'd4);
    assign other_accept = other_valid && (
        (n_after + {2'b0, gemm_accept} + {2'b0, gemm_accept2}) < 3'd4);

    // Residue 1 means fifteen flits of this tile have already left.
    assign square_finished = consume && grant_occ && held_gemm && (held_left == 5'd1);
    assign ready_count = count_q;
    assign v0 = occ[0];
    assign v1 = occ[1];
    assign v2 = occ[2];
    assign v3 = occ[3];
    assign r0 = slot_q[0];
    assign r1 = slot_q[1];
    assign r2 = slot_q[2];
    assign r3 = slot_q[3];
    assign record    = grant_occ ? held : last_q;
    assign score_rec = record;

    function [1:0] first_free;
        input [N_SLOTS-1:0] m;
        begin
            if (!m[0])
                first_free = 2'd0;
            else if (!m[1])
                first_free = 2'd1;
            else if (!m[2])
                first_free = 2'd2;
            else
                first_free = 2'd3;
        end
    endfunction

    // Bits [317:313] are the only field this replaces.
    function [335:0] with_left;
        input [335:0] rec;
        input [4:0]   sent;
        reg   [4:0]   left;
        begin
            left = 5'd16 - sent;
            with_left = {rec[335:318], left, rec[312:0]};
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            for (si = 0; si < N_SLOTS; si = si + 1) begin
                slot_q[si] <= {REC_W{1'b0}};
                occ[si]    <= 1'b0;
            end
            issue_q <= {SEQ_W{1'b0}};
            last_q  <= {REC_W{1'b0}};
            count_q <= 9'd0;
            last_admit <= 1'b0;
            for (si = 0; si < 256; si = si + 1)
                sent_cnt[si] <= 5'd0;
        end else begin
            begin : write_both
                reg [N_SLOTS-1:0] mask;
                reg [1:0] gs, gs2, os;
                reg take_g, take_g2, take_o;
                reg [SEQ_W-1:0] seq_g, seq_g2, seq_o;
                reg [8:0] n_occ;
                reg [7:0] sent_tile;
                reg sent_gemm;
                reg [4:0] old_sent, new_sent, stamp_sent, stamp_sent2;
                reg [REC_W-1:0] n0, n1, n2, n3, gemm_rec, gemm_rec2;
                integer fi;

                mask = occ;
                if (grant_take)
                    mask[gix] = 1'b0;
                sent_tile = held[263:256];
                sent_gemm = held[334];
                old_sent  = sent_cnt[sent_tile];
                if (grant_take && sent_gemm && (old_sent != 5'd15))
                    new_sent = old_sent + 5'd1;
                else if (grant_take && sent_gemm)
                    new_sent = 5'd0;
                else
                    new_sent = old_sent;

                take_g = gemm_accept;
                take_g2 = gemm_accept2;
                take_o = other_accept;
                gs = 2'd0;
                gs2 = 2'd0;
                os = 2'd0;
                if (take_g) begin
                    gs = first_free(mask);
                    mask[gs] = 1'b1;
                end
                if (take_g2) begin
                    gs2 = first_free(mask);
                    mask[gs2] = 1'b1;
                end
                if (take_o) begin
                    os = first_free(mask);
                    mask[os] = 1'b1;
                end
                n_occ = 9'd0;
                for (fi = 0; fi < N_SLOTS; fi = fi + 1)
                    if (mask[fi])
                        n_occ = n_occ + 9'd1;
                seq_g = issue_q;
                seq_g2 = issue_q + (take_g ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}});
                seq_o = issue_q
                    + (take_g ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}})
                    + (take_g2 ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}});

                n0 = slot_q[0];
                n1 = slot_q[1];
                n2 = slot_q[2];
                n3 = slot_q[3];
                if (consume && grant_occ && sent_gemm) begin
                    if (mask[0] && slot_q[0][334] && (slot_q[0][263:256] == sent_tile))
                        n0 = with_left(slot_q[0], new_sent);
                    if (mask[1] && slot_q[1][334] && (slot_q[1][263:256] == sent_tile))
                        n1 = with_left(slot_q[1], new_sent);
                    if (mask[2] && slot_q[2][334] && (slot_q[2][263:256] == sent_tile))
                        n2 = with_left(slot_q[2], new_sent);
                    if (mask[3] && slot_q[3][334] && (slot_q[3][263:256] == sent_tile))
                        n3 = with_left(slot_q[3], new_sent);
                    sent_cnt[sent_tile] <= new_sent;
                    last_q <= held;
                end
                if (take_g) begin
                    if (consume && grant_occ && sent_gemm && (rec_tile == sent_tile))
                        stamp_sent = new_sent;
                    else
                        stamp_sent = sent_cnt[rec_tile];
                    gemm_rec = {
                        1'b1, 1'b1, rec_wave, rec_consumers, 5'd0,
                        gemm_deadline, seq_g, rec_sel, rec_tile, rec_payload
                    };
                    gemm_rec = with_left(gemm_rec, stamp_sent);
                    case (gs)
                        2'd0: n0 = gemm_rec;
                        2'd1: n1 = gemm_rec;
                        2'd2: n2 = gemm_rec;
                        default: n3 = gemm_rec;
                    endcase
                end
                if (take_g2) begin
                    if (consume && grant_occ && sent_gemm && (rec2_tile == sent_tile))
                        stamp_sent2 = new_sent;
                    else
                        stamp_sent2 = sent_cnt[rec2_tile];
                    gemm_rec2 = {
                        1'b1, 1'b1, rec2_wave, rec2_consumers, 5'd0,
                        gemm_deadline2, seq_g2, rec2_sel, rec2_tile, rec2_payload
                    };
                    gemm_rec2 = with_left(gemm_rec2, stamp_sent2);
                    case (gs2)
                        2'd0: n0 = gemm_rec2;
                        2'd1: n1 = gemm_rec2;
                        2'd2: n2 = gemm_rec2;
                        default: n3 = gemm_rec2;
                    endcase
                end
                if (take_o) begin
                    case (os)
                        2'd0: n0 = {
                            1'b1, 1'b0, 8'd0, 8'd1, 5'd1,
                            other_deadline, seq_o, 1'b0, {TILE_W{1'b0}}, other_flit
                        };
                        2'd1: n1 = {
                            1'b1, 1'b0, 8'd0, 8'd1, 5'd1,
                            other_deadline, seq_o, 1'b0, {TILE_W{1'b0}}, other_flit
                        };
                        2'd2: n2 = {
                            1'b1, 1'b0, 8'd0, 8'd1, 5'd1,
                            other_deadline, seq_o, 1'b0, {TILE_W{1'b0}}, other_flit
                        };
                        default: n3 = {
                            1'b1, 1'b0, 8'd0, 8'd1, 5'd1,
                            other_deadline, seq_o, 1'b0, {TILE_W{1'b0}}, other_flit
                        };
                    endcase
                end
                slot_q[0] <= n0;
                slot_q[1] <= n1;
                slot_q[2] <= n2;
                slot_q[3] <= n3;
                occ <= mask;
                if (take_g || take_g2 || take_o)
                    issue_q <= issue_q
                        + (take_g ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}})
                        + (take_g2 ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}})
                        + (take_o ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}});
                count_q <= n_occ;
                if (!deadline_admit && contested && gemm_accept)
                    last_admit <= 1'b1;
                else if (!deadline_admit && contested && other_accept)
                    last_admit <= 1'b0;
            end
        end
    end
endmodule

`default_nettype wire
