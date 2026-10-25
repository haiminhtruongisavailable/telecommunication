`timescale 1ns/1ps

module tb_hop_path;
    reg         clk;
    reg         rst;
    reg         a_pv, b_pv;
    reg  [7:0]  a_pb, b_pb;
    reg  [7:0]  a_tid, b_tid;
    reg         a_psel, b_psel;
    reg         a_ov, b_ov;
    reg  [255:0] a_of, b_of;
    reg  [31:0] a_od, b_od;

    wire        a_rel, a_let, a_pass, a_sq, a_done, a_ovld, a_gemm, a_opsel, a_bvld, a_bpanel;
    wire [7:0]  a_cred, a_otile, a_bout, a_btile;
    wire [255:0] a_oflit;
    wire        b_rel, b_let, b_pass, b_sq, b_done, b_ovld, b_gemm, b_opsel, b_bvld, b_bpanel;
    wire [7:0]  b_cred, b_otile, b_bout, b_btile;
    wire [255:0] b_oflit;

    integer errors;
    integer a_bytes, a_flits, a_sq_n, a_pack_n;
    integer b_pass_n, b_sq_n;
    integer b_hold_seen;
    integer b_pass_at, b_return_at;
    integer saw_edf;
    integer cyc;
    integer bi;
    reg [7:0] exp_b;
    reg       gemm_tag;
    integer   gemm_left;

    hop_path #(.POLICY(1), .K(16), .N_TILES(1), .W_LEN(1), .ADMIT_LIMIT(1)) u_a (
        .clk(clk), .rst(rst),
        .panel_valid(a_pv), .panel_byte(a_pb), .tile_id(a_tid), .panel_sel(a_psel),
        .other_valid(a_ov), .other_flit(a_of), .other_deadline(a_od),
        .release_en(a_rel), .let_square(a_let), .pass_en(a_pass), .credit_count(a_cred),
        .square_finished(a_sq), .done(a_done),
        .out_valid(a_ovld), .out_is_gemm(a_gemm), .out_flit(a_oflit),
        .out_tile(a_otile), .out_panel_sel(a_opsel),
        .byte_valid(a_bvld), .byte_out(a_bout), .byte_tile(a_btile), .byte_panel(a_bpanel)
    );

    hop_path #(.POLICY(1), .K(1), .N_TILES(1), .W_LEN(1), .ADMIT_LIMIT(1)) u_b (
        .clk(clk), .rst(rst),
        .panel_valid(b_pv), .panel_byte(b_pb), .tile_id(b_tid), .panel_sel(b_psel),
        .other_valid(b_ov), .other_flit(b_of), .other_deadline(b_od),
        .release_en(b_rel), .let_square(b_let), .pass_en(b_pass), .credit_count(b_cred),
        .square_finished(b_sq), .done(b_done),
        .out_valid(b_ovld), .out_is_gemm(b_gemm), .out_flit(b_oflit),
        .out_tile(b_otile), .out_panel_sel(b_opsel),
        .byte_valid(b_bvld), .byte_out(b_bout), .byte_tile(b_btile), .byte_panel(b_bpanel)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task fail;
        input [255:0] msg;
        begin
            errors = errors + 1;
            $display("FAIL cyc %0d  %0s", cyc, msg);
        end
    endtask

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (!rst && a_pass && (a_cred == 0))
            fail("A sent with zero credit");
        if (!rst && b_pass && (b_cred == 0))
            fail("B sent with zero credit");
        if (!rst && a_sq)
            a_sq_n <= a_sq_n + 1;
        if (!rst && b_sq)
            b_sq_n <= b_sq_n + 1;
        if (!rst && b_pass) begin
            if (b_pass_n == 0)
                b_pass_at <= cyc;
            b_pass_n <= b_pass_n + 1;
        end
        if (!rst && u_b.u_credit.credit_return && b_return_at == 0)
            b_return_at <= cyc;
        if (!rst && a_pass && u_a.u_ready.record[280:265] == 16'd0
                && u_a.u_ready.record[263:256] == 8'd3) begin
            saw_edf <= 1;
            if (u_a.u_score.score !== {32'd88, 16'd0})
                fail("EDF score is not deadline then seq");
        end
        if (!rst && u_a.u_release.admitted > 8'd1)
            fail("admitted above the cap");
        if (!rst && u_a.u_packer.pack_done) begin
            a_pack_n <= a_pack_n + 1;
            if (u_a.u_release.admitted != 8'd1)
                fail("pack_done changed the admitted count");
        end
        if (!rst && a_ovld && a_gemm)
            a_flits <= a_flits + 1;
        if (!rst && a_bvld && gemm_tag) begin
            exp_b = a_bytes[7:0];
            if (a_bout !== exp_b)
                fail("payload byte");
            if (a_btile !== 8'd3)
                fail("byte tile");
            if (a_bpanel !== (a_bytes >= 256))
                fail("byte panel");
            a_bytes <= a_bytes + 1;
            if (gemm_left == 1)
                gemm_tag <= 0;
            gemm_left <= gemm_left - 1;
        end
        if (!rst && a_ovld) begin
            gemm_tag  <= a_gemm;
            gemm_left <= 32;
        end
    end

    initial begin
        errors = 0;
        cyc = 0;
        a_bytes = 0;
        a_flits = 0;
        a_sq_n = 0;
        a_pack_n = 0;
        b_pass_n = 0;
        b_sq_n = 0;
        b_hold_seen = 0;
        b_pass_at = 0;
        b_return_at = 0;
        saw_edf = 0;
        gemm_tag = 0;
        gemm_left = 0;
        rst = 1;
        a_pv = 0; b_pv = 0;
        a_pb = 0; b_pb = 0;
        a_tid = 8'd3; b_tid = 8'd3;
        a_psel = 0; b_psel = 0;
        a_ov = 0; b_ov = 0;
        a_of = 0; b_of = 0;
        a_od = 0; b_od = 32'd1000;
        repeat (4) @(posedge clk);
        rst = 0;
        @(posedge clk);

        // K = 1. The second other-stack flit must wait out a zero credit.
        b_of = {32{8'hA5}};
        b_ov = 1;
        @(posedge clk);
        b_ov = 0;
        repeat (4) @(posedge clk);
        if (b_pass_n < 1)
            fail("first other flit was not sent");
        @(posedge clk);
        b_of = {32{8'h5A}};
        b_ov = 1;
        @(posedge clk);
        b_ov = 0;
        repeat (6) begin
            @(posedge clk);
            if (b_cred == 0 && u_b.fresh && !b_pass)
                b_hold_seen = 1;
            if (b_pass && b_cred == 0)
                fail("second flit left with an empty credit");
        end
        if (!b_hold_seen)
            fail("a flit with a winner did not wait for credit");
        if (b_sq_n !== 0)
            fail("other-stack consume finished a square");
        if (b_return_at - b_pass_at != 8)
            fail("credit did not return 8 cycles after the send");

        // Tile 3, 512 bytes, on the K = 16 hop. Lane is already open.
        if (a_let !== 1)
            fail("byte lane did not open");
        for (bi = 0; bi < 512; bi = bi + 1) begin
            a_pv   = 1;
            a_pb   = bi[7:0];
            a_psel = (bi >= 256);
            @(posedge clk);
        end
        a_pv = 0;

        repeat (80) @(posedge clk);
        if (a_pack_n !== 1)
            fail("tile did not pack once");
        if (a_sq_n !== 1)
            fail("square_finished count");
        if (a_flits !== 16)
            fail("PHY flit count");
        if (a_bytes !== 512)
            fail("unpacked byte count");
        if (a_done !== 1)
            fail("CU did not finish");
        if (u_a.u_release.admitted !== 0)
            fail("admitted did not return to zero");
        if (a_sq_n !== 1)
            fail("extra square_finished");
        // First GEMM score is the deadline of tile 3, then seq 0.
        // Checked while that flit was the one in the slot: seq field of record.
        if (!saw_edf)
            fail("EDF score was not checked on the first flit");
        if (u_a.u_ready.record[312:281] !== 32'd88)
            fail("deadline was not 16*tile+40");

        $display("pack %0d  square %0d  phy %0d  bytes %0d  hold %0d  credit_gap %0d  errors %0d",
                 a_pack_n, a_sq_n, a_flits, a_bytes, b_hold_seen, b_return_at - b_pass_at, errors);
        if (errors == 0)
            $display("PASS");
        else
            $display("FAIL");
        $finish;
    end

    initial begin
        #200000;
        $display("TIMEOUT");
        $finish;
    end
endmodule
