"""Tests for theme-based filtering."""

import pytest

from indexmaker.core.constituent import Constituent
from indexmaker.selection.criteria import SelectionCriteria
from indexmaker.selection.theme import (
    ThemeFilter,
    create_theme_filter,
    get_predefined_theme,
    PREDEFINED_THEMES,
)


class TestThemeFilter:
    """Tests for ThemeFilter class."""

    def test_matches_single_keyword(self):
        """Test matching a single keyword."""
        filter = ThemeFilter(keywords=["quantum"])

        matching = Constituent(
            ticker="IONQ",
            name="IonQ Inc",
            business_description="IonQ is a leader in quantum computing hardware",
        )
        non_matching = Constituent(
            ticker="AAPL",
            name="Apple Inc",
            business_description="Apple designs consumer electronics and software",
        )

        assert filter.matches(matching) is True
        assert filter.matches(non_matching) is False

    def test_matches_multiple_keywords_any_mode(self):
        """Test matching with multiple keywords in 'any' mode."""
        filter = ThemeFilter(keywords=["quantum", "solar", "renewable"])

        quantum = Constituent(
            ticker="IONQ",
            business_description="Quantum computing company",
        )
        solar = Constituent(
            ticker="ENPH",
            business_description="Solar energy solutions",
        )
        other = Constituent(
            ticker="XOM",
            business_description="Oil and gas company",
        )

        assert filter.matches(quantum) is True
        assert filter.matches(solar) is True
        assert filter.matches(other) is False

    def test_matches_multiple_keywords_all_mode(self):
        """Test matching with multiple keywords in 'all' mode."""
        filter = ThemeFilter(keywords=["quantum", "computing"], match_mode="all")

        both = Constituent(
            ticker="IONQ",
            business_description="IonQ is a quantum computing company",
        )
        only_quantum = Constituent(
            ticker="QBTS",
            business_description="Quantum mechanics research",
        )

        assert filter.matches(both) is True
        assert filter.matches(only_quantum) is False

    def test_case_sensitive_matching(self):
        """Test case-sensitive matching."""
        filter = ThemeFilter(keywords=["AI"], case_sensitive=True)

        uppercase = Constituent(
            ticker="NVDA",
            business_description="NVIDIA provides AI and graphics solutions",
        )
        lowercase = Constituent(
            ticker="OTHER",
            business_description="This company uses ai technology",
        )

        assert filter.matches(uppercase) is True
        assert filter.matches(lowercase) is False

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching (default)."""
        filter = ThemeFilter(keywords=["AI"], case_sensitive=False)

        uppercase = Constituent(
            ticker="NVDA",
            business_description="NVIDIA provides AI solutions",
        )
        lowercase = Constituent(
            ticker="OTHER",
            business_description="This company uses ai technology",
        )

        assert filter.matches(uppercase) is True
        assert filter.matches(lowercase) is True

    def test_matches_in_industry_field(self):
        """Test that matching works on industry field too."""
        filter = ThemeFilter(keywords=["biotechnology"])

        biotech = Constituent(
            ticker="MRNA",
            industry="Biotechnology",
            business_description="mRNA therapeutics company",
        )

        assert filter.matches(biotech) is True

    def test_matches_in_name_field(self):
        """Test that matching works on company name too."""
        filter = ThemeFilter(keywords=["quantum"])

        quantum_corp = Constituent(
            ticker="QBTS",
            name="D-Wave Quantum Inc",
            business_description="Develops quantum computing systems",
        )

        assert filter.matches(quantum_corp) is True

    def test_filter_as_callable(self):
        """Test using ThemeFilter as a callable."""
        filter = ThemeFilter(keywords=["electric", "ev"])

        ev_company = Constituent(
            ticker="TSLA",
            business_description="Electric vehicles and energy storage",
        )

        # Should work both ways
        assert filter.matches(ev_company) is True
        assert filter(ev_company) is True

    def test_empty_keywords_raises_error(self):
        """Test that empty keywords raises ValueError."""
        with pytest.raises(ValueError, match="keywords list cannot be empty"):
            ThemeFilter(keywords=[])

    def test_invalid_match_mode_raises_error(self):
        """Test that invalid match_mode raises ValueError."""
        with pytest.raises(ValueError, match="match_mode must be 'any' or 'all'"):
            ThemeFilter(keywords=["test"], match_mode="invalid")


class TestCreateThemeFilter:
    """Tests for create_theme_filter factory function."""

    def test_creates_callable_filter(self):
        """Test that factory creates a callable filter."""
        filter_fn = create_theme_filter(["renewable", "clean energy"])

        renewable = Constituent(
            ticker="FSLR",
            business_description="First Solar manufactures renewable energy solutions",
        )
        fossil = Constituent(
            ticker="XOM",
            business_description="Exxon is an oil and gas company",
        )

        assert filter_fn(renewable) is True
        assert filter_fn(fossil) is False

    def test_factory_with_all_mode(self):
        """Test factory with all match mode."""
        filter_fn = create_theme_filter(["electric", "vehicle"], match_mode="all")

        ev = Constituent(
            ticker="RIVN",
            business_description="Rivian makes electric vehicles",
        )
        battery = Constituent(
            ticker="ALB",
            business_description="Albemarle produces electric battery materials",
        )

        assert filter_fn(ev) is True
        assert filter_fn(battery) is False


class TestPredefinedThemes:
    """Tests for predefined themes."""

    def test_get_predefined_theme_exists(self):
        """Test getting an existing predefined theme."""
        theme = get_predefined_theme("quantum_computing")

        assert theme is not None
        assert isinstance(theme, ThemeFilter)
        assert "quantum" in theme.keywords

    def test_get_predefined_theme_not_exists(self):
        """Test getting a non-existent theme."""
        theme = get_predefined_theme("nonexistent_theme")
        assert theme is None

    def test_predefined_themes_dictionary(self):
        """Test that predefined themes dictionary has expected keys."""
        expected_themes = [
            "quantum_computing",
            "renewable_energy",
            "artificial_intelligence",
            "electric_vehicles",
            "cybersecurity",
            "biotechnology",
            "blockchain",
        ]

        for theme_name in expected_themes:
            assert theme_name in PREDEFINED_THEMES
            assert len(PREDEFINED_THEMES[theme_name]) > 0


class TestSelectionCriteriaWithTheme:
    """Tests for SelectionCriteria integration with theme filtering."""

    def test_builder_theme_filter(self):
        """Test using theme_filter in builder."""
        criteria = (
            SelectionCriteria.builder().theme_filter(["quantum", "qubit"]).select_top(10).build()
        )

        constituents = [
            Constituent(
                ticker="IONQ",
                market_cap=5e9,
                business_description="IonQ is a quantum computing company",
            ),
            Constituent(
                ticker="RGTI",
                market_cap=1e9,
                business_description="Rigetti develops qubit processors",
            ),
            Constituent(
                ticker="AAPL",
                market_cap=3e12,
                business_description="Apple makes consumer electronics",
            ),
        ]

        selected = criteria.select(constituents)

        assert len(selected) == 2
        selected_tickers = {c.ticker for c in selected}
        assert selected_tickers == {"IONQ", "RGTI"}

    def test_theme_filter_with_ranking(self):
        """Test theme filter combined with ranking."""
        from indexmaker.core.types import Factor

        criteria = (
            SelectionCriteria.builder()
            .theme_filter(["renewable", "solar", "wind"])
            .ranking_by(Factor.MARKET_CAP)
            .select_top(2)
            .build()
        )

        constituents = [
            Constituent(
                ticker="ENPH",
                market_cap=30e9,
                business_description="Enphase makes solar microinverters",
            ),
            Constituent(
                ticker="FSLR",
                market_cap=20e9,
                business_description="First Solar manufactures solar panels",
            ),
            Constituent(
                ticker="NEE",
                market_cap=150e9,
                business_description="NextEra Energy operates wind farms",
            ),
            Constituent(
                ticker="XOM",
                market_cap=400e9,
                business_description="Exxon is in oil and gas",
            ),
        ]

        selected = criteria.select(constituents)

        assert len(selected) == 2
        # Should be top 2 renewable companies by market cap
        selected_tickers = {c.ticker for c in selected}
        assert "XOM" not in selected_tickers  # Oil company excluded
        assert "NEE" in selected_tickers  # Highest market cap renewable

    def test_multiple_custom_filters_with_theme(self):
        """Test combining theme filter with other custom filters."""
        criteria = (
            SelectionCriteria.builder()
            .theme_filter(["technology", "software"])
            .custom_filter(lambda c: c.market_cap > 100e9)  # Large cap only
            .select_top(10)
            .build()
        )

        constituents = [
            Constituent(
                ticker="MSFT",
                market_cap=3e12,
                business_description="Microsoft develops software",
            ),
            Constituent(
                ticker="SMALL",
                market_cap=10e9,
                business_description="Small technology company",
            ),
        ]

        selected = criteria.select(constituents)

        assert len(selected) == 1
        assert selected[0].ticker == "MSFT"
