#!/bin/bash
# Key builds first (FCFS and EDF at K=8 and K=16), then the other six.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOG="$ROOT/results/ppa/logs/openlane_all.txt"
mkdir -p "$ROOT/results/ppa/logs"
echo "start $(date -Is)" > "$LOG"
order="0 8
0 16
1 8
1 16
2 8
2 16
3 8
3 16
4 8
4 16"
while read -r pol k; do
  [ -n "$pol" ] || continue
  echo "BEGIN p${pol}_k${k} $(date -Is)" | tee -a "$LOG"
  if "$ROOT/results/ppa/scripts/run_openlane.sh" "$pol" "$k"; then
    echo "END p${pol}_k${k} exit 0 $(date -Is)" | tee -a "$LOG"
  else
    echo "END p${pol}_k${k} exit $? $(date -Is)" | tee -a "$LOG"
  fi
done <<< "$order"
echo "ALL_DONE $(date -Is)" | tee -a "$LOG"
