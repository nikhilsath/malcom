#!/usr/bin/env python3
"""
Simple validator to detect duplicated step numbers within .agents task files.
Run: python3 scripts/validate_task_steps.py
Exits with non-zero code if duplicates are found.
"""
import re
import sys
from pathlib import Path

TASK_DIR = Path('.github/tasks')
PATTERN = re.compile(r'^\s*(\d+)\.\s*\[')
SECTION_TITLES = [
    'Execution steps',
    'Test impact review',
    'Testing steps',
    'Documentation review',
    'GitHub update',
]

errors = []
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--all', action='store_true', help='Check both open and closed tasks')
args = parser.parse_args()

subdirs = ('open', 'closed') if args.all else ('open',)

for subdir in subdirs:
    dirpath = TASK_DIR / subdir
    if not dirpath.exists():
        continue
    for p in sorted(dirpath.glob('*.md')):
        text = p.read_text()
        lines = text.splitlines()

        # Build section ranges by locating title lines
        title_indices = {}
        for idx, line in enumerate(lines):
            if line.strip() in SECTION_TITLES:
                title_indices[line.strip()] = idx

        # For each defined section, examine its lines (from title to next title or EOF)
        for i, title in enumerate(SECTION_TITLES):
            if title not in title_indices:
                continue
            start = title_indices[title] + 1
            # find next title index after start
            end = len(lines)
            for other_title in SECTION_TITLES[i+1:]:
                if other_title in title_indices and title_indices[other_title] > title_indices[title]:
                    end = title_indices[other_title]
                    break

            nums = []
            for lineno, line in enumerate(lines[start:end], start=start+1):
                m = PATTERN.match(line)
                if m:
                    nums.append((m.group(1), lineno))

            seen = {}
            for num, lineno in nums:
                if num in seen:
                    errors.append(f"{p}: duplicate step number {num} in section '{title}' (lines {seen[num]} and {lineno})")
                else:
                    seen[num] = lineno

if errors:
    print("Duplicate step numbers found in task files (per-section):")
    for e in errors:
        print(" - ", e)
    sys.exit(2)

print("No duplicate task step numbers found in task files.")
sys.exit(0)
