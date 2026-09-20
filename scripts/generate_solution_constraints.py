#!/usr/bin/env python3
"""
scripts/generate_solution_constraints.py
Formalizes benchmark anti-cheating constraints for each Track A transition:
1. API Deprecation Gate (old API deprecated/removed/rejected)
2. Replacement Mechanism Gate (new mechanism/chain executed)
3. Behavior Fidelity Gate (dynamic inputs/boundary conditions verified)

Saves constraints manifest to data/solution_constraints/<tid>.json.
"""

import os
import sys
import json

DATA_DIR = "/code/rolemem-agent-memory/data"
OUTPUT_DIR = os.path.join(DATA_DIR, "solution_constraints")
MANIFEST_PATH = os.path.join(DATA_DIR, "track_a_reconstructed_manifest.jsonl")

os.makedirs(OUTPUT_DIR, exist_ok=True)

CONSTRAINTS_SPEC = {
    "trans_track_a_01_click_stream_deprecations": {
        "target_file": "stream_helper.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "click.utils.get_binary_stream",
            "enforcement": "DeprecationWarning raised or AttributeError when calling deprecated API in target snapshot",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "Direct sys.stdout.buffer and sys.stdin.buffer stream reference",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["get_io_stream('stdout') is sys.stdout.buffer", "get_io_stream('stdin') is sys.stdin.buffer"],
            "boundary_checks": ["Invalid stream names raise ValueError"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_02_flask_should_ignore_error": {
        "target_file": "custom_app.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "CustomApp.should_ignore_error",
            "enforcement": "Prohibit defining should_ignore_error on subclass; triggers Flask 2.3+ deprecation exception",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "teardown_request handler registration on Flask application instance",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["issubclass(CustomApp, Flask)", "app.test_client().get('/') returns status_code == 200"],
            "boundary_checks": ["Error handling handled via teardown pipeline"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_03_werkzeug_environ_property": {
        "target_file": "header_proxy.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "werkzeug.wsgi.environ_property",
            "enforcement": "werkzeug.wsgi.environ_property deprecated/removed in Werkzeug 2.1+",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "Dynamic property descriptor accessing self.environ dictionary",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["isinstance(prop, property)", "Dynamic resolution of HTTP_HOST across multiple instances", "Missing key fallback to empty string"],
            "boundary_checks": ["Empty environ handling"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_04_jinja_version_deprecation": {
        "target_file": "version_checker.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "jinja2.__version__",
            "enforcement": "Prohibit reading jinja2.__version__; assert not hasattr(jinja2, '__version__')",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "importlib.metadata.version('jinja2') with dynamic mock validation",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["Dynamic mock version propagation ('99.88.77-jinja-mock-ver')", "Package argument exact match: jinja2"],
            "boundary_checks": ["Exception fallback handling"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_05_itsdangerous_version_removal": {
        "target_file": "signer_version.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "itsdangerous.__version__",
            "enforcement": "Prohibit reading itsdangerous.__version__; assert not hasattr(itsdangerous, '__version__')",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "importlib.metadata.version('itsdangerous') with dynamic mock validation",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["Dynamic mock version propagation ('88.77.66-itsdangerous-mock-ver')", "Package argument exact match: itsdangerous"],
            "boundary_checks": ["Exception fallback handling"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_06_markupsafe_version_removal": {
        "target_file": "markup_version.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "markupsafe.__version__",
            "enforcement": "Prohibit reading markupsafe.__version__; assert not hasattr(markupsafe, '__version__')",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "importlib.metadata.version('markupsafe') with dynamic mock validation",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["Dynamic mock version propagation ('77.66.55-markupsafe-mock-ver')", "Package argument exact match: markupsafe"],
            "boundary_checks": ["Exception fallback handling"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_07_pluggy_varnames_noself": {
        "target_file": "spec_helper.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "varnames(..., legacy_noself=True)",
            "enforcement": "legacy_noself=True triggers pluggy DeprecationWarning",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "varnames(..., legacy_noself=False) preserving self parameter on hook methods",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["Dynamic hook spec resolution ('self', 'foo', 'bar', 'baz')", "Return type is 2-tuple of tuples"],
            "boundary_checks": ["Clean hook spec validation without warning"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_08_attrs_py313_replace_control": {
        "target_file": "point_manager.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "N/A (Control Transition: Valid API evolution)",
            "enforcement": "Control ensures valid code without deprecation passes across Python 3.13",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "attr.evolve(pt, **changes) or copy/mutation preserving Point class invariants",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["Dynamic coordinate evolution across multiple instances (x=30, y=99, x=45 y=55)", "isinstance(p, Point)"],
            "boundary_checks": ["Type invariance and attribute preservation"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_09_virtualenv_drop_py38_control": {
        "target_file": "cpython_patch.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "CPython3Posix.pyvenv_launch_patch_active",
            "enforcement": "assert not hasattr(CPython3Posix, 'pyvenv_launch_patch_active') - method removed",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "Direct boolean evaluation returning False without calling removed launcher patch",
            "prohibited_returns": ["1.0", None, "dummy", "False"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["type(res) is bool", "Both Linux Python 3.10 and Darwin Python 3.8 return False"],
            "boundary_checks": ["Boolean type strictness"],
            "constraint_status": "SPECIFIED"
        }
    },
    "trans_track_a_10_httpx_client_proxies_deprecation": {
        "target_file": "client_factory.py",
        "api_deprecation_gate": {
            "deprecated_symbol": "httpx.Client(proxies=...)",
            "enforcement": "proxies parameter triggers DeprecationWarning in modern HTTPX",
            "constraint_status": "SPECIFIED"
        },
        "replacement_mechanism_gate": {
            "required_mechanism": "httpx.Client(proxy=proxy_url) passing singular proxy parameter",
            "prohibited_returns": ["1.0", None, "dummy"],
            "constraint_status": "SPECIFIED"
        },
        "behavior_fidelity_gate": {
            "dynamic_checks": ["isinstance(client, httpx.Client)", "client._transport is not None"],
            "boundary_checks": ["Deprecation filter catches legacy parameter"],
            "constraint_status": "SPECIFIED"
        }
    }
}


def generate_all_constraints():
    print("=== Generating Solution Constraints Manifest (Anti-Cheating Gate) ===")
    specs = []
    manifests = [MANIFEST_PATH, os.path.join(DATA_DIR, "track_a_scale_manifest.jsonl")]
    for mf in manifests:
        if os.path.exists(mf):
            with open(mf, "r") as f:
                for line in f:
                    if line.strip():
                        specs.append(json.loads(line))

    for spec in specs:
        tid = spec["transition_id"]
        if tid in CONSTRAINTS_SPEC:
            constraints = CONSTRAINTS_SPEC[tid]
        else:
            constraints = {
                "target_file": spec.get("target_file", "solution.py"),
                "api_deprecation_gate": {
                    "deprecated_symbol": ", ".join(spec.get("deprecated_symbols", [])),
                    "enforcement": "Prohibits active deprecated/removed symbol invocation",
                    "constraint_status": "SPECIFIED"
                },
                "replacement_mechanism_gate": {
                    "required_mechanism": ", ".join(spec.get("replacement_symbols", [])),
                    "prohibited_returns": ["1.0", None, "dummy"],
                    "constraint_status": "SPECIFIED"
                },
                "behavior_fidelity_gate": {
                    "dynamic_checks": ["Pytest execution passes on target workspace"],
                    "boundary_checks": ["Valid solution execution strictly verified"],
                    "constraint_status": "SPECIFIED"
                }
            }
        payload = {
            "transition_id": tid,
            "anti_cheating_gate_version": "v1.0",
            "constraints": constraints,
            "verification_status": "CONSTRAINTS_SPECIFIED",
            "constraint_status": "SPECIFIED"
        }
        out_path = os.path.join(OUTPUT_DIR, f"{tid}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[{tid}] Registered 3-gate solution constraints.")

    print(f"All {len(specs)} solution constraints registered in {OUTPUT_DIR}\n")


if __name__ == "__main__":
    generate_all_constraints()
