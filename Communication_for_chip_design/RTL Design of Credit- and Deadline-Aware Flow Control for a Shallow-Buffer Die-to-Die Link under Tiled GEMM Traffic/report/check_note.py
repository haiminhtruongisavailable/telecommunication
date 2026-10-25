#!/usr/bin/env python3
"""Writing checks for report/d2d_architecture.tex. Exit 1 on any FAIL."""
import re
import sys
from pathlib import Path

tex = Path(__file__).with_name("d2d_architecture.tex").read_text()
fails = []

def fail(rule, detail):
    fails.append(f"FAIL {rule}: {detail}")

# 1. Acronym expansion appears before the first bare use.
expansions = {
    "D2D": "die-to-die",
    "GEMM": "general matrix multiply",
    "RTL": "register-transfer level",
    "FCFS": "first-come, first-served",
    "EDF": "earliest deadline first",
    "PHY": "physical layer",
    "CXL": "Compute Express Link",
}
low = tex.lower()
for acr, exp in expansions.items():
    bare = re.search(rf"\b{acr}\b", tex)
    exp_at = low.find(exp.lower())
    if bare is None:
        fail("acronym", f"{acr} is never used")
        continue
    if exp_at < 0 or exp_at > bare.start():
        line = tex[: bare.start()].count("\n") + 1
        fail("acronym", f"{acr} at line {line} appears before '{exp}'")

if r"\section{Glossary}" in tex or "for the teacher" in tex:
    fail("glossary", "glossary table or teacher aside is still present")

# 3. The bench states the count. It does not list one row per case.
if "22 cases in three groups" not in tex:
    fail("count", "opening count sentence missing")
low_tex = tex.lower()
if "index 7" not in low_tex or "16, 4, 12, and 8" not in low_tex:
    fail("count", "testbench dropped the pair indices or the case 11 scores")
bench = tex.split(r"\section{Testbench}", 1)[-1].split(r"\section{", 1)[0]
if "tb_cases" in bench or "cases_1_22" in bench or ".v" in bench:
    fail("count", "testbench section names a source file")
if re.search(r"\\item 2, firing|\\item 3, shared|\\item 4, row\b|& firing &|& shared &|& row &", tex):
    fail("policy-name", "informal fill name firing, shared, or row is still a policy label")
for formal in ("shortest remaining", "most consumers", "longest remaining"):
    if formal not in tex:
        fail("policy-name", "missing formal name " + formal)
if re.search(r"bit 4[0-9]|bit 0", tex):
    fail("count", "testbench still names a score bit")
rows = re.findall(r"^(\d+) & (pair|tree|mutant) &", tex, re.M)
if len(rows) != 22:
    fail("count", f"case table has {len(rows)} rows, expected 22")
if "Expected" not in tex or "Result" not in tex:
    fail("count", "case table is missing Expected or Result")

# 4. The English word square is forbidden.
# Verilog port names that contain those letters are listed and still fail
# the skill's substring grep. Report them as their own rule.
ports = {"let_square", "square_finished"}
bare_sq = []
for i, line in enumerate(tex.splitlines(), 1):
    raw = line.replace(r"\_", "_")
    if re.search(r"\bsquare\b", raw) and not any(p in raw for p in ports):
        bare_sq.append(i)
if bare_sq:
    fail("square-word", "bare word square on lines " + ",".join(map(str, bare_sq)))
# Source port names contain the letters of the forbidden English word.
# The bare word still fails above. A hit that is only those ports is allowed
# because the name must match the Verilog.
allowed = ("let_square", "square_finished")
for i, line in enumerate(tex.splitlines(), 1):
    raw = line.replace(r"\_", "_")
    if "square" not in raw:
        continue
    leftover = raw
    for name in allowed:
        leftover = leftover.replace(name, "")
    if "square" in leftover:
        fail("square-port", f"line {i} has square outside the Verilog port names")

if "no driver" not in tex or "not pins of" not in tex:
    fail("sheet", "the no-driver stubs on the editor sheets are not explained")
if r"\section{Done}" in tex:
    fail("frame", "Done section is present")

# The measurement campaign is the strategy, not a proposition subsection.
def campaign_outside(document):
    if r"\subsection{Evaluation}" in document or "This note declares the measurement" in document:
        return True
    start = document.find(r"\section{Strategy}")
    if start < 0:
        return True
    return "same hop and the same traffic" in document[:start]

if campaign_outside(tex):
    where = tex.find(r"\subsection{Evaluation}")
    if where < 0:
        where = tex.find("This note declares the measurement")
    if where < 0:
        where = tex.find("same hop and the same traffic")
    n = tex[: max(where, 0)].count("\n") + 1
    fail("strategy", f"measurement is still outside Strategy, near line {n}")
strat = tex.find(r"\section{Strategy}")
body = tex[strat:] if strat >= 0 else ""
for needle in (
    r"N\_WIRES",
    "one leaf per receive slot",
    r"B_{\mathrm{useful}}",
    r"N_{\mathrm{GEMM}}",
    r"N_{\mathrm{other}}",
    r"L_k",
):
    if needle not in body:
        fail("strategy", "Strategy is missing " + needle)
planted_eval = tex.replace(
    r"\section{Proposed policies}",
    "\\subsection{Evaluation}\nThis note declares the measurement.\n\\section{Proposed policies}",
    1,
)
if not campaign_outside(planted_eval):
    fail("strategy", "planted Evaluation probe did not trip the rule")
needed = ["figpath", "figcu", "figpu", "figrelease", "figpacker", "figready", "figsched", "figcredit", "figphy", "figunpack"]
for name in needed:
    if "\\" + name not in tex:
        fail("figure", name + " is missing")

# Spoken words from REPORT.md
spoken = re.findall(r"(?i)\b(buys|fight|favorite|runner-up|TODO|CHANGE|\bban\b)\b", tex)
if spoken:
    fail("spoken", " ".join(spoken))

# Prove the bare-word rule. A planted sentence must fail, then this file must pass.
planted = tex + "\nOne square waits.\n"
plant_hit = False
for line in planted.splitlines():
    raw = line.replace(r"\_", "_")
    if re.search(r"\bsquare\b", raw) and not any(p in raw for p in ports):
        plant_hit = True
if not plant_hit:
    fail("square-word", "planted probe did not trip the bare-word rule")

if fails:
    print("\n".join(fails))
    sys.exit(1)
print("ALL PASS")
print("bench table, 22 rows, no source file")
print(f"acronyms {len(expansions)}")
print("probe: planted 'one square' trips square-word")
