// Credit counter. Send only if credit > 0 (Dally TPDS 1992, UCIe adapter credits).
module credit #(
    parameter integer K = 16,
    parameter integer CW = 8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire [CW-1:0]    inc_n,
    input  wire             dec,
    output reg  [CW-1:0]    count,
    output wire             can_send
);
    assign can_send = (count > 0);

    always @(posedge clk) begin
        if (rst) begin
            count <= K[CW-1:0];
        end else begin
            count <= count + inc_n - dec;
        end
    end
endmodule
