"""One D2D hop. Words:

K = how many flits the compute die can hold (credits start at K).
credit > 0 = a free slot, we may send one flit.
FCFS = front of the queue.
EDF = among waiting flits, the one with soonest D_k (least spare time).
Bulk flits have a far deadline so FCFS can block an urgent GEMM tile.
"""

from collections import deque


def simulate(K, policy, N_tiles=64, C_tile=16, T_0=0, flits_per_tile=16, D_phy=4,
             bulk_every=2, extra=40, W_flit_bytes=32, f_link_Hz=1e9):
    T_k = [T_0 + k * C_tile for k in range(N_tiles)]
    D_k = [T_k[k] + extra for k in range(N_tiles)]
    remaining = [flits_per_tile] * N_tiles
    t_last = [None] * N_tiles

    ready = deque()  # (seq, deadline, tile_id or None if bulk)
    seq = 0
    next_tile = 0
    credit = K
    wire = deque()  # (arrive_cycle, "flit"|"credit", tile_id)
    payload_flits = 0
    stall = 0
    t = 0
    done = 0
    max_t = 200000

    def release(now):
        nonlocal next_tile, seq
        while next_tile < N_tiles and T_k[next_tile] - C_tile <= now:
            k = next_tile
            for _ in range(flits_per_tile):
                ready.append((seq, D_k[k], k))
                seq += 1
            next_tile += 1

    while done < N_tiles and t < max_t:
        release(t)
        if bulk_every and t > 0 and t % bulk_every == 0:
            ready.append((seq, 10**9, None))
            seq += 1

        while wire and wire[0][0] <= t:
            _, kind, tile_id = wire.popleft()
            if kind == "credit":
                credit += 1
            else:
                payload_flits += 1
                if tile_id is not None:
                    remaining[tile_id] -= 1
                    if remaining[tile_id] == 0:
                        t_last[tile_id] = t
                        done += 1

        sent = False
        if credit > 0 and ready:
            if policy == "fcfs":
                item = ready.popleft()
            else:
                i = min(range(len(ready)), key=lambda j: (ready[j][1], ready[j][0]))
                item = ready[i]
                del ready[i]
            _, _, tile_id = item
            credit -= 1
            wire.append((t + D_phy, "flit", tile_id))
            wire.append((t + 2 * D_phy, "credit", None))
            sent = True
        if not sent:
            stall += 1
        t += 1

    W_bits = W_flit_bytes * 8
    eta = payload_flits * W_bits / (t * W_bits) if t else 0.0
    B_peak = W_flit_bytes * f_link_Hz / 1e9
    L = [max(0, (t_last[k] if t_last[k] is not None else t) - D_k[k]) for k in range(N_tiles)]
    misses = sum(1 for x in L if x > 0)
    return {
        "policy": policy,
        "K": K,
        "eta_eff": eta,
        "B_useful_GBps": eta * B_peak,
        "miss_rate": misses / N_tiles,
        "mean_L": sum(L) / N_tiles,
        "stall_cycles": stall,
        "done": done == N_tiles,
    }
