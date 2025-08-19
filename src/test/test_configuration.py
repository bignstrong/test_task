"""
Tests for configuration management
"""

import pytest
import json
from twisted.test import test_internet
from twisted.web import server
from twisted.internet import defer

# Simple DummyRequest for testing
class DummyRequest:
    def __init__(self, method=b'GET', uri=b'/config/test', args=None, content=b''):
        self.method = method
        self.uri = uri
        self.args = args or {}
        self.content = content
        self.headers = {}
        self.responseCode = 200
    
    def setHeader(self, name, value):
        self.headers[name] = value
    
    def setResponseCode(self, code):
        self.responseCode = code
    
    def write(self, data):
        if not hasattr(self, 'written'):
            self.written = b''
        self.written += data
    
    def finish(self):
        pass

# Mock database manager for testing
class MockDatabaseManager:
    def __init__(self):
        self.configs = {}
        self.history = {}
    
    @defer.inlineCallbacks
    def save_configuration(self, service, payload, version=None):
        if service not in self.configs:
            self.configs[service] = {}
            self.history[service] = []
        
        if version is None:
            version = max(self.configs[service].keys(), default=0) + 1
        
        if version in self.configs[service]:
            raise Exception("duplicate key value violates unique constraint")
        
        self.configs[service][version] = payload
        self.history[service].append({
            "version": version,
            "created_at": "2025-08-19T12:00:00"
        })
        
        defer.returnValue({
            "service": service,
            "version": version,
            "status": "saved"
        })
    
    @defer.inlineCallbacks
    def get_configuration(self, service, version=None):
        if service not in self.configs or not self.configs[service]:
            defer.returnValue(None)
        
        if version is not None:
            config = self.configs[service].get(version)
        else:
            # Get latest version
            latest_version = max(self.configs[service].keys())
            config = self.configs[service][latest_version]
        
        defer.returnValue(config)
    
    @defer.inlineCallbacks
    def get_configuration_history(self, service):
        if service not in self.history:
            defer.returnValue([])
        defer.returnValue(self.history[service])

class TestConfigurationValidation:
    """Test configuration validation"""
    
    def test_valid_yaml_parsing(self):
        from models.configuration import ConfigurationValidator
        
        yaml_content = """
        version: 1
        database:
          host: "db.local"
          port: 5432
        features:
          enable_auth: true
        """
        
        result = ConfigurationValidator.validate_yaml(yaml_content)
        assert result['version'] == 1
        assert result['database']['host'] == 'db.local'
        assert result['database']['port'] == 5432
    
    def test_invalid_yaml_parsing(self):
        from models.configuration import ConfigurationValidator
        
        yaml_content = """
        version: 1
        database:
          host: "db.local"
          port: invalid_port
          invalid_syntax: [
        """
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            ConfigurationValidator.validate_yaml(yaml_content)
    
    def test_configuration_validation(self):
        from models.configuration import ConfigurationValidator
        
        # Valid configuration
        valid_config = {
            "version": 1,
            "database": {
                "host": "db.local",
                "port": 5432
            }
        }
        
        errors = ConfigurationValidator.validate_configuration(valid_config)
        assert len(errors) == 0
        
        # Invalid configuration - missing required fields
        invalid_config = {
            "database": {
                "host": "db.local"
            }
        }
        
        errors = ConfigurationValidator.validate_configuration(invalid_config)
        assert len(errors) == 2  # Missing version and database.port
        assert "Missing required field: version" in errors
        assert "Missing required field: database.port" in errors

class TestConfigurationProcessor:
    """Test configuration template processing"""
    
    def test_template_processing(self):
        from models.configuration import ConfigurationProcessor
        
        config = {
            "version": 2,
            "welcome_message": "Hello {{ user }}!",
            "database": {
                "host": "{{ db_host | default('localhost') }}"
            }
        }
        
        template_vars = {
            "user": "Alice",
            "db_host": "prod.db.local"
        }
        
        result = ConfigurationProcessor.process_template(config, template_vars)
        assert result['welcome_message'] == "Hello Alice!"
        assert result['database']['host'] == "prod.db.local"
    
    def test_template_processing_with_defaults(self):
        from models.configuration import ConfigurationProcessor
        
        config = {
            "version": 1,
            "message": "Hello {{ user | default('World') }}!"
        }
        
        result = ConfigurationProcessor.process_template(config, {})
        assert result['message'] == "Hello World!"

class TestAPIHandlers:
    """Test API request handlers"""
    
    @pytest.mark.twisted
    @defer.inlineCallbacks
    def test_post_configuration(self):
        from api.handlers import ConfigurationHandler
        
        db_manager = MockDatabaseManager()
        handler = ConfigurationHandler(db_manager)
        
        # Create mock request
        class MockRequest:
            def __init__(self, content):
                self.content = MockContent(content)
        
        class MockContent:
            def __init__(self, content):
                self._content = content.encode('utf-8')
            
            def read(self):
                return self._content
        
        yaml_content = """
        version: 1
        database:
          host: "test.local"
          port: 5432
        """
        
        request = MockRequest(yaml_content)
        result = yield handler.handle_post_config(request, "test_service")
        
        assert result['service'] == "test_service"
        assert result['version'] == 1
        assert result['status'] == "saved"
    
    @pytest.mark.twisted
    @defer.inlineCallbacks
    def test_get_configuration(self):
        from api.handlers import ConfigurationHandler
        
        db_manager = MockDatabaseManager()
        handler = ConfigurationHandler(db_manager)
        
        # First save a configuration
        yield db_manager.save_configuration("test_service", {
            "version": 1,
            "database": {"host": "test.local", "port": 5432}
        })
        
        # Create mock request
        class MockRequest:
            def __init__(self):
                self.args = {}
        
        request = MockRequest()
        result = yield handler.handle_get_config(request, "test_service")
        
        assert result['version'] == 1
        assert result['database']['host'] == "test.local"
    
    @pytest.mark.twisted
    @defer.inlineCallbacks
    def test_get_configuration_not_found(self):
        from api.handlers import ConfigurationHandler
        
        db_manager = MockDatabaseManager()
        handler = ConfigurationHandler(db_manager)
        
        class MockRequest:
            def __init__(self):
                self.args = {}
        
        request = MockRequest()
        result = yield handler.handle_get_config(request, "nonexistent_service")
        
        assert result['error'] == "Not Found"
        assert result['status_code'] == 404