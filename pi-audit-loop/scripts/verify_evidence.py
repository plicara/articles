#!/usr/bin/env python3
"""Export article evidence from the original logs and deterministic fixture checks."""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def session(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    calls = {}
    reviews = []
    changes = []
    states = []
    name = path.stem
    model = None
    fixture = None
    command = None
    successful_tests = 0
    skill_read = False
    rejections = []
    for row in rows:
        kind = row.get('type')
        if kind == 'session':
            fixture = Path(row['cwd']).name
        elif kind == 'session_info':
            name = row['name']
        elif kind == 'model_change':
            model = row['provider'] + '/' + row['modelId']
        elif kind == 'custom' and row.get('customType') == 'audit_loop_state':
            states.append(row['data'])
        message = row.get('message', {})
        for content in message.get('content', []):
            if not isinstance(content, dict) or content.get('type') != 'toolCall':
                continue
            tool, args = content['name'], content.get('arguments', {})
            calls[content['id']] = content
            if tool == 'audit_loop_start':
                command = args.get('test_command')
                successful_tests = 0
            elif tool == 'audit_review':
                reviews.append({'verdict': args.get('verdict'), 'findings': args.get('findings', 0),
                                'successful_test_results_before_call': successful_tests})
            elif tool == 'audit_simplify':
                changes.append(args.get('changed', False))
            elif tool == 'read' and 'SKILL.md' in args.get('path', args.get('file_path', '')):
                skill_read = True
        if message.get('role') != 'toolResult':
            continue
        call = calls.get(message.get('toolCallId'), {})
        text = '\n'.join(c.get('text', '') for c in message.get('content', []) if isinstance(c, dict))
        if 'audit_rejected' in text:
            rejections.append(text)
        invoked = call.get('arguments', {}).get('command', '')
        if call.get('name') == 'bash' and command and ' '.join(command.split()) in ' '.join(invoked.split()):
            if not message.get('isError', False):
                successful_tests += 1
    terminal = states[-1] if states else {}
    return {'name': name, 'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'model': model, 'fixture': fixture, 'probe': name.startswith('gate-probe'),
            'reviews': reviews, 'simplify_changed': changes, 'skill_read_call': skill_read,
            'rejections': rejections, 'gate': terminal.get('doneReason'),
            'terminal_findings': terminal.get('lastFindings'),
            'has_enforced_test_state': any('testVerified' in s for s in states)}


def fixture_checks():
    checks = []
    for fixture in sorted((ROOT / 'scripts/matrix/fixtures').iterdir()):
        if not fixture.is_dir():
            continue
        run = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
                             cwd=fixture, capture_output=True, text=True)
        checks.append({'fixture': fixture.name, 'exit_code': run.returncode, 'output': run.stderr.strip()})
    path = ROOT / 'scripts/matrix/fixtures/D-failing/tests/test_window.py'
    sys.path.insert(0, str(path.parents[1]))
    spec = importlib.util.spec_from_file_location('window_tests', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def candidate(items, n):
        if n < 0:
            raise ValueError('n must be non-negative')
        return list(items[len(items) - n:])
    module.last_n = candidate
    import io
    import unittest
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    sweep = [{'n': n, 'expected': list(range(1, 4))[-n:] if n else [],
              'candidate': candidate([1, 2, 3], n)} for n in range(9)]
    return {'baseline': checks, 'candidate_suite': {'tests': result.testsRun,
            'successful': result.wasSuccessful(), 'output': output.getvalue().strip()}, 'slice_sweep': sweep}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, required=True)
    args = parser.parse_args()
    matrix = [session(p) for p in sorted((args.original / 'matrix/runs').glob('*.jsonl'))]
    dogfood = [session(p) for p in sorted((args.original / 'dogfood/runs').glob('*.jsonl'))]
    sessions = matrix + dogfood
    normal = [s for s in sessions if not s['probe']]
    clean = [r for s in normal for r in s['reviews'] if r['verdict'] == 'clean']
    initial = [s for s in matrix if not s['probe'] and '-v2' not in s['name'] and '-v3' not in s['name'] and '-gate' not in s['name']]
    b_runs = {m: [int(s['reviews'][0]['findings'] > 0) for s in initial
                  if s['fixture'] == 'B-simplify' and m in s['model']]
              for m in ['muse', 'deepseek', 'luna']}
    recorded = {}
    for p in sorted((args.original / 'dogfood/runs').glob('*.jsonl')):
        for row in [json.loads(line) for line in p.read_text().splitlines() if line]:
            message = row.get('message', {})
            for content in message.get('content', []):
                if not isinstance(content, dict):
                    continue
                if content.get('type') == 'toolCall' and content.get('name') == 'bash':
                    cmd = content.get('arguments', {}).get('command', '')
                    match = re.search(r'for i := 0; i < (\d+); i\+\+', cmd)
                    if match and 'total read errors:' in cmd:
                        recorded['concurrency_calls'] = int(match[1])
                if message.get('role') == 'toolResult':
                    output = content.get('text', '')
                    match = re.search(r'^total read errors: (\d+)$', output, re.M)
                    if match:
                        recorded['concurrency_failures'] = int(match[1])
                    match = re.search(r'^(\d+) passed, (\d+) skipped', output, re.M)
                    if match and int(match[1]) > 1000:
                        recorded['sqlite_passed'], recorded['sqlite_skipped'] = map(int, match.groups())
    data = {'source': 'Original local JSONL; hashes and session names retained, transcripts excluded.',
            'sessions': sessions, 'aggregate': {'fixture_runs': len([s for s in matrix if not s['probe']]),
            'real_repository_runs': len(dogfood), 'probes': len(sessions) - len(normal),
            'non_probe_runs': len(normal), 'clean_calls': len(clean),
            'clean_with_prior_successful_test_result': sum(r['successful_test_results_before_call'] > 0 for r in clean),
            'non_probe_rejections': sum(len(s['rejections']) for s in normal),
            'terminal_states': dict(Counter(s['gate'] for s in normal)),
            'discarded_logs': len(list((args.original / 'matrix/runs/invalid').glob('*.jsonl'))),
            'initial_runs': len(initial), 'duplication_detection': b_runs},
            'skill_read_cohorts': [{'name': 'initial matrix plus v2', 'total': len(initial) + 3,
                'read_calls': sum(s['skill_read_call'] for s in matrix if s in initial or '-v2' in s['name'])},
                {'name': 'v2 only', 'total': 3, 'read_calls': sum(s['skill_read_call'] for s in matrix if '-v2' in s['name'])}],
            'recorded_probes': recorded, 'deterministic_checks': fixture_checks()}
    out = ROOT / 'results/evidence.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({k: v for k, v in data.items() if k not in ['sessions', 'source']}, indent=2))


if __name__ == '__main__':
    main()
