#!/usr/bin/env python3
"""
API Documentation Generator

Automatically generates OpenAPI specifications from code annotations
and keeps documentation synchronized with code changes.
"""

import ast
import json
import yaml
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIEndpoint:
    """Represents an API endpoint"""
    path: str
    method: str
    function_name: str
    docstring: str
    parameters: List[Dict]
    responses: Dict[str, Dict]
    tags: List[str]
    summary: str
    description: str

class APIDocGenerator:
    """Generates OpenAPI documentation from Python code"""
    
    def __init__(self, source_dirs: List[str], output_dir: str):
        self.source_dirs = source_dirs
        self.output_dir = Path(output_dir)
        self.endpoints: List[APIEndpoint] = []
        
    def scan_source_files(self) -> List[Path]:
        """Scan source directories for Python files"""
        python_files = []
        for source_dir in self.source_dirs:
            source_path = Path(source_dir)
            if source_path.exists():
                python_files.extend(source_path.rglob("*.py"))
        return python_files
    
    def parse_fastapi_routes(self, file_path: Path) -> List[APIEndpoint]:
        """Parse FastAPI routes from a Python file"""
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for FastAPI decorators
                    for decorator in node.decorator_list:
                        if self._is_fastapi_route_decorator(decorator):
                            endpoint = self._extract_endpoint_info(node, decorator, content)
                            if endpoint:
                                endpoints.append(endpoint)
                                
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            
        return endpoints
    
    def _is_fastapi_route_decorator(self, decorator) -> bool:
        """Check if decorator is a FastAPI route decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']
            elif isinstance(decorator.func, ast.Name):
                return decorator.func.id in ['get', 'post', 'put', 'delete', 'patch']
        return False
    
    def _extract_endpoint_info(self, func_node: ast.FunctionDef, decorator, content: str) -> Optional[APIEndpoint]:
        """Extract endpoint information from function node"""
        try:
            # Get HTTP method
            method = self._get_http_method(decorator)
            
            # Get path
            path = self._get_route_path(decorator)
            
            # Get docstring
            docstring = ast.get_docstring(func_node) or ""
            
            # Parse docstring for additional info
            parsed_doc = self._parse_docstring(docstring)
            
            # Get function parameters
            parameters = self._extract_parameters(func_node)
            
            # Get response information
            responses = self._extract_responses(docstring)
            
            return APIEndpoint(
                path=path,
                method=method.upper(),
                function_name=func_node.name,
                docstring=docstring,
                parameters=parameters,
                responses=responses,
                tags=parsed_doc.get('tags', []),
                summary=parsed_doc.get('summary', ''),
                description=parsed_doc.get('description', '')
            )
            
        except Exception as e:
            logger.error(f"Error extracting endpoint info: {e}")
            return None
    
    def _get_http_method(self, decorator) -> str:
        """Extract HTTP method from decorator"""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr
            elif isinstance(decorator.func, ast.Name):
                return decorator.func.id
        return "get"
    
    def _get_route_path(self, decorator) -> str:
        """Extract route path from decorator"""
        if isinstance(decorator, ast.Call) and decorator.args:
            if isinstance(decorator.args[0], ast.Constant):
                return decorator.args[0].value
            elif isinstance(decorator.args[0], ast.Str):  # Python < 3.8
                return decorator.args[0].s
        return "/"
    
    def _parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse structured docstring"""
        result = {
            'summary': '',
            'description': '',
            'tags': [],
            'parameters': [],
            'responses': {}
        }
        
        if not docstring:
            return result
        
        lines = docstring.strip().split('\n')
        current_section = 'description'
        description_lines = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Summary:'):
                result['summary'] = line[8:].strip()
            elif line.startswith('Tags:'):
                result['tags'] = [tag.strip() for tag in line[5:].split(',')]
            elif line.startswith('Args:') or line.startswith('Parameters:'):
                current_section = 'parameters'
            elif line.startswith('Returns:') or line.startswith('Responses:'):
                current_section = 'responses'
            elif current_section == 'description' and line:
                description_lines.append(line)
        
        if description_lines:
            result['description'] = '\n'.join(description_lines)
            if not result['summary']:
                result['summary'] = description_lines[0]
        
        return result
    
    def _extract_parameters(self, func_node: ast.FunctionDef) -> List[Dict]:
        """Extract function parameters"""
        parameters = []
        
        for arg in func_node.args.args:
            if arg.arg in ['self', 'cls']:
                continue
                
            param = {
                'name': arg.arg,
                'type': 'string',  # Default type
                'required': True,
                'description': ''
            }
            
            # Try to get type annotation
            if arg.annotation:
                param['type'] = self._get_type_from_annotation(arg.annotation)
            
            parameters.append(param)
        
        return parameters
    
    def _get_type_from_annotation(self, annotation) -> str:
        """Convert AST type annotation to OpenAPI type"""
        if isinstance(annotation, ast.Name):
            type_map = {
                'str': 'string',
                'int': 'integer',
                'float': 'number',
                'bool': 'boolean',
                'list': 'array',
                'dict': 'object'
            }
            return type_map.get(annotation.id, 'string')
        elif isinstance(annotation, ast.Constant):
            return 'string'
        else:
            return 'string'
    
    def _extract_responses(self, docstring: str) -> Dict[str, Dict]:
        """Extract response information from docstring"""
        responses = {
            '200': {
                'description': 'Successful response',
                'content': {
                    'application/json': {
                        'schema': {'type': 'object'}
                    }
                }
            }
        }
        
        # Parse docstring for response codes
        if docstring:
            lines = docstring.split('\n')
            for line in lines:
                if re.match(r'^\s*\d{3}:', line):
                    code, desc = line.split(':', 1)
                    code = code.strip()
                    desc = desc.strip()
                    responses[code] = {
                        'description': desc,
                        'content': {
                            'application/json': {
                                'schema': {'type': 'object'}
                            }
                        }
                    }
        
        return responses
    
    def generate_openapi_spec(self, service_name: str, version: str = "1.0.0") -> Dict:
        """Generate complete OpenAPI specification"""
        spec = {
            'openapi': '3.0.3',
            'info': {
                'title': f'{service_name} API',
                'description': f'API documentation for {service_name}',
                'version': version,
                'contact': {
                    'name': 'Codegen Support',
                    'url': 'https://codegen.sh/support',
                    'email': 'support@codegen.sh'
                },
                'license': {
                    'name': 'Apache 2.0',
                    'url': 'https://www.apache.org/licenses/LICENSE-2.0.html'
                }
            },
            'servers': [
                {
                    'url': 'https://api.codegen.sh/v1',
                    'description': 'Production server'
                },
                {
                    'url': 'http://localhost:8001/v1',
                    'description': 'Local development server'
                }
            ],
            'paths': {},
            'components': {
                'securitySchemes': {
                    'BearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT'
                    }
                },
                'schemas': {}
            },
            'security': [{'BearerAuth': []}],
            'tags': []
        }
        
        # Add paths from endpoints
        for endpoint in self.endpoints:
            if endpoint.path not in spec['paths']:
                spec['paths'][endpoint.path] = {}
            
            spec['paths'][endpoint.path][endpoint.method.lower()] = {
                'summary': endpoint.summary or f'{endpoint.method} {endpoint.path}',
                'description': endpoint.description or endpoint.docstring,
                'tags': endpoint.tags or ['default'],
                'parameters': self._format_parameters(endpoint.parameters),
                'responses': endpoint.responses
            }
            
            # Add tags
            for tag in endpoint.tags:
                if tag not in [t['name'] for t in spec['tags']]:
                    spec['tags'].append({
                        'name': tag,
                        'description': f'{tag} operations'
                    })
        
        return spec
    
    def _format_parameters(self, parameters: List[Dict]) -> List[Dict]:
        """Format parameters for OpenAPI spec"""
        formatted = []
        
        for param in parameters:
            formatted.append({
                'name': param['name'],
                'in': 'query',  # Default to query parameter
                'required': param.get('required', False),
                'description': param.get('description', ''),
                'schema': {
                    'type': param.get('type', 'string')
                }
            })
        
        return formatted
    
    def generate_documentation(self):
        """Generate all API documentation"""
        logger.info("Starting API documentation generation...")
        
        # Scan source files
        python_files = self.scan_source_files()
        logger.info(f"Found {len(python_files)} Python files")
        
        # Parse endpoints
        for file_path in python_files:
            endpoints = self.parse_fastapi_routes(file_path)
            self.endpoints.extend(endpoints)
            logger.info(f"Found {len(endpoints)} endpoints in {file_path}")
        
        logger.info(f"Total endpoints found: {len(self.endpoints)}")
        
        # Generate specifications for different services
        services = {
            'task-manager': [e for e in self.endpoints if 'task' in e.path.lower()],
            'webhook-orchestrator': [e for e in self.endpoints if 'webhook' in e.path.lower()],
            'codegen-agent': [e for e in self.endpoints if 'agent' in e.path.lower()]
        }
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        for service_name, service_endpoints in services.items():
            if service_endpoints:
                self.endpoints = service_endpoints  # Temporarily set for generation
                spec = self.generate_openapi_spec(service_name)
                
                # Save as YAML
                yaml_file = self.output_dir / f"{service_name}.yaml"
                with open(yaml_file, 'w') as f:
                    yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
                
                # Save as JSON
                json_file = self.output_dir / f"{service_name}.json"
                with open(json_file, 'w') as f:
                    json.dump(spec, f, indent=2)
                
                logger.info(f"Generated documentation for {service_name}: {yaml_file}")
        
        logger.info("API documentation generation completed!")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate API documentation")
    parser.add_argument('--source-dirs', nargs='+', required=True,
                       help='Source directories to scan')
    parser.add_argument('--output-dir', required=True,
                       help='Output directory for generated docs')
    parser.add_argument('--config', help='Configuration file')
    
    args = parser.parse_args()
    
    generator = APIDocGenerator(args.source_dirs, args.output_dir)
    generator.generate_documentation()

if __name__ == "__main__":
    main()

