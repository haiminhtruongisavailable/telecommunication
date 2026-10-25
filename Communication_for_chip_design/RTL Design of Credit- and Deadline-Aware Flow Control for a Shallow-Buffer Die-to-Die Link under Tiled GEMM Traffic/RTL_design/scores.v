`default_nettype none
`timescale 1ns/1ps

// Fields of the 336-bit Ready record. Lower score wins in every policy.
// payload [255:0], tile_id [263:256], panel_sel [264], seq [280:265],
// deadline [312:281], flits_left [317:313], consumers [325:318].
module record_fields (
    input  wire [335:0] record,
    output wire [15:0]  seq,
    output wire [31:0]  deadline,
    output wire         panel_sel,
    output wire [4:0]   flits_left,
    output wire [7:0]   consumers
);
    assign seq        = record[280:265];
    assign deadline   = record[312:281];
    assign panel_sel  = record[264];
    assign flits_left = record[317:313];
    assign consumers  = record[325:318];
endmodule

// 0. Oldest packed flit.
module score_fcfs (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    wire [15:0] seq;
    wire [31:0] deadline;
    wire        panel_sel;
    wire [4:0]  flits_left;
    wire [7:0]  consumers;
    record_fields u_fields (record, seq, deadline, panel_sel, flits_left, consumers);
    assign score = {32'd0, seq};
endmodule

// 1. Earliest deadline, then packing order.
module score_edf (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    wire [15:0] seq;
    wire [31:0] deadline;
    wire        panel_sel;
    wire [4:0]  flits_left;
    wire [7:0]  consumers;
    record_fields u_fields (record, seq, deadline, panel_sel, flits_left, consumers);
    assign score = {deadline, seq};
endmodule

// 2. Fewest flits left on this panel, then packing order.
// The record has no bit for "the other panel is already complete".
module score_firing (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    wire [15:0] seq;
    wire [31:0] deadline;
    wire        panel_sel;
    wire [4:0]  flits_left;
    wire [7:0]  consumers;
    record_fields u_fields (record, seq, deadline, panel_sel, flits_left, consumers);
    assign score = {27'd0, flits_left, seq};
endmodule

// 3. Panel A before panel B, then the panel with more waiting squares,
//    then fewest flits left.
module score_shared (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    wire [15:0] seq;
    wire [31:0] deadline;
    wire        panel_sel;
    wire [4:0]  flits_left;
    wire [7:0]  consumers;
    record_fields u_fields (record, seq, deadline, panel_sel, flits_left, consumers);
    assign score = {18'd0, panel_sel, ~consumers, flits_left, seq};
endmodule

// 4. Most flits still left, then packing order.
module score_row (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    wire [15:0] seq;
    wire [31:0] deadline;
    wire        panel_sel;
    wire [4:0]  flits_left;
    wire [7:0]  consumers;
    record_fields u_fields (record, seq, deadline, panel_sel, flits_left, consumers);
    assign score = {27'd0, ~flits_left, seq};
endmodule

// One score on the Ready record. POLICY picks which chip this is.
module score_link #(
    parameter integer POLICY = 1
) (
    input  wire [335:0] record,
    output wire [47:0]  score
);
    generate
        if (POLICY == 0) begin : g_fcfs
            score_fcfs u_score (record, score);
        end else if (POLICY == 2) begin : g_firing
            score_firing u_score (record, score);
        end else if (POLICY == 3) begin : g_shared
            score_shared u_score (record, score);
        end else if (POLICY == 4) begin : g_row
            score_row u_score (record, score);
        end else begin : g_edf
            score_edf u_score (record, score);
        end
    endgenerate
endmodule

`default_nettype wire
