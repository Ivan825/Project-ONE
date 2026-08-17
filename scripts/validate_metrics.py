#!/usr/bin/env python3
"""M2 metric-validation gate: observer measurements checked against constructed
cases with known answers. Exit code 0 = validated pipeline."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    r = subprocess.run(
        [sys.executable, "-m", "pytest",
         os.path.join(HERE, "..", "tests", "test_metrics.py"), "-q"])
    if r.returncode == 0:
        print("Metric pipeline validated: fragmentation, centralization, "
              "inequality, cooperation and turnover all match known cases.")
    sys.exit(r.returncode)
