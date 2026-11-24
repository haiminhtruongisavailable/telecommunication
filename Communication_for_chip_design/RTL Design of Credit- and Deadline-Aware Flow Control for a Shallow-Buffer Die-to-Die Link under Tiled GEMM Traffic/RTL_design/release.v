`default_nettype none
`timescale 1ns/1ps

// Structural admission counter.
// let_square opens the lane for the square now being packed.
// pack_done frees that square's cap slot on the same edge, so the next
// square can be admitted while the finished square's last flit is still
// in ready. square_finished does not change the cap.
// W is copied at the first square of a wave and held until the wave rolls.
module square_release #(
    parameter integer WAVE_W = 8
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  release_en,
    input  wire [WAVE_W-1:0]     W,
    input  wire [WAVE_W-1:0]     admit_limit,
    input  wire                  pack_done,
    input  wire                  pack_done2,
    input  wire                  square_finished,
    output wire                  let_square,
    output wire                  admit_now,
    output wire [WAVE_W-1:0]     wave_id
);
    wire [WAVE_W-1:0] cap;
    wire              room;
    wire              busy;
    wire              rel_room;
    wire              can_admit;
    wire              none_open;
    wire              busy_d;
    wire [WAVE_W-1:0] admitted;
    wire [WAVE_W-1:0] admitted_eff1;
    wire [WAVE_W-1:0] admitted_eff;
    wire [WAVE_W-1:0] admitted_mid;
    wire [WAVE_W-1:0] admitted_d;
    wire [WAVE_W-1:0] in_wave;
    wire [WAVE_W-1:0] in_wave_inc;
    wire [WAVE_W-1:0] in_wave_next;
    wire [WAVE_W-1:0] in_wave_d;
    wire [WAVE_W-1:0] wave_alloc;
    wire [WAVE_W-1:0] wave_inc;
    wire [WAVE_W-1:0] wave_d;
    wire [WAVE_W-1:0] stamp_d;
    wire              wave_full;
    wire              start_new;
    wire              at_start;
    wire              latch_w;
    wire [WAVE_W-1:0] w_hold;
    wire [WAVE_W-1:0] w_hold_d;
    wire [WAVE_W-1:0] w_ref;

    min2 #(.WIDTH(WAVE_W)) u_min (
        .a (W),
        .b (admit_limit),
        .y (cap)
    );
    // The square whose last flit was just accepted no longer occupies the cap.
    // Another square may be admitted on that edge, or while one is still
    // packing, whenever admitted_eff < cap. let_square stays high while
    // any admitted square is still open.
    // pack_done2 tied low leaves y equal to a, so one completion is unchanged.
    addsub_incdec #(.WIDTH(WAVE_W)) u_eff (
        .a   (admitted),
        .inc (1'b0),
        .dec (pack_done),
        .y   (admitted_eff1)
    );
    addsub_incdec #(.WIDTH(WAVE_W)) u_eff2 (
        .a   (admitted_eff1),
        .inc (1'b0),
        .dec (pack_done2),
        .y   (admitted_eff)
    );
    cmp_lt #(.WIDTH(WAVE_W)) u_lt (
        .a (admitted_eff),
        .b (cap),
        .y (room)
    );
    assign can_admit = 1'b1;
    and2 u_rel_room (
        .a (release_en),
        .b (room),
        .y (rel_room)
    );
    and2 u_admit (
        .a (rel_room),
        .b (can_admit),
        .y (admit_now)
    );
    assign let_square = busy;
    cmp_eq #(.WIDTH(WAVE_W)) u_none (
        .a (admitted_d),
        .b ({WAVE_W{1'b0}}),
        .y (none_open)
    );
    not1 u_busy_lvl (
        .a (none_open),
        .y (busy_d)
    );
    dreg #(.WIDTH(1)) u_busy (
        .clk (clk),
        .rst (rst),
        .d   (busy_d),
        .q   (busy)
    );
    addsub_incdec #(.WIDTH(WAVE_W)) u_add (
        .a   (admitted),
        .inc (admit_now),
        .dec (pack_done),
        .y   (admitted_mid)
    );
    addsub_incdec #(.WIDTH(WAVE_W)) u_add2 (
        .a   (admitted_mid),
        .inc (1'b0),
        .dec (pack_done2),
        .y   (admitted_d)
    );
    dreg #(.WIDTH(WAVE_W)) u_admitted (
        .clk (clk),
        .rst (rst),
        .d   (admitted_d),
        .q   (admitted)
    );

    // in_wave counts squares in the wave now being filled.
    // On the W-th square the count returns to 0 and the next wave id is armed.
    // wave_id stays on the square just admitted, so its flits keep that id.
    incr #(.WIDTH(WAVE_W)) u_in_inc (
        .a (in_wave),
        .y (in_wave_inc)
    );
    cmp_eq #(.WIDTH(WAVE_W)) u_at_start (
        .a (in_wave),
        .b ({WAVE_W{1'b0}}),
        .y (at_start)
    );
    and2 u_latch (
        .a (admit_now),
        .b (at_start),
        .y (latch_w)
    );
    mux2 #(.WIDTH(WAVE_W)) u_w_mux (
        .sel (latch_w),
        .on1 (W),
        .on0 (w_hold),
        .y   (w_hold_d)
    );
    dreg #(.WIDTH(WAVE_W)) u_w_hold (
        .clk (clk),
        .rst (rst),
        .d   (w_hold_d),
        .q   (w_hold)
    );
    mux2 #(.WIDTH(WAVE_W)) u_w_ref (
        .sel (at_start),
        .on1 (W),
        .on0 (w_hold),
        .y   (w_ref)
    );
    cmp_eq #(.WIDTH(WAVE_W)) u_full (
        .a (in_wave_inc),
        .b (w_ref),
        .y (wave_full)
    );
    and2 u_start (
        .a (admit_now),
        .b (wave_full),
        .y (start_new)
    );
    mux2 #(.WIDTH(WAVE_W)) u_in_reload (
        .sel (start_new),
        .on1 ({WAVE_W{1'b0}}),
        .on0 (in_wave_inc),
        .y   (in_wave_next)
    );
    mux2 #(.WIDTH(WAVE_W)) u_in_hold (
        .sel (admit_now),
        .on1 (in_wave_next),
        .on0 (in_wave),
        .y   (in_wave_d)
    );
    dreg #(.WIDTH(WAVE_W)) u_in_wave (
        .clk (clk),
        .rst (rst),
        .d   (in_wave_d),
        .q   (in_wave)
    );
    incr #(.WIDTH(WAVE_W)) u_wave_inc (
        .a (wave_alloc),
        .y (wave_inc)
    );
    mux2 #(.WIDTH(WAVE_W)) u_alloc_mux (
        .sel (start_new),
        .on1 (wave_inc),
        .on0 (wave_alloc),
        .y   (wave_d)
    );
    dreg #(.WIDTH(WAVE_W)) u_alloc (
        .clk (clk),
        .rst (rst),
        .d   (wave_d),
        .q   (wave_alloc)
    );
    mux2 #(.WIDTH(WAVE_W)) u_stamp (
        .sel (admit_now),
        .on1 (wave_alloc),
        .on0 (wave_id),
        .y   (stamp_d)
    );
    dreg #(.WIDTH(WAVE_W)) u_stamp_reg (
        .clk (clk),
        .rst (rst),
        .d   (stamp_d),
        .q   (wave_id)
    );
endmodule

`default_nettype wire
