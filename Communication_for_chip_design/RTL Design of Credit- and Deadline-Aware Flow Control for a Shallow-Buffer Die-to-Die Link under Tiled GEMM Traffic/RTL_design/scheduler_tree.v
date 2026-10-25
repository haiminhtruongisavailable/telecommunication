`default_nettype none
`timescale 1ns/1ps

// One match in the tree. The smaller valid score wins, and its slot index
// follows it up. An invalid leaf is not a contestant.
module score_pair #(
    parameter integer WIDTH = 48
) (
    input  wire                  va,
    input  wire                  vb,
    input  wire [WIDTH-1:0]      sa,
    input  wire [WIDTH-1:0]      sb,
    input  wire [7:0]            ia,
    input  wire [7:0]            ib,
    output wire                  vy,
    output wire [WIDTH-1:0]      sy,
    output wire [7:0]            iy
);
    wire b_smaller;
    wire a_out;
    wire take_b_raw;
    wire take_b;
    cmp_lt #(.WIDTH(WIDTH)) u_lt (.a(sb), .b(sa), .y(b_smaller));
    not1 u_no_a (.a(va), .y(a_out));
    or2  u_or  (.a(a_out), .b(b_smaller), .y(take_b_raw));
    and2 u_and (.a(vb), .b(take_b_raw), .y(take_b));
    or2  u_any (.a(va), .b(vb), .y(vy));
    mux2 #(.WIDTH(WIDTH)) u_score (.sel(take_b), .on1(sb), .on0(sa), .y(sy));
    mux2 #(.WIDTH(8))     u_idx   (.sel(take_b), .on1(ib), .on0(ia), .y(iy));
endmodule

// Four waiting scores, compared in one cycle. No register holds last cycle's order.
module scheduler_tree #(
    parameter integer WIDTH = 48
) (
    input  wire                  v0,
    input  wire                  v1,
    input  wire                  v2,
    input  wire                  v3,
    input  wire [WIDTH-1:0]      s0,
    input  wire [WIDTH-1:0]      s1,
    input  wire [WIDTH-1:0]      s2,
    input  wire [WIDTH-1:0]      s3,
    output wire                  grant_valid,
    output wire [7:0]            grant_idx,
    output wire [WIDTH-1:0]      grant_score
);
    wire             v01, v23;
    wire [WIDTH-1:0] s01, s23;
    wire [7:0]       i01, i23;
    score_pair #(.WIDTH(WIDTH)) u_left (
        .va(v0), .vb(v1), .sa(s0), .sb(s1), .ia(8'd0), .ib(8'd1),
        .vy(v01), .sy(s01), .iy(i01)
    );
    score_pair #(.WIDTH(WIDTH)) u_right (
        .va(v2), .vb(v3), .sa(s2), .sb(s3), .ia(8'd2), .ib(8'd3),
        .vy(v23), .sy(s23), .iy(i23)
    );
    score_pair #(.WIDTH(WIDTH)) u_root (
        .va(v01), .vb(v23), .sa(s01), .sb(s23), .ia(i01), .ib(i23),
        .vy(grant_valid), .sy(grant_score), .iy(grant_idx)
    );
endmodule

`default_nettype wire
