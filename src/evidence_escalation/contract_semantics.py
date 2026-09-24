"""
src/evidence_escalation/contract_semantics.py

Behavioral Contract Semantics Module for Protocol V2.2-V1.2:
- Parses structured and unstructured BehavioralContract statements into fine-grained BehavioralRequirement units.
- Supports requirement types: OPERATION, ATTRIBUTE_STATE, CONSTRUCTOR_ARGUMENT, DEFAULT_VALUE, RETURN_RELATION, SEQUENCE.
- Eliminates hand-waving assumption that 'no operations' implies 100% operation coverage.
- Enforces strict multi-requirement verification for state and default semantics.
"""

from __future__ import annotations
import re
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple

from src.claim_validity.types import MemoryClaim, ClaimType


class BehavioralRequirementType(str, Enum):
    OPERATION = "OPERATION"
    ATTRIBUTE_STATE = "ATTRIBUTE_STATE"
    CONSTRUCTOR_ARGUMENT = "CONSTRUCTOR_ARGUMENT"
    DEFAULT_VALUE = "DEFAULT_VALUE"
    RETURN_RELATION = "RETURN_RELATION"
    SEQUENCE = "SEQUENCE"


@dataclass
class BehavioralRequirement:
    req_id: str
    req_type: BehavioralRequirementType
    target_name: str
    expected_value: Optional[str] = None
    is_critical: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "req_id": self.req_id,
            "req_type": self.req_type.value if isinstance(self.req_type, Enum) else str(self.req_type),
            "target_name": self.target_name,
            "expected_value": self.expected_value,
            "is_critical": self.is_critical,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> BehavioralRequirement:
        rtype = BehavioralRequirementType(d["req_type"]) if isinstance(d["req_type"], str) else d["req_type"]
        return cls(
            req_id=d["req_id"],
            req_type=rtype,
            target_name=d["target_name"],
            expected_value=d.get("expected_value"),
            is_critical=d.get("is_critical", True),
            description=d.get("description", "")
        )


class ContractSemanticsExtractor:
    """Extracts semantic BehavioralRequirement specifications from MemoryClaims."""

    @classmethod
    def extract_requirements(cls, claim: MemoryClaim) -> List[BehavioralRequirement]:
        """Extracts deterministic semantic requirements from a claim without case IDs."""
        reqs: List[BehavioralRequirement] = []
        if claim.claim_type != ClaimType.BEHAVIORAL_CONTRACT:
            return reqs

        text = f"{claim.object or ''} {claim.raw_statement or ''}"
        cid = claim.claim_id or "REQ"
        count = 1

        # -----------------------------------------------------------------
        # 1. Constructor Requirements
        # -----------------------------------------------------------------
        # A. Without arguments / zero args
        if re.search(r"\b(?:without arguments|without parameters|no parameters|no required arguments|default constructor|no arguments)\b", text, re.IGNORECASE):
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.CONSTRUCTOR_ARGUMENT,
                target_name="constructor",
                expected_value="0_args",
                is_critical=True,
                description=f"{claim.subject} constructor accepts invocation without arguments"
            ))
            count += 1

        # B. Explicit constructor keyword arguments: e.g., record=True, debug=False
        kw_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z0-9_'\"]+)", text)
        for k, v in kw_matches:
            clean_v = v.strip("'\"")
            # Avoid capturing default attribute descriptions as constructor kwargs
            if not any(r.target_name == k for r in reqs) and not re.search(rf"default\s+{k}", text, re.IGNORECASE):
                reqs.append(BehavioralRequirement(
                    req_id=f"{cid}-R{count}",
                    req_type=BehavioralRequirementType.CONSTRUCTOR_ARGUMENT,
                    target_name=k,
                    expected_value=clean_v,
                    is_critical=True,
                    description=f"{claim.subject} constructor configured with {k}={clean_v}"
                ))
                count += 1


        # C. Initialized with a [type/object]
        init_with_match = re.search(r"(?:initialized with a|initialized with an|wrapping a|wrapping an)\s+([a-zA-Z0-9_]+(?:\s+[a-zA-Z0-9_]+)?)", text, re.IGNORECASE)
        if init_with_match:
            init_val = init_with_match.group(1).strip()
            # Avoid duplicate if already captured as kwarg
            if not any(r.target_name == "input_arg" for r in reqs):
                reqs.append(BehavioralRequirement(
                    req_id=f"{cid}-R{count}",
                    req_type=BehavioralRequirementType.CONSTRUCTOR_ARGUMENT,
                    target_name="input_arg",
                    expected_value=init_val,
                    is_critical=True,
                    description=f"{claim.subject} instantiated with {init_val}"
                ))
                count += 1

        # -----------------------------------------------------------------
        # 2. Attribute State & Default Value Requirements
        # -----------------------------------------------------------------
        # A. Default attribute with value: e.g. "default title attribute set to 'FastAPI'", "default debug mode set to False"
        def_attr_match = re.search(r"default\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:attribute|mode|property|setting)?\s*(?:set to|is|=)?\s*([a-zA-Z0-9_'\"]+)", text, re.IGNORECASE)
        if def_attr_match:
            attr_name = def_attr_match.group(1)
            expected_val = def_attr_match.group(2).strip("'\"")
            # If word is "connection", it might be "default connection pool configuration"
            if attr_name.lower() not in ("connection", "pool"):
                reqs.append(BehavioralRequirement(
                    req_id=f"{cid}-R{count}",
                    req_type=BehavioralRequirementType.ATTRIBUTE_STATE,
                    target_name=attr_name,
                    expected_value=expected_val,
                    is_critical=True,
                    description=f"Attribute '{attr_name}' matches expected state '{expected_val}'"
                ))
                count += 1
                reqs.append(BehavioralRequirement(
                    req_id=f"{cid}-R{count}",
                    req_type=BehavioralRequirementType.DEFAULT_VALUE,
                    target_name=attr_name,
                    expected_value=expected_val,
                    is_critical=True,
                    description=f"Attribute '{attr_name}' defaults to '{expected_val}' without explicit configuration"
                ))
                count += 1

        # B. Default state/configuration (e.g. "default connection pool configuration")
        if re.search(r"\bdefault\s+(?:connection\s+pool\s+)?configuration\b", text, re.IGNORECASE):
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.DEFAULT_VALUE,
                target_name="default_configuration",
                expected_value="default",
                is_critical=True,
                description="Default configuration state verified on instance"
            ))
            count += 1

        # C. General attribute access: e.g. "via the method attribute"
        gen_attr_match = re.search(r"via the\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+attribute", text, re.IGNORECASE)
        if gen_attr_match:
            attr_name = gen_attr_match.group(1)
            if not any(r.target_name == attr_name for r in reqs):
                reqs.append(BehavioralRequirement(
                    req_id=f"{cid}-R{count}",
                    req_type=BehavioralRequirementType.ATTRIBUTE_STATE,
                    target_name=attr_name,
                    expected_value=None,
                    is_critical=True,
                    description=f"Instance exposes attribute '{attr_name}'"
                ))
                count += 1

        # -----------------------------------------------------------------
        # 3. Explicit Operation Requirements
        # -----------------------------------------------------------------
        op_names: List[str] = []
        # Matches fn() tokens: e.g. write_text(), getvalue(), export_text(), str(), len(), print()
        fn_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)", text)
        for fn in fn_matches:
            if fn not in op_names:
                op_names.append(fn)

        for op in op_names:
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.OPERATION,
                target_name=op,
                expected_value=None,
                is_critical=True,
                description=f"Executes operation '{op}()' on or with subject"
            ))
            count += 1

        # -----------------------------------------------------------------
        # 4. Sequence Requirements (if multiple operations extracted)
        # -----------------------------------------------------------------
        if len(op_names) >= 2:
            seq_target = " -> ".join(op_names)
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.SEQUENCE,
                target_name=seq_target,
                expected_value=None,
                is_critical=True,
                description=f"Sequential execution order: {seq_target}"
            ))
            count += 1

        # -----------------------------------------------------------------
        # 5. Return Relation Requirements
        # -----------------------------------------------------------------
        # e.g., "returns the plain string content when converted via str()"
        if "str()" in text and re.search(r"plain(?:\s+string)?\s+content", text, re.IGNORECASE):
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.RETURN_RELATION,
                target_name="str",
                expected_value="plain_content",
                is_critical=True,
                description="Conversion via str() returns plain string content"
            ))
            count += 1
        elif "len()" in text and re.search(r"(?:total\s+item\s+count|length\s+inspection)", text, re.IGNORECASE):
            reqs.append(BehavioralRequirement(
                req_id=f"{cid}-R{count}",
                req_type=BehavioralRequirementType.RETURN_RELATION,
                target_name="len",
                expected_value="total_count",
                is_critical=True,
                description="len() returns total item count"
            ))
            count += 1

        return reqs
