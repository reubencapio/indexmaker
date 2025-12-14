"""
Type definitions and enums for Index Maker.

These types use domain-specific language familiar to index professionals.
"""

from enum import Enum


class Currency(str, Enum):
    """Supported currencies for index calculation."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    HKD = "HKD"
    SGD = "SGD"
    CNY = "CNY"
    KRW = "KRW"
    INR = "INR"
    BRL = "BRL"
    MXN = "MXN"

    def __str__(self) -> str:
        return self.value


class IndexType(str, Enum):
    """Types of index return calculation."""

    PRICE_RETURN = "PRICE_RETURN"
    TOTAL_RETURN = "TOTAL_RETURN"
    NET_RETURN = "NET_RETURN"
    CURRENCY_HEDGED = "CURRENCY_HEDGED"

    def __str__(self) -> str:
        return self.value


class AssetClass(str, Enum):
    """Asset classes for universe definition."""

    EQUITIES = "EQUITIES"
    FIXED_INCOME = "FIXED_INCOME"
    COMMODITIES = "COMMODITIES"
    CURRENCIES = "CURRENCIES"
    ALTERNATIVES = "ALTERNATIVES"
    MULTI_ASSET = "MULTI_ASSET"

    def __str__(self) -> str:
        return self.value


class Region(str, Enum):
    """Geographic regions for universe filtering."""

    GLOBAL = "GLOBAL"
    NORTH_AMERICA = "NORTH_AMERICA"
    EUROPE = "EUROPE"
    ASIA_PACIFIC = "ASIA_PACIFIC"
    EMERGING_MARKETS = "EMERGING_MARKETS"
    DEVELOPED_MARKETS = "DEVELOPED_MARKETS"
    LATIN_AMERICA = "LATIN_AMERICA"
    MIDDLE_EAST = "MIDDLE_EAST"
    AFRICA = "AFRICA"

    # Specific countries
    US = "US"
    UK = "UK"
    GERMANY = "GERMANY"
    FRANCE = "FRANCE"
    JAPAN = "JAPAN"
    CHINA = "CHINA"
    INDIA = "INDIA"
    BRAZIL = "BRAZIL"
    CANADA = "CANADA"
    AUSTRALIA = "AUSTRALIA"

    def __str__(self) -> str:
        return self.value


class Country(str, Enum):
    """Country codes used for universe filtering."""

    # North America
    UNITED_STATES = "United States"
    CANADA = "Canada"
    MEXICO = "Mexico"

    # Europe - Developed
    AUSTRIA = "Austria"
    BELGIUM = "Belgium"
    DENMARK = "Denmark"
    FINLAND = "Finland"
    FRANCE = "France"
    GERMANY = "Germany"
    GREECE = "Greece"
    IRELAND = "Ireland"
    ITALY = "Italy"
    LUXEMBOURG = "Luxembourg"
    NETHERLANDS = "Netherlands"
    NORWAY = "Norway"
    PORTUGAL = "Portugal"
    SPAIN = "Spain"
    SWEDEN = "Sweden"
    SWITZERLAND = "Switzerland"
    UNITED_KINGDOM = "United Kingdom"

    # Europe - Emerging
    CZECH_REPUBLIC = "Czech Republic"
    HUNGARY = "Hungary"
    POLAND = "Poland"
    TURKEY = "Turkey"

    # Asia-Pacific - Developed
    AUSTRALIA = "Australia"
    HONG_KONG = "Hong Kong"
    JAPAN = "Japan"
    NEW_ZEALAND = "New Zealand"
    SINGAPORE = "Singapore"

    # Asia-Pacific - Emerging
    CHINA = "China"
    INDIA = "India"
    INDONESIA = "Indonesia"
    MALAYSIA = "Malaysia"
    PHILIPPINES = "Philippines"
    SOUTH_KOREA = "South Korea"
    TAIWAN = "Taiwan"
    THAILAND = "Thailand"

    # Latin America
    ARGENTINA = "Argentina"
    BRAZIL = "Brazil"
    CHILE = "Chile"
    COLOMBIA = "Colombia"

    # Middle East & Africa
    EGYPT = "Egypt"
    ISRAEL = "Israel"
    KUWAIT = "Kuwait"
    QATAR = "Qatar"
    SAUDI_ARABIA = "Saudi Arabia"
    SOUTH_AFRICA = "South Africa"
    UNITED_ARAB_EMIRATES = "United Arab Emirates"

    def __str__(self) -> str:
        return self.value


class Factor(str, Enum):
    """Factors for selection and weighting."""

    MARKET_CAP = "MARKET_CAP"
    FREE_FLOAT_MARKET_CAP = "FREE_FLOAT_MARKET_CAP"
    LIQUIDITY = "LIQUIDITY"
    VOLUME = "VOLUME"
    MOMENTUM = "MOMENTUM"
    VALUE = "VALUE"
    QUALITY = "QUALITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    DIVIDEND_YIELD = "DIVIDEND_YIELD"
    EARNINGS_GROWTH = "EARNINGS_GROWTH"
    REVENUE_GROWTH = "REVENUE_GROWTH"
    ROE = "ROE"
    ROA = "ROA"
    DEBT_TO_EQUITY = "DEBT_TO_EQUITY"
    PRICE_TO_EARNINGS = "PRICE_TO_EARNINGS"
    PRICE_TO_BOOK = "PRICE_TO_BOOK"

    def __str__(self) -> str:
        return self.value


class WeightingScheme(str, Enum):
    """Weighting scheme types."""

    EQUAL_WEIGHT = "EQUAL_WEIGHT"
    MARKET_CAP = "MARKET_CAP"
    FREE_FLOAT_MARKET_CAP = "FREE_FLOAT_MARKET_CAP"
    FACTOR_BASED = "FACTOR_BASED"
    CUSTOM = "CUSTOM"

    def __str__(self) -> str:
        return self.value


class RebalancingFrequency(str, Enum):
    """Rebalancing frequency options."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"

    def __str__(self) -> str:
        return self.value


class CorporateActionType(str, Enum):
    """Types of corporate actions."""

    DIVIDEND = "DIVIDEND"
    STOCK_SPLIT = "STOCK_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    SPIN_OFF = "SPIN_OFF"
    MERGER = "MERGER"
    ACQUISITION = "ACQUISITION"
    BANKRUPTCY = "BANKRUPTCY"
    DELISTING = "DELISTING"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"

    def __str__(self) -> str:
        return self.value


class Sector(str, Enum):
    """
    GICS Sectors (Global Industry Classification Standard).

    These are the 11 standard sectors used by MSCI and S&P.
    Yahoo Finance and most data providers use these classifications.
    """

    # The 11 GICS Sectors
    COMMUNICATION_SERVICES = "Communication Services"
    CONSUMER_DISCRETIONARY = "Consumer Discretionary"
    CONSUMER_STAPLES = "Consumer Staples"
    ENERGY = "Energy"
    FINANCIALS = "Financials"
    HEALTH_CARE = "Health Care"
    INDUSTRIALS = "Industrials"
    INFORMATION_TECHNOLOGY = "Information Technology"
    MATERIALS = "Materials"
    REAL_ESTATE = "Real Estate"
    UTILITIES = "Utilities"

    # Aliases for common variations (Yahoo Finance uses these)
    TECHNOLOGY = "Technology"
    HEALTHCARE = "Healthcare"
    FINANCIAL_SERVICES = "Financial Services"
    CONSUMER_DEFENSIVE = "Consumer Defensive"
    CONSUMER_CYCLICAL = "Consumer Cyclical"
    BASIC_MATERIALS = "Basic Materials"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "Sector":
        """
        Convert string to Sector enum, handling common variations.

        Args:
            value: Sector name string

        Returns:
            Matching Sector enum
        """
        # Normalize the input
        normalized = value.strip()

        # Try exact match first
        for sector in cls:
            if sector.value == normalized:
                return sector

        # Try case-insensitive match
        normalized_lower = normalized.lower()
        for sector in cls:
            if sector.value.lower() == normalized_lower:
                return sector

        # Common mappings
        mappings = {
            "tech": cls.TECHNOLOGY,
            "info tech": cls.INFORMATION_TECHNOLOGY,
            "it": cls.INFORMATION_TECHNOLOGY,
            "finance": cls.FINANCIALS,
            "financial": cls.FINANCIALS,
            "health": cls.HEALTH_CARE,
            "telecom": cls.COMMUNICATION_SERVICES,
            "telecommunications": cls.COMMUNICATION_SERVICES,
            "consumer goods": cls.CONSUMER_STAPLES,
            "retail": cls.CONSUMER_DISCRETIONARY,
        }

        if normalized_lower in mappings:
            return mappings[normalized_lower]

        # If no match, raise error with helpful message
        valid_sectors = [s.value for s in cls]
        raise ValueError(
            f"Unknown sector: '{value}'. " f"Valid sectors: {', '.join(valid_sectors[:6])}..."
        )


class Industry(str, Enum):
    """
    Common industries for more granular classification.

    These are examples of GICS Sub-Industries. The full list has 100+.
    Add more as needed for your use case.
    """

    # Technology
    SOFTWARE = "Software"
    SEMICONDUCTORS = "Semiconductors"
    IT_SERVICES = "IT Services"
    HARDWARE = "Hardware"
    CONSUMER_ELECTRONICS = "Consumer Electronics"

    # Healthcare
    PHARMACEUTICALS = "Pharmaceuticals"
    BIOTECHNOLOGY = "Biotechnology"
    MEDICAL_DEVICES = "Medical Devices"
    HEALTHCARE_SERVICES = "Healthcare Services"

    # Financials
    BANKS = "Banks"
    INSURANCE = "Insurance"
    ASSET_MANAGEMENT = "Asset Management"
    CAPITAL_MARKETS = "Capital Markets"

    # Consumer
    RETAIL = "Retail"
    AUTOMOBILES = "Automobiles"
    HOTELS_RESTAURANTS = "Hotels & Restaurants"
    APPAREL = "Apparel"

    # Energy
    OIL_GAS = "Oil & Gas"
    RENEWABLE_ENERGY = "Renewable Energy"

    # Industrials
    AEROSPACE_DEFENSE = "Aerospace & Defense"
    AIRLINES = "Airlines"
    MACHINERY = "Machinery"

    # Communication
    MEDIA = "Media"
    ENTERTAINMENT = "Entertainment"
    TELECOM = "Telecommunications"
    INTERNET = "Internet"

    def __str__(self) -> str:
        return self.value


# Type aliases for clarity
Ticker = str
ISIN = str
SEDOL = str
Weight = float
Price = float
MarketCap = float
Volume = float


# Country code mapping for region resolution
REGION_COUNTRIES: dict[Region, list[str]] = {
    Region.NORTH_AMERICA: ["US", "CA", "MX"],
    Region.EUROPE: [
        "GB",
        "DE",
        "FR",
        "IT",
        "ES",
        "NL",
        "CH",
        "SE",
        "NO",
        "DK",
        "FI",
        "BE",
        "AT",
        "IE",
        "PT",
        "PL",
    ],
    Region.ASIA_PACIFIC: [
        "JP",
        "CN",
        "HK",
        "KR",
        "TW",
        "SG",
        "AU",
        "NZ",
        "IN",
        "ID",
        "MY",
        "TH",
        "PH",
        "VN",
    ],
    Region.LATIN_AMERICA: ["BR", "MX", "AR", "CL", "CO", "PE"],
    Region.MIDDLE_EAST: ["AE", "SA", "IL", "QA", "KW"],
    Region.AFRICA: ["ZA", "EG", "NG", "KE", "MA"],
}

DEVELOPED_MARKETS = ["US", "CA", "GB", "DE", "FR", "JP", "AU", "CH", "NL", "SE", "HK", "SG"]
EMERGING_MARKETS = ["CN", "IN", "BR", "RU", "ZA", "MX", "KR", "TW", "ID", "TH", "MY", "PL"]
