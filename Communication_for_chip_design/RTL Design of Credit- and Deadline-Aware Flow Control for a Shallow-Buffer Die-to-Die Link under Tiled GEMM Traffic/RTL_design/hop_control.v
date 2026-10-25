`default_nettype none
`timescale 1ns/1ps

// Release request and send permission. The score is not a pin of this block.
// release_en is high once tile k's time has arrived, and it falls after N_TILES
// squares have finished. ready_count is visible and does not enter the cap.
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
    input  wire [8:0]                ready_count,
    input  wire                      grant_valid,
    input  wire                      square_finished,
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
    wire [TIME_W-1:0] t_plus;
    wire [TIME_W-1:0] thresh;
    wire              too_early;
    wire              time_ok;
    wire              not_done;
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

    // T_k = k * C_TILE with C_TILE = 16. Release from T_k - C_TILE, i.e. t + 16 >= 16k.
    assign t_plus = t_q + C_TILE[TIME_W-1:0];
    assign thresh = {{(TIME_W-12){1'b0}}, tiles_q, 4'b0};
    cmp_lt #(.WIDTH(TIME_W)) u_early (
        .a (t_plus),
        .b (thresh),
        .y (too_early)
    );
    not1 u_time (
        .a (too_early),
        .y (time_ok)
    );
    cmp_eq #(.WIDTH(8)) u_done (
        .a (tiles_q),
        .b (N_TILES[7:0]),
        .y (done)
    );
    not1 u_not_done (
        .a (done),
        .y (not_done)
    );
    and2 u_rel (
        .a (time_ok),
        .b (not_done),
        .y (release_en)
    );

    cmp_lt #(.WIDTH(CW)) u_has (
        .a ({CW{1'b0}}),
        .b (credit_count),
        .y (has_credit)
    );
    and2 u_send (
        .a (grant_valid),
        .b (has_credit),
        .y (send_en)
    );

    assign W           = W_LEN[WAVE_W-1:0];
    assign admit_limit = ADMIT_LIMIT[WAVE_W-1:0];
endmodule

`default_nettype wire
