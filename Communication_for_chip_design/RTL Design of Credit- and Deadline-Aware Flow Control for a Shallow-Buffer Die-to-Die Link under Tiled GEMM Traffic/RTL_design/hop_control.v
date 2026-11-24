`default_nettype none
`timescale 1ns/1ps

// Release request and send permission. The score is not a pin of this block.
// release_en counts squares as they are admitted and falls after N_TILES
// admits. done stays on squares whose last flit has left ready.
// ready_count is visible and does not enter the cap.
module hop_control #(
    parameter integer WAVE_W      = 8,
    parameter integer CW          = 8,
    parameter integer N_TILES     = 1,
    parameter integer C_TILE      = 16,
    parameter integer W_LEN       = 1,
    parameter integer ADMIT_LIMIT = 1,
    parameter integer TIME_W      = 16
) (
    input  wire                      clk,
    input  wire                      rst,
    input  wire [CW-1:0]             credit_count,
    input  wire                      credit_return,
    input  wire [8:0]                ready_count,
    input  wire                      grant_valid,
    input  wire                      square_finished,
    input  wire                      admit_now,
    output wire                      release_en,
    output wire [WAVE_W-1:0]         W,
    output wire [WAVE_W-1:0]         admit_limit,
    output wire                      send_en,
    output wire                      done
);
    wire [TIME_W-1:0] t_q;
    wire [TIME_W-1:0] t_d;
    wire [7:0]        tiles_q;
    wire [7:0]        tiles_d;
    wire [7:0]        started_q;
    wire [7:0]        started_d;
    wire              admits_done;
    wire              more;
    wire [TIME_W-1:0] t_plus;
    wire [TIME_W-1:0] thresh;
    wire              too_early;
    wire              time_ok;
    wire              has_credit;

    incr #(.WIDTH(TIME_W)) u_t_inc (
        .a (t_q),
        .y (t_d)
    );
    dreg #(.WIDTH(TIME_W)) u_t (
        .clk (clk),
        .rst (rst),
        .d   (t_d),
        .q   (t_q)
    );

    addsub_incdec #(.WIDTH(8)) u_tiles (
        .a   (tiles_q),
        .inc (square_finished),
        .dec (1'b0),
        .y   (tiles_d)
    );
    dreg #(.WIDTH(8)) u_tiles_r (
        .clk (clk),
        .rst (rst),
        .d   (tiles_d),
        .q   (tiles_q)
    );

    addsub_incdec #(.WIDTH(8)) u_started (
        .a   (started_q),
        .inc (admit_now),
        .dec (1'b0),
        .y   (started_d)
    );
    dreg #(.WIDTH(8)) u_started_r (
        .clk (clk),
        .rst (rst),
        .d   (started_d),
        .q   (started_q)
    );

    // T_k = k * C_TILE with C_TILE = 16. Release from T_k - C_TILE.
    // started_q is how many squares have been admitted, which is the index
    // of the square release_en is considering.
    assign t_plus = t_q + C_TILE[TIME_W-1:0];
    assign thresh = {{(TIME_W-12){1'b0}}, started_q, 4'b0};
    cmp_lt #(.WIDTH(TIME_W)) u_early (
        .a (t_plus),
        .b (thresh),
        .y (too_early)
    );
    not1 u_time (
        .a (too_early),
        .y (time_ok)
    );
    cmp_eq #(.WIDTH(8)) u_admits_done (
        .a (started_q),
        .b (N_TILES[7:0]),
        .y (admits_done)
    );
    not1 u_more (
        .a (admits_done),
        .y (more)
    );
    and2 u_rel (
        .a (time_ok),
        .b (more),
        .y (release_en)
    );
    cmp_eq #(.WIDTH(8)) u_done (
        .a (tiles_q),
        .b (N_TILES[7:0]),
        .y (done)
    );

    cmp_lt #(.WIDTH(CW)) u_has (
        .a ({CW{1'b0}}),
        .b (credit_count),
        .y (has_credit)
    );
    // Same rule as hop_credit: a return already on the delay line can fund
    // this edge. Return and send together leave the count where it was.
    wire funded;
    or2 u_funded (
        .a (has_credit),
        .b (credit_return),
        .y (funded)
    );
    and2 u_send (
        .a (grant_valid),
        .b (funded),
        .y (send_en)
    );

    assign W           = W_LEN[WAVE_W-1:0];
    assign admit_limit = ADMIT_LIMIT[WAVE_W-1:0];
endmodule

`default_nettype wire
