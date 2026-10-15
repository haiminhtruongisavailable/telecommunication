// Pick next flit. EDF: min D_k then seq (Liu-Layland 1973). FCFS: min seq (queue order).
module scheduler_edf #(
    parameter integer SLOTS  = 256,
    parameter integer SEQ_W  = 16,
    parameter integer DL_W   = 32,
    parameter integer IDX_W  = 8
) (
    input  wire                 policy_edf,
    input  wire [SLOTS-1:0]     valid,
    input  wire [DL_W*SLOTS-1:0] deadline,
    input  wire [SEQ_W*SLOTS-1:0] seq,
    output reg                  grant_valid,
    output reg  [IDX_W-1:0]     grant_idx
);
    integer i;
    reg             found;
    reg [DL_W-1:0]  best_dl;
    reg [SEQ_W-1:0] best_seq;
    reg [DL_W-1:0]  d;
    reg [SEQ_W-1:0] s;
    reg             better;

    always @(*) begin
        grant_valid = 1'b0;
        grant_idx   = {IDX_W{1'b0}};
        found       = 1'b0;
        best_dl     = {DL_W{1'b1}};
        best_seq    = {SEQ_W{1'b1}};
        for (i = 0; i < SLOTS; i = i + 1) begin
            if (valid[i]) begin
                d = deadline[i*DL_W +: DL_W];
                s = seq[i*SEQ_W +: SEQ_W];
                if (!found) begin
                    better = 1'b1;
                end else if (policy_edf) begin
                    better = (d < best_dl) || ((d == best_dl) && (s < best_seq));
                end else begin
                    better = (s < best_seq);
                end
                if (better) begin
                    found       = 1'b1;
                    best_dl     = d;
                    best_seq    = s;
                    grant_valid = 1'b1;
                    grant_idx   = i[IDX_W-1:0];
                end
            end
        end
    end
endmodule
