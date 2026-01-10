#!/usr/bin/env python3
"""Run tests with coverage - run all tests in batches."""
import subprocess
import sys
import os

# Change to the testing directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Define test batches - split to avoid Qt cleanup issues
batches = [
    ['TestCodeEditor', 'TestAutoIndentation', 'TestBracketMatching', 'TestFileTreeView'],
    ['TestTextEditorMainWindow', 'TestLineNumberArea', 'TestEditorSelection', 'TestUndoRedo'],
    ['TestFileOperations'],
    ['TestCheckSaveDialog'],
    ['TestFindDialog'],
    ['TestCloseEvent'],
    ['TestMainFunction'],
    ['TestFileDialogs'],
    ['TestEnterBetweenBracketsWithIndent', 'TestSelectionAtBlockStart'],
]

# Remove old coverage data
try:
    os.remove('.coverage')
except:
    pass

all_passed = True
total_tests = 0

for i, batch in enumerate(batches):
    test_args = [f'test_text_editor.py::{tc}' for tc in batch]
    cmd = [sys.executable, '-m', 'coverage', 'run']
    if i > 0:
        cmd.append('--append')
    cmd.extend(['--source=../text_editor', '-m', 'pytest', '-q', '--tb=no'] + test_args)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(result.stdout, end='')
    if result.returncode != 0:
        all_passed = False
        print(result.stderr)
    
    # Count passed tests
    for line in result.stdout.split('\n'):
        if 'passed' in line:
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    total_tests += int(p)
                    break

# Generate report
print(f"\n{'=' * 70}")
print(f"TOTAL: {total_tests} tests passed")
print(f"{'=' * 70}")
print("COVERAGE REPORT")
print('=' * 70)

import coverage
cov = coverage.Coverage()
cov.load()
cov.report(show_missing=True)

sys.exit(0 if all_passed else 1)
