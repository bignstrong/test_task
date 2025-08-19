"""
Request handlers for the configuration API
"""

from twisted.internet import defer
from twisted.python import log
from typing import Dict, Any, Optional, List
import json

from database.connection import DatabaseManager
from models.configuration import ConfigurationValidator, ConfigurationProcessor

class ConfigurationHandler:
    """Handles configuration-related HTTP requests"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.validator = ConfigurationValidator()
        self.processor = ConfigurationProcessor()
    
    @defer.inlineCallbacks
    def handle_post_config(self, request, service_name: str) -> Dict[str, Any]:
        """Handle POST request to save configuration"""
        try:
            # Read request body
            content = request.content.read()
            if not content:
                defer.returnValue({
                    "error": "Empty request body",
                    "status_code": 400
                })
            
            yaml_content = content.decode('utf-8')
            
            # Validate YAML format
            try:
                config_data = self.validator.validate_yaml(yaml_content)
            except ValueError as e:
                defer.returnValue({
                    "error": "Bad Request",
                    "message": str(e),
                    "status_code": 400
                })
            
            # Validate configuration structure
            validation_errors = self.validator.validate_configuration(config_data)
            if validation_errors:
                defer.returnValue({
                    "error": "Unprocessable Entity",
                    "validation_errors": validation_errors,
                    "status_code": 422
                })
            
            # Extract version if specified
            version = config_data.get('version')
            
            # Save configuration to database
            try:
                result = yield self.db_manager.save_configuration(
                    service_name, config_data, version
                )
                defer.returnValue(result)
            except Exception as e:
                log.err(f"Database error: {e}")
                if "duplicate key value" in str(e).lower():
                    defer.returnValue({
                        "error": "Version already exists",
                        "message": f"Version {version} already exists for service {service_name}",
                        "status_code": 409
                    })
                raise
        
        except Exception as e:
            log.err(f"Error handling POST config: {e}")
            defer.returnValue({
                "error": "Internal server error",
                "message": str(e),
                "status_code": 500
            })
    
    @defer.inlineCallbacks
    def handle_get_config(self, request, service_name: str) -> Dict[str, Any]:
        """Handle GET request to retrieve configuration"""
        try:
            # Parse query parameters
            version = self._get_query_param(request, 'version')
            template_flag = self._get_query_param(request, 'template')
            
            # Convert version to int if provided
            if version:
                try:
                    version = int(version)
                except ValueError:
                    defer.returnValue({
                        "error": "Invalid version parameter",
                        "message": "Version must be an integer",
                        "status_code": 400
                    })
            
            # Retrieve configuration from database
            config = yield self.db_manager.get_configuration(service_name, version)
            
            if config is None:
                if version:
                    message = f"Configuration version {version} not found for service {service_name}"
                else:
                    message = f"No configuration found for service {service_name}"
                
                defer.returnValue({
                    "error": "Not Found",
                    "message": message,
                    "status_code": 404
                })
            
            # Process template if requested
            if template_flag == '1':
                # Extract template variables from query parameters
                template_vars = {}
                
                # Get template variables from query params
                for key, values in request.args.items():
                    key_str = key.decode('utf-8')
                    if key_str not in ['version', 'template']:  # Skip special params
                        template_vars[key_str] = values[0].decode('utf-8')
                
                # Add default template variables
                template_vars.setdefault('user', 'Anonymous')
                
                try:
                    config = self.processor.process_template(config, template_vars)
                except ValueError as e:
                    defer.returnValue({
                        "error": "Template processing error",
                        "message": str(e),
                        "status_code": 400
                    })
            
            defer.returnValue(config)
        
        except Exception as e:
            log.err(f"Error handling GET config: {e}")
            defer.returnValue({
                "error": "Internal server error",
                "message": str(e),
                "status_code": 500
            })
    
    @defer.inlineCallbacks
    def handle_get_history(self, request, service_name: str) -> List[Dict[str, Any]]:
        """Handle GET request to retrieve configuration history"""
        try:
            # Retrieve configuration history from database
            history = yield self.db_manager.get_configuration_history(service_name)
            
            if not history:
                defer.returnValue({
                    "error": "Not Found",
                    "message": f"No configuration history found for service {service_name}",
                    "status_code": 404
                })
            
            defer.returnValue(history)
        
        except Exception as e:
            log.err(f"Error handling GET history: {e}")
            defer.returnValue({
                "error": "Internal server error",
                "message": str(e),
                "status_code": 500
            })
    
    def _get_query_param(self, request, param_name: str) -> Optional[str]:
        """Extract query parameter from request"""
        args = request.args
        if param_name.encode() in args:
            return args[param_name.encode()][0].decode('utf-8')
        return None