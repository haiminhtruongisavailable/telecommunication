`default_nettype none
`timescale 1ns/1ps

// Structural byte collector. One accepted byte joins the low end of u_word.
// The byte that makes the count 32 is the payload of this flit, then the word clears.
module packer #(
    parameter integer W_FLIT = 256,
    parameter integer TILE_W = 8,
    parameter integer SEQ_W  = 16
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    let_square,
    input  wire                    panel_valid,
    input  wire [7:0]              panel_byte,
    input  wire [TILE_W-1:0]       tile_id,
    input  wire                    panel_sel,
    input  wire [7:0]              wave_id,
    output wire                    rec_valid,
    output wire [SEQ_W-1:0]        rec_seq,
    output wire [TILE_W-1:0]       rec_tile,
    output wire                    rec_sel,
    output wire [7:0]              rec_wave,
    output wire [W_FLIT-1:0]       rec_payload,
    output wire                    pack_done
);
    localparam integer CNT_W = 6;
    localparam [CNT_W-1:0] LAST = (W_FLIT / 8) - 1;

    wire                  accept;
    wire [W_FLIT-1:0]     word_q;
    wire [W_FLIT-1:0]     shifted;
    wire [W_FLIT-1:0]     word_hold;
    wire [W_FLIT-1:0]     word_d;
    wire [CNT_W-1:0]      cnt_q;
    wire [CNT_W-1:0]      cnt_inc;
    wire [CNT_W-1:0]      cnt_hold;
    wire [CNT_W-1:0]      cnt_d;
    wire                  at_last;
    wire [SEQ_W-1:0]      seq_q;
    wire [SEQ_W-1:0]      seq_inc;
    wire [SEQ_W-1:0]      seq_d;

    and2 u_accept (
        .a (let_square),
        .b (panel_valid),
        .y (accept)
    );
    cat_low #(.WIDTH(W_FLIT)) u_cat (
        .word    (word_q),
        .byte_in (panel_byte),
        .y       (shifted)
    );
    cmp_eq #(.WIDTH(CNT_W)) u_last (
        .a (cnt_q),
        .b (LAST),
        .y (at_last)
    );
    and2 u_fire (
        .a (accept),
        .b (at_last),
        .y (rec_valid)
    );

    mux2 #(.WIDTH(W_FLIT)) u_payload (
        .sel (accept),
        .on1 (shifted),
        .on0 (word_q),
        .y   (rec_payload)
    );
    mux2 #(.WIDTH(W_FLIT)) u_word_hold (
        .sel (accept),
        .on1 (shifted),
        .on0 (word_q),
        .y   (word_hold)
    );
    mux2 #(.WIDTH(W_FLIT)) u_word_mux (
        .sel (rec_valid),
        .on1 ({W_FLIT{1'b0}}),
        .on0 (word_hold),
        .y   (word_d)
    );
    dreg #(.WIDTH(W_FLIT)) u_word (
        .clk (clk),
        .rst (rst),
        .d   (word_d),
        .q   (word_q)
    );

    incr #(.WIDTH(CNT_W)) u_cnt_inc (
        .a (cnt_q),
        .y (cnt_inc)
    );
    mux2 #(.WIDTH(CNT_W)) u_cnt_hold (
        .sel (accept),
        .on1 (cnt_inc),
        .on0 (cnt_q),
        .y   (cnt_hold)
    );
    mux2 #(.WIDTH(CNT_W)) u_cnt_mux (
        .sel (rec_valid),
        .on1 ({CNT_W{1'b0}}),
        .on0 (cnt_hold),
        .y   (cnt_d)
    );
    dreg #(.WIDTH(CNT_W)) u_cnt (
        .clk (clk),
        .rst (rst),
        .d   (cnt_d),
        .q   (cnt_q)
    );

    incr #(.WIDTH(SEQ_W)) u_seq_inc (
        .a (seq_q),
        .y (seq_inc)
    );
    mux2 #(.WIDTH(SEQ_W)) u_seq_mux (
        .sel (rec_valid),
        .on1 (seq_inc),
        .on0 (seq_q),
        .y   (seq_d)
    );
    dreg #(.WIDTH(SEQ_W)) u_seq (
        .clk (clk),
        .rst (rst),
        .d   (seq_d),
        .q   (seq_q)
    );

    assign rec_seq  = seq_q;
    assign rec_tile = tile_id;
    assign rec_sel  = panel_sel;
    assign rec_wave = wave_id;

    // Sixteen fires end the byte stream. This does not free the admission cap.
    localparam [4:0] LAST_FLIT = 5'd15;
    wire [4:0] flit_q;
    wire [4:0] flit_inc;
    wire [4:0] flit_hold;
    wire [4:0] flit_d;
    wire       last_flit;
    incr #(.WIDTH(5)) u_flit_inc (
        .a (flit_q),
        .y (flit_inc)
    );
    cmp_eq #(.WIDTH(5)) u_last_flit (
        .a (flit_q),
        .b (LAST_FLIT),
        .y (last_flit)
    );
    and2 u_sq_done (
        .a (rec_valid),
        .b (last_flit),
        .y (pack_done)
    );
    mux2 #(.WIDTH(5)) u_flit_hold (
        .sel (rec_valid),
        .on1 (flit_inc),
        .on0 (flit_q),
        .y   (flit_hold)
    );
    mux2 #(.WIDTH(5)) u_flit_mux (
        .sel (pack_done),
        .on1 (5'b0),
        .on0 (flit_hold),
        .y   (flit_d)
    );
    dreg #(.WIDTH(5)) u_flit (
        .clk (clk),
        .rst (rst),
        .d   (flit_d),
        .q   (flit_q)
    );
endmodule

`default_nettype wire
