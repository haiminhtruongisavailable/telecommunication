// One bidirectional D2D hop. Two checks: credit > 0, then min D_k (EDF) or seq (FCFS).
// PHY delay box copies golden hop.py wire (FIFO of dated events). hop_top is the adapter assembly.
module hop_top #(
    parameter integer K               = 16,
    parameter integer D_PHY           = 4,
    parameter integer N_TILES         = 8,
    parameter integer C_TILE          = 16,
    parameter integer EXTRA           = 40,
    parameter integer FLITS_PER_TILE  = 16,
    parameter integer BULK_EVERY      = 2,
    parameter integer POLICY_EDF      = 1,
    parameter integer READY_SLOTS     = 256,
    parameter integer CW              = 8,
    parameter integer SEQ_W           = 16,
    parameter integer DL_W            = 32,
    parameter integer TILE_W          = 8,
    parameter integer IDX_W           = 8,
    parameter integer TIME_W          = 32,
    parameter integer WIRE_N          = 512
) (
    input  wire                      clk,
    input  wire                      rst,
    output wire                      done,
    output wire [TIME_W-1:0]         cycle,
    output wire [CW-1:0]             credit_count,
    output wire                      send_valid,
    output wire [TILE_W-1:0]         send_tile,
    output wire                      send_is_gemm,
    output wire [TIME_W-1:0]         stall_cycles,
    output wire [TIME_W-1:0]         payload_flits,
    output wire [TIME_W-1:0]         miss_count,
    output wire                      credit_neg,
    output wire [N_TILES*TIME_W-1:0] t_last_bus
);

    integer i, s, nwr, krel, miss_i, taken;

    reg [TIME_W-1:0] t;
    reg [SEQ_W-1:0]  seq;
    reg [TILE_W-1:0] next_tile;
    reg [TIME_W-1:0] stall_r;
    reg [TIME_W-1:0] payload_r;
    reg [TIME_W-1:0] t_last [0:N_TILES-1];
    reg [15:0]       remaining [0:N_TILES-1];
    reg [TILE_W:0]   done_n;
    reg              credit_neg_r;

    reg [READY_SLOTS-1:0] r_valid;
    reg [DL_W-1:0]        r_dl   [0:READY_SLOTS-1];
    reg [SEQ_W-1:0]       r_seq  [0:READY_SLOTS-1];
    reg [TILE_W-1:0]      r_tid  [0:READY_SLOTS-1];
    reg                   r_gemm [0:READY_SLOTS-1];

    // Combinational inject overlay so newly released flits can send this cycle (golden hop.py).
    reg [READY_SLOTS-1:0] v_vis;
    reg [DL_W-1:0]        d_vis  [0:READY_SLOTS-1];
    reg [SEQ_W-1:0]       s_vis  [0:READY_SLOTS-1];
    reg [TILE_W-1:0]      t_vis  [0:READY_SLOTS-1];
    reg                   g_vis  [0:READY_SLOTS-1];
    integer               seq_comb;
    integer               nt_comb;

    wire [DL_W*READY_SLOTS-1:0]  dl_bus;
    wire [SEQ_W*READY_SLOTS-1:0] seq_bus;
    wire                  g_valid;
    wire [IDX_W-1:0]      g_idx;

    genvar gi;
    generate
        for (gi = 0; gi < READY_SLOTS; gi = gi + 1) begin : pack_buses
            assign dl_bus [gi*DL_W  +: DL_W]  = d_vis[gi];
            assign seq_bus[gi*SEQ_W +: SEQ_W] = s_vis[gi];
        end
        for (gi = 0; gi < N_TILES; gi = gi + 1) begin : tlast_pack
            assign t_last_bus[gi*TIME_W +: TIME_W] = t_last[gi];
        end
    endgenerate

    scheduler_edf #(
        .SLOTS(READY_SLOTS), .SEQ_W(SEQ_W), .DL_W(DL_W), .IDX_W(IDX_W)
    ) u_sched (
        .policy_edf(POLICY_EDF[0]),
        .valid(v_vis),
        .deadline(dl_bus),
        .seq(seq_bus),
        .grant_valid(g_valid),
        .grant_idx(g_idx)
    );

    // Event FIFO copies golden/hop.py wire (not two independent pipes).
    // A credit at the head with a later timestamp blocks flits behind it.
    reg [TIME_W-1:0] w_arr    [0:WIRE_N-1];
    reg              w_is_flit[0:WIRE_N-1];
    reg [TILE_W-1:0] w_tid    [0:WIRE_N-1];
    reg              w_gemm   [0:WIRE_N-1];
    integer          w_head;
    integer          w_count;

    integer n_cr_pop;
    integer n_flit_pop;
    integer walk;
    integer idx;
    integer cred_after;
    integer flit_tid_pop [0:15];
    integer flit_g_pop   [0:15];
    integer fi;

    always @(*) begin
        n_cr_pop = 0;
        n_flit_pop = 0;
        walk = w_count;
        idx = w_head;
        for (i = 0; i < WIRE_N; i = i + 1) begin
            if (walk > 0 && w_arr[idx] <= t && !rst) begin
                if (w_is_flit[idx]) begin
                    if (n_flit_pop < 16) begin
                        flit_tid_pop[n_flit_pop] = w_tid[idx];
                        flit_g_pop[n_flit_pop] = w_gemm[idx];
                    end
                    n_flit_pop = n_flit_pop + 1;
                end else begin
                    n_cr_pop = n_cr_pop + 1;
                end
                walk = walk - 1;
                idx = (idx + 1) % WIRE_N;
            end
        end
        cred_after = cred + n_cr_pop;
    end

    wire [CW-1:0] cred;
    wire          can_send_raw;
    wire          do_send;
    wire [CW-1:0] inc_n = n_cr_pop[CW-1:0];
    wire          flit_arriving = (n_flit_pop != 0);

    credit #(.K(K), .CW(CW)) u_credit (
        .clk(clk), .rst(rst),
        .inc_n(inc_n),
        .dec(do_send),
        .count(cred),
        .can_send(can_send_raw)
    );

    fifo_k #(.K(K), .CW(CW)) u_fifo (
        .clk(clk), .rst(rst),
        .push(do_send),
        .pop(flit_arriving),
        .occ(), .full(), .empty()
    );

    packer #(
        .FLITS_PER_TILE(FLITS_PER_TILE), .C_TILE(C_TILE), .EXTRA(EXTRA),
        .TILE_W(TILE_W), .DL_W(DL_W)
    ) u_packer (
        .tile_id(next_tile),
        .fire(1'b1),
        .do_pack(),
        .deadline(),
        .tile_out(),
        .n_flits()
    );

    assign do_send = !rst && !done && (cred_after > 0) && g_valid;

    assign send_valid    = do_send;
    assign send_tile     = do_send ? t_vis[g_idx] : {TILE_W{1'b0}};
    assign send_is_gemm  = do_send ? g_vis[g_idx] : 1'b0;
    assign cycle         = t;
    assign credit_count  = cred;
    assign stall_cycles  = stall_r;
    assign payload_flits = payload_r;
    assign credit_neg    = credit_neg_r;
    assign done          = (done_n == N_TILES[TILE_W:0]);

    function [DL_W-1:0] tile_deadline;
        input integer kk;
        begin
            tile_deadline = kk * C_TILE + EXTRA;
        end
    endfunction

    always @(*) begin
        v_vis = r_valid;
        for (s = 0; s < READY_SLOTS; s = s + 1) begin
            d_vis[s] = r_dl[s];
            s_vis[s] = r_seq[s];
            t_vis[s] = r_tid[s];
            g_vis[s] = r_gemm[s];
        end
        seq_comb = seq;
        nt_comb  = next_tile;
        if (!rst && !done) begin
            for (krel = 0; krel < N_TILES; krel = krel + 1) begin
                if (nt_comb == krel) begin
                    if ((krel == 0) || (((krel - 1) * C_TILE) <= t)) begin
                        nwr = 0;
                        for (s = 0; s < READY_SLOTS; s = s + 1) begin
                            if (!v_vis[s] && nwr < FLITS_PER_TILE) begin
                                v_vis[s] = 1'b1;
                                d_vis[s] = tile_deadline(krel);
                                s_vis[s] = seq_comb[SEQ_W-1:0];
                                t_vis[s] = krel[TILE_W-1:0];
                                g_vis[s] = 1'b1;
                                seq_comb = seq_comb + 1;
                                nwr      = nwr + 1;
                            end
                        end
                        nt_comb = nt_comb + 1;
                    end
                end
            end
            if ((BULK_EVERY != 0) && (t > 0) && ((t % BULK_EVERY) == 0)) begin
                taken = 0;
                for (s = 0; s < READY_SLOTS; s = s + 1) begin
                    if (!v_vis[s] && taken == 0) begin
                        v_vis[s] = 1'b1;
                        d_vis[s] = 32'd1000000000;
                        s_vis[s] = seq_comb[SEQ_W-1:0];
                        t_vis[s] = {TILE_W{1'b0}};
                        g_vis[s] = 1'b0;
                        seq_comb = seq_comb + 1;
                        taken    = 1;
                    end
                end
            end
        end
    end

    reg [TIME_W-1:0] miss_r;
    always @(*) begin
        miss_r = 0;
        for (miss_i = 0; miss_i < N_TILES; miss_i = miss_i + 1) begin
            if (remaining[miss_i] != 0)
                miss_r = miss_r + 1;
            else if (t_last[miss_i] > (miss_i * C_TILE + EXTRA))
                miss_r = miss_r + 1;
        end
    end
    assign miss_count = miss_r;

    integer rem_tmp [0:N_TILES-1];
    integer payload_tmp;
    integer done_tmp;
    integer npop;
    integer tail;
    integer tidp;

    always @(posedge clk) begin
        if (rst) begin
            t <= 0;
            seq <= 0;
            next_tile <= 0;
            stall_r <= 0;
            payload_r <= 0;
            done_n <= 0;
            credit_neg_r <= 1'b0;
            r_valid <= {READY_SLOTS{1'b0}};
            w_head <= 0;
            w_count <= 0;
            for (i = 0; i < N_TILES; i = i + 1) begin
                remaining[i] <= FLITS_PER_TILE[15:0];
                t_last[i] <= 0;
            end
        end else if (!done) begin
            seq <= seq_comb[SEQ_W-1:0];
            next_tile <= nt_comb[TILE_W-1:0];

            for (s = 0; s < READY_SLOTS; s = s + 1) begin
                r_valid[s] <= v_vis[s];
                r_dl[s]    <= d_vis[s];
                r_seq[s]   <= s_vis[s];
                r_tid[s]   <= t_vis[s];
                r_gemm[s]  <= g_vis[s];
            end
            if (do_send)
                r_valid[g_idx] <= 1'b0;

            for (i = 0; i < N_TILES; i = i + 1)
                rem_tmp[i] = remaining[i];
            payload_tmp = payload_r;
            done_tmp = done_n;
            for (fi = 0; fi < 16; fi = fi + 1) begin
                if (fi < n_flit_pop) begin
                    payload_tmp = payload_tmp + 1;
                    if (flit_g_pop[fi]) begin
                        tidp = flit_tid_pop[fi];
                        rem_tmp[tidp] = rem_tmp[tidp] - 1;
                        if (rem_tmp[tidp] == 0) begin
                            t_last[tidp] <= t;
                            done_tmp = done_tmp + 1;
                        end
                    end
                end
            end
            for (i = 0; i < N_TILES; i = i + 1)
                remaining[i] <= rem_tmp[i][15:0];
            payload_r <= payload_tmp[TIME_W-1:0];
            done_n <= done_tmp[TILE_W:0];

            npop = n_cr_pop + n_flit_pop;
            tail = (w_head + w_count) % WIRE_N;
            if (do_send) begin
                w_arr[tail]     <= t + D_PHY;
                w_is_flit[tail] <= 1'b1;
                w_tid[tail]     <= t_vis[g_idx];
                w_gemm[tail]    <= g_vis[g_idx];
                w_arr[(tail + 1) % WIRE_N]     <= t + (2 * D_PHY);
                w_is_flit[(tail + 1) % WIRE_N] <= 1'b0;
                w_tid[(tail + 1) % WIRE_N]     <= 0;
                w_gemm[(tail + 1) % WIRE_N]    <= 1'b0;
                w_head  <= (w_head + npop) % WIRE_N;
                w_count <= w_count - npop + 2;
                if (cred_after <= 0)
                    credit_neg_r <= 1'b1;
            end else begin
                w_head  <= (w_head + npop) % WIRE_N;
                w_count <= w_count - npop;
                stall_r <= stall_r + 1;
            end

            t <= t + 1;
        end
    end
endmodule
