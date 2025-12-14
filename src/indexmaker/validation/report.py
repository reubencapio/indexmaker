"""
Validation report for index configuration and compliance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationError:
    """
    A single validation error or warning.

    Attributes:
        field: The field or component that has the issue
        message: Description of the issue
        severity: Severity level
        current_value: The current value that caused the issue
        expected: What was expected
        suggestion: How to fix the issue
    """

    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    current_value: Optional[Any] = None
    expected: Optional[str] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        parts = [f"{self.severity.value}: {self.field} - {self.message}"]
        if self.current_value is not None:
            parts.append(f"  Current: {self.current_value}")
        if self.expected:
            parts.append(f"  Expected: {self.expected}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


@dataclass
class ValidationReport:
    """
    Report containing validation results.

    Attributes:
        errors: List of validation issues
        is_valid: Whether the configuration is valid (no errors)

    Example:
        >>> report = index.validate()
        >>> if not report.is_valid:
        ...     for error in report.errors:
        ...         print(error)
    """

    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if there are no errors (warnings are ok)."""
        return not any(e.severity == ValidationSeverity.ERROR for e in self.errors)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(e.severity == ValidationSeverity.WARNING for e in self.errors)

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for e in self.errors if e.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for e in self.errors if e.severity == ValidationSeverity.WARNING)

    def add_error(
        self,
        field: str,
        message: str,
        current_value: Optional[Any] = None,
        expected: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add an error to the report."""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                severity=ValidationSeverity.ERROR,
                current_value=current_value,
                expected=expected,
                suggestion=suggestion,
            )
        )

    def add_warning(
        self,
        field: str,
        message: str,
        current_value: Optional[Any] = None,
        expected: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a warning to the report."""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                severity=ValidationSeverity.WARNING,
                current_value=current_value,
                expected=expected,
                suggestion=suggestion,
            )
        )

    def add_info(self, field: str, message: str) -> None:
        """Add an info message to the report."""
        self.errors.append(
            ValidationError(
                field=field,
                message=message,
                severity=ValidationSeverity.INFO,
            )
        )

    def merge(self, other: "ValidationReport") -> None:
        """Merge another report into this one."""
        self.errors.extend(other.errors)

    def __str__(self) -> str:
        if not self.errors:
            return "Validation passed: No issues found"

        lines = [f"Validation {'failed' if not self.is_valid else 'passed with warnings'}:"]
        lines.append(f"  {self.error_count} error(s), {self.warning_count} warning(s)")
        lines.append("")

        for error in self.errors:
            lines.append(str(error))
            lines.append("")

        return "\n".join(lines)

    def __bool__(self) -> bool:
        """Boolean conversion returns is_valid."""
        return self.is_valid
