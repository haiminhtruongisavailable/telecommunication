# Why communication, and what I intend to work on

This note sets out how I read the requirements of an AI or 3D-graphics chip, and why I intend to work on communication rather than on a larger MAC array or on HBM itself. I am writing it so that the direction can be checked against a major project, a graduation thesis, and a later master’s application in photonic integrated circuits. I would like comments on whether the problem below is the right first step.

---

## The chip in three pieces

To reach high performance in AI or 3D graphics, the silicon must complete a very large number of multiply-accumulate (MAC) operations before a deadline. At 60 Hz, a frame budget is on the order of 16 ms. For this reason, the design places many MAC units on the die and clocks them at about 1–2 GHz.

Those MAC units operate only if three requirements are satisfied together:

1. Computing: the MAC array itself.
2. Memory: SRAM or HBM that stores bits next to the array.
3. Communication: moving bits across a boundary (tile to tile, die to die, or box to box).

The performance that is actually delivered is the minimum of MAC peak, arithmetic intensity times memory bandwidth, and link bandwidth. If the link is the smallest of the three, adding MAC units or adding HBM does not improve the result.

The MAC array already exists at a large scale. The question is which of the remaining two requirements I should study, given both the technical gap and the path I want to follow.

---

## Computing grew quickly; movement did not

Gholami et al., “AI and Memory Wall,” IEEE Micro, 2024 (https://doi.org/10.1109/MM.2024.3373763), report that over about twenty years of server hardware, every two years:

- peak FLOPS grew by about 3.0 times,
- DRAM bandwidth grew by about 1.6 times,
- interconnect bandwidth grew by about 1.4 times.

Over the full period, compute increased by about 60,000 times, DRAM bandwidth by about 100 times, and interconnect bandwidth by about 30 times.

Compute therefore pulled far ahead. Memory lagged. Moving bits between chips lagged even more.

A product-level check of the same idea is the step from NVIDIA A100 to H100: about 3.2 times FP16 peak versus about 1.7 times HBM bandwidth. Replacing only the memory (H100 to H200) on the same compute die helps memory-bound work. That case is still memory on a single package. As soon as the engine occupies several dies, which is already true of current AI GPUs, the additional wall is the die-to-die or box-to-box link.

Horowitz, ISSCC 2014 (https://doi.org/10.1109/ISSCC.2014.6757323), gives the energy form of the same argument. After voltage scaling ended, power, not transistor count, limits performance, and moving a word often costs more energy than adding it. A larger MAC array that waits on a wire is therefore not additional performance; it is additional heat.

---

## Why communication

I choose communication, not a larger compute array and not HBM as the device, for two reasons that should stay aligned.

The first is the technical split above. Computing is already the fast curve. Interconnect is the slowest of the three (Gholami et al., https://doi.org/10.1109/MM.2024.3373763). Chiplets have made die-to-die the hop that feeds the MAC array (Das Sharma, UCIe, https://eps.ieee.org/wp-content/uploads/2026/03/TC-article-Universal-Chiplet-Interconnect-Express-UCIe.pdf). That is a communication problem: how bits move across a boundary, not how a DRAM cell is built.

The second is the path I want. My advisor works in communication. I intend to apply for a master’s degree in photonic integrated circuits. Photonic ICs are a physical layer for the same requirement: moving bits. If the major project is already in communication, the master’s work can sit on the same axis (electrical die-to-die now, photonic interconnect later) instead of a reset into memory-device or MAC-array research.

I do not start with a photonic PHY in the first year because that is a foundry and process problem. The first implementable layer is a digital die-to-die link in simulation: credits, packing, and schedule. That layer is still communication. A photonic PIC master’s can later replace copper delay and energy with optical parameters. The question I would like to discuss is whether this first layer is formulated tightly enough.

---

## Data movement today: many wires are already there

Industry has not ignored this problem. UCIe (Das Sharma, https://eps.ieee.org/wp-content/uploads/2026/03/TC-article-Universal-Chiplet-Interconnect-Express-UCIe.pdf) is the open die-to-die standard: a PHY plus an adapter with credits, CRC, and retry. Measured links in advanced CMOS are on the order of 0.3–0.5 pJ/bit and terabits per second per millimetre of beachfront, which is substantially better than board-level SerDes.

Peak bandwidth remains

peak bandwidth = (number of wires) × (rate).

Useful bandwidth is lower:

useful bandwidth ≈ payload / (payload + header + idle + credit stall + retry).

Chiplet AI produces short, bursty messages, for example a tile of activations or a fragment of a collective. Those messages do not fill the serializer. Credits require a round trip. If the receiver has only a small buffer, a naive sender either underfills the link or overflows it.

Electrical die-to-die design hides this behaviour with deep FIFOs. Photonic and quantum links will not offer that hiding: light is difficult to store, and a quantum state cannot be copied. A schedule that only works with a deep electrical queue does not carry over to a PIC master’s topic.

The remaining problem is not a request for more wires. The wires are already present. The schedule still assumes buffering that a photonic PHY will not provide.

---

## Previous work: three mindsets

A. A fatter PHY (UCIe and foundry die-to-die papers).  
These works raise beachfront density and energy per bit, and they add retry. The mindset is that if the analog interface is good and the FIFO is large, peak bandwidth is approximately useful bandwidth. Analog PHY and PIC process belong to a later laboratory stage. The first project should not try to reproduce that silicon.

B. Bufferless networks-on-chip (BLESS, ISCA 2009, https://doi.org/10.1145/1555754.1555781; CHIPPER, HPCA 2011, https://doi.org/10.1109/HPCA.2011.5749724).  
These designs remove router FIFOs and deflect flits to another port. They reduce NoC power, but they degrade at high load. Optics used deflection because light is hard to store. The mindset assumes many hops, so a packet can bounce. A single die-to-die hop has no other port to bounce to, and chiplet AI operates at high load.

C. A deep queue with a simple schedule.  
Credit and replay allow the sender to run ahead into a large receive SRAM. The mindset is that CMOS queues are cheap. That does not carry over to photonics or to quantum communication, and even in CMOS that SRAM is itself data movement.

I do not take A, B, or C as the contribution. I keep one existing die-to-die hop and treat shallow buffering as a first-class constraint, because that is the constraint a photonic master’s topic will meet.

---

## Proposed work

I propose deadline-aware flow control on one die-to-die link with only a few flits of buffer, so that useful bandwidth remains high when the receiver cannot queue.

The block would:

1. Decide what enters the link in this cycle (which stream, and how short messages are packed).
2. Decide whether the other die can accept it with one to four flits of buffer, rather than a deep FIFO.
3. Respect a deadline for the current layer, token, or frame: send, reduce, or defer.
4. Treat the PHY as a table of delay, picojoules per bit, and buffer depth. The first table is electrical. A photonic table can replace it without rewriting the schedule if the rule is independent of the PHY.

It would not implement a UCIe analog PHY, a laser, an HBM cube, or additional MAC units.

Baselines:

- first-come, first-served with a deep FIFO (the usual electrical design);
- first-come, first-served with a shallow FIFO (to show that the naive policy fails).

The result that would support the claim is a sweep of buffer depth (1, 2, 4, 16, … flits). Under first-come, first-served, useful bandwidth falls or deadlines are missed. Under the proposed policy, useful bandwidth remains higher at the same wire clock.

At the scale of a major project, this can be a cycle-accurate model of one bidirectional link, first in Python and optionally later in Verilog: flits, credits, two or three streams, and short versus long traffic. Verification is the absence of overflow and deadlock, and conservation of payload. Evaluation is useful bandwidth over peak, deadline misses, and a sweep of buffer depth.

---

## Summary

Compute scaled by about 3 times every two years, DRAM by about 1.6 times, and interconnect by about 1.4 times (Gholami et al., IEEE Micro, 2024, https://doi.org/10.1109/MM.2024.3373763). Moving a bit already rivals the energy of computing on it (Horowitz, ISSCC, 2014, https://doi.org/10.1109/ISSCC.2014.6757323). Chiplets made die-to-die the hop that feeds the MAC array (UCIe, https://eps.ieee.org/wp-content/uploads/2026/03/TC-article-Universal-Chiplet-Interconnect-Express-UCIe.pdf).

I will work on communication: a shallow-buffer, deadline-aware die-to-die schedule. That choice matches the slowest of the three hardware curves, matches an advisor in communication, and stays on the same axis as a master’s application in photonic integrated circuits. The first implementation is electrical and simulated. I would like a review of whether this problem is stated at the right depth, and which constraint (buffer depth, deadline, or packing) should be frozen first.
