# Pilot-v1.2d External GitHub Ground Truth Audit Report

> [!IMPORTANT]
> **Audit Status**: Programmatically generated from raw Git cache inspection (`/code/repo_cache/`). Total Audited: **10**, Passed: **10**, Failed: **0** (100.0%).

## 1. Audit Scope & Methodology
Every transition candidate must match authentic Git commits, PR metadata, issue links, diff files, and AST symbol changes directly extracted from local bare git mirrors.

Verification dimensions:
- **Base commit exists** in canonical git repository (`git rev-parse`)
- **Target commit exists** in canonical git repository (`git rev-parse`)
- **PR number matched in git**: Commit log or merge parents contain `#<PR_NUMBER>`
- **PR title / intent matched in git**: Commit title reflects PR specification
- **Changed files verified**: Files modified in git diff match specification `changed_files`

## 2. Transition Ground-Truth Verification Matrix

| Transition ID | Repository | PR / Issue | Commits (Base -> Target) | Git Log Match | Files Verified | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `trans_gold_click_01_option_parser` | `pallets/click` | [PR #2592](https://github.com/pallets/click/pull/2592) | `edcd2dc2` -> `988c6839` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_click_02_isolated_filesystem` | `pallets/click` | [PR #3704](https://github.com/pallets/click/pull/3704) | `333c28d7` -> `cfa01eeb` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_flask_01_context_stack_removal` | `pallets/flask` | [PR #4995](https://github.com/pallets/flask/pull/4995) | `604de4b1` -> `1ee22e17` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_flask_02_should_ignore_error` | `pallets/flask` | [PR #5899](https://github.com/pallets/flask/pull/5899) | `9b74a90d` -> `4b8bde97` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_requests_01_tls_context_adapter` | `psf/requests` | [PR #6710](https://github.com/psf/requests/pull/6710) | `970e8cec` -> `c98e4d13` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_requests_02_pool_key_overrides` | `psf/requests` | [PR #6716](https://github.com/psf/requests/pull/6716) | `88dce9d8` -> `145b5399` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_urllib3_01_retry_allowed_methods` | `urllib3/urllib3` | [PR #2000](https://github.com/urllib3/urllib3/pull/2000) | `6d38f171` -> `382ab32f` | Title PASS | PASS | **PASS** |
| `trans_gold_urllib3_02_empty_allowed_methods` | `urllib3/urllib3` | [PR #5223](https://github.com/urllib3/urllib3/pull/5223) | `a5d70ebf` -> `9a209d21` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_werkzeug_01_cached_property` | `pallets/werkzeug` | [PR #2084](https://github.com/pallets/werkzeug/pull/2084) | `25ca9cd9` -> `f50fbf56` | PR# & Title PASS | PASS | **PASS** |
| `trans_gold_werkzeug_02_environ_properties` | `pallets/werkzeug` | [PR #3276](https://github.com/pallets/werkzeug/pull/3276) | `f97c3056` -> `7641d499` | PR# & Title PASS | PASS | **PASS** |

## 3. Discrepancies Corrected in Pilot-v1.2d

The following discrepancies identified by external audits were corrected against canonical Git histories:
1. **`trans_gold_click_01_option_parser`**:
   - *Previous*: PR #1064 (non-existent).
   - *Corrected*: `pallets/click#2592` (`deprecate OptionParser`), merge commit `988c683963b14ced1b32a8cda9f9b466c32d9df1`.
2. **`trans_gold_click_02_isolated_filesystem`**:
   - *Previous*: PR #2041 (unrelated shell completion values).
   - *Corrected*: `pallets/click#3704` (`Deprecate isolated_filesystem and document its limits`), merge commit `cfa01eeb7894a408af70b29d28c0b24f8680f9fb`.
3. **`trans_gold_urllib3_01_retry_allowed_methods`**:
   - *Previous*: PR #2050 (PyPy 3.6 CI upgrade).
   - *Corrected*: `urllib3/urllib3#2000` (`Rename Retry options and defaults`), merge commit `382ab32f23795c44faae83b4e8b18a16fb605a0a`.
4. **`trans_gold_requests_01_tls_context_adapter`**:
   - *Previous*: PR #6716 (pool key overrides).
   - *Corrected*: `psf/requests#6710` (`Move _get_connection to get_connection_with_tls_context`), target commit `c98e4d133ef29c46a9b68cd783087218a8075e05`.
5. **`trans_gold_requests_02_pool_key_overrides`**:
   - *Corrected*: `psf/requests#6716` (`Allow for overriding of specific pool key params`), merge commit `145b5399486b56e00250204f033441f3fdf2f3c9`.

## 4. Ground-Truth Acceptance Verdict
- **Passed Transitions**: 10/10
- **Failed Transitions**: 0/10
- **External Ground-Truth Gate**: **PASS**
