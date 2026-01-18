"""Data connectors for various data sources."""

from indexmaker.data.connectors.base import DataConnector
from indexmaker.data.connectors.yahoo import YahooFinanceConnector

# Optional connectors (may require additional dependencies)
try:
    from indexmaker.data.connectors.openbb import OpenBBConnector
except ImportError:
    OpenBBConnector = None  # type: ignore

__all__ = [
    "DataConnector",
    "YahooFinanceConnector",
    "OpenBBConnector",
]
