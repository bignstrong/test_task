#!/usr/bin/env python3
"""
Configuration Management Service
Main entry point for the Twisted web service
"""

import os
from twisted.internet import reactor, defer
from twisted.web import server
from twisted.python import log
import sys

from api.server import ConfigurationService
from database.connection import DatabaseManager

def main():
    """Initialize and start the configuration service"""
    log.startLogging(sys.stdout)
    
    # Database connection
    database_url = os.getenv('DATABASE_URL', 'postgresql://config_user:config_pass@localhost:5432/config_db')
    db_manager = DatabaseManager(database_url)
    
    # Initialize database connection
    @defer.inlineCallbacks
    def setup():
        yield db_manager.initialize()
        log.msg("Database connection initialized")
        
        # Create and start the web service
        service = ConfigurationService(db_manager)
        site = server.Site(service.app)
        reactor.listenTCP(8080, site)
        log.msg("Configuration service started on port 8080")
    
    # Setup and run
    setup()
    reactor.run()

if __name__ == '__main__':
    main()