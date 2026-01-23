"""Tests for validation rules and reports."""

import pytest

from indexforge.core.constituent import Constituent
from indexforge.validation.report import ValidationError, ValidationReport, ValidationSeverity
from indexforge.validation.rules import ValidationRules


class TestValidationReport:
    """Tests for ValidationReport class."""

    def test_empty_report_is_valid(self):
        """Test that empty report is valid."""
        report = ValidationReport()

        assert report.is_valid
        assert not report.has_warnings
        assert report.error_count == 0

    def test_add_error(self):
        """Test adding error to report."""
        report = ValidationReport()
        report.add_error(
            field="test_field",
            message="Test error message",
            current_value=10,
            expected="Greater than 20",
        )

        assert not report.is_valid
        assert report.error_count == 1
        assert len(report.errors) == 1

    def test_add_warning(self):
        """Test adding warning to report."""
        report = ValidationReport()
        report.add_warning(field="test_field", message="Test warning")

        assert report.is_valid  # Warnings don't make report invalid
        assert report.has_warnings
        assert report.warning_count == 1

    def test_add_info(self):
        """Test adding info to report."""
        report = ValidationReport()
        report.add_info(field="test_field", message="Test info")

        assert report.is_valid
        assert len(report.errors) == 1

    def test_merge_reports(self):
        """Test merging two reports."""
        report1 = ValidationReport()
        report1.add_error("field1", "Error 1")

        report2 = ValidationReport()
        report2.add_warning("field2", "Warning 1")

        report1.merge(report2)

        assert report1.error_count == 1
        assert report1.warning_count == 1
        assert len(report1.errors) == 2

    def test_bool_conversion(self):
        """Test boolean conversion."""
        valid_report = ValidationReport()
        invalid_report = ValidationReport()
        invalid_report.add_error("field", "error")

        assert bool(valid_report) is True
        assert bool(invalid_report) is False

    def test_string_representation(self):
        """Test string representation."""
        report = ValidationReport()
        report.add_error(
            field="weight", message="Weight exceeds maximum", current_value="15%", expected="10%"
        )

        output = str(report)

        assert "failed" in output.lower()
        assert "weight" in output.lower()


class TestValidationError:
    """Tests for ValidationError class."""

    def test_error_creation(self):
        """Test creating a validation error."""
        error = ValidationError(
            field="constituent_count",
            message="Too few constituents",
            severity=ValidationSeverity.ERROR,
            current_value=5,
            expected="At least 10",
            suggestion="Add more constituents",
        )

        assert error.field == "constituent_count"
        assert error.severity == ValidationSeverity.ERROR
        assert error.current_value == 5

    def test_error_string(self):
        """Test error string representation."""
        error = ValidationError(
            field="weight",
            message="Weight too high",
            severity=ValidationSeverity.ERROR,
            current_value="15%",
            suggestion="Apply weight cap",
        )

        output = str(error)

        assert "ERROR" in output
        assert "weight" in output
        assert "15%" in output


class TestValidationRules:
    """Tests for ValidationRules class."""

    def test_default_rules(self):
        """Test default validation rules."""
        rules = ValidationRules.default()

        assert rules.min_constituents == 1

    def test_validate_constituent_count(self):
        """Test validating constituent count."""
        rules = ValidationRules(min_constituents=5, max_constituents=10)

        # Too few
        constituents = [Constituent(ticker=f"T{i}", weight=0.5) for i in range(3)]
        report = rules.validate_constituents(constituents)

        assert not report.is_valid
        assert any("Too few" in e.message for e in report.errors)

        # Just right
        constituents = [Constituent(ticker=f"T{i}", weight=0.1) for i in range(7)]
        report = rules.validate_constituents(constituents)

        assert report.is_valid

    def test_validate_max_weight(self):
        """Test validating maximum constituent weight."""
        rules = ValidationRules(max_single_constituent_weight=0.10)

        constituents = [
            Constituent(ticker="HEAVY", weight=0.15),
            Constituent(ticker="LIGHT", weight=0.05),
        ]

        report = rules.validate_constituents(constituents)

        assert not report.is_valid
        assert any("HEAVY" in e.field for e in report.errors)

    def test_validate_sector_concentration(self):
        """Test validating sector concentration."""
        rules = ValidationRules(max_single_sector_weight=0.40)

        constituents = [
            Constituent(ticker="T1", weight=0.30, sector="Technology"),
            Constituent(ticker="T2", weight=0.25, sector="Technology"),
            Constituent(ticker="F1", weight=0.45, sector="Financials"),
        ]

        report = rules.validate_constituents(constituents)

        assert not report.is_valid
        assert any("sector" in e.field.lower() for e in report.errors)

    def test_validate_country_concentration(self):
        """Test validating country concentration."""
        rules = ValidationRules(max_single_country_weight=0.50)

        constituents = [
            Constituent(ticker="A1", weight=0.40, country="US"),
            Constituent(ticker="A2", weight=0.30, country="US"),
            Constituent(ticker="G1", weight=0.30, country="Germany"),
        ]

        report = rules.validate_constituents(constituents)

        assert not report.is_valid
        assert any("country" in e.field.lower() for e in report.errors)

    def test_validate_weights_sum(self):
        """Test that weights sum to 1.0."""
        rules = ValidationRules.default()

        # Weights don't sum to 1
        constituents = [
            Constituent(ticker="A", weight=0.3),
            Constituent(ticker="B", weight=0.3),
        ]

        report = rules.validate_constituents(constituents)

        assert report.has_warnings
        assert any("sum" in e.message.lower() for e in report.errors)

    def test_to_dict(self):
        """Test converting to dictionary."""
        rules = ValidationRules(
            min_constituents=20, max_constituents=100, max_single_constituent_weight=0.10
        )

        data = rules.to_dict()

        assert data["min_constituents"] == 20
        assert data["max_constituents"] == 100
        assert data["max_single_constituent_weight"] == 0.10


class TestValidationRulesBuilder:
    """Tests for ValidationRulesBuilder class."""

    def test_builder_basic(self):
        """Test basic builder usage."""
        rules = ValidationRules.builder().min_constituents(20).max_constituents(50).build()

        assert rules.min_constituents == 20
        assert rules.max_constituents == 50

    def test_builder_with_all_options(self):
        """Test builder with all options."""
        rules = (
            ValidationRules.builder()
            .min_constituents(30)
            .max_constituents(100)
            .max_single_constituent_weight(0.10)
            .max_single_sector_weight(0.35)
            .max_single_country_weight(0.50)
            .min_market_cap(1_000_000_000)
            .build()
        )

        assert rules.min_constituents == 30
        assert rules.max_single_constituent_weight == 0.10
        assert rules.min_market_cap == 1_000_000_000

    def test_invalid_min_constituents(self):
        """Test that invalid min constituents raises error."""
        with pytest.raises(ValueError):
            ValidationRules.builder().min_constituents(0).build()

    def test_invalid_max_weight(self):
        """Test that invalid max weight raises error."""
        with pytest.raises(ValueError):
            ValidationRules.builder().max_single_constituent_weight(1.5).build()

        with pytest.raises(ValueError):
            ValidationRules.builder().max_single_constituent_weight(0).build()
