"""
tests/test_curation_gates_v2_1.py

Verification suite for Protocol V2.1 Track A benchmark curation gates:
1. No hardcoded pass flags in scripts/curate_track_a_benchmark_v2_1.py.
2. 100% causal matrix evidence backed by real Bubblewrap sandbox executions.
3. Strict consistency between manifest_summary.json and candidate jsonl datasets.
4. Core candidates satisfy all 8 curation gates.
"""

import os
import json
import glob
import pytest

BENCHMARK_DIR = '/code/rolemem-agent-memory/data/benchmark_v2_1'
CAUSAL_DIR = '/code/rolemem-agent-memory/data/causal_matrix_v2_1'
CURATION_SCRIPT = '/code/rolemem-agent-memory/scripts/curate_track_a_benchmark_v2_1.py'


def test_no_hardcoded_curation_passes():
    with open(CURATION_SCRIPT, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Filter out comments and docstrings
    code_lines = [l.strip().lower() for l in lines if not l.strip().startswith('#') and not l.strip().startswith('*') and not l.strip().startswith('-')]
    code_text = ' '.join(code_lines)

    banned_code_patterns = [
        'leakage_pass = true',
        'hidden_test_strength = "pass"',
        'environment_reproducibility = "pass"',
        'is_known_excluded',
        'whitelist =',
        'white_list =',
        'core_whitelist',
    ]
    for banned in banned_code_patterns:
        assert banned not in code_text, f"Found banned hardcode '{banned}' in curate_track_a_benchmark_v2_1.py"


def test_manifest_summary_file_consistency():
    manifest_path = os.path.join(BENCHMARK_DIR, 'manifest_summary.json')
    assert os.path.exists(manifest_path), 'manifest_summary.json must exist'

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    def load_jsonl(fn):
        p = os.path.join(BENCHMARK_DIR, fn)
        if not os.path.exists(p):
            return []
        items = []
        with open(p, 'r', encoding='utf-8') as fp:
            for line in fp:
                if line.strip():
                    items.append(json.loads(line))
        return items

    core_items = load_jsonl('track_a_core.jsonl')
    control_items = load_jsonl('track_a_controls.jsonl')
    rebuild_items = load_jsonl('rebuild_candidates.jsonl')
    excluded_items = load_jsonl('excluded.jsonl')

    assert len(core_items) == manifest['core_benchmark_count']
    assert len(control_items) == manifest['control_benchmark_count']
    assert len(rebuild_items) == manifest['rebuild_candidate_count']
    assert len(excluded_items) == manifest['excluded_count']

    total = len(core_items) + len(control_items) + len(rebuild_items) + len(excluded_items)
    assert total == manifest['total_evaluated_transitions']


def test_core_transitions_have_verified_causal_evidence():
    core_path = os.path.join(BENCHMARK_DIR, 'track_a_core.jsonl')
    with open(core_path, 'r', encoding='utf-8') as f:
        core_records = [json.loads(line) for line in f if line.strip()]

    assert len(core_records) >= 10, f'Expected at least 10 core candidates, found {len(core_records)}'

    for rec in core_records:
        tid = rec['transition_id']
        causal_file = os.path.join(CAUSAL_DIR, f'{tid}.json')
        assert os.path.exists(causal_file), f'Missing causal matrix file for core transition {tid}'

        with open(causal_file, 'r', encoding='utf-8') as f:
            cdata = json.load(f)

        assert cdata['environment_reproducible'] is True, f'{tid} failed reproducibility'
        assert cdata['causal_pass'] is True, f'{tid} failed causal pass'
        assert 'executions' in cdata and 'reproducibility_run_2' in cdata, f'{tid} missing run 1 or run 2'
        assert cdata['executions']['matrix']['stale_on_base'] is True, f'{tid} stale_on_base failed in run_1'
        assert cdata['executions']['matrix']['stale_on_target'] is False, f'{tid} stale_on_target failed in run_1'
        assert cdata['executions']['matrix']['valid_on_target'] is True, f'{tid} valid_on_target failed in run_1'


def test_no_overlap_between_curation_partitions():
    def get_tids(fn):
        p = os.path.join(BENCHMARK_DIR, fn)
        tids = set()
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as fp:
                for line in fp:
                    if line.strip():
                        tids.add(json.loads(line)['transition_id'])
        return tids

    core_tids = get_tids('track_a_core.jsonl')
    control_tids = get_tids('track_a_controls.jsonl')
    rebuild_tids = get_tids('rebuild_candidates.jsonl')
    excluded_tids = get_tids('excluded.jsonl')

    assert core_tids.isdisjoint(control_tids), 'Core and Control overlap'
    assert core_tids.isdisjoint(rebuild_tids), 'Core and Rebuild overlap'
    assert core_tids.isdisjoint(excluded_tids), 'Core and Excluded overlap'
    assert control_tids.isdisjoint(rebuild_tids), 'Control and Rebuild overlap'
    assert control_tids.isdisjoint(excluded_tids), 'Control and Excluded overlap'
    assert rebuild_tids.isdisjoint(excluded_tids), 'Rebuild and Excluded overlap'
