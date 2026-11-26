# Same constraints for every POLICY and K. The netlist is already mapped
# to sky130_fd_sc_hd by the host Yosys run. Liberty cells stay black boxes
# so this flow does not remap them.
set ::env(DESIGN_NAME) hop_path
set ::env(VERILOG_FILES) [list "VERILOG_LIST"]
set ::env(CLOCK_PORT) clk
set ::env(CLOCK_PERIOD) 22
set ::env(GLB_RESIZER_TIMING_OPTIMIZATIONS) 0
set ::env(SYNTH_READ_BLACKBOX_LIB) 1
set ::env(QUIT_ON_SYNTH_CHECKS) 0
set ::env(QUIT_ON_UNMAPPED_CELLS) 0
set ::env(QUIT_ON_LINTER_ERRORS) 0
set ::env(QUIT_ON_TIMING_VIOLATIONS) 0
set ::env(QUIT_ON_HOLD_VIOLATIONS) 0
set ::env(QUIT_ON_SETUP_VIOLATIONS) 0
set ::env(QUIT_ON_TR_DRC) 0
set ::env(QUIT_ON_MAGIC_DRC) 0
set ::env(QUIT_ON_LVS_ERROR) 0
set ::env(QUIT_ON_XOR_ERROR) 0
set ::env(QUIT_ON_ILLEGAL_OVERLAPS) 0
set ::env(FP_SIZING) absolute
set ::env(DIE_AREA) "0 0 1600 1600"
set ::env(FP_CORE_UTIL) 40
set ::env(PL_TARGET_DENSITY) 0.45
set ::env(RUN_MAGIC) 0
set ::env(RUN_MAGIC_DRC) 0
set ::env(RUN_KLAYOUT) 0
set ::env(RUN_KLAYOUT_XOR) 0
set ::env(RUN_LVS) 0
set ::env(RUN_CVC) 0
set ::env(RUN_IRDROP_REPORT) 0
