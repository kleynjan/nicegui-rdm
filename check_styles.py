"""
CSS audit script for ng_rdm.css.

Extracts all .rdm-* class definitions from the CSS file and cross-references
them against usage in Python source files, reporting:
  - Unused classes (defined in CSS, not referenced in Python)
  - Missing classes (referenced in Python, not defined in CSS)
  - Duplicate selectors (same class defined in multiple rule blocks)

Usage:
    python check_styles.py
    python check_styles.py --consumer /path/to/consumer/app
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

CSS_FILE = Path('src/ng_rdm/components/ng_rdm.css')
SRC_DIR = Path('src/ng_rdm')

# Known color variants for dynamic f-string patterns in button.py
COLOR_VARIANTS = ['default', 'primary', 'secondary', 'success', 'warning', 'danger', 'text']

# F-string class templates: prefix -> list of suffixes
DYNAMIC_TEMPLATES: dict[str, list[str]] = {
    'rdm-btn': COLOR_VARIANTS,
    'rdm-btn-icon': COLOR_VARIANTS,
    'rdm-icon': COLOR_VARIANTS,
}


# ---------------------------------------------------------------------------
# CSS parsing
# ---------------------------------------------------------------------------

def extract_css_classes(css_path: Path) -> dict[str, list[int]]:
    """Return {class_name: [line_numbers]} for all active .rdm-* class selectors."""
    result: dict[str, list[int]] = defaultdict(list)
    in_block_comment = False

    for i, line in enumerate(css_path.read_text().splitlines(), 1):
        stripped = line.strip()

        # Track block comments /* ... */
        if '/*' in stripped:
            in_block_comment = True
        if in_block_comment:
            if '*/' in stripped:
                in_block_comment = False
            continue

        for match in re.finditer(r'\.(rdm-[a-zA-Z0-9_-]+)', line):
            result[match.group(1)].append(i)

    return dict(result)


def find_duplicate_selectors(css_classes: dict[str, list[int]]) -> dict[str, list[int]]:
    """Return classes whose selector appears in more than one distinct rule block."""
    return {cls: lines for cls, lines in css_classes.items() if len(set(lines)) > 1}


# ---------------------------------------------------------------------------
# Python scanning
# ---------------------------------------------------------------------------

def expand_dynamic_classes(template: str) -> list[str]:
    """Expand f-string template like 'rdm-btn-{color}' to concrete class names."""
    for prefix, variants in DYNAMIC_TEMPLATES.items():
        pattern = re.compile(re.escape(prefix) + r'-\{[^}]+\}')
        if pattern.search(template):
            return [f'{prefix}-{v}' for v in variants]
    return []


def scan_python_file(path: Path) -> set[str]:
    """Return all rdm-* class names referenced in a Python file."""
    content = path.read_text()
    found: set[str] = set()

    # 1. F-string templates first: f'rdm-btn-{color}' etc.
    #    Process before literal scan to avoid double-counting truncated prefixes.
    fstring_spans: list[tuple[int, int]] = []
    for m in re.finditer(r'f["\']([^"\']*rdm-[^"\']*\{[^}]+\}[^"\']*)["\']', content):
        fstring_spans.append((m.start(), m.end()))
        expanded = expand_dynamic_classes(m.group(1))
        found.update(expanded)  # may be empty if template not recognised — that's fine

    # 2. Literal strings outside f-string spans
    for m in re.finditer(r'["\']([^"\']*rdm-[^"\']*)["\']', content):
        # Skip if this match overlaps an already-processed f-string
        if any(s <= m.start() <= e for s, e in fstring_spans):
            continue
        for cls in re.findall(r'rdm-[a-zA-Z0-9_-]+', m.group(1)):
            if not cls.endswith('-'):  # skip truncated f-string fragments
                found.add(cls)

    # 3. _css_class attribute assignments
    for m in re.finditer(r'_css_class\s*=\s*["\']([^"\']+)["\']', content):
        for cls in m.group(1).split():
            if cls.startswith('rdm-'):
                found.add(cls)

    return found


def scan_directory(directory: Path) -> dict[str, set[str]]:
    """Return {class_name: {file_paths}} for all rdm-* references in .py files."""
    usage: dict[str, set[str]] = defaultdict(set)
    root = Path.cwd().resolve()
    for py_file in directory.resolve().rglob('*.py'):
        label = str(py_file.relative_to(root)) if py_file.is_relative_to(root) else str(py_file)
        for cls in scan_python_file(py_file):
            usage[cls].add(label)
    return dict(usage)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_section(title: str, items: list[str]) -> None:
    print(f'\n{"=" * 60}')
    print(f'  {title} ({len(items)})')
    print('=' * 60)
    for item in sorted(items):
        print(f'  {item}')
    if not items:
        print('  (none)')


def main() -> None:
    parser = argparse.ArgumentParser(description='Audit ng_rdm.css for unused/missing classes.')
    parser.add_argument('--consumer', metavar='PATH', help='Also scan a consumer app directory')
    args = parser.parse_args()

    if not CSS_FILE.exists():
        print(f'Error: {CSS_FILE} not found. Run from the project root.', file=sys.stderr)
        sys.exit(1)

    # --- Extract CSS definitions ---
    css_classes = extract_css_classes(CSS_FILE)
    print(f'CSS: {len(css_classes)} distinct rdm-* class names in {CSS_FILE}')

    # --- Scan Python usage ---
    usage = scan_directory(SRC_DIR)
    if args.consumer:
        consumer_path = Path(args.consumer)
        if not consumer_path.exists():
            print(f'Warning: consumer path {consumer_path} not found', file=sys.stderr)
        else:
            consumer_usage = scan_directory(consumer_path)
            for cls, files in consumer_usage.items():
                if cls not in usage:
                    usage[cls] = set()
                usage[cls].update(files)
            print(f'Consumer: also scanned {consumer_path}')

    print(f'Python: {len(usage)} distinct rdm-* class names referenced')

    # --- Cross-reference ---
    defined = set(css_classes.keys())
    referenced = set(usage.keys())

    unused = defined - referenced
    missing = referenced - defined

    duplicates = find_duplicate_selectors(css_classes)

    # --- Output ---
    print_section('UNUSED (defined in CSS, not found in Python)', list(unused))

    if missing:
        print_section('MISSING from CSS (referenced in Python, not defined)', list(missing))

    if duplicates:
        print('\n' + '=' * 60)
        print(f'  DUPLICATE SELECTORS ({len(duplicates)})')
        print('=' * 60)
        for cls, lines in sorted(duplicates.items()):
            print(f'  .{cls}  — lines: {lines}')

    # Usage detail for referenced classes
    print('\n' + '=' * 60)
    print('  USAGE DETAIL (referenced classes with file counts)')
    print('=' * 60)
    for cls in sorted(referenced & defined):
        files = usage[cls]
        print(f'  {cls:<45} {len(files)} file(s)')


if __name__ == '__main__':
    main()
