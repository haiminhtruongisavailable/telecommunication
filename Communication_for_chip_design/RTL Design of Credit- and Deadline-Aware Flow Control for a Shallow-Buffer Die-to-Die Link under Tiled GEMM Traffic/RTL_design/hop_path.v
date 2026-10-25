`default_nettype none
`timescale 1ns/1ps

// One hop. u_cu and the datapath are wired here.
// Ready holds one slot, so one leaf of the four-leaf tree is used.
// A record is offered to the tree once, through fresh, until pass_en takes it.
module hop_path #(
    parameter integer POLICY      = 1,
    parameter integer K           = 16,
    parameter integer D_PHY       = 4,
    parameter integer N_TILES     = 1,
    parameter integer W_LEN       = 1,
    parameter integer ADMIT_LIMIT = 1,
    parameter integer C_TILE      = 16
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  panel_valid,
    input  wire [7:0]            panel_byte,
    input  wire [7:0]            tile_id,
    input  wire                  panel_sel,
    input  wire                  other_valid,
    input  wire [255:0]          other_flit,
    input  wire [31:0]           other_deadline,
    output wire                  release_en,
    output wire                  let_square,
    output wire                  pass_en,
    output wire [7:0]            credit_count,
    output wire                  square_finished,
    output wire                  done,
    output wire                  out_valid,
    output wire                  out_is_gemm,
    output wire [255:0]          out_flit,
    output wire [7:0]            out_tile,
    output wire                  out_panel_sel,
    output wire                  byte_valid,
    output wire [7:0]            byte_out,
    output wire [7:0]            byte_tile,
    output wire                  byte_panel
);
    localparam integer REC_W = 336;

    wire [7:0]  W;
    wire [7:0]  admit_limit;
    wire [7:0]  wave_id;
    wire        pack_done;
    wire        send_en;
    wire        grant_valid;
    wire [7:0]  grant_idx;
    wire [47:0] grant_score;
    wire [8:0]  ready_count;
    wire        rec_valid;
    wire [15:0] rec_seq;
    wire [7:0]  rec_tile;
    wire        rec_sel;
    wire [7:0]  rec_wave;
    wire [255:0] rec_payload;
    wire [REC_W-1:0] score_rec;
    wire [REC_W-1:0] record;
    wire [47:0] score;
    wire        credit_return;
    wire        fresh;
    wire        fresh_d;
    wire        wr;
    wire        not_pass;
    wire        keep;

    hop_control #(
        .N_TILES(N_TILES),
        .C_TILE(C_TILE),
        .W_LEN(W_LEN),
        .ADMIT_LIMIT(ADMIT_LIMIT)
    ) u_cu (
        .clk(clk),
        .rst(rst),
        .credit_count(credit_count),
        .ready_count(ready_count),
        .grant_valid(grant_valid),
        .square_finished(square_finished),
        .release_en(release_en),
        .W(W),
        .admit_limit(admit_limit),
        .send_en(send_en),
        .done(done)
    );

    square_release u_release (
        .clk(clk),
        .rst(rst),
        .release_en(release_en),
        .W(W),
        .admit_limit(admit_limit),
        .pack_done(pack_done),
        .square_finished(square_finished),
        .let_square(let_square),
        .wave_id(wave_id)
    );

    packer u_packer (
        .clk(clk),
        .rst(rst),
        .let_square(let_square),
        .panel_valid(panel_valid),
        .panel_byte(panel_byte),
        .tile_id(tile_id),
        .panel_sel(panel_sel),
        .wave_id(wave_id),
        .rec_valid(rec_valid),
        .rec_seq(rec_seq),
        .rec_tile(rec_tile),
        .rec_sel(rec_sel),
        .rec_wave(rec_wave),
        .rec_payload(rec_payload),
        .pack_done(pack_done)
    );

    ready_mem u_ready (
        .clk(clk),
        .rst(rst),
        .rec_valid(rec_valid),
        .rec_seq(rec_seq),
        .rec_tile(rec_tile),
        .rec_sel(rec_sel),
        .rec_wave(rec_wave),
        .rec_payload(rec_payload),
        .other_valid(other_valid),
        .other_flit(other_flit),
        .other_deadline(other_deadline),
        .grant_idx(grant_idx),
        .consume(pass_en),
        .square_finished(square_finished),
        .ready_count(ready_count),
        .score_rec(score_rec),
        .record(record)
    );

    score_link #(.POLICY(POLICY)) u_score (
        .record(score_rec),
        .score(score)
    );

    // One occupied slot drives leaf 0. The other leaves are empty.
    or2 u_wr (
        .a (rec_valid),
        .b (other_valid),
        .y (wr)
    );
    not1 u_not_pass (
        .a (pass_en),
        .y (not_pass)
    );
    and2 u_keep (
        .a (fresh),
        .b (not_pass),
        .y (keep)
    );
    or2 u_fresh_d (
        .a (wr),
        .b (keep),
        .y (fresh_d)
    );
    dreg #(.WIDTH(1)) u_fresh (
        .clk (clk),
        .rst (rst),
        .d   (fresh_d),
        .q   (fresh)
    );

    scheduler_tree #(.WIDTH(48)) u_sched (
        .v0(fresh),
        .v1(1'b0),
        .v2(1'b0),
        .v3(1'b0),
        .s0(score),
        .s1(48'd0),
        .s2(48'd0),
        .s3(48'd0),
        .grant_valid(grant_valid),
        .grant_idx(grant_idx),
        .grant_score(grant_score)
    );

    hop_credit #(
        .K(K),
        .DEPTH(2*D_PHY)
    ) u_credit (
        .clk(clk),
        .rst(rst),
        .send_en(send_en),
        .grant_valid(grant_valid),
        .credit_count(credit_count),
        .pass_en(pass_en),
        .credit_return(credit_return)
    );

    phy_box #(.D_PHY(D_PHY)) u_phy (
        .clk(clk),
        .rst(rst),
        .pass_en(pass_en),
        .record(record),
        .out_valid(out_valid),
        .out_is_gemm(out_is_gemm),
        .out_flit(out_flit),
        .out_tile(out_tile),
        .out_panel_sel(out_panel_sel)
    );

    hop_unpack u_unpack (
        .clk(clk),
        .rst(rst),
        .in_valid(out_valid),
        .flit(out_flit),
        .tile(out_tile),
        .panel_sel(out_panel_sel),
        .byte_valid(byte_valid),
        .panel_byte(byte_out),
        .out_tile(byte_tile),
        .out_panel_sel(byte_panel)
    );
endmodule

`default_nettype wire
