"""
src/claim_validity/validators/__init__.py

Registry and exports for Protocol V2.2 Claim Validators.
"""

from typing import Dict, Type
from ..types import ClaimType
from .base import BaseClaimValidator
from .symbol_exists import SymbolExistsValidator
from .attribute_exists import AttributeExistsValidator
from .import_path import ImportPathValidator
from .signature import SignatureValidator
from .default_value import DefaultValueValidator
from .deprecation import DeprecationValidator
from .return_value import ReturnValueValidator
from .behavioral_contract import BehavioralContractValidator
from .dependency_contract import DependencyContractValidator

VALIDATOR_REGISTRY: Dict[ClaimType, Type[BaseClaimValidator]] = {
    ClaimType.SYMBOL_EXISTS: SymbolExistsValidator,
    ClaimType.ATTRIBUTE_EXISTS: AttributeExistsValidator,
    ClaimType.IMPORT_PATH_VALID: ImportPathValidator,
    ClaimType.SIGNATURE_COMPATIBLE: SignatureValidator,
    ClaimType.CALLABLE: SignatureValidator,
    ClaimType.DEFAULT_VALUE: DefaultValueValidator,
    ClaimType.DEPRECATION_STATUS: DeprecationValidator,
    ClaimType.RETURN_VALUE: ReturnValueValidator,
    ClaimType.BEHAVIORAL_CONTRACT: BehavioralContractValidator,
    ClaimType.DEPENDENCY_CONTRACT: DependencyContractValidator,
}

__all__ = [
    "BaseClaimValidator",
    "SymbolExistsValidator",
    "AttributeExistsValidator",
    "ImportPathValidator",
    "SignatureValidator",
    "DefaultValueValidator",
    "DeprecationValidator",
    "ReturnValueValidator",
    "BehavioralContractValidator",
    "DependencyContractValidator",
    "VALIDATOR_REGISTRY",
]
