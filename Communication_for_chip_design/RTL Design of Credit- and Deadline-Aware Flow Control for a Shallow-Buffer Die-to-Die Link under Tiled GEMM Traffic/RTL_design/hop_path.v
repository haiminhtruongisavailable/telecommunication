`default_nettype none
`timescale 1ns/1ps

// One hop. u_cu and the datapath are wired here.
// Ready holds four slots. Each occupied slot is one leaf of the tree.
module hop_path #(
    parameter integer POLICY      = 1,
    parameter integer K           = 16,
    parameter integer D_PHY       = 4,
    parameter integer N_TILES     = 1,
    parameter integer W_LEN       = 1,
    parameter integer ADMIT_LIMIT = 1,
    parameter integer C_TILE      = 16,
    parameter integer TRACK_TILE  = 0
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  panel_valid,
    input  wire [255:0]          panel_flit,
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
    output wire                  byte_panel,
    input  wire                  panel2_valid,
    input  wire [255:0]          panel2_flit,
    input  wire [7:0]            tile2_id,
    input  wire                  panel2_sel,
    input  wire [7:0]            rec_consumers,
    input  wire [7:0]            rec2_consumers,
    input  wire                  use_wave_dl,
    input  wire [7:0]            wave_w
);
    localparam integer REC_W = 336;

    wire [7:0]  W;
    wire [7:0]  admit_limit;
    wire [7:0]  wave_id;
    wire        pack_done;
    wire        pack_done2;
    wire        admit_now;
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
    wire        gemm_accept;
    wire        gemm_accept2;
    wire        other_accept;
    wire        oth_hold;
    wire        oth_present;
    wire        oth_keep;
    wire        oth_not_acc;
    wire        oth_not_hold;
    wire        oth_ext_taken;
    wire        oth_not_keep;
    wire        oth_not_ext;
    wire        oth_load_pre;
    wire        oth_load;
    wire        oth_hold_d;
    wire [255:0] oth_flit_q;
    wire [255:0] oth_flit_d;
    wire [255:0] oth_pdata;
    wire [31:0] oth_dl_q;
    wire [31:0] oth_dl_d;
    wire [31:0] oth_pdl;
    wire        v0, v1, v2, v3;
    wire [REC_W-1:0] r0, r1, r2, r3;
    wire [47:0] s0, s1, s2, s3;

    hop_control #(
        .N_TILES(N_TILES),
        .C_TILE(C_TILE),
        .W_LEN(W_LEN),
        .ADMIT_LIMIT(ADMIT_LIMIT)
    ) u_cu (
        .clk(clk),
        .rst(rst),
        .credit_count(credit_count),
        .credit_return(credit_return),
        .ready_count(ready_count),
        .grant_valid(grant_valid),
        .square_finished(square_finished),
        .admit_now(admit_now),
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
        .pack_done2(pack_done2),
        .square_finished(square_finished),
        .let_square(let_square),
        .admit_now(admit_now),
        .wave_id(wave_id)
    );

    packer #(.TRACK_TILE(TRACK_TILE)) u_packer (
        .clk(clk),
        .rst(rst),
        .let_square(let_square),
        .panel_valid(panel_valid),
        .panel_flit(panel_flit),
        .tile_id(tile_id),
        .panel_sel(panel_sel),
        .wave_id(wave_id),
        .rec_valid(rec_valid),
        .rec_seq(rec_seq),
        .rec_tile(rec_tile),
        .rec_sel(rec_sel),
        .rec_wave(rec_wave),
        .rec_payload(rec_payload),
        .pack_done(pack_done),
        .pack_done2(pack_done2),
        .gemm_accept(gemm_accept),
        .gemm_accept2(gemm_accept2),
        .tile2_id(tile2_id)
    );

    // One other-stack hold. A refused flit stays here until other_accept.
    // An offer that ready takes on this edge does not occupy the hold.
    or2 u_oth_present (
        .a (oth_hold),
        .b (other_valid),
        .y (oth_present)
    );
    mux2 #(.WIDTH(256)) u_oth_pdata (
        .sel (oth_hold),
        .on1 (oth_flit_q),
        .on0 (other_flit),
        .y   (oth_pdata)
    );
    mux2 #(.WIDTH(32)) u_oth_pdl (
        .sel (oth_hold),
        .on1 (oth_dl_q),
        .on0 (other_deadline),
        .y   (oth_pdl)
    );
    not1 u_oth_nacc (
        .a (other_accept),
        .y (oth_not_acc)
    );
    and2 u_oth_keep (
        .a (oth_hold),
        .b (oth_not_acc),
        .y (oth_keep)
    );
    not1 u_oth_nhold (
        .a (oth_hold),
        .y (oth_not_hold)
    );
    and2 u_oth_ext (
        .a (other_accept),
        .b (oth_not_hold),
        .y (oth_ext_taken)
    );
    not1 u_oth_nkeep (
        .a (oth_keep),
        .y (oth_not_keep)
    );
    not1 u_oth_next (
        .a (oth_ext_taken),
        .y (oth_not_ext)
    );
    and2 u_oth_ld1 (
        .a (other_valid),
        .b (oth_not_keep),
        .y (oth_load_pre)
    );
    and2 u_oth_ld2 (
        .a (oth_load_pre),
        .b (oth_not_ext),
        .y (oth_load)
    );
    or2 u_oth_hd (
        .a (oth_keep),
        .b (oth_load),
        .y (oth_hold_d)
    );
    mux2 #(.WIDTH(256)) u_oth_fd (
        .sel (oth_load),
        .on1 (other_flit),
        .on0 (oth_flit_q),
        .y   (oth_flit_d)
    );
    mux2 #(.WIDTH(32)) u_oth_dd (
        .sel (oth_load),
        .on1 (other_deadline),
        .on0 (oth_dl_q),
        .y   (oth_dl_d)
    );
    dreg #(.WIDTH(1)) u_oth_h (
        .clk (clk),
        .rst (rst),
        .d   (oth_hold_d),
        .q   (oth_hold)
    );
    dreg #(.WIDTH(256)) u_oth_f (
        .clk (clk),
        .rst (rst),
        .d   (oth_flit_d),
        .q   (oth_flit_q)
    );
    dreg #(.WIDTH(32)) u_oth_dl (
        .clk (clk),
        .rst (rst),
        .d   (oth_dl_d),
        .q   (oth_dl_q)
    );

    ready_mem #(.POLICY(POLICY)) u_ready (
        .clk(clk),
        .rst(rst),
        .rec_valid(rec_valid),
        .rec_tile(rec_tile),
        .rec_sel(rec_sel),
        .rec_wave(rec_wave),
        .rec_payload(rec_payload),
        .other_valid(oth_present),
        .other_flit(oth_pdata),
        .other_deadline(oth_pdl),
        .grant_valid(grant_valid),
        .grant_idx(grant_idx),
        .consume(pass_en),
        .square_finished(square_finished),
        .ready_count(ready_count),
        .v0(v0), .v1(v1), .v2(v2), .v3(v3),
        .r0(r0), .r1(r1), .r2(r2), .r3(r3),
        .score_rec(score_rec),
        .record(record),
        .gemm_accept(gemm_accept),
        .gemm_accept2(gemm_accept2),
        .other_accept(other_accept),
        .rec_consumers(rec_consumers),
        .use_wave_dl(use_wave_dl),
        .wave_w(wave_w),
        .rec2_valid(panel2_valid),
        .rec2_sel(panel2_sel),
        .rec2_tile(tile2_id),
        .rec2_wave(wave_id),
        .rec2_payload(panel2_flit),
        .rec2_consumers(rec2_consumers)
    );

    score_link #(.POLICY(POLICY)) u_score (
        .record(score_rec),
        .score(score)
    );
    score_link #(.POLICY(POLICY)) u_sc0 (.record(r0), .score(s0));
    score_link #(.POLICY(POLICY)) u_sc1 (.record(r1), .score(s1));
    score_link #(.POLICY(POLICY)) u_sc2 (.record(r2), .score(s2));
    score_link #(.POLICY(POLICY)) u_sc3 (.record(r3), .score(s3));

    scheduler_tree #(.WIDTH(48)) u_sched (
        .v0(v0),
        .v1(v1),
        .v2(v2),
        .v3(v3),
        .s0(s0),
        .s1(s1),
        .s2(s2),
        .s3(s3),
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
