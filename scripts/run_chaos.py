#!/usr/bin/env python3
"""Run Kanyx chaos tests in temporary directories and write a JSON report.

Usage: py scripts/run_chaos.py [--full] [--seed 12648430] [--report report.json]
Does not open or write the user's real Kanyx workspace.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest


def main() -> int:
    ap = argparse.ArgumentParser(description='Isolated Kanyx chaos/robustness suite')
    ap.add_argument('--full', action='store_true', help='1,000 fuzz iterations and 32 MiB attachment')
    ap.add_argument('--seed', type=int, default=12648430, help='Reproducible random seed')
    ap.add_argument('--iterations', type=int, help='Override number of fuzz iterations')
    ap.add_argument('--large-mb', type=int, help='Override large test file in MiB (1–64)')
    ap.add_argument('--report', default='chaos_report.json', help='JSON report destination')
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    if not (root / 'db.py').is_file() or not (root / 'portability.py').is_file():
        ap.error('Run from a Kanyx repository: db.py / portability.py missing')

    os.environ['KANYX_CHAOS_SEED'] = str(args.seed)
    os.environ['KANYX_CHAOS_ITERATIONS'] = str(args.iterations if args.iterations is not None else (1000 if args.full else 200))
    os.environ['KANYX_CHAOS_BIG_MB'] = str(args.large_mb if args.large_mb is not None else (32 if args.full else 8))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    sys.path.insert(0, str(root))

    suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_chaos*.py')
    print('Kanyx CHAOS:', os.environ['KANYX_CHAOS_ITERATIONS'], 'seeded iterations; ',
          os.environ['KANYX_CHAOS_BIG_MB'], 'MiB binary; seed', args.seed, flush=True)
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed = round(time.perf_counter() - start, 3)

    def item_name(case):
        return case.id() if hasattr(case, 'id') else str(case)

    report = {
        'suite': 'Kanyx chaos / robustness',
        'seed': args.seed,
        'iterations': int(os.environ['KANYX_CHAOS_ITERATIONS']),
        'large_attachment_mib': int(os.environ['KANYX_CHAOS_BIG_MB']),
        'elapsed_seconds': elapsed,
        'tests_run': result.testsRun,
        'passed': result.testsRun - len(result.failures) - len(result.errors)
                  - len(result.skipped) - len(result.expectedFailures) - len(result.unexpectedSuccesses),
        'failures': [{'test': item_name(t), 'traceback': tb} for t, tb in result.failures],
        'errors': [{'test': item_name(t), 'traceback': tb} for t, tb in result.errors],
        'skipped': [{'test': item_name(t), 'reason': why} for t, why in result.skipped],
        'known_issues_expected_failures': [{'test': item_name(t), 'traceback': tb} for t, tb in result.expectedFailures],
        'known_issue_unexpected_successes': [item_name(t) for t in result.unexpectedSuccesses],
        'overall_success': result.wasSuccessful(),
        'real_user_data_touched': False,
    }
    report_path = Path(args.report).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf8')
    print('\nSummary: %s | %s tests | %s expected known issues | %s skipped | %.2fs' %
          ('PASS' if result.wasSuccessful() else 'FAIL', result.testsRun,
           len(result.expectedFailures), len(result.skipped), elapsed))
    print('Report:', report_path)
    if result.skipped:
        print('NOTE: Skipped GUI tests need PySide6 / the Windows development environment.')
    if result.expectedFailures:
        print('NOTE: expected failures are CONFIRMED, UNFIXED application issues, not successes.')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
