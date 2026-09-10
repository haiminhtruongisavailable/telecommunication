IVERILOG ?= iverilog
VVP      ?= vvp
RTL      := ../rtl/credit.v ../rtl/fifo_k.v ../rtl/packer.v ../rtl/scheduler_edf.v ../rtl/hop_top.v
TB       := hop_tb.v

.PHONY: all sim-edf sim-fcfs sim-k1 clean

all: sim-edf

sim-edf: $(RTL) $(TB)
	$(IVERILOG) -g2005-sv -o hop_edf.vvp -I../rtl $(RTL) $(TB) -P hop_tb.K=16 -P hop_tb.POLICY_EDF=1
	$(VVP) hop_edf.vvp

sim-fcfs: $(RTL) $(TB)
	$(IVERILOG) -g2005-sv -o hop_fcfs.vvp -I../rtl $(RTL) $(TB) -P hop_tb.K=16 -P hop_tb.POLICY_EDF=0
	$(VVP) hop_fcfs.vvp

sim-k1: $(RTL) $(TB)
	$(IVERILOG) -g2005-sv -o hop_k1.vvp -I../rtl $(RTL) $(TB) -P hop_tb.K=1 -P hop_tb.POLICY_EDF=1
	$(VVP) hop_k1.vvp

clean:
	rm -f *.vvp rtl_tlast.csv
