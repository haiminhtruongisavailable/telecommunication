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
    parameter integer N_SLOTS = 4
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
    output wire [335:0]            record
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

    wire [31:0] gemm_deadline = {20'b0, rec_tile, 4'b0} + 32'd40;

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
            for (si = 0; si < 256; si = si + 1)
                sent_cnt[si] <= 5'd0;
        end else begin
            begin : write_both
                reg [N_SLOTS-1:0] mask;
                reg [1:0] gs, os;
                reg take_g, take_o;
                reg [SEQ_W-1:0] seq_g, seq_o;
                reg [8:0] n_occ;
                reg [7:0] sent_tile;
                reg sent_gemm;
                reg [4:0] old_sent, new_sent, stamp_sent;
                reg [REC_W-1:0] n0, n1, n2, n3, gemm_rec;
                integer fi;

                mask = occ;
                if (consume && grant_occ)
                    mask[gix] = 1'b0;
                sent_tile = held[263:256];
                sent_gemm = held[334];
                old_sent  = sent_cnt[sent_tile];
                if (consume && grant_occ && sent_gemm && (old_sent != 5'd15))
                    new_sent = old_sent + 5'd1;
                else if (consume && grant_occ && sent_gemm)
                    new_sent = 5'd0;
                else
                    new_sent = old_sent;

                take_g = 1'b0;
                take_o = 1'b0;
                gs = 2'd0;
                os = 2'd0;
                n_occ = 9'd0;
                for (fi = 0; fi < N_SLOTS; fi = fi + 1)
                    if (mask[fi])
                        n_occ = n_occ + 9'd1;
                if (rec_valid && (n_occ < N_SLOTS)) begin
                    gs = first_free(mask);
                    take_g = 1'b1;
                    mask[gs] = 1'b1;
                    n_occ = n_occ + 9'd1;
                end
                if (other_valid && (n_occ < N_SLOTS)) begin
                    os = first_free(mask);
                    take_o = 1'b1;
                    mask[os] = 1'b1;
                    n_occ = n_occ + 9'd1;
                end
                seq_g = issue_q;
                seq_o = issue_q + (take_g ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}});

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
                        1'b1, 1'b1, rec_wave, 8'd1, 5'd0,
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
                if (take_g || take_o)
                    issue_q <= issue_q
                        + (take_g ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}})
                        + (take_o ? {{(SEQ_W-1){1'b0}}, 1'b1} : {SEQ_W{1'b0}});
                count_q <= n_occ;
            end
        end
    end
endmodule

`default_nettype wire
