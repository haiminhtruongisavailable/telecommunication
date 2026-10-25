`default_nettype none
`timescale 1ns/1ps

// One arrived flit becomes 32 panel bytes. The first byte accepted by the
// packer sits at the top of the flit and leaves first.
module hop_unpack (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  in_valid,
    input  wire [255:0]          flit,
    input  wire [7:0]            tile,
    input  wire                  panel_sel,
    output wire                  byte_valid,
    output wire [7:0]            panel_byte,
    output wire [7:0]            out_tile,
    output wire                  out_panel_sel
);
    wire [5:0]   cnt_q;
    wire [5:0]   cnt_dec;
    wire [5:0]   cnt_hold;
    wire [5:0]   cnt_d;
    wire         busy;
    wire [255:0] word_q;
    wire [255:0] shifted;
    wire [255:0] word_hold;
    wire [255:0] word_d;
    wire [7:0]   tile_d;
    wire         sel_d;

    cmp_lt #(.WIDTH(6)) u_busy (
        .a (6'd0),
        .b (cnt_q),
        .y (busy)
    );
    addsub_incdec #(.WIDTH(6)) u_dec (
        .a   (cnt_q),
        .inc (1'b0),
        .dec (busy),
        .y   (cnt_dec)
    );
    mux2 #(.WIDTH(6)) u_cnt_hold (
        .sel (busy),
        .on1 (cnt_dec),
        .on0 (cnt_q),
        .y   (cnt_hold)
    );
    mux2 #(.WIDTH(6)) u_cnt_ld (
        .sel (in_valid),
        .on1 (6'd32),
        .on0 (cnt_hold),
        .y   (cnt_d)
    );
    dreg #(.WIDTH(6)) u_cnt (
        .clk (clk),
        .rst (rst),
        .d   (cnt_d),
        .q   (cnt_q)
    );

    assign shifted = {word_q[247:0], 8'h00};
    mux2 #(.WIDTH(256)) u_word_hold (
        .sel (busy),
        .on1 (shifted),
        .on0 (word_q),
        .y   (word_hold)
    );
    mux2 #(.WIDTH(256)) u_word_ld (
        .sel (in_valid),
        .on1 (flit),
        .on0 (word_hold),
        .y   (word_d)
    );
    dreg #(.WIDTH(256)) u_word (
        .clk (clk),
        .rst (rst),
        .d   (word_d),
        .q   (word_q)
    );

    mux2 #(.WIDTH(8)) u_tile (
        .sel (in_valid),
        .on1 (tile),
        .on0 (out_tile),
        .y   (tile_d)
    );
    dreg #(.WIDTH(8)) u_tile_r (
        .clk (clk),
        .rst (rst),
        .d   (tile_d),
        .q   (out_tile)
    );
    mux2 #(.WIDTH(1)) u_sel (
        .sel (in_valid),
        .on1 (panel_sel),
        .on0 (out_panel_sel),
        .y   (sel_d)
    );
    dreg #(.WIDTH(1)) u_sel_r (
        .clk (clk),
        .rst (rst),
        .d   (sel_d),
        .q   (out_panel_sel)
    );

    assign byte_valid = busy;
    assign panel_byte = word_q[255:248];
endmodule

`default_nettype wire
