# D2D hop adapter: verified schematics (doc-only source, commit 8a0d7dd)
Open index.html (offline): tabs per view, click a box to go inside, "up to parent" / back links.
Views: L1 top (hop_top) | L2 cu (hop_control), pu (hop_processing) | L3 fsm, release, packer, ready,
sched, credit, phy, unpack (leaves: dregs, muxes, comparators, adders, constants).
Rebuild:  python3 build_spec.py && python3 layout.py && python3 check.py && ./render.sh
Prove:    python3 break_demo.py   (14 deliberate breaks, each must make check.py exit 1)
RTL pins: python3 rtl_pins.py > rtl_pins.txt
Findings: findings.md (F1-F30; several are closed in the netlist, see the note at the top).
Inputs: source/ (doc, workflow doc, Grok script + html, old rtl).
Coordinates are hand-placed in layout.py; there is no auto-router.
