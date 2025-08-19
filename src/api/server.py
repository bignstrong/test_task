"""
REST API server for configuration management
"""

from twisted.web import resource, server
from twisted.internet import defer
from twisted.python import log
import json
from typing import Dict, Any, Optional

from database.connection import DatabaseManager
from models.configuration import ConfigurationValidator, ConfigurationProcessor
from .handlers import ConfigurationHandler

class ConfigurationService:
    """Main configuration service class"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.app = self._create_app()
    
    def _create_app(self) -> resource.Resource:
        """Create the web application resource tree"""
        root = resource.Resource()
        
        # Add config resource with handlers
        config_resource = ConfigResource(self.db_manager)
        root.putChild(b'config', config_resource)
        
        return root

class ConfigResource(resource.Resource):
    """Main config resource that handles routing"""
    
    def __init__(self, db_manager: DatabaseManager):
        resource.Resource.__init__(self)
        self.db_manager = db_manager
        self.handler = ConfigurationHandler(db_manager)
    
    def getChild(self, path: bytes, request) -> resource.Resource:
        """Route requests to service-specific resources"""
        service_name = path.decode('utf-8')
        return ServiceResource(self.db_manager, service_name, self.handler)

class ServiceResource(resource.Resource):
    """Resource for service-specific operations"""
    
    def __init__(self, db_manager: DatabaseManager, service_name: str, handler: ConfigurationHandler):
        resource.Resource.__init__(self)
        self.db_manager = db_manager
        self.service_name = service_name
        self.handler = handler
        
        # Add history child resource
        self.putChild(b'history', HistoryResource(db_manager, service_name, handler))
    
    def render_POST(self, request) -> bytes:
        """Handle POST requests to upload configuration"""
        def handle_response(result):
            request.setHeader(b'content-type', b'application/json')
            if isinstance(result, dict) and 'error' in result:
                request.setResponseCode(result.get('status_code', 500))
            else:
                request.setResponseCode(201)
            request.write(json.dumps(result, indent=2).encode('utf-8'))
            request.finish()
        
        def handle_error(failure):
            log.err(failure)
            request.setResponseCode(500)
            request.setHeader(b'content-type', b'application/json')
            error_response = {
                "error": "Internal server error",
                "message": str(failure.value)
            }
            request.write(json.dumps(error_response, indent=2).encode('utf-8'))
            request.finish()
        
        d = self.handler.handle_post_config(request, self.service_name)
        d.addCallback(handle_response)
        d.addErrback(handle_error)
        
        return server.NOT_DONE_YET
    
    def render_GET(self, request) -> bytes:
        """Handle GET requests to retrieve configuration"""
        def handle_response(result):
            request.setHeader(b'content-type', b'application/json')
            if isinstance(result, dict) and 'error' in result:
                request.setResponseCode(result.get('status_code', 404))
            else:
                request.setResponseCode(200)
            request.write(json.dumps(result, indent=2).encode('utf-8'))
            request.finish()
        
        def handle_error(failure):
            log.err(failure)
            request.setResponseCode(500)
            request.setHeader(b'content-type', b'application/json')
            error_response = {
                "error": "Internal server error",
                "message": str(failure.value)
            }
            request.write(json.dumps(error_response, indent=2).encode('utf-8'))
            request.finish()
        
        d = self.handler.handle_get_config(request, self.service_name)
        d.addCallback(handle_response)
        d.addErrback(handle_error)
        
        return server.NOT_DONE_YET

class HistoryResource(resource.Resource):
    """Resource for configuration history"""
    
    def __init__(self, db_manager: DatabaseManager, service_name: str, handler: ConfigurationHandler):
        resource.Resource.__init__(self)
        self.db_manager = db_manager
        self.service_name = service_name
        self.handler = handler
    
    def render_GET(self, request) -> bytes:
        """Handle GET requests for configuration history"""
        def handle_response(result):
            request.setHeader(b'content-type', b'application/json')
            if isinstance(result, dict) and 'error' in result:
                request.setResponseCode(result.get('status_code', 404))
            else:
                request.setResponseCode(200)
            request.write(json.dumps(result, indent=2).encode('utf-8'))
            request.finish()
        
        def handle_error(failure):
            log.err(failure)
            request.setResponseCode(500)
            request.setHeader(b'content-type', b'application/json')
            error_response = {
                "error": "Internal server error",
                "message": str(failure.value)
            }
            request.write(json.dumps(error_response, indent=2).encode('utf-8'))
            request.finish()
        
        d = self.handler.handle_get_history(request, self.service_name)
        d.addCallback(handle_response)
        d.addErrback(handle_error)
        
        return server.NOT_DONE_YET