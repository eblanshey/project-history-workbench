"""Module responsibility: Runtime protocol compliance validation utilities.

This module provides functions to validate that classes implement protocol
interfaces correctly at runtime. Since mypy uses structural typing and doesn't
enforce exact signature matching for Protocols, these runtime checks ensure
that view implementations properly conform to their protocol contracts.

Usage:
    from tests.unit.ui.protocols.protocol_validation import validate_protocol_compliance

    validate_protocol_compliance(DiffPanelView, DiffView)
    validate_protocol_compliance(DiffPanelView, SnapshotView)
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol


def get_protocol_methods(protocol: type[Protocol]) -> dict[str, inspect.Signature]:
    """Extract all method signatures from a Protocol.

    Args:
        protocol: The Protocol class to extract methods from.

    Returns:
        Dictionary mapping method names to their signatures.
    """
    methods: dict[str, inspect.Signature] = {}

    for name, obj in inspect.getmembers(protocol):
        if not name.startswith("_") and callable(obj) and isinstance(obj, type(lambda: None)):
            # Get signature, handling both function and method descriptors
            try:
                sig = inspect.signature(obj)
                # Remove 'self' parameter for instance methods
                params = list(sig.parameters.values())
                if params and params[0].name == "self":
                    params = params[1:]
                sig = sig.replace(parameters=params)
                methods[name] = sig
            except (ValueError, TypeError):
                # Some objects can't be inspected, skip them
                continue

    return methods


def _get_implementation_methods(cls: type[Any]) -> dict[str, inspect.Signature]:
    """Extract all public method signatures from a class.

    Args:
        cls: The class to extract methods from.

    Returns:
        Dictionary mapping method names to their signatures.
    """
    methods: dict[str, inspect.Signature] = {}

    for name in dir(cls):
        if not name.startswith("_"):
            try:
                attr = getattr(cls, name)
                if callable(attr):
                    sig = inspect.signature(attr)
                    # Remove 'self' parameter for instance methods
                    params = list(sig.parameters.values())
                    if params and params[0].name == "self":
                        params = params[1:]
                    sig = sig.replace(parameters=params)
                    methods[name] = sig
            except (ValueError, TypeError):
                # Some objects can't be inspected, skip them
                continue

    return methods


def _signatures_compatible(
    protocol_sig: inspect.Signature,
    impl_sig: inspect.Signature,
    method_name: str,
) -> tuple[bool, str | None]:
    """Check if implementation signature is compatible with protocol signature.

    For protocol compliance, the implementation must:
    - Have at least all required parameters from the protocol
    - Allow all calls that the protocol allows
    - Parameter names are NOT enforced (Python uses positional/keyword matching)

    Args:
        protocol_sig: The protocol method signature.
        impl_sig: The implementation method signature.
        method_name: Name of the method being checked (for error messages).

    Returns:
        Tuple of (is_compatible, error_message).
        If compatible, error_message is None.
    """
    protocol_params = list(protocol_sig.parameters.values())
    impl_params = list(impl_sig.parameters.values())

    # Count required parameters (those without defaults)
    protocol_required_count = sum(
        1
        for p in protocol_params
        if p.default == inspect.Parameter.empty
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    )

    impl_required_count = sum(
        1
        for p in impl_params
        if p.default == inspect.Parameter.empty
        and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    )

    # Implementation must accept at least as many required arguments as protocol
    if impl_required_count > protocol_required_count:
        return False, (
            f"{method_name} requires {impl_required_count} arguments but "
            f"protocol only specifies {protocol_required_count}"
        )

    # Check for **kwargs which makes implementation more flexible
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in impl_params)
    if has_var_keyword:
        return True, None

    # Check parameter count (positional arguments)
    protocol_positional_count = sum(
        1
        for p in protocol_params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )
    impl_positional_count = sum(
        1 for p in impl_params if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )

    if impl_positional_count < protocol_positional_count:
        return False, (f"{method_name} accepts fewer positional parameters than protocol requires")

    return True, None


class ProtocolValidationError(Exception):
    """Raised when a class fails to comply with a protocol."""

    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


def validate_protocol_compliance(
    implementation: type[Any],
    protocol: type[Protocol],
    raise_on_error: bool = True,
) -> list[str]:
    """Validate that a class implements a Protocol correctly.

    This function checks:
    1. All required methods exist in the implementation
    2. Method signatures are compatible with the protocol

    Args:
        implementation: The class to validate.
        protocol: The Protocol to validate against.
        raise_on_error: If True, raise ProtocolValidationError on failures.
                       If False, return list of violations.

    Returns:
        Empty list if compliant, otherwise list of violation descriptions.

    Raises:
        ProtocolValidationError: If raise_on_error is True and violations found.
    """
    violations: list[str] = []

    protocol_methods = get_protocol_methods(protocol)
    impl_methods = _get_implementation_methods(implementation)

    # Check for missing methods
    for method_name, protocol_sig in protocol_methods.items():
        if method_name not in impl_methods:
            violations.append(f"Missing method '{method_name}' in {implementation.__name__}")
            continue

        # Check signature compatibility
        impl_sig = impl_methods[method_name]
        is_compatible, error_msg = _signatures_compatible(protocol_sig, impl_sig, method_name)
        if not is_compatible and error_msg:
            violations.append(f"{error_msg} in {implementation.__name__}")

    if violations and raise_on_error:
        raise ProtocolValidationError(
            f"{implementation.__name__} does not comply with {protocol.__name__}",
            violations,
        )

    return violations


def assert_protocol_compliance(
    implementation: type[Any],
    protocol: type[Protocol],
) -> None:
    """Assert that a class implements a Protocol correctly (for use in tests).

    Args:
        implementation: The class to validate.
        protocol: The Protocol to validate against.

    Raises:
        AssertionError: If compliance validation fails.
    """
    violations = validate_protocol_compliance(implementation, protocol, raise_on_error=False)
    if violations:
        violations_str = "\n  - ".join(violations)
        raise AssertionError(
            f"{implementation.__name__} does not comply with {protocol.__name__}:\n  - {violations_str}"
        )
