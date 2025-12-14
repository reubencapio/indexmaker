"""
Data Source Service.

Handles syncing securities from external APIs and databases.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import CustomDataSource, CustomSecurity, DataSourceType


class DataSourceService:
    """
    Service for syncing data from external sources.
    
    Supports:
    - REST API endpoints
    - PostgreSQL/MySQL databases
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def sync_from_api(
        self,
        data_source: CustomDataSource,
    ) -> dict[str, Any]:
        """
        Sync securities from an external REST API.
        
        Expected config:
        {
            "endpoint": "https://api.example.com/securities",
            "method": "GET",  # GET or POST
            "headers": {"Authorization": "Bearer xxx"},
            "params": {"limit": 1000},  # Query params for GET
            "body": {},  # Body for POST
            "response_path": "data.securities",  # JSONPath to securities array
        }
        
        Expected field_mapping:
        {
            "ticker": "symbol",  # Their field -> our field
            "name": "company_name",
            "sector": "sector",
            "market_cap": "marketCap",
            ...
        }
        """
        config = data_source.config or {}
        field_mapping = data_source.field_mapping or {}
        
        endpoint = config.get("endpoint")
        if not endpoint:
            raise ValueError("API endpoint URL is required")
        
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        body = config.get("body", {})
        response_path = config.get("response_path", "")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if method == "GET":
                    response = await client.get(endpoint, headers=headers, params=params)
                else:
                    response = await client.post(endpoint, headers=headers, json=body)
                
                response.raise_for_status()
                data = response.json()
                
                # Navigate to the securities array using response_path
                securities_data = self._get_nested_value(data, response_path)
                
                if not isinstance(securities_data, list):
                    raise ValueError(f"Expected list at path '{response_path}', got {type(securities_data)}")
                
                # Get existing tickers
                result = await self.db.execute(
                    select(CustomSecurity.ticker).where(
                        CustomSecurity.data_source_id == data_source.id
                    )
                )
                existing_tickers = {row[0] for row in result.fetchall()}
                
                added_count = 0
                updated_count = 0
                
                for item in securities_data:
                    ticker = self._map_field(item, field_mapping.get("ticker", "ticker"))
                    if not ticker:
                        continue
                    
                    ticker = str(ticker).upper().strip()
                    
                    if ticker in existing_tickers:
                        # Update existing
                        result = await self.db.execute(
                            select(CustomSecurity).where(
                                CustomSecurity.data_source_id == data_source.id,
                                CustomSecurity.ticker == ticker,
                            )
                        )
                        security = result.scalar_one_or_none()
                        if security:
                            self._update_security_from_data(security, item, field_mapping)
                            updated_count += 1
                    else:
                        # Create new
                        security = CustomSecurity(
                            data_source_id=data_source.id,
                            ticker=ticker,
                        )
                        self._update_security_from_data(security, item, field_mapping)
                        self.db.add(security)
                        added_count += 1
                        existing_tickers.add(ticker)
                
                # Update data source metadata
                data_source.securities_count = len(existing_tickers)
                data_source.last_synced = datetime.now(timezone.utc)
                
                await self.db.commit()
                
                return {
                    "success": True,
                    "added": added_count,
                    "updated": updated_count,
                    "total": len(existing_tickers),
                }
                
        except httpx.HTTPError as e:
            raise ValueError(f"HTTP error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Sync failed: {str(e)}")
    
    async def sync_from_database(
        self,
        data_source: CustomDataSource,
    ) -> dict[str, Any]:
        """
        Sync securities from an external database.
        
        Expected config:
        {
            "db_type": "postgresql",  # postgresql or mysql
            "host": "localhost",
            "port": 5432,
            "database": "securities_db",
            "username": "user",
            "password": "pass",
            "query": "SELECT symbol, name, sector, market_cap FROM securities WHERE active = true",
        }
        
        Expected field_mapping:
        {
            "ticker": "symbol",
            "name": "name",
            "sector": "sector",
            "market_cap": "market_cap",
        }
        """
        config = data_source.config or {}
        field_mapping = data_source.field_mapping or {}
        
        db_type = config.get("db_type", "postgresql")
        host = config.get("host")
        port = config.get("port", 5432 if db_type == "postgresql" else 3306)
        database = config.get("database")
        username = config.get("username")
        password = config.get("password")
        query = config.get("query")
        
        if not all([host, database, username, query]):
            raise ValueError("Database host, database name, username, and query are required")
        
        try:
            if db_type == "postgresql":
                import asyncpg
                
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    timeout=30,
                )
                
                try:
                    rows = await conn.fetch(query)
                    # Convert to list of dicts
                    securities_data = [dict(row) for row in rows]
                finally:
                    await conn.close()
                    
            elif db_type == "mysql":
                import aiomysql
                
                conn = await aiomysql.connect(
                    host=host,
                    port=port,
                    db=database,
                    user=username,
                    password=password,
                    connect_timeout=30,
                )
                
                try:
                    async with conn.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(query)
                        securities_data = await cursor.fetchall()
                finally:
                    conn.close()
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            # Get existing tickers
            result = await self.db.execute(
                select(CustomSecurity.ticker).where(
                    CustomSecurity.data_source_id == data_source.id
                )
            )
            existing_tickers = {row[0] for row in result.fetchall()}
            
            added_count = 0
            updated_count = 0
            
            for item in securities_data:
                ticker = self._map_field(item, field_mapping.get("ticker", "ticker"))
                if not ticker:
                    continue
                
                ticker = str(ticker).upper().strip()
                
                if ticker in existing_tickers:
                    # Update existing
                    result = await self.db.execute(
                        select(CustomSecurity).where(
                            CustomSecurity.data_source_id == data_source.id,
                            CustomSecurity.ticker == ticker,
                        )
                    )
                    security = result.scalar_one_or_none()
                    if security:
                        self._update_security_from_data(security, item, field_mapping)
                        updated_count += 1
                else:
                    # Create new
                    security = CustomSecurity(
                        data_source_id=data_source.id,
                        ticker=ticker,
                    )
                    self._update_security_from_data(security, item, field_mapping)
                    self.db.add(security)
                    added_count += 1
                    existing_tickers.add(ticker)
            
            # Update data source metadata
            data_source.securities_count = len(existing_tickers)
            data_source.last_synced = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            return {
                "success": True,
                "added": added_count,
                "updated": updated_count,
                "total": len(existing_tickers),
            }
            
        except Exception as e:
            raise ValueError(f"Database sync failed: {str(e)}")
    
    async def test_api_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test an API connection without saving any data."""
        endpoint = config.get("endpoint")
        if not endpoint:
            return {"success": False, "error": "Endpoint URL is required"}
        
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        body = config.get("body", {})
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(endpoint, headers=headers, params=params)
                else:
                    response = await client.post(endpoint, headers=headers, json=body)
                
                response.raise_for_status()
                data = response.json()
                
                # Return sample of response structure
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "sample_keys": list(data.keys()) if isinstance(data, dict) else f"Array with {len(data)} items",
                }
        except httpx.HTTPError as e:
            return {"success": False, "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_database_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        """Test a database connection without running the full query."""
        db_type = config.get("db_type", "postgresql")
        host = config.get("host")
        port = config.get("port", 5432 if db_type == "postgresql" else 3306)
        database = config.get("database")
        username = config.get("username")
        password = config.get("password")
        
        if not all([host, database, username]):
            return {"success": False, "error": "Host, database, and username are required"}
        
        try:
            if db_type == "postgresql":
                import asyncpg
                
                conn = await asyncpg.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    timeout=10,
                )
                
                try:
                    version = await conn.fetchval("SELECT version()")
                    return {"success": True, "message": f"Connected to PostgreSQL", "version": version[:50]}
                finally:
                    await conn.close()
                    
            elif db_type == "mysql":
                import aiomysql
                
                conn = await aiomysql.connect(
                    host=host,
                    port=port,
                    db=database,
                    user=username,
                    password=password,
                    connect_timeout=10,
                )
                
                try:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT VERSION()")
                        version = await cursor.fetchone()
                        return {"success": True, "message": "Connected to MySQL", "version": version[0]}
                finally:
                    conn.close()
            else:
                return {"success": False, "error": f"Unsupported database type: {db_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Get a nested value from a dict using dot notation path."""
        if not path:
            return data
        
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        
        return current
    
    def _map_field(self, data: dict, field_name: str) -> Any:
        """Get a field value from data, supporting nested paths."""
        if not field_name:
            return None
        return self._get_nested_value(data, field_name)
    
    def _update_security_from_data(
        self,
        security: CustomSecurity,
        data: dict,
        field_mapping: dict[str, str],
    ) -> None:
        """Update a security object from source data using field mapping."""
        mapping = {
            "name": "name",
            "sector": "sector",
            "industry": "industry",
            "country": "country",
            "exchange": "exchange",
            "market_cap": "market_cap",
            "price": "price",
            "avg_volume": "avg_volume",
            "free_float": "free_float",
            "pe_ratio": "pe_ratio",
            "pb_ratio": "pb_ratio",
            "dividend_yield": "dividend_yield",
            "revenue": "revenue",
            "earnings": "earnings",
        }
        
        for our_field, default_source_field in mapping.items():
            source_field = field_mapping.get(our_field, default_source_field)
            value = self._map_field(data, source_field)
            
            if value is not None:
                # Convert numeric fields
                if our_field in ["market_cap", "price", "avg_volume", "free_float", 
                                 "pe_ratio", "pb_ratio", "dividend_yield", "revenue", "earnings"]:
                    try:
                        value = float(str(value).replace(",", "").replace("$", ""))
                    except (ValueError, TypeError):
                        value = None
                
                if value is not None:
                    setattr(security, our_field, value)

