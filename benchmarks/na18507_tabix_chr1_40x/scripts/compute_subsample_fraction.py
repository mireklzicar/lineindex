#!/usr/bin/env python3
import sys, math

if len(sys.argv) != 3:
    print("Usage: compute_subsample_fraction.py <current_depth> <target_depth>", file=sys.stderr)
    sys.exit(1)

current = float(sys.argv[1])
target  = float(sys.argv[2])
if current <= 0:
    print("0.0")
    sys.exit(0)

f = target / current
# samtools -s expects a float in (0,1]; cap and print 6 decimals
f = min(max(f, 0.0), 1.0)
print(f"{f:.6f}")
