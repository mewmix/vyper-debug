# fuzz/scripts/minimize_failure.py
import json, os, subprocess, sys

FAIL_DIR = os.path.join(os.getcwd(), "fuzz_failures")
if len(sys.argv) < 2:
    print("usage: minimize_failure.py fail_file.json")
    sys.exit(2)

fname = sys.argv[1]
with open(fname) as f:
    fail = json.load(f)

print("Failure:", fail)
# For now we just print the failure and leave it for manual reduction.
# You can extend this to run Hypothesis with specific seeds or to
# rewrite the state machine to only run the failing trace.
