#!/bin/sh
# render each view to <view>.png at 1600 px wide with headless Chrome
cd "$(dirname "$0")"
for v in top cu fsm pu release packer ready sched credit phy unpack; do
  h=$(python3 -c "import json;L=json.load(open('layout_$v.json'));print(round(L['H']*1600/L['W']))")
  google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1600,$h --screenshot="$PWD/$v.png" "file://$PWD/render_$v.html" 2>/dev/null
done
ls -l *.png
