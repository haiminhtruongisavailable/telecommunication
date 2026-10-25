`default_nettype none
`timescale 1ns/1ps

// Credit starts at K. A send takes one. The return booked by that send
// arrives DEPTH cycles later. out_valid is not this return.
module hop_credit #(
    parameter integer K     = 16,
    parameter integer CW    = 8,
    parameter integer DEPTH = 8
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  send_en,
    input  wire                  grant_valid,
    output wire [CW-1:0]         credit_count,
    output wire                  pass_en,
    output wire                  credit_return
);
    wire              gt0;
    wire              send_grant;
    wire [CW-1:0]     count_d;
    wire [DEPTH-1:0]  dly_d;
    wire [DEPTH-1:0]  dly_q;

    cmp_lt #(.WIDTH(CW)) u_gt0 (
        .a ({CW{1'b0}}),
        .b (credit_count),
        .y (gt0)
    );
    and2 u_sg (
        .a (send_en),
        .b (grant_valid),
        .y (send_grant)
    );
    and2 u_pass (
        .a (send_grant),
        .b (gt0),
        .y (pass_en)
    );

    // Shift the pass pulse. The bit that falls out has waited DEPTH cycles.
    assign dly_d = {dly_q[DEPTH-2:0], pass_en};
    dreg #(.WIDTH(DEPTH)) u_dly (
        .clk (clk),
        .rst (rst),
        .d   (dly_d),
        .q   (dly_q)
    );
    assign credit_return = dly_q[DEPTH-1];

    addsub_incdec #(.WIDTH(CW)) u_cnt (
        .a   (credit_count),
        .inc (credit_return),
        .dec (pass_en),
        .y   (count_d)
    );
    dreg #(.WIDTH(CW), .RST_VAL(K)) u_count (
        .clk (clk),
        .rst (rst),
        .d   (count_d),
        .q   (credit_count)
    );
endmodule

`default_nettype wire
