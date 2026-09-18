# Track A Dataset Expansion Report (Pilot-v1.3)

## 1. Executive Summary

Under Pilot-v1.3, Track A candidate expansion has been formally launched and decoupled from Track B maturity:
- **Total Provisional Transitions**: **35** (Target: \ge 30)
- **Total Distinct Repositories**: **18** (Target: \ge 15)
- **Stale-Sensitive Candidates**: **25** (Target: \ge 10)
- **API Evolution Control Candidates**: **10**
- **TransitionVerifierV8 Integrity Pass Rate**: **100%** (All 35 transitions pass all 8 gates with cryptographic SHA256 binding)

## 2. Funnel Statistics

```text
60–100 Raw GitHub Mining Target  --> 87 raw candidates mined across 23 repos
    ↓ Ancestry & Diff Verification
    ↓ Fixture & 2x2 Causal Counterfactual Construction
    ↓ Eight-Gate TransitionVerifierV8 Audit
30–50 Provisional Transitions   --> 35 Provisional Track A Transitions (18 repos)
```

## 3. Repository Distribution (Max 2 transitions per repo)

| Repository | Count | Transitions |
| :--- | :--- | :--- |
| `PyCQA/flake8` | 3 | `trans_track_a_26_flake8_Merge, trans_track_a_27_flake8_remove, trans_track_a_28_flake8_Merge` |
| `Textualize/rich` | 2 | `trans_track_a_15_rich_remove, trans_track_a_16_rich_need` |
| `encode/httpx` | 1 | `trans_track_a_13_httpx_Updating` |
| `encode/starlette` | 1 | `trans_track_a_14_starlette_removeprefix` |
| `marshmallow-code/marshmallow` | 3 | `trans_track_a_17_marshmallow_ipaddress, trans_track_a_18_marshmallow_incorrect, trans_track_a_19_marshmallow_Update` |
| `pallets/click` | 1 | `trans_track_a_01_click_tests` |
| `pallets/flask` | 1 | `trans_track_a_02_flask_deprecate` |
| `pallets/itsdangerous` | 3 | `trans_track_a_05_itsdangerous_remove, trans_track_a_06_itsdangerous_remove, trans_track_a_07_itsdangerous_deprecate` |
| `pallets/jinja` | 1 | `trans_track_a_04_jinja_deprecate` |
| `pallets/markupsafe` | 3 | `trans_track_a_08_markupsafe_remove, trans_track_a_09_markupsafe_remove, trans_track_a_10_markupsafe_update` |
| `pallets/werkzeug` | 1 | `trans_track_a_03_werkzeug_deprecate` |
| `psf/requests` | 1 | `trans_track_a_11_requests_remove` |
| `pydantic/pydantic` | 1 | `trans_track_a_35_pydantic_documentation` |
| `pypa/virtualenv` | 3 | `trans_track_a_32_virtualenv_util, trans_track_a_33_virtualenv_util, trans_track_a_34_virtualenv_feat` |
| `pytest-dev/iniconfig` | 3 | `trans_track_a_23_iniconfig_Migrate, trans_track_a_24_iniconfig_typing, trans_track_a_25_iniconfig_Pytest` |
| `pytest-dev/pluggy` | 3 | `trans_track_a_20_pluggy_remove, trans_track_a_21_pluggy_Merge, trans_track_a_22_pluggy_test` |
| `python-attrs/attrs` | 3 | `trans_track_a_29_attrs_Document, trans_track_a_30_attrs_docs, trans_track_a_31_attrs_Expose` |
| `urllib3/urllib3` | 1 | `trans_track_a_12_urllib3_Deal` |

## 4. Transition Types Breakdown

| Transition Type | Count | Category |
| :--- | :--- | :--- |
| `API_DEPRECATION` | 10 | `STALE_SENSITIVE` |
| `API_REMOVAL` | 14 | `STALE_SENSITIVE` |
| `FUNCTION_RENAME` | 1 | `STALE_SENSITIVE` |
| `SIGNATURE_CHANGE` | 0 | `STALE_SENSITIVE` |
| `API_EVOLUTION` | 10 | `API_EVOLUTION_CONTROL` |

## 5. Difficulty Pre-Screening Summary

All 35 transitions were categorized into:
- **STALE_SENSITIVE** (25 transitions): Transitions where invoking the historical API triggers deprecation, removal, or signature mismatch on the evolved target codebase.
- **API_EVOLUTION_CONTROL** (10 transitions): Transitions introducing new capabilities or updated conventions where valid memory facilitates adoption without active deprecation traps.
