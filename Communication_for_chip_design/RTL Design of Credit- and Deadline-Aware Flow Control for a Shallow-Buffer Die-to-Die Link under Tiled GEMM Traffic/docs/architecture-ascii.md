# Architecture, layer by layer

Same reading order as `I05_Intro_to_chip_design_project`:

1. Top, control beside processing.
2. Open the control unit.
3. Open the processing unit.
4. Open one block inside the processing unit.

`hop_top` only wires the two units. It does not hold flits and it does not pick a score. `N_WIRES` is 1 in the base machine. The pins marked `*` grow when that parameter grows. Packer, `ready`, each score, and unpack do not grow.

This is the drawing. `arch/*.v` is not written yet. `golden/hop.py` is still one square on `T_k = T_0 + k * C_tile`, first-come-first-served against earliest `D_k`.

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
