`default_nettype none
`timescale 1ns/1ps

// One lane. The granted record shifts for D_PHY cycles. A quiet cycle
// shifts a bubble. This block does not read the score.
module phy_box #(
    parameter integer D_PHY = 4,
    parameter integer REC_W = 336
) (
    input  wire                      clk,
    input  wire                      rst,
    input  wire                      pass_en,
    input  wire [REC_W-1:0]          record,
    output wire                      out_valid,
    output wire                      out_is_gemm,
    output wire [255:0]              out_flit,
    output wire [7:0]                out_tile,
    output wire                      out_panel_sel
);
    wire [REC_W-1:0] stage_d [0:D_PHY-1];
    wire [REC_W-1:0] stage_q [0:D_PHY-1];
    genvar gi;

    mux2 #(.WIDTH(REC_W)) u_load (
        .sel (pass_en),
        .on1 (record),
        .on0 ({REC_W{1'b0}}),
        .y   (stage_d[0])
    );

    generate
        for (gi = 0; gi < D_PHY; gi = gi + 1) begin : g_dly
            if (gi > 0) begin : g_chain
                assign stage_d[gi] = stage_q[gi-1];
            end
            dreg #(.WIDTH(REC_W)) u_stage (
                .clk (clk),
                .rst (rst),
                .d   (stage_d[gi]),
                .q   (stage_q[gi])
            );
        end
    endgenerate

    assign out_valid     = stage_q[D_PHY-1][335];
    assign out_is_gemm   = stage_q[D_PHY-1][334];
    assign out_tile      = stage_q[D_PHY-1][263:256];
    assign out_panel_sel = stage_q[D_PHY-1][264];
    assign out_flit      = stage_q[D_PHY-1][255:0];
endmodule

`default_nettype wire
