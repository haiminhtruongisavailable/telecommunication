`default_nettype none
`timescale 1ns/1ps

// The only leaf that stores a value. Reset is active high, matching the hop.
module dreg #(
    parameter integer WIDTH = 1,
    parameter integer RST_VAL = 0
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire [WIDTH-1:0]      d,
    output reg  [WIDTH-1:0]      q
);
    always @(posedge clk) begin
        if (rst) begin
            if (RST_VAL == 0)
                q <= {WIDTH{1'b0}};
            else
                q <= RST_VAL[WIDTH-1:0];
        end else
            q <= d;
    end
endmodule

module and2 (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a & b;
endmodule

module or2 (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a | b;
endmodule

module not1 (
    input  wire a,
    output wire y
);
    assign y = ~a;
endmodule

module mux2 #(
    parameter integer WIDTH = 1
) (
    input  wire                  sel,
    input  wire [WIDTH-1:0]      on1,
    input  wire [WIDTH-1:0]      on0,
    output wire [WIDTH-1:0]      y
);
    assign y = sel ? on1 : on0;
endmodule

// Smaller of two counts. Used as min(W, admit_limit).
module min2 #(
    parameter integer WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire [WIDTH-1:0] y
);
    assign y = (a < b) ? a : b;
endmodule

module cmp_lt #(
    parameter integer WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire             y
);
    assign y = (a < b);
endmodule

module cmp_eq #(
    parameter integer WIDTH = 6
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire             y
);
    assign y = (a == b);
endmodule

// admitted + 1 when inc, - 1 when dec. A finish at zero stays zero.
module addsub_incdec #(
    parameter integer WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire             inc,
    input  wire             dec,
    output wire [WIDTH-1:0] y
);
    wire [WIDTH:0] sum = {1'b0, a} + {{WIDTH{1'b0}}, inc} - {{WIDTH{1'b0}}, dec};
    assign y = (dec && !inc && (a == {WIDTH{1'b0}})) ? {WIDTH{1'b0}} : sum[WIDTH-1:0];
endmodule

// New byte joins the low end of the flit word.
module cat_low #(
    parameter integer WIDTH = 256
) (
    input  wire [WIDTH-1:0] word,
    input  wire [7:0]       byte_in,
    output wire [WIDTH-1:0] y
);
    assign y = {word[WIDTH-9:0], byte_in};
endmodule

module incr #(
    parameter integer WIDTH = 6
) (
    input  wire [WIDTH-1:0] a,
    output wire [WIDTH-1:0] y
);
    assign y = a + {{(WIDTH-1){1'b0}}, 1'b1};
endmodule

`default_nettype wire
