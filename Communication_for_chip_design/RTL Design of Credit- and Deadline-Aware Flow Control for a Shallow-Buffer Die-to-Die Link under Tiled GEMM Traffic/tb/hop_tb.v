// Short-seed hop: N_tiles=8. Compare t_last with golden/hop.py.
module hop_tb;
    parameter integer K          = 16;
    parameter integer POLICY_EDF = 1;
    parameter integer N_TILES    = 8;
    parameter integer TIME_W     = 32;
    parameter integer CW         = 8;

    reg clk;
    reg rst;
    wire done;
    wire [TIME_W-1:0] cycle;
    wire [CW-1:0] credit_count;
    wire send_valid;
    wire [7:0] send_tile;
    wire send_is_gemm;
    wire [TIME_W-1:0] stall_cycles;
    wire [TIME_W-1:0] payload_flits;
    wire [TIME_W-1:0] miss_count;
    wire credit_neg;
    wire [N_TILES*TIME_W-1:0] t_last_bus;

    hop_top #(
        .K(K),
        .POLICY_EDF(POLICY_EDF),
        .N_TILES(N_TILES),
        .READY_SLOTS(256)
    ) dut (
        .clk(clk),
        .rst(rst),
        .done(done),
        .cycle(cycle),
        .credit_count(credit_count),
        .send_valid(send_valid),
        .send_tile(send_tile),
        .send_is_gemm(send_is_gemm),
        .stall_cycles(stall_cycles),
        .payload_flits(payload_flits),
        .miss_count(miss_count),
        .credit_neg(credit_neg),
        .t_last_bus(t_last_bus)
    );

    integer f, k;
    integer send_count, gemm_send, bulk_head_edf_pick;
    reg saw_bulk_at_head_fcfs_style;

    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        send_count = 0;
        gemm_send = 0;
        bulk_head_edf_pick = 0;
        rst = 1;
        repeat (4) @(posedge clk);
        rst = 0;
        while (!done) begin
            @(posedge clk);
            if (send_valid) begin
                send_count = send_count + 1;
                if (send_is_gemm)
                    gemm_send = gemm_send + 1;
            end
            if (credit_neg) begin
                $display("FAIL credit negative");
                $finish;
            end
            if (cycle > 200000) begin
                $display("FAIL timeout");
                $finish;
            end
        end
        @(posedge clk);
        f = $fopen("rtl_tlast.csv", "w");
        $fwrite(f, "tile,t_last\n");
        for (k = 0; k < N_TILES; k = k + 1)
            $fwrite(f, "%0d,%0d\n", k, t_last_bus[k*TIME_W +: TIME_W]);
        $fclose(f);
        $display("PASS policy=%0d K=%0d cycles=%0d miss=%0d stall=%0d payload=%0d gemm_send=%0d",
                 POLICY_EDF, K, cycle, miss_count, stall_cycles, payload_flits, gemm_send);
        $finish;
    end
endmodule
