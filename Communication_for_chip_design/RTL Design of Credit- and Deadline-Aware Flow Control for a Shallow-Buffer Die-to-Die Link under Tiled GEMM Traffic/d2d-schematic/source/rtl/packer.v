// Pack one GEMM tile into FLITS_PER_TILE flits. D_k = T_k + extra, T_k = T_0 + k * C_tile.
module packer #(
    parameter integer FLITS_PER_TILE = 16,
    parameter integer C_TILE         = 16,
    parameter integer EXTRA          = 40,
    parameter integer TILE_W         = 8,
    parameter integer DL_W           = 32
) (
    input  wire [TILE_W-1:0] tile_id,
    input  wire              fire,
    output wire              do_pack,
    output wire [DL_W-1:0]   deadline,
    output wire [TILE_W-1:0] tile_out,
    output wire [4:0]        n_flits
);
    assign do_pack  = fire;
    assign deadline = { {(DL_W-TILE_W){1'b0}}, tile_id } * C_TILE[DL_W-1:0] + EXTRA[DL_W-1:0];
    assign tile_out = tile_id;
    assign n_flits  = FLITS_PER_TILE[4:0];
endmodule
