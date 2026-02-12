#!/usr/bin/env python3
"""Run tests with coverage and produce a report."""
import subprocess
import sys
import os

# Change to the testing directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Absolute path to the source file for coverage tracking
source_file = os.path.abspath(os.path.join('..', 'text_editor.py'))

# Remove old coverage data
try:
    os.remove('.coverage')
except FileNotFoundError:
    pass

# Run all tests with coverage in a single invocation
cmd = [
    sys.executable, '-m', 'coverage', 'run',
    '--include', source_file,
    '-m', 'pytest', '-q', 'test_text_editor.py',
]

print(f"Running: {' '.join(cmd)}\n")
result = subprocess.run(cmd, timeout=120)

# Generate report
print(f"\n{'=' * 70}")
print("COVERAGE REPORT")
print('=' * 70)
subprocess.run([sys.executable, '-m', 'coverage', 'report', '--show-missing'])

sys.exit(result.returncode)
