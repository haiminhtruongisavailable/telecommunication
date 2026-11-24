`default_nettype none
`timescale 1ns/1ps

// One 256-bit flit per edge. The flit is offered the same edge it arrives.
// It stays until gemm_accept. A further flit waits while that word is held.
module packer #(
    parameter integer W_FLIT = 256,
    parameter integer TILE_W = 8,
    parameter integer SEQ_W  = 16,
    parameter integer TRACK_TILE = 0
) (
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    let_square,
    input  wire                    panel_valid,
    input  wire [W_FLIT-1:0]       panel_flit,
    input  wire [TILE_W-1:0]       tile_id,
    input  wire                    panel_sel,
    input  wire [7:0]              wave_id,
    input  wire                    gemm_accept,
    input  wire                    gemm_accept2,
    input  wire [TILE_W-1:0]       tile2_id,
    output wire                    rec_valid,
    output wire [SEQ_W-1:0]        rec_seq,
    output wire [TILE_W-1:0]       rec_tile,
    output wire                    rec_sel,
    output wire [7:0]              rec_wave,
    output wire [W_FLIT-1:0]       rec_payload,
    output wire                    pack_done,
    output wire                    pack_done2
);
    wire                  raw_accept;
    wire                  accept;
    wire                  held;
    wire                  not_held;
    wire                  not_take;
    wire                  hold_d;
    wire [W_FLIT-1:0]     word_q;
    wire [W_FLIT-1:0]     word_keep;
    wire [W_FLIT-1:0]     word_d;
    wire [SEQ_W-1:0]      seq_q;
    wire [SEQ_W-1:0]      seq_inc;
    wire [SEQ_W-1:0]      seq_d;

    and2 u_raw (
        .a (let_square),
        .b (panel_valid),
        .y (raw_accept)
    );
    not1 u_not_held (
        .a (held),
        .y (not_held)
    );
    and2 u_accept (
        .a (raw_accept),
        .b (not_held),
        .y (accept)
    );
    or2 u_fire (
        .a (accept),
        .b (held),
        .y (rec_valid)
    );
    mux2 #(.WIDTH(W_FLIT)) u_payload (
        .sel (held),
        .on1 (word_q),
        .on0 (panel_flit),
        .y   (rec_payload)
    );

    not1 u_not_take (
        .a (gemm_accept),
        .y (not_take)
    );
    and2 u_hold_d (
        .a (rec_valid),
        .b (not_take),
        .y (hold_d)
    );
    dreg #(.WIDTH(1)) u_held (
        .clk (clk),
        .rst (rst),
        .d   (hold_d),
        .q   (held)
    );
    mux2 #(.WIDTH(W_FLIT)) u_word_keep (
        .sel (accept),
        .on1 (panel_flit),
        .on0 (word_q),
        .y   (word_keep)
    );
    mux2 #(.WIDTH(W_FLIT)) u_word_mux (
        .sel (gemm_accept),
        .on1 ({W_FLIT{1'b0}}),
        .on0 (word_keep),
        .y   (word_d)
    );
    dreg #(.WIDTH(W_FLIT)) u_word (
        .clk (clk),
        .rst (rst),
        .d   (word_d),
        .q   (word_q)
    );

    incr #(.WIDTH(SEQ_W)) u_seq_inc (
        .a (seq_q),
        .y (seq_inc)
    );
    mux2 #(.WIDTH(SEQ_W)) u_seq_mux (
        .sel (gemm_accept),
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
    assign rec_seq = seq_q;

    // The offer edge still shows the live tile. A held word keeps the tile
    // captured on that edge, so a later flit cannot rename it.
    wire                  cap_meta;
    wire [TILE_W-1:0]     tile_q;
    wire [TILE_W-1:0]     tile_d;
    wire                  sel_q;
    wire                  sel_d;
    wire [7:0]            wave_q;
    wire [7:0]            wave_d;
    wire [TILE_W-1:0]     tile_out;
    wire                  sel_out;
    wire [7:0]            wave_out;
    and2 u_cap_meta (
        .a (accept),
        .b (not_take),
        .y (cap_meta)
    );
    mux2 #(.WIDTH(TILE_W)) u_tile_d (
        .sel (cap_meta),
        .on1 (tile_id),
        .on0 (tile_q),
        .y   (tile_d)
    );
    dreg #(.WIDTH(TILE_W)) u_tile (
        .clk (clk),
        .rst (rst),
        .d   (tile_d),
        .q   (tile_q)
    );
    mux2 #(.WIDTH(TILE_W)) u_tile_out (
        .sel (held),
        .on1 (tile_q),
        .on0 (tile_id),
        .y   (tile_out)
    );
    mux2 #(.WIDTH(1)) u_sel_d (
        .sel (cap_meta),
        .on1 (panel_sel),
        .on0 (sel_q),
        .y   (sel_d)
    );
    dreg #(.WIDTH(1)) u_sel (
        .clk (clk),
        .rst (rst),
        .d   (sel_d),
        .q   (sel_q)
    );
    mux2 #(.WIDTH(1)) u_sel_out (
        .sel (held),
        .on1 (sel_q),
        .on0 (panel_sel),
        .y   (sel_out)
    );
    mux2 #(.WIDTH(8)) u_wave_d (
        .sel (cap_meta),
        .on1 (wave_id),
        .on0 (wave_q),
        .y   (wave_d)
    );
    dreg #(.WIDTH(8)) u_wave (
        .clk (clk),
        .rst (rst),
        .d   (wave_d),
        .q   (wave_q)
    );
    mux2 #(.WIDTH(8)) u_wave_out (
        .sel (held),
        .on1 (wave_q),
        .on0 (wave_id),
        .y   (wave_out)
    );
    assign rec_tile = tile_out;
    assign rec_sel  = sel_out;
    assign rec_wave = wave_out;

    // Sixteen takes of one square end it. TRACK_TILE counts per tile so a
    // second open square can be offered before the first has 16 flits.
    // The one-tile counter below is the same edges when squares are serial.
    generate
        if (TRACK_TILE == 0) begin : g_serial
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
                .a (gemm_accept),
                .b (last_flit),
                .y (pack_done)
            );
            // The serial counter is one square. A second accept does not end it.
            assign pack_done2 = gemm_accept2 & 1'b0 & tile2_id[0];
            mux2 #(.WIDTH(5)) u_flit_hold (
                .sel (gemm_accept),
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
        end else begin : g_tile
            // Four slots. admit_limit in this sweep is at most 4, and a
            // slot frees on the edge that accepts that tile's 16th flit.
            reg [3:0] sv;
            reg [7:0] st0, st1, st2, st3;
            reg [4:0] sc0, sc1, sc2, sc3;
            reg       hit;
            reg       pack_w;
            reg [1:0] hi;
            reg [4:0] sc_hit;
            reg       pack2;
            always @* begin
                hit = 1'b0;
                pack_w = 1'b0;
                hi = 2'd0;
                sc_hit = 5'd0;
                if (sv[0] && (st0 == tile_out)) begin
                    hit = 1'b1;
                    hi = 2'd0;
                    pack_w = (sc0 == 5'd15);
                    sc_hit = sc0;
                end else if (sv[1] && (st1 == tile_out)) begin
                    hit = 1'b1;
                    hi = 2'd1;
                    pack_w = (sc1 == 5'd15);
                    sc_hit = sc1;
                end else if (sv[2] && (st2 == tile_out)) begin
                    hit = 1'b1;
                    hi = 2'd2;
                    pack_w = (sc2 == 5'd15);
                    sc_hit = sc2;
                end else if (sv[3] && (st3 == tile_out)) begin
                    hit = 1'b1;
                    hi = 2'd3;
                    pack_w = (sc3 == 5'd15);
                    sc_hit = sc3;
                end
                // Second accept of the same tile sees the count after the first.
                // A different tile sees the count stored before this edge.
                if (gemm_accept && (tile2_id == tile_out)) begin
                    if (hit && pack_w)
                        pack2 = 1'b0;
                    else if (hit)
                        pack2 = ((sc_hit + 5'd1) == 5'd15);
                    else
                        pack2 = 1'b0;
                end else if (sv[0] && (st0 == tile2_id))
                    pack2 = (sc0 == 5'd15);
                else if (sv[1] && (st1 == tile2_id))
                    pack2 = (sc1 == 5'd15);
                else if (sv[2] && (st2 == tile2_id))
                    pack2 = (sc2 == 5'd15);
                else if (sv[3] && (st3 == tile2_id))
                    pack2 = (sc3 == 5'd15);
                else
                    pack2 = 1'b0;
            end
            assign pack_done = gemm_accept & hit & pack_w;
            assign pack_done2 = gemm_accept2 & pack2;
            always @(posedge clk) begin
                if (rst) begin
                    sv <= 4'd0;
                    sc0 <= 5'd0;
                    sc1 <= 5'd0;
                    sc2 <= 5'd0;
                    sc3 <= 5'd0;
                end else if (gemm_accept2) begin
                    begin : two_take
                        reg [3:0] svb;
                        reg [7:0] t0, t1, t2, t3;
                        reg [4:0] c0, c1, c2, c3;
                        reg [7:0] tile_now;
                        reg found;
                        reg [1:0] idx;
                        reg [4:0] cnt;
                        integer step;
                        svb = sv;
                        t0 = st0; t1 = st1; t2 = st2; t3 = st3;
                        c0 = sc0; c1 = sc1; c2 = sc2; c3 = sc3;
                        for (step = 0; step < 2; step = step + 1) begin
                            if ((step == 0 && gemm_accept) || (step == 1)) begin
                                tile_now = (step == 0) ? tile_out : tile2_id;
                                found = 1'b0;
                                idx = 2'd0;
                                cnt = 5'd0;
                                if (svb[0] && (t0 == tile_now)) begin
                                    found = 1'b1; idx = 2'd0; cnt = c0;
                                end else if (svb[1] && (t1 == tile_now)) begin
                                    found = 1'b1; idx = 2'd1; cnt = c1;
                                end else if (svb[2] && (t2 == tile_now)) begin
                                    found = 1'b1; idx = 2'd2; cnt = c2;
                                end else if (svb[3] && (t3 == tile_now)) begin
                                    found = 1'b1; idx = 2'd3; cnt = c3;
                                end
                                if (found && (cnt == 5'd15)) begin
                                    if (idx == 2'd0) svb[0] = 1'b0;
                                    else if (idx == 2'd1) svb[1] = 1'b0;
                                    else if (idx == 2'd2) svb[2] = 1'b0;
                                    else svb[3] = 1'b0;
                                end else if (found) begin
                                    if (idx == 2'd0) c0 = c0 + 5'd1;
                                    else if (idx == 2'd1) c1 = c1 + 5'd1;
                                    else if (idx == 2'd2) c2 = c2 + 5'd1;
                                    else c3 = c3 + 5'd1;
                                end else if (!svb[0]) begin
                                    svb[0] = 1'b1; t0 = tile_now; c0 = 5'd1;
                                end else if (!svb[1]) begin
                                    svb[1] = 1'b1; t1 = tile_now; c1 = 5'd1;
                                end else if (!svb[2]) begin
                                    svb[2] = 1'b1; t2 = tile_now; c2 = 5'd1;
                                end else if (!svb[3]) begin
                                    svb[3] = 1'b1; t3 = tile_now; c3 = 5'd1;
                                end
                            end
                        end
                        sv <= svb;
                        st0 <= t0; st1 <= t1; st2 <= t2; st3 <= t3;
                        sc0 <= c0; sc1 <= c1; sc2 <= c2; sc3 <= c3;
                    end
                end else if (gemm_accept && hit && pack_w) begin
                    sv[hi] <= 1'b0;
                end else if (gemm_accept && hit) begin
                    if (hi == 2'd0)
                        sc0 <= sc0 + 5'd1;
                    else if (hi == 2'd1)
                        sc1 <= sc1 + 5'd1;
                    else if (hi == 2'd2)
                        sc2 <= sc2 + 5'd1;
                    else
                        sc3 <= sc3 + 5'd1;
                end else if (gemm_accept) begin
                    if (!sv[0]) begin
                        sv[0] <= 1'b1;
                        st0 <= tile_out;
                        sc0 <= 5'd1;
                    end else if (!sv[1]) begin
                        sv[1] <= 1'b1;
                        st1 <= tile_out;
                        sc1 <= 5'd1;
                    end else if (!sv[2]) begin
                        sv[2] <= 1'b1;
                        st2 <= tile_out;
                        sc2 <= 5'd1;
                    end else if (!sv[3]) begin
                        sv[3] <= 1'b1;
                        st3 <= tile_out;
                        sc3 <= 5'd1;
                    end
                end
            end
        end
    endgenerate
endmodule

`default_nettype wire
