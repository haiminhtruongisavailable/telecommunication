# Architecture, layer by layer

Same reading order as `I05_Intro_to_chip_design_project`:

1. Top, control beside processing.
2. Open the control unit.
3. Open the processing unit.
4. Open one block inside the processing unit.

`hop_top` only wires the two units. It does not hold flits and it does not pick a score. `N_WIRES` is 1 in the base machine. The pins marked `*` grow when that parameter grows. Packer, `ready`, each score, and unpack do not grow.

This is the drawing. `arch/*.v` is not written yet. `golden/hop.py` is still one square on `T_k = T_0 + k * C_tile`, first-come-first-served against earliest `D_k`.

## Bit widths

These match the widths already used in `rtl/hop_top.v`, plus `N_WIRES` and `W_FLIT` for this drawing. A width written `N_WIRES x 8` is a bus of `N_WIRES` fields, each 8 bits. With `N_WIRES = 1` that bus is 8 bits.

| Parameter | Value in the base machine | What it sizes |
| --- | --- | --- |
| `N_WIRES` | 1, later 2 or 4 | how many flits may leave in one cycle |
| `W_FLIT` | 256 bits (32 bytes) | payload of one flit. A different knob from `N_WIRES` |
| `TILE_W` | 8 | square number `k` |
| `SEQ_W` | 16 | packer order |
| `DL_W` | 32 | `D_k` and the other-stack deadline |
| `IDX_W` | 8 | index of one `ready` slot (256 slots) |
| `CW` | 8 | credit count. `K = 16` fits |
| `TIME_W` | 32 | cycle count and `t_last` |
| `POLICY_W` | 3 | five scores, values 0 to 4 |
| `WAVE_W` | 8 | wave width `W` and `admit_limit` |

Pins of `hop_top`. Control wires such as `policy_id` are not in this list. The control unit creates them.

| Pin | Width | Direction |
| --- | --- | --- |
| `clk`, `rst` | 1, 1 | in |
| `panel_valid` | 1 | in |
| `panel_byte` | 8 | in. One INT8 byte. A square is 256 bytes of A, then 256 bytes of B. The whole panel is not one pin. |
| `tile_id` | 8 | in. The square `k` those bytes belong to. |
| `panel_sel` | 1 | in. 0 is A, 1 is B. |
| `other_valid` | 1 | in |
| `other_flit` | 256 | in. Already one flit. It does not pass through the packer. |
| `other_deadline` | 32 | in. The golden still drives this with `10^9` until that knob is edited. |
| `out_valid` | 1 | out. One unpacked flit beat. Stays 1 when `N_WIRES` grows. |
| `out_flit` | 256 | out |
| `out_tile` | 8 | out |
| `out_panel_sel` | 1 | out |
| `done` | 1 | out |
| `t_last_bus` | `N_TILES x 32` | out. Arrival time of the last flit of each square. |

Wires between the control unit and the processing unit:

| Wire | Width | Grows with `N_WIRES` |
| --- | --- | --- |
| `release_en` | 1 | no |
| `W` | 8 | no |
| `policy_id` | 3 | no |
| `admit_limit` | 8 | no |
| `send_en` | `N_WIRES` | yes |
| `credit_count` | 8 | no |
| `ready_count` | 9 | no. Counts 0 to 256. |
| `grant_idx` | `N_WIRES x 8` | yes |
| `grant_valid` | `N_WIRES` | yes |
| `first_done`, `wave_done` | 1, 1 | no |

One record inside `ready`. This format stays put when `N_WIRES` grows.

| Field | Width |
| --- | --- |
| `valid` | 1 |
| `seq` | 16 |
| `deadline` | 32 |
| `tile_id` | 8 |
| `panel_sel` | 1 |
| `flits_left` | 5. A panel pair is 16 flits, so 0 to 16 fits. |
| `consumers` | 8 |
| `wave_id` | 8 |
| `is_gemm` | 1 |
| `payload` | 256 |
| `score` out of each score block | 32. A 16-bit `seq` is placed in the low bits. |

## How to widen the wires

Change the parameter `N_WIRES` from 1 to 2, or from 1 to 4. Do that in three places only.

1. The buses `send_en`, `grant_idx`, and `grant_valid` on the boundary in layer 1. At `N_WIRES = 2`, `send_en` is 2 bits, `grant_valid` is 2 bits, and `grant_idx` is 16 bits (two indexes of 8).
2. The credit block. In one cycle it may accept `min(credit_count, N_WIRES)` sends. It still accepts none when `credit_count` is 0. The count register stays 8 bits, because `K` did not change.
3. The PHY. It gets `N_WIRES` delay lanes, each of `D_phy` cycles. A gather of depth `N_WIRES` then hands `unpack` one 256-bit flit per cycle, so `out_flit` stays 256 bits and `out_valid` stays 1 bit.

Leave these at the widths in the tables above: `panel_byte`, `other_flit`, the `ready` record, every score block, and `unpack`.

`W_FLIT` is the other knob. Raising it from 256 bits makes each flit carry more panel bytes, so the packer emits fewer flits per square. That is a wider word, not a second wire. Do not use it as a substitute for `N_WIRES`.

## Layer 1. Top

```text
                         clk          rst
                          |            |
                          |            |
          panel bytes, k  |            |   other-stack flit
                 |        |            |          |
                 v        v            v          v
        +------------------------------------------------------+
        | hop_top                                              |
        |                                                      |
        |   +---------------------------+   +----------------+ |
        |   | PU                        |   | CU             | |
        |   |                           |   |                | |
        |   | clk  <--------------------+---+-- clk          | |
        |   | rst  <--------------------+---+-- rst          | |
        |   |                           |   |                | |
        |   | release_en <--------------+---+-- release_en   | |
        |   | W          <--------------+---+-- W            | |
        |   | policy_id  <--------------+---+-- policy_id    | |
        |   | admit_limit <-------------+---+-- admit_limit  | |
        |   | send_en[*] <--------------+---+-- send_en[*]   | |
        |   |                           |   |                | |
        |   | credit_count -------------+-->| credit_count   | |
        |   | ready_count --------------+-->| ready_count    | |
        |   | grant_idx[*] -------------+-->| grant_idx[*]   | |
        |   | grant_valid[*] -----------+-->| grant_valid[*] | |
        |   | first_done ---------------+-->| first_done     | |
        |   | wave_done ----------------+-->| wave_done      | |
        |   |                           |   |                | |
        |   | panels out                |   | done ----------+-+--> done
        |   +---------------------------+   +----------------+ |
        +------------------------------------------------------+
```

Those ten named wires are this design's `load`, `run`, `i`, `x`, and `y`. Control never sees A or B bytes.

## Layer 2. Control unit

Control decides the cycle. It does not scan `ready`.

```text
 clk rst
   |  |
   v  v
+------------------------------------------------------------------+
| CU                                                               |
|                                                                  |
|  +------------------+      +-------------------------------+     |
|  | release_fsm      |      | policy_reg                    |     |
|  |                  |      |  0 first-come-first-served    |     |
|  | T_k = T_0+k*C    |      |  1 earliest D_k               |     |
|  | or one wave of W |----->|  2 closest-to-firing          |     |
|  |                  |      |  3 shared-panel-first         |     |
|  | release_en ----->|      |  4 finish-the-row             |     |
|  | W -------------->|      |                               |     |
|  +------------------+      | policy_id ------------------> |     |
|                            +-------------------------------+     |
|  +------------------+                                            |
|  | admit_limit_reg  |   how many squares may enter ready         |
|  | admit_limit ---->|                                            |
|  +------------------+                                            |
|                                                                  |
|  credit_count --+                                                |
|                 +--> compare > 0 --+--> send_en[*]               |
|  grant_valid[*] -------------------+                             |
|                                                                  |
|  first_done, wave_done ------------------> done                 |
+------------------------------------------------------------------+
```

`send_en` is the only place control touches the hop. It stays 0 when `credit_count` is 0.

## Layer 3. Processing unit

Same role as `cordic_processing`: the blocks sit inside, and the outside only sees the pins from layer 1.

```text
 clk rst   release_en W policy_id admit_limit send_en[*]
   |  |         |      |     |          |          |
   v  v         v      v     v          v          v
+-----------------------------------------------------------------------+
| PU                                                                    |
|                                                                       |
|  panel bytes, k                                                       |
|       |                                                               |
|       v                                                               |
|  +-----------+    records     +------------+                          |
|  | release   |--------------->| packer     |                          |
|  | hold wave |  admit_limit   | A/B -> 16  |                          |
|  | until a   |                | flits, one |                          |
|  | square    |                | D_k        |                          |
|  | finishes  |                +-----+------+                          |
|  +-----------+                      |                                 |
|                                     v                                 |
|              other-stack flit -> +--------+                           |
|                                  | ready  |  one buffer, many records |
|                                  +---+----+                           |
|                                      |                                |
|                    +-----------------+------------------+             |
|                    v                 v                  v             |
|              +----------+     +-------------+    +-------------+      |
|              | score_   |     | score_edf   |    | score_firing|      |
|              | fcfs     |     | score_shared|    | score_row   |      |
|              +----+-----+     +------+------+    +------+------+      |
|                   \                 |                  /              |
|                    +--------+-------+--------+---------+              |
|                             v                v                        |
|                      +-------------+    policy_id selects             |
|                      | scheduler   |    one score bus                 |
|                      | argmin      |                                  |
|                      | grant_idx[*]|                                  |
|                      +------+------+                                  |
|                             |                                         |
|                             v                                         |
|                      +-------------+    send_en[*] and credit > 0     |
|                      | credit     |------------------------------+    |
|                      | count reg  |    credit_count (back to CU) |    |
|                      +------+-----+                              |    |
|                             | 1 flit, or N_WIRES later           |    |
|                             v                                    |    |
|                      +-------------+                             |    |
|                      | phy_box    |  D_phy delay, lanes = N_WIRES|    |
|                      | + gather   |  gather hands one record out |    |
|                      +------+-----+                             |    |
|                             |                                    |    |
|                             v                                    |    |
|                      +-------------+    credit return ---------->+    |
|                      | unpack     |    after 2*D_phy                 |
|                      | panels out |                                  |
|                      +-------------+                                  |
+-----------------------------------------------------------------------+
```

The other stack joins at `ready`, after the packer. It does not enter the packer and it does not enter the PHY by itself.

## Layer 4. Inside two blocks

Open these the way I05 opens block B, then block A. The other score blocks have the same shell as `score_fcfs`: one record in, one integer out.

### 4a. `score_fcfs` and `score_edf`

```text
 record from ready                         policy_id
 (seq, D_k, valid)                              |
        |                                       |
        v                                       v
 +------------------+                  +------------------+
 | score_fcfs       |                  | score_edf        |
 |                  |                  |                  |
 | score = seq      |                  | score = D_k      |
 |                  |                  | tie keeps seq    |
 | score_out ------>|                  | score_out ------>|
 +------------------+                  +------------------+
```

`score_firing`, `score_shared`, and `score_row` use the same ports. Only the number inside changes:

| Block | Score |
| --- | --- |
| `score_firing` | fewer flits left before both panels of that square are complete |
| `score_shared` | more squares stuck on this panel |
| `score_row` | more flits left in that square |

### 4b. `scheduler`

```text
 score_fcfs  score_edf  score_firing  score_shared  score_row
      \          |           |             |            /
       +---------+-----------+-------------+-----------+
                               |
                               v
                    +---------------------+
                    | scheduler           |
                    |                     |
                    | mux by policy_id    |
                    | then argmin         |
                    |                     |
                    | grant_idx[0] ------>|   base: one index
                    | grant_valid[0] ---> |
                    |                     |
                    | grant_idx[*] ------>|   later, if N_WIRES > 1
                    +---------------------+
```

The argmin reads every valid slot. Extra wires here are extra winners, not a wider view of `ready`.

### 4c. `credit`

```text
 grant_valid[*]          send request
        |                      |
        v                      v
 +-------------------------------------------+
 | credit                                    |
 |                                           |
 | count starts at K                         |
 |                                           |
 | accept = min(credit, popcount send_en)   |
 | count = count - accept + returns         |
 |                                           |
 | credit_count ----------------------------+--> back to CU
 | pass_en[*] ------------------------------+--> into phy_box
 +-------------------------------------------+
                      ^
                      |
               credit return
               (one slot freed on the compute die,
                arrives after 2*D_phy)
```

`K` is slots in the compute-die buffer. It is not a wire count. `pass_en` is 0 for every lane when the count is 0.

## What a later wire changes

| Pin | Layer that owns it |
| --- | --- |
| `send_en[*]`, `grant_idx[*]`, `grant_valid[*]` | the boundary drawn in layer 1 |
| accept count inside `credit` | layer 4c |
| delay lanes inside `phy_box` | layer 3 |

Release, packer, `ready`, the five score blocks, and unpack keep the ports drawn above.
