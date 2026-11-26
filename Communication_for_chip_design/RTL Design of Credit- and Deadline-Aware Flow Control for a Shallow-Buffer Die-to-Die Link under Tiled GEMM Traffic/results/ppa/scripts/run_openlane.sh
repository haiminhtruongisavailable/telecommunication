#!/bin/bash
# Place and route one mapped hop_path. Same clock, die, and density for every build.
set -euo pipefail
POLICY="${1:?policy}"
K="${2:?k}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DESIGN="$ROOT/results/ppa/openlane/p${POLICY}_k${K}"
VLOG="/work/results/ppa/yosys/p${POLICY}_k${K}/hop_path_mapped.v"
IMAGE="ghcr.io/the-openroad-project/openlane:ff5509f65b17bfa4068d5336495ab1718987ff69"
PDK_HOST="${PDK_HOST:-$HOME/.ciel/ciel/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af}"
TEMPLATE="${CONFIG_TEMPLATE:-$ROOT/results/ppa/scripts/openlane_config.tcl}"
mkdir -p "$DESIGN"
sed "s|VERILOG_LIST|$VLOG|" "$TEMPLATE" > "$DESIGN/config.tcl"
# The template uses the token VERILOG_LIST. Put the real path in.
if ! grep -q "$VLOG" "$DESIGN/config.tcl"; then
  echo "config did not receive the verilog path" >&2
  exit 1
fi
echo "POLICY=${POLICY} K=${K}" > "$DESIGN/run.txt"
echo "image: ${IMAGE}" >> "$DESIGN/run.txt"
echo "pdk: sky130A sky130_fd_sc_hd tt 25C 1.80V" >> "$DESIGN/run.txt"
echo "pdk_host: ${PDK_HOST}" >> "$DESIGN/run.txt"
grep 'CLOCK_PERIOD)\|DIE_AREA)\|DRT_OPT_ITERS)' "$DESIGN/config.tcl" >> "$DESIGN/run.txt"
docker run --rm -v "$ROOT:/work" "$IMAGE" \
  rm -rf "/work/results/ppa/openlane/p${POLICY}_k${K}/runs"
set +e
docker run --rm \
  -v "$ROOT:/work" \
  -v "$PDK_HOST:/build/pdk" \
  -e PDK_ROOT=/build/pdk \
  -e PDK=sky130A \
  -e PWD=/openlane \
  -w /openlane \
  "$IMAGE" \
  ./flow.tcl -design "/work/results/ppa/openlane/p${POLICY}_k${K}" -tag run -overwrite \
  > "$DESIGN/flow.console" 2>&1
flow_rc=$?
set -e
echo "openlane_exit: ${flow_rc}" >> "$DESIGN/run.txt"
if [ "$flow_rc" -ne 0 ]; then
  exit "$flow_rc"
fi
sed "s#BUILD#p${POLICY}_k${K}#" "$ROOT/results/ppa/scripts/report_area.tcl" > "$DESIGN/report_area.tcl"
docker run --rm \
  -v "$ROOT:/work" \
  -v "$PDK_HOST:/build/pdk" \
  -e PDK_ROOT=/build/pdk \
  -e PDK=sky130A \
  "$IMAGE" /build/bin/openroad -exit "/work/results/ppa/openlane/p${POLICY}_k${K}/report_area.tcl" \
  > "$DESIGN/area_design.log" 2>&1
echo "area_exit: $?" >> "$DESIGN/run.txt"
