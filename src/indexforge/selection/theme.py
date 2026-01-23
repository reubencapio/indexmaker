"""
Theme-based filtering for companies.

Provides utilities to filter constituents based on keywords in their
business descriptions, enabling thematic index creation.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

from indexforge.core.constituent import Constituent


@dataclass
class ThemeFilter:
    """
    Filter constituents by keywords in their business descriptions.

    This enables thematic index creation by selecting companies
    involved in specific themes like "quantum computing", "renewable energy", etc.

    Attributes:
        keywords: List of keywords to match
        match_mode: "any" (match at least one) or "all" (match all keywords)
        case_sensitive: Whether matching is case-sensitive

    Example:
        >>> filter = ThemeFilter(keywords=["quantum", "qubit"])
        >>> quantum_companies = [c for c in constituents if filter.matches(c)]
    """

    keywords: list[str] = field(default_factory=list)
    match_mode: str = "any"  # "any" or "all"
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.match_mode not in ("any", "all"):
            raise ValueError(f"match_mode must be 'any' or 'all', got '{self.match_mode}'")
        if not self.keywords:
            raise ValueError("keywords list cannot be empty")

    def matches(self, constituent: Constituent) -> bool:
        """
        Check if constituent matches the theme keywords.

        Searches both business_description and industry fields.

        Args:
            constituent: The constituent to check

        Returns:
            True if constituent matches the theme criteria
        """
        # Combine searchable text fields
        searchable_text = " ".join(
            [
                constituent.business_description or "",
                constituent.industry or "",
                constituent.name or "",
            ]
        )

        if not self.case_sensitive:
            searchable_text = searchable_text.lower()
            keywords = [k.lower() for k in self.keywords]
        else:
            keywords = self.keywords

        if self.match_mode == "any":
            return any(keyword in searchable_text for keyword in keywords)
        else:  # match_mode == "all"
            return all(keyword in searchable_text for keyword in keywords)

    def __call__(self, constituent: Constituent) -> bool:
        """Allow using ThemeFilter as a callable filter function."""
        return self.matches(constituent)


def create_theme_filter(
    keywords: list[str],
    match_mode: str = "any",
    case_sensitive: bool = False,
) -> Callable[[Constituent], bool]:
    """
    Create a theme filter function.

    This is a convenience factory for creating filter functions
    that can be used with SelectionCriteria.custom_filter().

    Args:
        keywords: Keywords to search for in business descriptions
        match_mode: "any" (default) or "all"
        case_sensitive: Whether matching is case-sensitive

    Returns:
        A callable filter function

    Example:
        >>> criteria = (SelectionCriteria.builder()
        ...     .custom_filter(create_theme_filter(["quantum", "computing"]))
        ...     .select_top(20)
        ...     .build()
        ... )
    """
    return ThemeFilter(
        keywords=keywords,
        match_mode=match_mode,
        case_sensitive=case_sensitive,
    )


# Predefined themes for common use cases
PREDEFINED_THEMES: dict[str, list[str]] = {
    "quantum_computing": [
        "quantum",
        "qubit",
        "quantum computing",
        "quantum processor",
    ],
    "renewable_energy": [
        "solar",
        "wind energy",
        "renewable",
        "clean energy",
        "sustainable energy",
    ],
    "artificial_intelligence": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural network",
        "AI",
    ],
    "electric_vehicles": [
        "electric vehicle",
        "EV",
        "battery",
        "electric car",
        "charging station",
    ],
    "cybersecurity": [
        "cybersecurity",
        "cyber security",
        "information security",
        "data protection",
        "encryption",
    ],
    "biotechnology": [
        "biotech",
        "biotechnology",
        "gene therapy",
        "CRISPR",
        "pharmaceutical",
    ],
    "blockchain": [
        "blockchain",
        "cryptocurrency",
        "digital asset",
        "decentralized",
        "smart contract",
    ],
}


def get_predefined_theme(theme_name: str) -> Optional[ThemeFilter]:
    """
    Get a predefined theme filter.

    Args:
        theme_name: Name of the theme (e.g., "quantum_computing")

    Returns:
        ThemeFilter for the theme, or None if not found
    """
    keywords = PREDEFINED_THEMES.get(theme_name.lower().replace(" ", "_"))
    if keywords:
        return ThemeFilter(keywords=keywords)
    return None
