`default_nettype none
`timescale 1ns/1ps

// One waiting slot. The 256-bit flit and its tile_id become one record here.
// score_rec is that stored record. record is the same slot, the flit selected
// for the PHY. This file draws one slot, the same limit as the schematic.
module ready_mem #(
    parameter integer W_FLIT = 256,
    parameter integer TILE_W = 8,
    parameter integer SEQ_W  = 16,
    parameter integer DL_W   = 32
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    rec_valid,
    input  wire [SEQ_W-1:0]        rec_seq,
    input  wire [TILE_W-1:0]       rec_tile,
    input  wire                    rec_sel,
    input  wire [7:0]              rec_wave,
    input  wire [W_FLIT-1:0]       rec_payload,
    input  wire                    other_valid,
    input  wire [W_FLIT-1:0]       other_flit,
    input  wire [DL_W-1:0]         other_deadline,
    input  wire [7:0]              grant_idx,
    input  wire                    consume,
    output wire                    square_finished,
    output wire [8:0]              ready_count,
    output wire [335:0]            score_rec,
    output wire [335:0]            record
);
    // Record layout, low bits on the right:
    // {valid, is_gemm, wave_id[7:0], consumers[7:0], flits_left[4:0],
    //  deadline[31:0], seq[15:0], panel_sel, tile_id[7:0], payload[255:0]}
    localparam integer REC_W = 336;

    wire [DL_W-1:0] tile16 = {20'b0, rec_tile, 4'b0};
    wire [DL_W-1:0] deadline = tile16 + 32'd40;

    wire [REC_W-1:0] rec_gemm = {
        1'b1, 1'b1, rec_wave, 8'd1, 5'd16,
        deadline, rec_seq, rec_sel, rec_tile, rec_payload
    };
    wire [REC_W-1:0] rec_other = {
        1'b1, 1'b0, 8'd0, 8'd1, 5'd1,
        other_deadline, {SEQ_W{1'b0}}, 1'b0, {TILE_W{1'b0}}, other_flit
    };

    wire [REC_W-1:0] wr_rec;
    wire             wr;
    wire [REC_W-1:0] slot_q;
    wire [REC_W-1:0] slot_d;
    wire [8:0]       count_d;

    mux2 #(.WIDTH(REC_W)) u_src (
        .sel (other_valid),
        .on1 (rec_other),
        .on0 (rec_gemm),
        .y   (wr_rec)
    );
    or2 u_wr (
        .a (rec_valid),
        .b (other_valid),
        .y (wr)
    );
    // A quiet cycle keeps the slot. The schematic dreg has no write enable.
    mux2 #(.WIDTH(REC_W)) u_hold (
        .sel (wr),
        .on1 (wr_rec),
        .on0 (slot_q),
        .y   (slot_d)
    );
    dreg #(.WIDTH(REC_W)) u_slot (
        .clk (clk),
        .rst (rst),
        .d   (slot_d),
        .q   (slot_q)
    );

    addsub_incdec #(.WIDTH(9)) u_cnt_add (
        .a   (ready_count),
        .inc (wr),
        .dec (consume),
        .y   (count_d)
    );
    dreg #(.WIDTH(9)) u_cnt (
        .clk (clk),
        .rst (rst),
        .d   (count_d),
        .q   (ready_count)
    );

    // One drawn slot, so grant_idx does not switch the data yet.
    // tile_id is bits [263:256]. The payload is bits [255:0].
    assign score_rec = slot_q;
    assign record    = slot_q;

    // Cap frees when the 16th GEMM flit of a tile leaves through consume.
    reg [4:0] sent_cnt [0:255];
    integer si;
    wire [7:0] leave_tile = slot_q[263:256];
    wire       leave_gemm = slot_q[334];
    // Procedural read of the per-tile count. The compare uses that value.
    reg  [4:0] leave_sent;
    always @* leave_sent = sent_cnt[leave_tile];
    assign square_finished = consume && leave_gemm && (leave_sent == 5'd15);
    always @(posedge clk) begin
        if (rst) begin
            for (si = 0; si < 256; si = si + 1)
                sent_cnt[si] <= 5'd0;
        end else if (consume && leave_gemm) begin
            if (sent_cnt[leave_tile] == 5'd15)
                sent_cnt[leave_tile] <= 5'd0;
            else
                sent_cnt[leave_tile] <= sent_cnt[leave_tile] + 5'd1;
        end
    end
endmodule

`default_nettype wire
