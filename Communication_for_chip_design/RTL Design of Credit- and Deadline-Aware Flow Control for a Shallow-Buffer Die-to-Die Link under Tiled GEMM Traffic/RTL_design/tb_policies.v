`timescale 1ns/1ps

// One contest, five chips. Each chip packs a different score from the same
// three records. Leaf 3 is empty. Smaller score wins.
//   slot 0  tile 3  seq 0  panel A  deadline 88  flits_left 16  consumers 1
//   slot 1  tile 1  seq 1  panel B  deadline 40  flits_left 16  consumers 1
//   slot 2  tile 2  seq 2  panel A  deadline 200 flits_left 1   consumers 1
module tb_policies;
    reg clk;
    reg [335:0] rec0, rec1, rec2;

    wire [47:0] sc [0:4][0:2];
    wire [7:0]  gidx [0:4];
    wire [47:0] gscore [0:4];
    wire        gvalid [0:4];

    wire [7:0] grant_fcfs   = gidx[0];
    wire [7:0] grant_edf    = gidx[1];
    wire [7:0] grant_firing = gidx[2];
    wire [7:0] grant_shared = gidx[3];
    wire [7:0] grant_row    = gidx[4];

    wire [47:0] score_fcfs   = sc[0][0];
    wire [47:0] score_edf    = sc[1][0];
    wire [47:0] score_firing = sc[2][0];
    wire [47:0] score_shared = sc[3][0];
    wire [47:0] score_row    = sc[4][0];

    wire [15:0] seq0 = rec0[280:265];
    wire [15:0] seq1 = rec1[280:265];
    wire [15:0] seq2 = rec2[280:265];
    wire [31:0] deadline0 = rec0[312:281];
    wire [31:0] deadline1 = rec1[312:281];
    wire [31:0] deadline2 = rec2[312:281];
    wire [4:0]  flits0 = rec0[317:313];
    wire [4:0]  flits1 = rec1[317:313];
    wire [4:0]  flits2 = rec2[317:313];
    wire        panel0 = rec0[264];
    wire        panel1 = rec1[264];
    wire        panel2 = rec2[264];

    integer errors;
    integer p;

    function [335:0] rec_of;
        input [7:0]  tile;
        input [15:0] seq;
        input        panel;
        input [31:0] deadline;
        input [4:0]  flits_left;
        input [7:0]  consumers;
        begin
            rec_of = {336{1'b0}};
            rec_of[335]     = 1'b1;
            rec_of[334]     = 1'b1;
            rec_of[325:318] = consumers;
            rec_of[317:313] = flits_left;
            rec_of[312:281] = deadline;
            rec_of[280:265] = seq;
            rec_of[264]     = panel;
            rec_of[263:256] = tile;
        end
    endfunction

    genvar gi;
    generate
        for (gi = 0; gi < 5; gi = gi + 1) begin : pol
            score_link #(.POLICY(gi)) u0 (.record(rec0), .score(sc[gi][0]));
            score_link #(.POLICY(gi)) u1 (.record(rec1), .score(sc[gi][1]));
            score_link #(.POLICY(gi)) u2 (.record(rec2), .score(sc[gi][2]));
            scheduler_tree u_tree (
                .v0(1'b1), .v1(1'b1), .v2(1'b1), .v3(1'b0),
                .s0(sc[gi][0]), .s1(sc[gi][1]), .s2(sc[gi][2]), .s3(48'd0),
                .grant_valid(gvalid[gi]),
                .grant_idx(gidx[gi]),
                .grant_score(gscore[gi])
            );
        end
    endgenerate

    initial clk = 0;
    always #5 clk = ~clk;

    task fail;
        input [255:0] msg;
        begin
            errors = errors + 1;
            $display("FAIL %0s", msg);
        end
    endtask

    initial begin
        errors = 0;
        rec0 = 0;
        rec1 = 0;
        rec2 = 0;
        $dumpfile("/home/haiminh/d2d_for_tile/RTL_design/tb_policies.vcd");
        $dumpvars(0, tb_policies);
        repeat (2) @(posedge clk);

        rec0 = rec_of(8'd3, 16'd0, 1'b0, 32'd88,  5'd16, 8'd1);
        rec1 = rec_of(8'd1, 16'd1, 1'b1, 32'd40,  5'd16, 8'd1);
        rec2 = rec_of(8'd2, 16'd2, 1'b0, 32'd200, 5'd1,  8'd1);
        #1;

        if (sc[0][0] !== {32'd0, 16'd0})              fail("fcfs score");
        if (sc[1][0] !== {32'd88, 16'd0})             fail("edf score");
        if (sc[2][0] !== {27'd0, 5'd16, 16'd0})       fail("firing score");
        if (sc[3][0] !== {18'd0, 1'b0, ~8'd1, 5'd16, 16'd0}) fail("shared score");
        if (sc[4][0] !== {27'd0, ~5'd16, 16'd0})      fail("row score");

        if (grant_fcfs   !== 8'd0 || !gvalid[0]) fail("fcfs grant");
        if (grant_edf    !== 8'd1 || !gvalid[1]) fail("edf grant");
        if (grant_firing !== 8'd2 || !gvalid[2]) fail("firing grant");
        if (grant_shared !== 8'd2 || !gvalid[3]) fail("shared grant");
        if (grant_row    !== 8'd0 || !gvalid[4]) fail("row grant");

        $display("grant  fcfs %0d  edf %0d  firing %0d  shared %0d  row %0d",
                 grant_fcfs, grant_edf, grant_firing, grant_shared, grant_row);
        $display("score0 fcfs %h  edf %h  firing %h  shared %h  row %h",
                 score_fcfs, score_edf, score_firing, score_shared, score_row);
        if (errors == 0)
            $display("PASS");
        else
            $display("FAIL  errors %0d", errors);

        repeat (6) @(posedge clk);
        $finish;
    end
endmodule
