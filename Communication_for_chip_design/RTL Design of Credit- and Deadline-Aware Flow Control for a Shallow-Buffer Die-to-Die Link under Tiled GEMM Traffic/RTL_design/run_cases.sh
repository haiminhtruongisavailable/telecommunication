#!/bin/bash
# One testbench. Writes the raw vvp log for cases 1 through 22.
set -u
cd "$(dirname "$0")"
mkdir -p logs
iverilog -g2012 -o /tmp/tb_cases.vvp cells.v scheduler_tree.v tb_cases.v
vvp -l logs/cases_1_22.log /tmp/tb_cases.vvp > /dev/null
printf '%s\n' logs/cases_1_22.log
