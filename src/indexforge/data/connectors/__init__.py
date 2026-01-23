"""Data connectors for various data sources."""

from indexforge.data.connectors.base import DataConnector
from indexforge.data.connectors.yahoo import YahooFinanceConnector

# Optional connectors (may require additional dependencies)
try:
    from indexforge.data.connectors.openbb import OpenBBConnector
except ImportError:
    OpenBBConnector = None  # type: ignore

__all__ = [
    "DataConnector",
    "YahooFinanceConnector",
    "OpenBBConnector",
]
