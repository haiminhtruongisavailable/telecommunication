`timescale 1ns/1ps

// Cases 1-19 drive the real score_pair and scheduler_tree.
// Cases 20-22 drive a one-line copy of that logic, so this file can fail
// without editing cells.v or scheduler_tree.v.

module cmp_le #(
    parameter integer WIDTH = 48
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire             y
);
    assign y = (a <= b);
endmodule

module score_pair_le #(
    parameter integer WIDTH = 48
) (
    input  wire             va,
    input  wire             vb,
    input  wire [WIDTH-1:0] sa,
    input  wire [WIDTH-1:0] sb,
    input  wire [7:0]       ia,
    input  wire [7:0]       ib,
    output wire             vy,
    output wire [WIDTH-1:0] sy,
    output wire [7:0]       iy
);
    wire b_smaller, a_out, take_b_raw, take_b;
    cmp_le #(.WIDTH(WIDTH)) u_lt (.a(sb), .b(sa), .y(b_smaller));
    not1 u_no_a (.a(va), .y(a_out));
    or2  u_or  (.a(a_out), .b(b_smaller), .y(take_b_raw));
    and2 u_and (.a(vb), .b(take_b_raw), .y(take_b));
    or2  u_any (.a(va), .b(vb), .y(vy));
    mux2 #(.WIDTH(WIDTH)) u_score (.sel(take_b), .on1(sb), .on0(sa), .y(sy));
    mux2 #(.WIDTH(8))     u_idx   (.sel(take_b), .on1(ib), .on0(ia), .y(iy));
endmodule

module score_pair_novalid #(
    parameter integer WIDTH = 48
) (
    input  wire             va,
    input  wire             vb,
    input  wire [WIDTH-1:0] sa,
    input  wire [WIDTH-1:0] sb,
    input  wire [7:0]       ia,
    input  wire [7:0]       ib,
    output wire             vy,
    output wire [WIDTH-1:0] sy,
    output wire [7:0]       iy
);
    wire b_smaller, a_out, take_b_raw, take_b;
    cmp_lt #(.WIDTH(WIDTH)) u_lt (.a(sb), .b(sa), .y(b_smaller));
    not1 u_no_a (.a(va), .y(a_out));
    or2  u_or  (.a(1'b0), .b(b_smaller), .y(take_b_raw));
    and2 u_and (.a(vb), .b(take_b_raw), .y(take_b));
    or2  u_any (.a(va), .b(vb), .y(vy));
    mux2 #(.WIDTH(WIDTH)) u_score (.sel(take_b), .on1(sb), .on0(sa), .y(sy));
    mux2 #(.WIDTH(8))     u_idx   (.sel(take_b), .on1(ib), .on0(ia), .y(iy));
endmodule

module scheduler_tree_le #(
    parameter integer WIDTH = 48
) (
    input  wire             v0, v1, v2, v3,
    input  wire [WIDTH-1:0] s0, s1, s2, s3,
    output wire             grant_valid,
    output wire [7:0]       grant_idx,
    output wire [WIDTH-1:0] grant_score
);
    wire             v01, v23;
    wire [WIDTH-1:0] s01, s23;
    wire [7:0]       i01, i23;
    score_pair_le #(.WIDTH(WIDTH)) u_left (
        .va(v0), .vb(v1), .sa(s0), .sb(s1), .ia(8'd0), .ib(8'd1),
        .vy(v01), .sy(s01), .iy(i01)
    );
    score_pair_le #(.WIDTH(WIDTH)) u_right (
        .va(v2), .vb(v3), .sa(s2), .sb(s3), .ia(8'd2), .ib(8'd3),
        .vy(v23), .sy(s23), .iy(i23)
    );
    score_pair_le #(.WIDTH(WIDTH)) u_root (
        .va(v01), .vb(v23), .sa(s01), .sb(s23), .ia(i01), .ib(i23),
        .vy(grant_valid), .sy(grant_score), .iy(grant_idx)
    );
endmodule

module scheduler_tree_novalid #(
    parameter integer WIDTH = 48
) (
    input  wire             v0, v1, v2, v3,
    input  wire [WIDTH-1:0] s0, s1, s2, s3,
    output wire             grant_valid,
    output wire [7:0]       grant_idx,
    output wire [WIDTH-1:0] grant_score
);
    wire             v01, v23;
    wire [WIDTH-1:0] s01, s23;
    wire [7:0]       i01, i23;
    score_pair_novalid #(.WIDTH(WIDTH)) u_left (
        .va(v0), .vb(v1), .sa(s0), .sb(s1), .ia(8'd0), .ib(8'd1),
        .vy(v01), .sy(s01), .iy(i01)
    );
    score_pair_novalid #(.WIDTH(WIDTH)) u_right (
        .va(v2), .vb(v3), .sa(s2), .sb(s3), .ia(8'd2), .ib(8'd3),
        .vy(v23), .sy(s23), .iy(i23)
    );
    score_pair_novalid #(.WIDTH(WIDTH)) u_root (
        .va(v01), .vb(v23), .sa(s01), .sb(s23), .ia(i01), .ib(i23),
        .vy(grant_valid), .sy(grant_score), .iy(grant_idx)
    );
endmodule

module scheduler_tree_swap #(
    parameter integer WIDTH = 48
) (
    input  wire             v0, v1, v2, v3,
    input  wire [WIDTH-1:0] s0, s1, s2, s3,
    output wire             grant_valid,
    output wire [7:0]       grant_idx,
    output wire [WIDTH-1:0] grant_score
);
    wire             v01, v23;
    wire [WIDTH-1:0] s01, s23;
    wire [7:0]       i01, i23;
    score_pair #(.WIDTH(WIDTH)) u_left (
        .va(v0), .vb(v1), .sa(s0), .sb(s1), .ia(8'd1), .ib(8'd0),
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

module tb_cases;
    reg         va, vb;
    reg [47:0]  sa, sb;
    wire        vy;
    wire [47:0] sy;
    wire [7:0]  iy;

    reg         v0, v1, v2, v3;
    reg [47:0]  s0, s1, s2, s3;
    wire        grant_valid;
    wire [7:0]  grant_idx;
    wire [47:0] grant_score;

    wire        le_vy, nv_vy;
    wire [47:0] le_sy, nv_sy;
    wire [7:0]  le_iy, nv_iy;
    wire        le_valid, nv_valid, sw_valid;
    wire [7:0]  le_idx, nv_idx, sw_idx;
    wire [47:0] le_score, nv_score, sw_score;

    integer errors, index_errors, n, seed, k, hits;
    integer mismatches, tie_hits;
    reg [4:0] check_id;
    reg [47:0] rv [0:3];
    reg        vv [0:3];
    reg [47:0] best_s;
    reg [1:0]  best_i;
    reg        any;

    score_pair #(.WIDTH(48)) u_pair (
        .va(va), .vb(vb), .sa(sa), .sb(sb),
        .ia(8'd7), .ib(8'd9),
        .vy(vy), .sy(sy), .iy(iy)
    );

    scheduler_tree #(.WIDTH(48)) u_tree (
        .v0(v0), .v1(v1), .v2(v2), .v3(v3),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3),
        .grant_valid(grant_valid),
        .grant_idx(grant_idx),
        .grant_score(grant_score)
    );

    score_pair_le #(.WIDTH(48)) u_le (
        .va(va), .vb(vb), .sa(sa), .sb(sb),
        .ia(8'd7), .ib(8'd9),
        .vy(le_vy), .sy(le_sy), .iy(le_iy)
    );
    scheduler_tree_le #(.WIDTH(48)) u_tree_le (
        .v0(v0), .v1(v1), .v2(v2), .v3(v3),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3),
        .grant_valid(le_valid), .grant_idx(le_idx), .grant_score(le_score)
    );
    score_pair_novalid #(.WIDTH(48)) u_nv (
        .va(va), .vb(vb), .sa(sa), .sb(sb),
        .ia(8'd7), .ib(8'd9),
        .vy(nv_vy), .sy(nv_sy), .iy(nv_iy)
    );
    scheduler_tree_novalid #(.WIDTH(48)) u_tree_nv (
        .v0(v0), .v1(v1), .v2(v2), .v3(v3),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3),
        .grant_valid(nv_valid), .grant_idx(nv_idx), .grant_score(nv_score)
    );
    scheduler_tree_swap #(.WIDTH(48)) u_swap (
        .v0(v0), .v1(v1), .v2(v2), .v3(v3),
        .s0(s0), .s1(s1), .s2(s2), .s3(s3),
        .grant_valid(sw_valid), .grant_idx(sw_idx), .grant_score(sw_score)
    );

    task fail_pair;
        input [255:0] msg;
        begin
            errors = errors + 1;
            $display("FAIL %0s  vy %b sy %h iy %0d", msg, vy, sy, iy);
        end
    endtask

    task drive_pair;
        input a_v, b_v;
        input [47:0] a_s, b_s;
        begin
            va = a_v; vb = b_v; sa = a_s; sb = b_s;
            #1;
        end
    endtask

    task expect_pair;
        input        exp_vy;
        input [47:0] exp_sy;
        input [7:0]  exp_iy;
        input [255:0] msg;
        begin
            if (vy !== exp_vy || (exp_vy && (sy !== exp_sy || iy !== exp_iy)))
                fail_pair(msg);
            else if (iy === 8'd9 && sy !== sb) begin
                index_errors = index_errors + 1;
                fail_pair(msg);
            end else if (iy === 8'd7 && sy !== sa) begin
                index_errors = index_errors + 1;
                fail_pair(msg);
            end else
                $display("PASS %0s  vy %b iy %0d", msg, vy, iy);
        end
    endtask

    task fail_tree;
        input [255:0] msg;
        begin
            errors = errors + 1;
            $display("FAIL %0s  valid %b idx %0d score %h",
                     msg, grant_valid, grant_idx, grant_score);
        end
    endtask

    task drive_tree;
        input a, b, c, d;
        input [47:0] as, bs, cs, ds;
        begin
            v0 = a; v1 = b; v2 = c; v3 = d;
            s0 = as; s1 = bs; s2 = cs; s3 = ds;
            #10;
        end
    endtask

    task expect_grant;
        input        exp_valid;
        input [7:0]  exp_idx;
        input [47:0] exp_score;
        input [255:0] msg;
        begin
            if (grant_valid !== exp_valid)
                fail_tree(msg);
            else if (exp_valid && (grant_idx !== exp_idx || grant_score !== exp_score))
                fail_tree(msg);
            else
                $display("PASS %0s  valid %b idx %0d", msg, grant_valid, grant_idx);
        end
    endtask

    task check_grant;
        input        exp_valid;
        input [7:0]  exp_idx;
        input [47:0] exp_score;
        input [255:0] msg;
        begin
            if (grant_valid !== exp_valid)
                fail_tree(msg);
            else if (exp_valid && (grant_idx !== exp_idx || grant_score !== exp_score))
                fail_tree(msg);
        end
    endtask

    initial begin
        errors = 0;
        index_errors = 0;
        seed = 32'h5A17_0001;
        check_id = 0;
        va = 0; vb = 0; sa = 0; sb = 0;
        v0 = 0; v1 = 0; v2 = 0; v3 = 0;
        s0 = 0; s1 = 0; s2 = 0; s3 = 0;
        $dumpfile("/home/haiminh/d2d_for_tile/RTL_design/tb_cases.vcd");
        $dumpvars(0, tb_cases);

        check_id = 1;
        drive_pair(0, 0, 48'd1, 48'd2);
        expect_pair(0, 48'd1, 8'd7, "1 both invalid");

        check_id = 2;
        drive_pair(0, 1, 48'd1, 48'd5);
        expect_pair(1, 48'd5, 8'd9, "2 only B, sa smaller");

        check_id = 3;
        drive_pair(1, 0, 48'd5, 48'd1);
        expect_pair(1, 48'd5, 8'd7, "3 only A, sb smaller");

        check_id = 4;
        drive_pair(1, 1, 48'd5, 48'd1);
        expect_pair(1, 48'd1, 8'd9, "4 B smaller");

        check_id = 5;
        drive_pair(1, 1, 48'd1, 48'd5);
        expect_pair(1, 48'd1, 8'd7, "5 A smaller");

        check_id = 6;
        drive_pair(1, 1, 48'd4, 48'd4);
        expect_pair(1, 48'd4, 8'd7, "6 tie keeps A");

        check_id = 7;
        drive_pair(1, 1, 48'd2, 48'd3);
        expect_pair(1, 48'd2, 8'd7, "7 bit 0, A smaller");
        drive_pair(1, 1, 48'd3, 48'd2);
        expect_pair(1, 48'd2, 8'd9, "7 bit 0, B smaller");

        check_id = 8;
        drive_pair(1, 1, 48'h8000_0000_0000, 48'h0000_0000_0000);
        expect_pair(1, 48'h0, 8'd9, "8 bit 47, B smaller");
        drive_pair(1, 1, 48'h0000_0000_0000, 48'h8000_0000_0000);
        expect_pair(1, 48'h0, 8'd7, "8 bit 47, A smaller");

        check_id = 9;
        if (index_errors == 0)
            $display("PASS 9 index follows score");
        else
            $display("FAIL 9 index follows score  errors %0d", index_errors);

        check_id = 10;
        drive_tree(0, 0, 0, 0, 48'd1, 48'd2, 48'd3, 48'd4);
        if (grant_valid !== 1'b0)
            fail_tree("10 none");
        else
            $display("PASS 10 none  valid 0");

        check_id = 11;
        hits = errors;
        for (n = 0; n < 16; n = n + 1) begin
            drive_tree(n[0], n[1], n[2], n[3], 48'd16, 48'd4, 48'd12, 48'd8);
            if (n == 0) begin
                if (grant_valid !== 1'b0)
                    fail_tree("11 mask 0");
                else
                    $display("PASS 11 mask %04b  valid 0", n[3:0]);
            end else if (n[1]) begin
                check_grant(1, 8'd1, 48'd4, "11");
                if (grant_valid === 1'b1 && grant_idx === 8'd1 && grant_score === 48'd4)
                    $display("PASS 11 mask %04b  valid 1 idx 1 score 4", n[3:0]);
            end else if (n[3]) begin
                check_grant(1, 8'd3, 48'd8, "11");
                if (grant_valid === 1'b1 && grant_idx === 8'd3 && grant_score === 48'd8)
                    $display("PASS 11 mask %04b  valid 1 idx 3 score 8", n[3:0]);
            end else if (n[2]) begin
                check_grant(1, 8'd2, 48'd12, "11");
                if (grant_valid === 1'b1 && grant_idx === 8'd2 && grant_score === 48'd12)
                    $display("PASS 11 mask %04b  valid 1 idx 2 score 12", n[3:0]);
            end else begin
                check_grant(1, 8'd0, 48'd16, "11");
                if (grant_valid === 1'b1 && grant_idx === 8'd0 && grant_score === 48'd16)
                    $display("PASS 11 mask %04b  valid 1 idx 0 score 16", n[3:0]);
            end
        end
        if (errors == hits)
            $display("PASS 11 scores 16 4 12 8");

        check_id = 12;
        drive_tree(0, 0, 1, 0, 48'd1, 48'd2, 48'd99, 48'd3);
        expect_grant(1, 8'd2, 48'd99, "12 only slot 2");

        check_id = 13;
        drive_tree(1, 1, 1, 1, 48'd1, 48'd5, 48'd9, 48'd13);
        expect_grant(1, 8'd0, 48'd1, "13 smallest in 0");
        drive_tree(1, 1, 1, 1, 48'd5, 48'd1, 48'd9, 48'd13);
        expect_grant(1, 8'd1, 48'd1, "13 smallest in 1");
        drive_tree(1, 1, 1, 1, 48'd5, 48'd9, 48'd1, 48'd13);
        expect_grant(1, 8'd2, 48'd1, "13 smallest in 2");
        drive_tree(1, 1, 1, 1, 48'd5, 48'd9, 48'd13, 48'd1);
        expect_grant(1, 8'd3, 48'd1, "13 smallest in 3");

        check_id = 14;
        drive_tree(1, 1, 1, 1, 48'd100, 48'd50, 48'd100, 48'd50);
        expect_grant(1, 8'd1, 48'd50, "14 tie slots 1 and 3");

        check_id = 15;
        drive_tree(1, 1, 1, 1, 48'd5, 48'd5, 48'd9, 48'd9);
        expect_grant(1, 8'd0, 48'd5, "15 tie slots 0 and 1");
        drive_tree(1, 1, 1, 1, 48'd9, 48'd9, 48'd5, 48'd5);
        expect_grant(1, 8'd2, 48'd5, "15 tie slots 2 and 3");

        check_id = 16;
        drive_tree(1, 1, 1, 1, 48'd7, 48'd7, 48'd7, 48'd7);
        expect_grant(1, 8'd0, 48'd7, "16 all equal");

        check_id = 17;
        drive_tree(1, 0, 0, 1, {32'hFFFF_FFFF, 16'd0}, 48'd0, 48'd0, {32'd1, 16'hFFFF});
        expect_grant(1, 8'd3, {32'd1, 16'hFFFF}, "17 wide deadline");

        $dumpoff;
        mismatches = 0;
        check_id = 18;
        for (n = 0; n < 1000; n = n + 1) begin
            vv[0] = $random(seed);
            vv[1] = $random(seed);
            vv[2] = $random(seed);
            vv[3] = $random(seed);
            rv[0] = {$random(seed), $random(seed)};
            rv[1] = {$random(seed), $random(seed)};
            rv[2] = {$random(seed), $random(seed)};
            rv[3] = {$random(seed), $random(seed)};
            drive_tree(vv[0], vv[1], vv[2], vv[3], rv[0], rv[1], rv[2], rv[3]);
            any = 0;
            best_s = 0;
            best_i = 0;
            for (k = 0; k < 4; k = k + 1) begin
                if (vv[k]) begin
                    if (!any || (rv[k] < best_s)) begin
                        any = 1;
                        best_s = rv[k];
                        best_i = k[1:0];
                    end
                end
            end
            if (grant_valid !== any)
                mismatches = mismatches + 1;
            else if (any && (grant_idx !== best_i || grant_score !== best_s))
                mismatches = mismatches + 1;
        end
        if (mismatches != 0) begin
            errors = errors + mismatches;
            $display("FAIL 18 random  mismatches %0d", mismatches);
        end else
            $display("PASS 18 random  1000");

        mismatches = 0;
        tie_hits = 0;
        check_id = 19;
        for (n = 0; n < 1000; n = n + 1) begin
            vv[0] = $random(seed);
            vv[1] = $random(seed);
            vv[2] = $random(seed);
            vv[3] = $random(seed);
            rv[0] = $random(seed) & 3;
            rv[1] = $random(seed) & 3;
            rv[2] = $random(seed) & 3;
            rv[3] = $random(seed) & 3;
            drive_tree(vv[0], vv[1], vv[2], vv[3], rv[0], rv[1], rv[2], rv[3]);
            any = 0;
            best_s = 0;
            best_i = 0;
            for (k = 0; k < 4; k = k + 1) begin
                if (vv[k]) begin
                    if (!any || (rv[k] < best_s)) begin
                        any = 1;
                        best_s = rv[k];
                        best_i = k[1:0];
                    end
                end
            end
            hits = 0;
            for (k = 0; k < 4; k = k + 1)
                if (vv[k] && any && (rv[k] == best_s))
                    hits = hits + 1;
            if (hits > 1)
                tie_hits = tie_hits + 1;
            if (grant_valid !== any)
                mismatches = mismatches + 1;
            else if (any && (grant_idx !== best_i || grant_score !== best_s))
                mismatches = mismatches + 1;
        end
        if (mismatches != 0 || tie_hits < 50) begin
            errors = errors + (mismatches == 0 ? 1 : mismatches);
            $display("FAIL 19 small  mismatches %0d  ties %0d", mismatches, tie_hits);
        end else
            $display("PASS 19 small  1000  ties %0d", tie_hits);

        $dumpon;
        check_id = 20;
        drive_pair(1, 1, 48'd4, 48'd4);
        if (le_vy !== 1'b1 || le_sy !== 48'd4 || le_iy !== 8'd7)
            $display("FAIL 20 tie keeps A  vy %b sy %h iy %0d", le_vy, le_sy, le_iy);
        else
            $display("PASS 20 tie keeps A  vy %b iy %0d", le_vy, le_iy);
        drive_tree(1, 1, 1, 1, 48'd100, 48'd50, 48'd100, 48'd50);
        if (le_valid !== 1'b1 || le_idx !== 8'd1 || le_score !== 48'd50)
            $display("FAIL 20 tie slots 1 and 3  valid %b idx %0d score %h",
                     le_valid, le_idx, le_score);
        else
            $display("PASS 20 tie slots 1 and 3  valid %b idx %0d", le_valid, le_idx);

        check_id = 21;
        drive_pair(0, 1, 48'd1, 48'd5);
        if (nv_vy !== 1'b1 || nv_sy !== 48'd5 || nv_iy !== 8'd9)
            $display("FAIL 21 only B, sa smaller  vy %b sy %h iy %0d", nv_vy, nv_sy, nv_iy);
        else
            $display("PASS 21 only B, sa smaller  vy %b iy %0d", nv_vy, nv_iy);
        drive_tree(0, 0, 1, 0, 48'd1, 48'd2, 48'd99, 48'd3);
        if (nv_valid !== 1'b1 || nv_idx !== 8'd2 || nv_score !== 48'd99)
            $display("FAIL 21 only slot 2  valid %b idx %0d score %h",
                     nv_valid, nv_idx, nv_score);
        else
            $display("PASS 21 only slot 2  valid %b idx %0d", nv_valid, nv_idx);

        check_id = 22;
        drive_tree(1, 1, 1, 1, 48'd1, 48'd5, 48'd9, 48'd13);
        if (sw_valid !== 1'b1 || sw_idx !== 8'd0 || sw_score !== 48'd1)
            $display("FAIL 22 smallest in 0  valid %b idx %0d score %h",
                     sw_valid, sw_idx, sw_score);
        else
            $display("PASS 22 smallest in 0  valid %b idx %0d", sw_valid, sw_idx);
        drive_tree(1, 1, 1, 1, 48'd5, 48'd1, 48'd9, 48'd13);
        if (sw_valid !== 1'b1 || sw_idx !== 8'd1 || sw_score !== 48'd1)
            $display("FAIL 22 smallest in 1  valid %b idx %0d score %h",
                     sw_valid, sw_idx, sw_score);
        else
            $display("PASS 22 smallest in 1  valid %b idx %0d", sw_valid, sw_idx);

        if (errors != 0)
            $display("FAIL  errors %0d", errors);
        $finish;
    end
endmodule
