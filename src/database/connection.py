"""
Database connection and management
"""

import aiopg
from twisted.internet import defer, threads, reactor
from twisted.python import log
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import asyncio

class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None
        self._loop = None
    
    @defer.inlineCallbacks
    def initialize(self):
        """Initialize database connection pool"""
        try:
            # Create event loop in a thread
            self._loop = yield threads.deferToThread(self._create_loop)
            self.pool = yield threads.deferToThread(self._create_pool)
            log.msg("Database pool created successfully")
        except Exception as e:
            log.err(f"Failed to initialize database: {e}")
            raise
    
    def _create_loop(self):
        """Create and return a new event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
    
    def _create_pool(self):
        """Create aiopg connection pool using the existing loop"""
        async def create():
            return await aiopg.create_pool(self.database_url)
        
        return self._loop.run_until_complete(create())
    
    @defer.inlineCallbacks
    def save_configuration(self, service: str, payload: Dict[str, Any], version: Optional[int] = None) -> Dict[str, Any]:
        """Save configuration to database"""
        try:
            result = yield threads.deferToThread(
                self._save_config_sync, service, payload, version
            )
            defer.returnValue(result)
        except Exception as e:
            log.err(f"Failed to save configuration: {e}")
            raise
    
    def _save_config_sync(self, service: str, payload: Dict[str, Any], version: Optional[int] = None) -> Dict[str, Any]:
        """Synchronous save configuration using the existing loop"""
        async def save():
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    # Get next version if not specified
                    if version is None:
                        await cur.execute(
                            "SELECT COALESCE(MAX(version), 0) + 1 FROM configurations WHERE service = %s",
                            (service,)
                        )
                        current_version = (await cur.fetchone())[0]
                    else:
                        current_version = version
                    
                    # Insert new configuration
                    await cur.execute(
                        """
                        INSERT INTO configurations (service, version, payload, created_at)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (service, current_version, json.dumps(payload), datetime.now())
                    )
                    
                    return {
                        "service": service,
                        "version": current_version,
                        "status": "saved"
                    }
        
        return self._loop.run_until_complete(save())
    
    @defer.inlineCallbacks
    def get_configuration(self, service: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get configuration from database"""
        try:
            result = yield threads.deferToThread(
                self._get_config_sync, service, version
            )
            defer.returnValue(result)
        except Exception as e:
            log.err(f"Failed to get configuration: {e}")
            raise
    
    def _get_config_sync(self, service: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Synchronous get configuration using the existing loop"""
        async def get():
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    if version is not None:
                        # Get specific version
                        await cur.execute(
                            "SELECT payload FROM configurations WHERE service = %s AND version = %s",
                            (service, version)
                        )
                    else:
                        # Get latest version
                        await cur.execute(
                            """
                            SELECT payload FROM configurations 
                            WHERE service = %s 
                            ORDER BY version DESC 
                            LIMIT 1
                            """,
                            (service,)
                        )
                    
                    row = await cur.fetchone()
                    if row:
                        return json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    return None
        
        return self._loop.run_until_complete(get())
    
    @defer.inlineCallbacks
    def get_configuration_history(self, service: str) -> List[Dict[str, Any]]:
        """Get configuration history for a service"""
        try:
            result = yield threads.deferToThread(
                self._get_history_sync, service
            )
            defer.returnValue(result)
        except Exception as e:
            log.err(f"Failed to get configuration history: {e}")
            raise
    
    def _get_history_sync(self, service: str) -> List[Dict[str, Any]]:
        """Synchronous get configuration history using the existing loop"""
        async def get_history():
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT version, created_at FROM configurations 
                        WHERE service = %s 
                        ORDER BY version DESC
                        """,
                        (service,)
                    )
                    
                    rows = await cur.fetchall()
                    return [
                        {
                            "version": row[0],
                            "created_at": row[1].isoformat()
                        }
                        for row in rows
                    ]
        
        return self._loop.run_until_complete(get_history())
    
    def close(self):
        """Close database connections"""
        if self.pool:
            self._loop.run_until_complete(self.pool.close())
        if self._loop and not self._loop.is_closed():
            self._loop.close()