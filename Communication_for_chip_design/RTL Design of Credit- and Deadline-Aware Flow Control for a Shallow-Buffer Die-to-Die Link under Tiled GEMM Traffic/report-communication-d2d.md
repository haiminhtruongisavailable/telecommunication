# RTL Design of Credit- and Deadline-Aware Flow Control for a Shallow-Buffer Die-to-Die Link under Tiled GEMM Traffic

This note is the updated statement of the topic after the advisor's comments. The work is chip design: the deliverable is a digital link-layer block in Verilog. Python is only the golden model used to lock traffic, deadlines, and bandwidth formulas before RTL. The object is one die-to-die hop. The traffic is tiled GEMM, not a full AI model zoo. Deadline and useful-bandwidth formulas are taken from the papers that already define them; I only map those definitions onto GEMM tiles on one hop. The direction stays communication, which matches the advisor's field and a later master's application in photonic integrated circuits. I would like a check on whether the workload, the inherited equations, and the RTL scope are now tight enough.

---

## 1. Three requirements of the chip

To reach high performance in AI, the silicon must finish a large number of MAC operations on time. The design therefore places many MAC units on the die and clocks them at about 1 to 2 GHz.

Those units run only if three requirements hold together:

1. Computing: the MAC array.
2. Memory: SRAM or HBM that stores bits next to the array.
3. Communication: moving bits across a boundary (tile to tile, die to die, or box to box).

Delivered performance is the minimum of MAC peak, arithmetic intensity times memory bandwidth, and link bandwidth (Roofline idea: Williams et al., CACM 2009, https://escholarship.org/content/qt78h8v7mr/qt78h8v7mr.pdf). If the link is the smallest, more MACs or more HBM do not help.

---

## 2. Why communication

Gholami et al., "AI and Memory Wall," IEEE Micro, 2024 (https://doi.org/10.1109/MM.2024.3373763), report that over about twenty years, every two years peak FLOPS grew about 3.0 times, DRAM bandwidth about 1.6 times, and interconnect bandwidth about 1.4 times. Over the full period, compute grew about 60,000 times, DRAM bandwidth about 100 times, interconnect about 30 times. Computing is already the fast curve. Moving bits between chips is the slowest of the three.

Horowitz, ISSCC 2014 (https://doi.org/10.1109/ISSCC.2014.6757323): after voltage scaling ended, power limits performance, and moving a word often costs more energy than adding it. A larger MAC array that waits on a wire is extra heat, not extra performance.

Chiplets made die-to-die the hop that feeds the MAC array. UCIe is the open on-package standard: PHY plus an adapter with flits, CRC, retry, and credits (Das Sharma, https://eps.ieee.org/wp-content/uploads/2026/03/TC-article-Universal-Chiplet-Interconnect-Express-UCIe.pdf). That adapter is communication, not an HBM device and not extra MAC units.

I choose communication for two reasons that should stay aligned. First, interconnect is the lagging hardware curve and the hop between dies. Second, the advisor works in communication, and I intend to apply for a master's in photonic integrated circuits, which is a physical layer for the same requirement (moving bits). This semester is electrical D2D in RTL, not a photonic PHY, because the PHY is foundry work. A PIC master's can later replace copper delay and energy with optical parameters if the flow-control rule does not assume a deep electrical FIFO.

---

## 3. Workload: tiled GEMM (the scale of the project)

The advisor asked for a concrete AI task so that traffic can be counted. I do not take a full AI accelerator (many models, many layers) as the experiment. The kernel that actually moves tiles across the hop is matrix multiply. The traffic is therefore tiled GEMM: C = A x B on two dies.

- Die A holds the MAC array and computes output tiles.
- Die B holds a panel of A or B (or both).
- Each output tile k needs an input tile (or panel) from die B across one D2D hop.

Let the tile side be T (for example 16 or 32) and the data type INT8. One input tile is then T x T bytes. That is the message size. How often a new tile is requested follows from how many cycles the array needs to compute one output tile. Bytes, C_tile, and D_k are then arithmetic. Chiplet-level AI communication (unicast, hops, time in the package network) is characterized in papers such as arXiv:2410.22262 (https://arxiv.org/pdf/2410.22262). I use one GEMM instance of that class, not a 12-model trace.

This is not a general CPU NoC mix (SPEC, PARSEC) and not an LLM or CNN zoo as the main workload.

---

## 4. Deadline (inherited from real-time scheduling)

I do not derive a new deadline theory. I use the periodic-task model of Liu and Layland, "Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment," J. ACM, 1973 (https://doi.org/10.1145/321738.321743; open HTML: https://mwhittaker.github.io/papers/html/liu1973scheduling.html).

Each output tile k of the GEMM is one job. The MAC array starts tile k at

T_k = T_0 + k * C_tile

where C_tile is the number of cycles to compute one output tile (from array size and T). The job's deadline is

D_k = T_k

that is, an implicit deadline equal to the period. In Liu and Layland, overflow is the deadline of an unfinished job; deadline-driven scheduling (EDF) always serves the job with the nearest deadline. On the hop, among flits with credit > 0, the scheduler prefers the tile with nearest D_k. That is EDF applied to flits, not a new policy name.

Finish time of tile k is t_last(k), the cycle when its last input flit arrives on die A. Tardiness and miss follow the usual real-time cost functions (Buttazzo, Hard Real-Time Computing Systems: lateness L = f - d, tardiness E = max(0, f - d), miss = 1 if f > d):

L_k = max(0, t_last(k) - D_k)

miss_k = 1 if L_k > 0, else 0

Miss rate = (1/N) * sum miss_k    over N tiles.

L_k here is tardiness (positive lateness). I keep the symbol L_k. The mapping that is mine is only: job k = GEMM tile k on one D2D hop.

---

## 5. Useful bandwidth (inherited from link goodput)

I do not invent a new bandwidth product. Peak of one hop, one flit per cycle, is the usual channel rate (Dally, "Virtual-Channel Flow Control," IEEE Trans. Parallel Distrib. Syst., 1992, https://doi.org/10.1109/71.127260; open PDF: https://people.eecs.berkeley.edu/~kubitron/courses/cs252-S07/handouts/papers/dally-ieee92.pdf):

B_peak = W_flit * f_link

Payload over raw flit-cycles is link efficiency. RFC 8238 (https://www.rfc-editor.org/rfc/rfc8238.html, Sec. 7) writes goodput as G = (S / F) * V, with S = payload, F = frame size, V = media speed. That is the same product:

eta_eff = payload_bits / (N_cycles * W_flit)

B_useful = eta_eff * B_peak

eta_eff folds header, idle, and credit stall (Dally: accepted throughput versus ideal). I will report both eta_eff and B_useful (for example in GB/s), at the same f_link.

Roofline (Williams et al., CACM 2009, https://escholarship.org/content/qt78h8v7mr/qt78h8v7mr.pdf) is the same useful-versus-peak idea; here it is applied only to the D2D hop, not to the whole GEMM kernel.

UCIe 1.0 table targets (standard / advanced package) such as 0.5 / 0.25 pJ/bit and shoreline GB/s/mm are PHY and package KPIs (Das Sharma PDF). They are not B_useful of my scheduler. I may quote them as the hop class, not as my measured result.

---

## 6. Previous work and novelty

A. UCIe adapter (Das Sharma PDF): flit (256 bytes in UCIe 1.0), credits, CRC, retry. Mindset: a capable PHY plus a normal adapter queue. I inherit the hop and the flit/credit idea. I do not implement the analog PHY. The gap is the assumption of a deep adapter buffer.

B. Bufferless NoCs: BLESS, ISCA 2009 (https://users.ece.cmu.edu/~omutlu/pub/bless_isca09.pdf); CHIPPER, HPCA 2011 (https://doi.org/10.1109/HPCA.2011.5749724). Mindset: almost no router FIFO, deflect to another port. They lose performance at high load. A single D2D hop has no extra port to deflect to. Tiled GEMM traffic is high load.

C. Credit-based flow control (Mutlu interconnect lectures, free slides, e.g. https://safari.ethz.ch/architecture/fall2023/lib/exe/fetch.php?media=onur-comparch-fall2023-lecture26-onchipnetworks-afterlecture.pdf): the receiver returns credits; if the number of slots K is smaller than the credit round-trip, throughput drops. That is the constraint I keep. Those lectures do not add a GEMM tile deadline D_k.

D. Liu and Layland (JACM 1973) and RFC 8238 own the deadline jobs and the goodput product. They do not study a shallow D2D hop.

Novelty I now claim (one sentence): on one D2D hop, when K is smaller than the credit round-trip, a credit-only policy either underfills the link or misses D_k; the contribution is to use credits and D_k together on tiled GEMM traffic so that B_useful stays high without a large miss rate.

That is stronger than "pack and schedule." Packing is a block inside the RTL, not the claim. Deadline math and B_useful are inherited; the application to this hop is not.

---

## 7. Architecture (what I will write in Verilog)

Two dies in one package, one bidirectional hop. On each die, a digital link-layer block (UCIe-style adapter, not the PHY):

streams from tiled GEMM (urgent input tile vs bulk)
-> packer (fixed flit size: pack short messages or split long ones)
-> scheduler + credit check (one flit per cycle if credit > 0; prefer the tile with nearest D_k, i.e. EDF)
-> tiny TX buffer (K = 1 to 4 flits)
-> PHY as a delay box
-> tiny RX buffer (K = 1 to 4 flits)
-> unpack to the MAC array

Flit size is fixed (toy: 32 bytes; real UCIe: 256 bytes). Header, body, and tail flits follow the usual split. The scheduler does not change flit size; it chooses which built flit may go.

The RTL of this project is that packer, credit counter, K-slot FIFO, and deadline scheduler. The PHY is a parameter (delay in cycles, energy per bit from the UCIe table). I do not design analog circuits, TSVs, or a photonic layout. I do not design a full AI SoC.

Baselines: FCFS with a deep FIFO; FCFS with a shallow FIFO (to show collapse). Same hop, same GEMM traffic, same f_link.

---

## 8. How I will implement it

Chip design requires RTL. The packer, credit counter, and scheduler will be written in Verilog and simulated with Verilator.

Python comes first only as a cycle-accurate golden model: GEMM tile generator, D_k, eta_eff, B_useful, miss rate, and a sweep of K. The Verilog is checked against that model (same traces, same no-overflow and payload conservation). Python is not the submitted design.

Optional later, still inside this topic: OpenROAD on an open PDK for area, timing, and power of this digital block only. That is PPA of the adapter, not a D2D analog PHY.

Photonic CAD and vendor PHY IP are not in this project. A later PIC master's topic can swap the PHY delay and energy table.

---

## 9. What I freeze if this version is accepted

- Title: RTL Design of Credit- and Deadline-Aware Flow Control for a Shallow-Buffer Die-to-Die Link under Tiled GEMM Traffic
- Object: one bidirectional D2D hop, two dies
- Traffic: tiled INT8 GEMM (C = A x B); die A computes, die B holds a panel
- Deadline: Liu and Layland 1973; D_k = T_0 + k * C_tile; EDF = nearest D_k; L_k = max(0, t_last(k) - D_k) is tardiness (Buttazzo)
- Useful bandwidth: Dally 1992 and RFC 8238; B_useful = eta_eff * B_peak, B_peak = W_flit * f_link
- K in {1, 2, 4, 16}
- Deliverable: Verilog of packer, credits, K-slot FIFO, and deadline scheduler; Python only as golden model
- Out of scope this semester: analog PHY, photonic layout, HBM device, extra MAC array, full AI model zoo; no new deadline or goodput theory

I would like a review of this freeze, especially C_tile (how to set it from a small array size) and whether OpenROAD PPA of the adapter is wanted in the same semester as the Verilog simulation.
