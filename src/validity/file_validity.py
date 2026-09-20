"""
src/validity/file_validity.py

File-level validity baseline checker.
Protocol V2.1 specification.

Computes exact SHA256 hashes of base file content vs target file content.
If hashes match -> VALID. If hashes differ -> STALE.
"""

import hashlib
from .types import ValidityResult, ValidityEvidence


class FileValidityChecker:
    """Evaluates memory validity strictly based on whole-file SHA256 equality."""

    @staticmethod
    def _sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def evaluate(
        self,
        base_source: str,
        target_source: str,
        file_path: str = ""
    ) -> ValidityResult:
        base_hash = self._sha256(base_source)
        target_hash = self._sha256(target_source)

        if base_hash == target_hash:
            return ValidityResult(
                decision="VALID",
                confidence=1.0,
                reasons=[f"File content SHA256 identical ({base_hash[:12]}...)."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="file_sha256_match",
                        source=file_path or "source_buffer",
                        detail=f"Base SHA matches target SHA: {base_hash}",
                        confidence=1.0
                    )
                ],
                file_changed=False,
                symbol_changed=False,
                symbol_removed=False,
                dependency_changed=False
            )
        else:
            return ValidityResult(
                decision="STALE",
                confidence=1.0,
                reasons=[f"File content SHA256 differs (base: {base_hash[:8]}..., target: {target_hash[:8]}...)."],
                evidence=[
                    ValidityEvidence(
                        evidence_type="file_sha256_mismatch",
                        source=file_path or "source_buffer",
                        detail=f"Base SHA ({base_hash}) != Target SHA ({target_hash})",
                        confidence=1.0
                    )
                ],
                file_changed=True,
                symbol_changed=None,
                symbol_removed=None,
                dependency_changed=None
            )
