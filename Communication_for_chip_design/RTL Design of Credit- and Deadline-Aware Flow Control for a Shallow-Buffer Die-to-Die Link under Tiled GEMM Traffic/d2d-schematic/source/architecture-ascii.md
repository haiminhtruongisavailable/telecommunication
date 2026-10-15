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

## Layer 4. Policy blocks, ports only

These five blocks are not opened. No mux and no register is drawn inside them. Each one takes the same record fields and returns one score. `policy_id` is not an input of these blocks. The scheduler mux, below, chooses which score is used.

```text
 valid   seq[15:0]  deadline[31:0]  tile_id[7:0]  panel_sel
 flits_left[4:0]  consumers[7:0]  wave_id[7:0]  is_gemm  payload[255:0]
        |              |                |
        +--------------+----------------+
                       |
                       v
              +------------------+
              | score_fcfs       |
              | score_edf        |
              | score_firing     |
              | score_shared     |
              | score_row        |
              |                  |
              | score[31:0] ---->|
              +------------------+
```

## Layer 5. Other blocks, down to mux, shift, and dreg

Same leaf cells as the I05 datapath. `dreg` stores on `clk`. A mux picks one of its inputs. A shift moves bits by a fixed amount or by a count. A compare drives a select. The policy blocks above are not in this layer.

### 5a. Packer

```text
 panel_byte[7:0]   panel_valid   panel_sel   tile_id[7:0]
        |               |            |            |
        v               v            v            v
 +----------------------------------------------------------+
 | packer                                                   |
 |                                                          |
 |  hold[255:0] --+                                        |
 |                v                                        |
 |         +------------+     panel_byte                   |
 |         | shift << 8 |<----+                            |
 |         +------+-----+                                  |
 |                |                                        |
 |                v                                        |
 |         +------------+   sel = {fire, panel_valid}      |
 |         | word_mux   |   fire  -> 0                     |
 |         |            |   valid -> shifted word          |
 |         |            |   else  -> hold                  |
 |         +------+-----+                                  |
 |                |                                        |
 |                v                                        |
 |         +------------+                                  |
 |         | dreg 256   |---- payload[255:0]               |
 |         +------------+                                  |
 |                                                          |
 |  byte_cnt[5:0] -> +1 -> cmp == 32 -> fire               |
 |                    |                                    |
 |                    v                                    |
 |              cnt_mux (fire ? 0 : cnt+1) -> dreg 6       |
 |                                                          |
 |  fire, tile_id, panel_sel, seq+1 -> one record          |
 +----------------------------------------------------------+
```

`<< 8` is the shift. Thirty-two bytes fill one 256-bit flit. A and B are two fills, 16 flits for the square.

### 5b. Ready memory

One slot is drawn. The block holds 256 copies. The other-stack flit uses the same write port as the packer. It does not have its own memory.

```text
 packer record          other_flit[255:0] + other_deadline[31:0]
        \                          /
         +------------+-----------+
                      v
               +-------------+
               | src_mux     |  sel = other_valid
               +------+------+
                      |
                      v
               +-------------+
               | slot dreg   |  valid, seq, deadline, tile_id,
               |             |  panel_sel, flits_left, consumers,
               |             |  wave_id, is_gemm, payload
               +------+------+
                      |
                      v
               +-------------+
               | read_mux    |  sel = grant_idx[7:0]
               +------+------+
                      |
                      +--> record out to the score ports
                      +--> record out to the PHY lane
```

`ready_count` is a separate `dreg` of 9 bits: plus one on a write, minus one when a granted slot is consumed.

### 5c. Scheduler

The mux is here. The score blocks stay closed.

```text
 score_fcfs[31:0]  score_edf  score_firing  score_shared  score_row
         \             |            |             |           /
          +------------+------------+-------------+----------+
                                   |
                                   v
                          +-----------------+
                          | policy_mux      |  sel = policy_id[2:0]
                          +--------+--------+
                                   |  one score per ready slot
                                   v
                          +-----------------+
                          | cmp_min         |  smaller score wins
                          |                 |  tie: smaller seq
                          +--------+--------+
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
            grant_idx[7:0]                 grant_valid
            index of the winner            0 when no slot is valid
```

For `N_WIRES` greater than 1, the same `cmp_min` is used again on the slots that are not yet chosen. Winner 0 is the smallest score. Winner 1 is the next. Each winner has its own `grant_idx` and `grant_valid`.

### 5d. Credit

```text
 send_en[*]   grant_valid[*]          credit_return (1 bit)
       \            /                        |
        +----------+                         |
                 v                          v
          +--------------+          +---------------+
          | accept_ones  |          | ret_count     |
          | how many     |          | how many      |
          | lanes fire   |          | came back     |
          +------+-------+          +-------+-------+
                 |                          |
                 +-----------+--------------+
                             v
                      +-------------+
                      | addsub      |
                      | count       |
                      |  - accept   |
                      |  + returns  |
                      +------+------+
                             |
                             v
                      +-------------+
                      | cnt_mux     |  hold old count if
                      |             |  accept and returns are 0
                      +------+------+
                             v
                      +-------------+
                      | dreg 8      |---- credit_count[7:0]
                      | reset = K   |
                      +------+------+
                             |
                             v
                      +-------------+
                      | cmp > 0     |---- gates send_en inside CU
                      +-------------+
```

`pass_en[lane]` is `send_en[lane] & grant_valid[lane]`, and the whole vector is cleared when the compare sees 0.

### 5e. PHY and gather

One lane is a shift of records through `D_phy` registers. `N_WIRES` lanes sit side by side.

```text
 pass_en --------+
 payload, tile --+
                 v
          +-------------+
          | load_mux    |  sel = pass_en
          | load record |  else shift from the previous dreg
          +------+------+
                 v
          +-------------+     +-------------+          +-------------+
          | dreg stage0 | --> | dreg stage1 | --> ...  | dreg stage  |
          +-------------+     +-------------+          | D_phy-1     |
                                                       +------+------+
                                                              |
                                                              v
                                                       arrived record
```

The gather takes the lanes that arrived in this cycle and shifts them out one per cycle, so `unpack` keeps a 256-bit input.

```text
 lane0 record --+
 lane1 record --+--> +----------+     +-----------+
 ...            |    | lane_mux | --> | dreg 256  | --> out_flit[255:0]
 laneN record --+    | sel = rr |     | + valid   |
                     +----------+     +-----------+
```

### 5f. Unpack

The reverse of the packer shift.

```text
 out_flit[255:0]
        |
        v
 +-------------+
 | shift >> 8  |  low byte is the next panel_byte
 +------+------+
        v
 +-------------+
 | byte_mux    |  sel = take_byte
 +------+------+
        v
 +-------------+
 | dreg 256    |
 +-------------+
        |
        +--> panel_byte[7:0]
        +--> out_tile[7:0], out_panel_sel
```

### 5g. Release hold

```text
 release_en   W[7:0]   admit_limit[7:0]   square_finished
      |          |            |                  |
      v          v            v                  v
 +------------------------------------------------------+
 | release                                              |
 |                                                      |
 |  admitted[7:0] -- dreg                               |
 |       |                                              |
 |       v                                              |
 |  cmp < admit_limit --+--> let the next square into   |
 |                      |    the packer                 |
 |  square_finished ----+--> admitted - 1               |
 |                                                      |
 |  k_cnt dreg -- + C_TILE -- cmp time --> release_en   |
 |  wave: the same cmp lets W squares through together  |
 +------------------------------------------------------+
```

## Leaf cells

| Cell | Where it sits | Job |
| --- | --- | --- |
| `dreg` | packer, ready, credit, PHY, gather, unpack, release, CU | stores the value |
| `word_mux`, `src_mux`, `read_mux`, `policy_mux`, `cnt_mux`, `load_mux`, `lane_mux`, `byte_mux` | the blocks in layer 5 | pick one input |
| `shift << 8` | packer | one new byte into the high side of the flit |
| `shift >> 8` | unpack | one byte out of the flit |
| `shift` of records | PHY | move one stage closer to the compute die |
| `addsub` | credit, release counters | count up or down |
| `cmp` | packer fire, credit `> 0`, scheduler `cmp_min`, release versus `admit_limit` | a select bit |

The five score blocks are not in this table. Their ports are layer 4.

## What a later wire changes

| Pin | Layer that owns it |
| --- | --- |
| `send_en[*]`, `grant_idx[*]`, `grant_valid[*]` | the boundary drawn in layer 1 |
| accept count inside `credit` | layer 5d |
| delay lanes inside `phy_box` | layer 3 |

Release, packer, `ready`, the five score blocks, and unpack keep the ports drawn above.
