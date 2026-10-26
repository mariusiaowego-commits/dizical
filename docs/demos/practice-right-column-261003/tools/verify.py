#!/usr/bin/env python3
"""
tools/verify.py - Proxy to tools/verify.js using Node.js
"""
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFY_JS = os.path.join(SCRIPT_DIR, "verify.js")

def main():
    cmd = ["node", VERIFY_JS] + sys.argv[1:]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
