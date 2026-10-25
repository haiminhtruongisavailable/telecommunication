`timescale 1ns/1ps

// The five packings. The first priority is the high field. The compare
// elsewhere sees one 48-bit word.
module tb_scores;
    reg [335:0] rec;
    wire [47:0] fcfs, edf, firing, shared, row;
    wire [47:0] link0, link1, link2, link3, link4;
    integer errors;

    score_fcfs   u_fcfs   (.record(rec), .score(fcfs));
    score_edf    u_edf    (.record(rec), .score(edf));
    score_firing u_firing (.record(rec), .score(firing));
    score_shared u_shared (.record(rec), .score(shared));
    score_row    u_row    (.record(rec), .score(row));
    score_link #(.POLICY(0)) u0 (.record(rec), .score(link0));
    score_link #(.POLICY(1)) u1 (.record(rec), .score(link1));
    score_link #(.POLICY(2)) u2 (.record(rec), .score(link2));
    score_link #(.POLICY(3)) u3 (.record(rec), .score(link3));
    score_link #(.POLICY(4)) u4 (.record(rec), .score(link4));

    function [335:0] rec_of;
        input [15:0] seq;
        input [31:0] deadline;
        input        panel;
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
            rec_of[263:256] = 8'd3;
        end
    endfunction

    task fail;
        input [255:0] msg;
        begin
            errors = errors + 1;
            $display("FAIL %0s  fcfs %h edf %h firing %h shared %h row %h",
                     msg, fcfs, edf, firing, shared, row);
        end
    endtask

    initial begin
        errors = 0;

        // Tile 3, seq 0, panel A, deadline 88, 16 flits, one consumer.
        rec = rec_of(16'd0, 32'd88, 1'b0, 5'd16, 8'd1);
        #1;
        if (fcfs   !== {32'd0, 16'd0})                         fail("fcfs pack");
        if (edf    !== {32'd88, 16'd0})                        fail("edf pack");
        if (firing !== {27'd0, 5'd16, 16'd0})                  fail("firing pack");
        if (shared !== {18'd0, 1'b0, ~8'd1, 5'd16, 16'd0})     fail("shared pack");
        if (row    !== {27'd0, ~5'd16, 16'd0})                 fail("row pack");
        if (link0 !== fcfs || link1 !== edf || link2 !== firing ||
            link3 !== shared || link4 !== row)
            fail("score_link");
        else if (errors == 0)
            $display("PASS pack  tile3 seq0 deadline88 flits16");

        // Same first field, larger seq. The low field decides.
        begin : seq_order
            reg [47:0] edf_lo, edf_hi;
            rec   = rec_of(16'd1, 32'd88, 1'b0, 5'd4, 8'd1);
            #1;
            edf_lo = edf;
            rec   = rec_of(16'd9, 32'd88, 1'b0, 5'd4, 8'd1);
            #1;
            edf_hi = edf;
            if (!(edf_lo < edf_hi))
                fail("edf seq");
            else
                $display("PASS edf same deadline, smaller seq wins");
        end

        // Smaller deadline, larger seq. The high field decides.
        begin : dl_order
            reg [47:0] early, late;
            rec = rec_of(16'd100, 32'd10, 1'b0, 5'd16, 8'd1);
            #1;
            early = edf;
            if (early !== {32'd10, 16'd100})
                fail("edf high field");
            rec = rec_of(16'd0, 32'd11, 1'b0, 5'd16, 8'd1);
            #1;
            late = edf;
            if (!(early < late))
                fail("edf deadline over seq");
            else
                $display("PASS edf smaller deadline beats larger seq");
        end

        // Firing. Fewer flits_left beats a smaller seq.
        begin : fire_order
            reg [47:0] few, many;
            rec = rec_of(16'd50, 32'd1, 1'b0, 5'd1, 8'd1);
            #1;
            few = firing;
            if (few !== {27'd0, 5'd1, 16'd50})
                fail("firing high field");
            rec = rec_of(16'd0, 32'd1, 1'b0, 5'd16, 8'd1);
            #1;
            many = firing;
            if (!(few < many))
                fail("firing flits over seq");
            else
                $display("PASS firing fewer flits beats smaller seq");
        end

        // Shared. Panel A beats panel B before consumers matter.
        begin : panel_order
            reg [47:0] panel_a, panel_b;
            rec = rec_of(16'd9, 32'd1, 1'b0, 5'd16, 8'd1);
            #1;
            panel_a = shared;
            rec = rec_of(16'd0, 32'd1, 1'b1, 5'd1, 8'd255);
            #1;
            panel_b = shared;
            if (!(panel_a < panel_b))
                fail("shared panel");
            else
                $display("PASS shared panel A beats panel B");
        end

        // Row. More flits still left beats a smaller seq.
        begin : row_order
            reg [47:0] more, less;
            rec = rec_of(16'd9, 32'd1, 1'b0, 5'd16, 8'd1);
            #1;
            more = row;
            if (more !== {27'd0, ~5'd16, 16'd9})
                fail("row high field");
            rec = rec_of(16'd0, 32'd1, 1'b0, 5'd1, 8'd1);
            #1;
            less = row;
            if (!(more < less))
                fail("row flits over seq");
            else
                $display("PASS row more flits beats smaller seq");
        end

        // FCFS ignores the deadline.
        begin : fcfs_order
            reg [47:0] older, newer;
            rec = rec_of(16'd0, 32'hFFFF_FFFF, 1'b1, 5'd1, 8'd1);
            #1;
            older = fcfs;
            rec = rec_of(16'd1, 32'd0, 1'b0, 5'd16, 8'd255);
            #1;
            newer = fcfs;
            if (older !== {32'd0, 16'd0} || !(older < newer))
                fail("fcfs seq only");
            else
                $display("PASS fcfs seq only");
        end

        if (errors == 0)
            $display("PASS");
        else
            $display("FAIL  errors %0d", errors);
        $finish;
    end
endmodule
