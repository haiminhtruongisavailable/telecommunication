# Other stack (bulk) on this hop

Read this after START-HERE and hop.py. For Grok CLI / D2D, not a new title.

## What bulk is

Not GEMM. Not analog delay. Not half a flit.

Tiled GEMM is one UCIe streaming class (A/B panels of tile k, D_k = T_k + extra).
A second protocol stack on the same adapter can share credits. Narrow stub: CXL.io (MMIO/control). Cite Sharma et al. ACM CSUR 10.1145/3819235 (Arb/Mux, per-flit grant, RR, 50% cap = alternate whole flits).

Insert after the GEMM packer, into ready. Never packer input. Never PHY.

Grant = mux gives this cycle to one stack. 1 flit per grant. Exclusive: if CXL.io wins this cycle, GEMM does not send.

## One wire, both busy

One PHY. Two queues can wait (Q_g GEMM, Q_o other). Both busy means both queues nonempty. Not a second wire.

## Occupancy p (not a lab CXL period)

lambda_g ~ flits_per_tile / C_tile. Freeze 16/16 = 1, so GEMM alone wants every cycle.
lambda_o = other offer rate.

- lambda_o = 0 -> p = 0 (dedicated GEMM). FCFS and EDF at K=16 both miss 0.
- lambda_o > 0 and RR both-busy -> p = 0.5 (alternate grants).
- hop.py bulk_every=2 is an offer near p=0.5 into one deque, not a true two-queue RR.

Sweep p or bulk_every in {0, 2}. Do not claim bulk_every=2 from PHY ns.

D_other is far (10**9 in golden, or T_other + extra_other >> extra) so GEMM stays the tight class.

## Why the idea is worth solving

Measured on golden/hop.py (N_tiles=64, extra=40, D_phy=4):

- bulk_every=0, K=16: FCFS miss=0, EDF miss=0, B_useful~31.78
- bulk_every=2, K=16: FCFS miss=0.938, EDF miss=0, B_useful~31.8
- K=1 or 4: credits cap both (miss ~1)
- K=64 with bulk on: FCFS still miss=0.938. Deep FIFO does not fix HOL.

Contribution: map other-stack activation to p, show the miss cliff vs FCFS at the same K and B_useful. Not a new mux. Not 2-D tile geometry. Not optics.

## Do not tell the student

Bulk is garbage flits. Bulk is C = A x B. p splits one flit in half. Mux is invented here.
