"""
Configuration models and validation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import yaml
import json
from jinja2 import Template, Environment, BaseLoader

@dataclass
class ConfigurationModel:
    """Configuration model"""
    service: str
    version: int
    payload: Dict[str, Any]
    created_at: Optional[str] = None

class ConfigurationValidator:
    """Validates configuration data"""
    
    REQUIRED_FIELDS = ['version']
    REQUIRED_DATABASE_FIELDS = ['database.host', 'database.port']
    
    @staticmethod
    def validate_yaml(yaml_content: str) -> Dict[str, Any]:
        """Validate and parse YAML content"""
        try:
            data = yaml.safe_load(yaml_content)
            if data is None:
                raise ValueError("Empty YAML content")
            return data
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {str(e)}")
    
    @staticmethod
    def validate_configuration(data: Dict[str, Any]) -> List[str]:
        """Validate configuration data and return list of errors"""
        errors = []
        
        # Check required fields
        for field in ConfigurationValidator.REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check nested database fields
        for field in ConfigurationValidator.REQUIRED_DATABASE_FIELDS:
            keys = field.split('.')
            current = data
            try:
                for key in keys:
                    if not isinstance(current, dict) or key not in current:
                        errors.append(f"Missing required field: {field}")
                        break
                    current = current[key]
            except (TypeError, KeyError):
                errors.append(f"Missing required field: {field}")
        
        # Validate version is integer
        if 'version' in data and not isinstance(data['version'], int):
            errors.append("Field 'version' must be an integer")
        
        # Validate database port is integer
        if 'database' in data and 'port' in data['database']:
            if not isinstance(data['database']['port'], int):
                errors.append("Field 'database.port' must be an integer")
        
        return errors

class ConfigurationProcessor:
    """Processes configurations with templating"""
    
    @staticmethod
    def process_template(config: Dict[str, Any], template_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process configuration through Jinja2 template engine"""
        if template_vars is None:
            template_vars = {}
        
        # Convert config to JSON string for template processing
        config_json = json.dumps(config, indent=2)
        
        # Create Jinja2 environment
        env = Environment(loader=BaseLoader())
        template = env.from_string(config_json)
        
        # Render template
        rendered_json = template.render(**template_vars)
        
        # Parse back to dictionary
        try:
            return json.loads(rendered_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Template processing resulted in invalid JSON: {str(e)}")
    
    @staticmethod
    def extract_template_vars(config: Dict[str, Any]) -> List[str]:
        """Extract template variables from configuration"""
        config_str = json.dumps(config)
        env = Environment(loader=BaseLoader())
        
        try:
            ast = env.parse(config_str)
            variables = []
            
            def visit(node):
                if hasattr(node, 'name') and isinstance(node.name, str):
                    variables.append(node.name)
                for child in node.iter_child_nodes():
                    visit(child)
            
            visit(ast)
            return list(set(variables))
        except Exception:
            return []