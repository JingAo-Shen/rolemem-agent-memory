"""
src/claim_validity/claim_extractor.py

Deterministic Claim Extractor for Protocol V2.2:
- Parses raw natural language or semi-structured memory statements into formal MemoryClaim objects.
- Operates 100% deterministically without LLM calls.
- Unparsable statements are marked as UNKNOWN_CLAIM_TYPE with claim_parse_status = UNRESOLVED.
"""

import re
import hashlib
from typing import Optional, Dict, Any, Tuple
from .types import ClaimType, MemoryClaim


class DeterministicClaimExtractor:
    """Extracts structured MemoryClaims from raw memory strings using deterministic AST/Regex patterns."""

    def __init__(self):
        # General pattern for module export in __all__ (e.g. "marshmallow exports pprint in __all__ at top level.")
        self.pat_module_export_all = re.compile(
            r"^(?:Module\s+|Package\s+)?([a-zA-Z0-9_\.]+)\s+exports\s+[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:in|via)\s+[`'\"]?(__all__)['`\"]?\s*(.*)",
            re.IGNORECASE
        )
        self.pat_symbol_exists = re.compile(
            r"^(?:Symbol|Function|Class|Method|Variable|Constant|Function/Class|Class/Function)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:defines\s+core\s+implementation|exists|is\s+defined|is\s+declared|is\s+available\s+directly|is\s+available|is\s+accessible|is\s+found)\s+(?:in|within)\s+[`'\"]?([^'`\"]+)['`\"]?",
            re.IGNORECASE
        )
        self.pat_attribute_exists = re.compile(
            r"^(?:Symbol|Class|Object|Module)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:defines\s+attribute|has\s+attribute|has\s+method|defines\s+property|contains\s+symbol|instances\s+provide|provides)\s+[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?(?:\(\))?\s*(?:method|attribute|property|function)?",
            re.IGNORECASE
        )
        self.pat_import_path = re.compile(
            r"^(?:Symbol|Object|Function|Class)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:can\s+be\s+imported\s+from|is\s+imported\s+from|available\s+at\s+import\s+path|exports)\s+[`'\"]?([^'`\"]+)['`\"]?",
            re.IGNORECASE
        )
        self.pat_deprecation = re.compile(
            r"^(?:Symbol|Function|Method|Class)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+is\s+(deprecated|active|supported|removed|raising\s+deprecationwarning)",
            re.IGNORECASE
        )
        self.pat_signature = re.compile(
            r"^(?:Function|Method|Callable)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:accepts\s+parameters?|accepts\s+parameter|signature\s+has\s+parameters?|takes\s+arguments?)\s+([^.]+)",
            re.IGNORECASE
        )
        self.pat_default_val = re.compile(
            r"^(?:Parameter|Argument)\s+[`'\"]?([a-zA-Z0-9_]+)['`\"]?\s+(?:of|in)\s+[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+defaults\s+to\s+[`'\"]?([^'`\"]+)['`\"]?",
            re.IGNORECASE
        )
        self.pat_return_val = re.compile(
            r"^(?:Function|Method|Symbol)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:returns|yields)\s+[`'\"]?([^'`\"]+)['`\"]?",
            re.IGNORECASE
        )
        self.pat_dependency = re.compile(
            r"^(?:(?:Symbol|Class|Function|Interface|Method|Module)\s+)?\s*[`'\"]?([a-zA-Z_][a-zA-Z0-9_\.]*)['`\"]?\s+(?:depends\s+on|delegates\s+to|invokes|calls|inspects\s+.*?via)\s+(?:dependency\s+)?[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s*(.*)",
            re.IGNORECASE
        )
        self.pat_contract = re.compile(
            r"^(?:When\s+)?(?:(?:Symbol|Class|Function)\s+)?\s*[`'\"]?([a-zA-Z0-9_\.]+)['`\"]?\s+(?:instance\s+|class\s+|application\s+instance\s+)?(?:is\s+initialized|initialized|wrapping|initializes|can\s+be\s+instantiated|maintains\s+contract|satisfies\s+behavioral\s+contract|satisfies\s+contract|ensures\s+behavior|returns\s+valid|formats\s+and\s+parses|implements\s+contract)\s*(.*)",
            re.IGNORECASE
        )

    def extract(
        self,
        raw_statement: str,
        claim_id: Optional[str] = None,
        repository: str = "",
        file_path: str = "",
        symbol: str = "",
        source_case_id: Optional[str] = None,
        explicit_metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryClaim:
        raw_statement = raw_statement.strip()
        if not claim_id:
            claim_id = f"CLM-{hashlib.sha256(raw_statement.encode('utf-8')).hexdigest()[:12]}"

        # 1. Explicit structured metadata
        if explicit_metadata and explicit_metadata.get("claim_type"):
            try:
                ctype = ClaimType(explicit_metadata["claim_type"])
                return MemoryClaim(
                    claim_id=claim_id,
                    raw_statement=raw_statement,
                    claim_type=ctype,
                    subject=explicit_metadata.get("subject", symbol),
                    predicate=explicit_metadata.get("predicate", "asserts"),
                    object=explicit_metadata.get("object", ""),
                    qualifiers=explicit_metadata.get("qualifiers", {}),
                    repository=repository or explicit_metadata.get("repository", ""),
                    file_path=file_path or explicit_metadata.get("file_path", ""),
                    symbol=symbol or explicit_metadata.get("symbol", ""),
                    confidence=float(explicit_metadata.get("confidence", 1.0)),
                    source_case_id=source_case_id,
                    claim_parse_status="PARSED"
                )
            except Exception:
                pass

        # 2. Pattern Matching
        # A. Module export in __all__
        m = self.pat_module_export_all.match(raw_statement)
        if m:
            module_name = m.group(1)
            exported_sym = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.IMPORT_PATH_VALID,
                subject=exported_sym,
                predicate="exported_in",
                object=f"{module_name}.__all__",
                repository=repository,
                file_path=file_path,
                symbol=exported_sym,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # B. Default Value (check before others to avoid greedy matching)
        m = self.pat_default_val.match(raw_statement)
        if m:
            param_name = m.group(1)
            sym_name = m.group(2)
            default_val = m.group(3)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.DEFAULT_VALUE,
                subject=sym_name,
                predicate="parameter_default",
                object=default_val,
                qualifiers={"parameter_name": param_name, "expected_default": default_val},
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # C. Signature Compatibility
        m = self.pat_signature.match(raw_statement)
        if m:
            sym_name = m.group(1)
            params_str = m.group(2).strip()
            params_list = [p.strip() for p in params_str.split(",") if p.strip()]
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.SIGNATURE_COMPATIBLE,
                subject=sym_name,
                predicate="accepts_parameters",
                object=params_str,
                qualifiers={"expected_parameters": params_list},
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # D. Deprecation Status
        m = self.pat_deprecation.match(raw_statement)
        if m:
            sym_name = m.group(1)
            status_val = m.group(2).lower()
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.DEPRECATION_STATUS,
                subject=sym_name,
                predicate="deprecation_status",
                object=status_val,
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # E. Return Value
        m = self.pat_return_val.match(raw_statement)
        if m:
            sym_name = m.group(1)
            ret_val = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.RETURN_VALUE,
                subject=sym_name,
                predicate="returns",
                object=ret_val,
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # F. Behavioral Contract
        m = self.pat_contract.match(raw_statement)
        if m:
            sym_name = m.group(1)
            contract_desc = m.group(2).strip()
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.BEHAVIORAL_CONTRACT,
                subject=sym_name,
                predicate="satisfies_contract",
                object=contract_desc,
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # G. Dependency Contract
        m = self.pat_dependency.match(raw_statement)
        if m:
            sym_name = m.group(1)
            dep_name = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.DEPENDENCY_CONTRACT,
                subject=sym_name,
                predicate="depends_on",
                object=dep_name,
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # H. Attribute Exists Pattern
        m = self.pat_attribute_exists.match(raw_statement)
        if m:
            parent_sym = m.group(1)
            attr_name = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.ATTRIBUTE_EXISTS,
                subject=parent_sym,
                predicate="has_attribute",
                object=attr_name,
                repository=repository,
                file_path=file_path,
                symbol=symbol or parent_sym,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # I. Import Path Valid
        m = self.pat_import_path.match(raw_statement)
        if m:
            sym_name = m.group(1)
            import_mod = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.IMPORT_PATH_VALID,
                subject=sym_name,
                predicate="imported_from",
                object=import_mod,
                repository=repository,
                file_path=file_path,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # J. Symbol Exists Pattern
        m = self.pat_symbol_exists.match(raw_statement)
        if m:
            sym_name = m.group(1)
            target_f = m.group(2)
            return MemoryClaim(
                claim_id=claim_id,
                raw_statement=raw_statement,
                claim_type=ClaimType.SYMBOL_EXISTS,
                subject=sym_name,
                predicate="exists_in",
                object=target_f,
                repository=repository,
                file_path=file_path or target_f,
                symbol=symbol or sym_name,
                source_case_id=source_case_id,
                claim_parse_status="PARSED"
            )

        # Fallback for unparsed statements
        return MemoryClaim(
            claim_id=claim_id,
            raw_statement=raw_statement,
            claim_type=ClaimType.UNKNOWN_CLAIM_TYPE,
            subject=symbol or "",
            predicate="unknown",
            object="",
            repository=repository,
            file_path=file_path,
            symbol=symbol or "",
            source_case_id=source_case_id,
            claim_parse_status="UNRESOLVED"
        )
