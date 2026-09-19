# RoleMem Pilot-v1.3-r2 — Corrected Handoff V4 Narrative & Stale Challenge Analysis

> **Topic**: Empirical Reality of Stale Memory Exposure under BM25 vs Forced Stale Injection  
> **Evaluation Script**: `scripts/run_stale_challenge_screen.py`  
> **Telemetry Artifact**: `data/stale_challenge_screen.json`  

---

## 1. Narrative Correction: Dynamic Retrieval vs Stale Exposure

In preliminary pilot explorations, reports noted a "Stale Exposure Rate = 33.3%". Rigorous code audit and execution telemetry reveal that this figure was an artifact of synthetic injection rather than standard BM25 retrieval behavior.

### Empirical Reality:
When BM25 retrieval operates without intervention:
- Evaluation queries contain target-state descriptions, method signatures, or error logs.
- BM25 calculates keyword frequencies against memory stores containing both historical (base-state) and modern (target-state) records.
- Because the target-state query strongly aligns with modern terminology and recent module names, BM25 predominantly retrieves the modern documentation or nothing at all.
- **Actual Stale Exposure Rate under standard BM25 = 0.0% (0 / 10 samples exposed)**.

---

## 2. The Real Benchmark Challenge: Forced Stale Injection (H2)

The scientific purpose of RoleMem is **not** to evaluate whether a generic lexical search engine (BM25) accidentally retrieves outdated text.

The fundamental research question is:
> **When an autonomous agent receives plausible but outdated architectural memory (e.g. from an earlier development session or legacy knowledge base), does the agent blindly adhere to that stale guidance and generate deprecated code, or does it exercise critical verification? And does introducing authentic target memory (H3) reliably repair this regression?**

To rigorously evaluate this, the benchmark defines three canonical experimental conditions:

1. **Condition H0 (No Memory Baseline)**:
   - Evaluates whether the LLM's pre-trained parametric knowledge can solve the transition without memory.
   - For novel API changes, the agent frequently guesses incorrectly or defaults to pre-training habits.

2. **Condition H2 (Stale-Injected Condition)**:
   - The agent's prompt explicitly injects the stale memory claim (e.g. recommending `click.utils.get_binary_stream` or `CustomApp.should_ignore_error`).
   - If the agent is vulnerable to memory interference, it will produce code calling the deprecated API.
   - In our Bubblewrap sandbox evaluation, **9 / 9 stale-sensitive transitions failed under H2**, triggering real `DeprecationWarning` or `AttributeError` exceptions.

3. **Condition H3 (Target Memory Condition)**:
   - The agent's prompt injects the verified target memory claim from `data/handoff_target_memory_snapshot.json`.
   - In our evaluation, **10 / 10 transitions passed under H3**.

---

## 3. Stale-Challenge Qualification Screen Results

Using `scripts/run_stale_challenge_screen.py`, candidate transitions are categorized into:
- **`QUALIFIED_STALE_CHALLENGE`**: Tasks where H2 causes failure/deprecation AND H3 restores PASS.
- **`EVOLUTION_CONTROL_BENCHMARK`**: Tasks where both H2 and H3 pass (evaluating API evolution without breaking deprecation).
- **`STALE_INSENSITIVE`**: Tasks where H2 passes despite stale injection (disqualified from stale-sensitive cohort).

### Screening Breakdown:
- **Qualified Stale Challenges**: 9 / 10 (90%)
  - `click` (DeprecationWarning)
  - `flask` (DeprecationWarning)
  - `werkzeug` (DeprecationWarning)
  - `jinja` (DeprecationWarning)
  - `itsdangerous` (API_ABSENT)
  - `markupsafe` (API_ABSENT)
  - `pluggy` (DeprecationWarning)
  - `virtualenv` (API_ABSENT)
  - `httpx` (DeprecationWarning)
- **Evolutionary Controls**: 1 / 10 (10%)
  - `attrs` (Python 3.13 API evolution control; passes under both H2 and H3)
- **Stale Insensitive Disqualifications**: 0 / 10 (0%)
