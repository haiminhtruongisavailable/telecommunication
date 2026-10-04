// K-slot dest occupancy. In-flight + dest slots = K - credit.
// PHY delay is not here. Occupancy rises on send, falls when the flit arrives.
module fifo_k #(
    parameter integer K = 16,
    parameter integer CW = 8
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          push,
    input  wire          pop,
    output reg  [CW-1:0] occ,
    output wire          full,
    output wire          empty
);
    assign full  = (occ == K[CW-1:0]);
    assign empty = (occ == 0);

    always @(posedge clk) begin
        if (rst) begin
            occ <= {CW{1'b0}};
        end else begin
            if (push && !pop)
                occ <= occ + 1'b1;
            else if (!push && pop)
                occ <= occ - 1'b1;
        end
    end
endmodule
