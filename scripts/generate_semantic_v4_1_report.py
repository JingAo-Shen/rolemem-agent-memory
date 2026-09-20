#!/usr/bin/env python3
"""
scripts/generate_semantic_v4_1_report.py
Generates reports/semantic-v4-1.md from data/transition_semantic_audit_v4_1/
"""

import glob
import json
import os

def generate_report():
    files = sorted(glob.glob('data/transition_semantic_audit_v4_1/*.json'))
    total = len(files)
    audits = [json.load(open(f)) for f in files]

    v_counts = {}
    m_counts = {}
    q_counts = {f'q{i}': 0 for i in range(1, 7)}
    q_names = [
        ('q1', 'q1_repo_change_pr_diff', 'PR/Diff Cross-Support'),
        ('q2', 'q2_stale_memory_base_supported', 'Base Memory Entailment'),
        ('q3', 'q3_valid_memory_target_supported', 'Target Memory Entailment'),
        ('q4', 'q4_current_task_capability', 'Task Capability Alignment'),
        ('q5', 'q5_stale_solution_asymmetry', 'Stale Solution Asymmetry'),
        ('q6', 'q6_valid_solution_target_pass', 'Valid Solution Target Pass')
    ]

    for a in audits:
        v = a['verdict']
        v_counts[v] = v_counts.get(v, 0) + 1
        m = a['task_mapping']
        m_counts[m] = m_counts.get(m, 0) + 1
        for q_k, field, name in q_names:
            if a.get(field, {}).get('pass', False):
                q_counts[q_k] += 1

    md = []
    md.append('# Semantic Transition Audit Report V4.1\n')
    md.append('## Executive Summary\n')
    md.append(f'- **Total Transitions Audited**: {total}')
    md.append(f'- **Evaluation Policy**: Fail-closed, strict schema validation, zero-boolean default fallbacks')
    pass_total = v_counts.get('SEMANTIC_STRONG_PASS', 0) + v_counts.get('SEMANTIC_WEAK_PASS', 0)
    md.append(f'- **Semantic Pass Rate**: {pass_total} / {total} ({pass_total/total*100:.1f}%)')
    md.append(f'  - `SEMANTIC_STRONG_PASS`: {v_counts.get("SEMANTIC_STRONG_PASS", 0)} ({v_counts.get("SEMANTIC_STRONG_PASS", 0)/total*100:.1f}%)')
    md.append(f'  - `SEMANTIC_WEAK_PASS`: {v_counts.get("SEMANTIC_WEAK_PASS", 0)} ({v_counts.get("SEMANTIC_WEAK_PASS", 0)/total*100:.1f}%)')
    md.append(f'  - `REBUILD_REQUIRED`: {v_counts.get("REBUILD_REQUIRED", 0)} ({v_counts.get("REBUILD_REQUIRED", 0)/total*100:.1f}%)\n')

    md.append('## Task Mapping Classifications\n')
    for m, c in sorted(m_counts.items()):
        md.append(f'- `{m}`: {c} / {total} ({c/total*100:.1f}%)')
    md.append('')

    md.append('## Six-Question Semantic Gate Audit\n')
    md.append('| Question | Gate Name | Passed | Pass Rate | Requirement |')
    md.append('| :--- | :--- | :--- | :--- | :--- |')
    for q_k, field, name in q_names:
        c = q_counts[q_k]
        md.append(f'| {q_k.upper()} | {name} | {c}/{total} | {c/total*100:.1f}% | Entailed code evidence & cross-support |')
    md.append('')

    md.append('## Transition Breakdown\n')
    md.append('| Transition ID | Verdict | Task Mapping | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |')
    md.append('| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |')
    for a in audits:
        tid = a['transition_id']
        v = a['verdict']
        m = a['task_mapping']
        q_vals = ['PASS' if a.get(field, {}).get('pass', False) else 'FAIL' for q_k, field, _ in q_names]
        md.append(f'| `{tid}` | `{v}` | `{m}` | ' + ' | '.join(q_vals) + ' |')

    os.makedirs('reports', exist_ok=True)
    with open('reports/semantic-v4-1.md', 'w') as f:
        f.write('\n'.join(md) + '\n')

    print('Generated reports/semantic-v4-1.md successfully')

if __name__ == '__main__':
    generate_report()
