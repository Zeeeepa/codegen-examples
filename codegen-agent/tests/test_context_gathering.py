#!/usr/bin/env python
"""
Tests for Context Gathering Engine

This module contains comprehensive tests for the context gathering
capabilities of the Advanced Codegen Agent.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.context_engine import ContextEngine, TaskContext, TeamContext, CodebaseContext


class TestContextEngine:
    """Test cases for the ContextEngine class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple Python project structure
            repo_path = Path(temp_dir)
            
            # Create source files
            src_dir = repo_path / "src"
            src_dir.mkdir()
            
            # Create a simple Python module
            (src_dir / "__init__.py").write_text("")
            (src_dir / "main.py").write_text('''
def main():
    """Main function for the application."""
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
            ''')
            
            (src_dir / "utils.py").write_text('''
"""Utility functions for the application."""

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    """
    return a + b

def validate_input(value: str) -> bool:
    """Validate input string.
    
    Args:
        value: Input string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return value is not None and len(value) > 0
            ''')
            
            # Create test files
            tests_dir = repo_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_utils.py").write_text('''
import pytest
from src.utils import calculate_sum, validate_input

def test_calculate_sum():
    """Test the calculate_sum function."""
    assert calculate_sum(2, 3) == 5
    assert calculate_sum(-1, 1) == 0

def test_validate_input():
    """Test the validate_input function."""
    assert validate_input("test") == True
    assert validate_input("") == False
    assert validate_input(None) == False
            ''')
            
            # Create requirements file
            (repo_path / "requirements.txt").write_text('''
pytest>=7.0.0
black>=22.0.0
mypy>=0.950
            ''')
            
            # Create README
            (repo_path / "README.md").write_text('''
# Test Project

This is a test project for the Advanced Codegen Agent.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from src.main import main
main()
```
            ''')
            
            yield str(repo_path)
    
    @pytest.fixture
    def context_engine(self):
        """Create a ContextEngine instance for testing."""
        with tempfile.TemporaryDirectory() as cache_dir:
            yield ContextEngine(cache_dir)
    
    @pytest.fixture
    def task_context(self):
        """Create a sample TaskContext for testing."""
        return TaskContext(
            task_type="feature_generation",
            description="Add a new calculator feature",
            requirements=["Support basic arithmetic operations", "Include error handling"],
            constraints=["Must be compatible with Python 3.8+"],
            target_files=["src/calculator.py"],
            related_issues=["ISSUE-123"],
            priority="high",
            estimated_complexity="medium"
        )
    
    @pytest.fixture
    def team_context(self):
        """Create a sample TeamContext for testing."""
        return TeamContext(
            coding_standards={"naming_convention": "snake_case", "line_length": 88},
            preferred_patterns=["dependency_injection", "factory_pattern"],
            testing_requirements={"framework": "pytest", "coverage": 80},
            review_guidelines=["Code review required", "Documentation required"],
            deployment_constraints=["Docker compatible", "No external dependencies"],
            technology_stack=["Python", "FastAPI", "PostgreSQL"]
        )
    
    def test_context_engine_initialization(self, context_engine):
        """Test ContextEngine initialization."""
        assert context_engine is not None
        assert context_engine.cache_dir.exists()
        assert hasattr(context_engine, '_codebase_analyzer')
        assert hasattr(context_engine, '_pattern_detector')
        assert hasattr(context_engine, '_dependency_analyzer')
        assert hasattr(context_engine, '_style_analyzer')
    
    def test_gather_comprehensive_context(self, context_engine, temp_repo, task_context):
        """Test comprehensive context gathering."""
        context = context_engine.gather_comprehensive_context(
            repo_path=temp_repo,
            task_context=task_context,
            use_cache=False
        )
        
        # Verify context structure
        assert 'codebase' in context
        assert 'task' in context
        assert 'team' in context
        assert 'patterns' in context
        assert 'dependencies' in context
        assert 'quality' in context
        assert 'compressed' in context
        
        # Verify codebase context
        codebase = context['codebase']
        assert codebase['total_files'] > 0
        assert 'Python' in codebase['programming_languages']
        assert codebase['repo_name'] is not None
        
        # Verify task context
        task = context['task']
        assert task['task_type'] == "feature_generation"
        assert task['description'] == "Add a new calculator feature"
        
        # Verify quality metrics
        quality = context['quality']
        assert 'documentation_coverage' in quality
        assert 'test_coverage_estimate' in quality
        assert 'maintainability_score' in quality
    
    def test_codebase_analysis(self, context_engine, temp_repo):
        """Test codebase analysis functionality."""
        codebase_context = context_engine._analyze_codebase(temp_repo)
        
        assert isinstance(codebase_context, CodebaseContext)
        assert codebase_context.total_files > 0
        assert 'Python' in codebase_context.programming_languages
        assert codebase_context.total_functions > 0
        assert codebase_context.functions_with_docs > 0
        assert len(codebase_context.test_files) > 0
        assert codebase_context.test_coverage_estimate > 0
    
    def test_language_detection(self, context_engine):
        """Test programming language detection."""
        file_extensions = {'.py': 10, '.js': 5, '.ts': 3, '.md': 2}
        languages = context_engine._detect_languages(file_extensions)
        
        assert 'Python' in languages
        assert 'JavaScript' in languages
        assert 'TypeScript' in languages
        assert len(languages) <= 5  # Top 5 languages
    
    def test_directory_structure_analysis(self, context_engine, temp_repo):
        """Test directory structure analysis."""
        # Mock file objects for testing
        mock_files = [
            Mock(path="src/main.py"),
            Mock(path="src/utils.py"),
            Mock(path="tests/test_utils.py"),
            Mock(path="docs/README.md"),
            Mock(path="config/settings.py")
        ]
        
        structure = context_engine._analyze_directory_structure(mock_files)
        
        assert 'src' in structure
        assert 'tests' in structure
        assert 'docs' in structure
        assert 'config' in structure
        
        # Check pattern detection
        assert 'source_code' in structure['src']['common_patterns']
        assert 'testing' in structure['tests']['common_patterns']
        assert 'documentation' in structure['docs']['common_patterns']
        assert 'configuration' in structure['config']['common_patterns']
    
    def test_dependency_extraction(self, context_engine, temp_repo):
        """Test dependency extraction from files."""
        # Create mock files with import statements
        mock_files = [
            Mock(path="test.py", content="import os\nfrom typing import List\nimport requests"),
            Mock(path="test.js", content="import React from 'react'\nimport axios from 'axios'")
        ]
        
        dependencies = context_engine._extract_dependencies(mock_files)
        
        assert 'python' in dependencies
        assert 'javascript' in dependencies
        assert 'os' in dependencies['python']
        assert 'typing' in dependencies['python']
        assert 'requests' in dependencies['python']
        assert 'react' in dependencies['javascript']
        assert 'axios' in dependencies['javascript']
    
    def test_python_import_extraction(self, context_engine):
        """Test Python import statement extraction."""
        content = '''
import os
import sys
from typing import List, Dict
from pathlib import Path
import requests
from .local_module import function
        '''
        
        imports = context_engine._extract_python_imports(content)
        
        assert 'os' in imports
        assert 'sys' in imports
        assert 'typing' in imports
        assert 'pathlib' in imports
        assert 'requests' in imports
        # Local imports should be excluded
        assert '.local_module' not in imports
    
    def test_javascript_import_extraction(self, context_engine):
        """Test JavaScript/TypeScript import statement extraction."""
        content = '''
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import './local-styles.css';
import { helper } from '../utils/helper';
        '''
        
        imports = context_engine._extract_js_imports(content)
        
        assert 'react' in imports
        assert 'axios' in imports
        # Local imports should be excluded
        assert './local-styles.css' not in imports
        assert '../utils/helper' not in imports
    
    def test_naming_convention_analysis(self, context_engine):
        """Test naming convention analysis."""
        # Mock functions with different naming styles
        mock_functions = [
            Mock(name="calculate_sum"),
            Mock(name="validate_input"),
            Mock(name="processData"),
            Mock(name="ProcessData"),
            Mock(name="process-data")
        ]
        
        conventions = context_engine._analyze_naming_conventions(mock_functions)
        
        assert 'snake_case' in conventions['counts']
        assert 'camelCase' in conventions['counts']
        assert 'PascalCase' in conventions['counts']
        assert 'kebab-case' in conventions['counts']
        assert conventions['dominant_convention'] in ['snake_case', 'camelCase', 'PascalCase', 'kebab-case']
        assert 0 <= conventions['consistency_score'] <= 1
    
    def test_code_style_analysis(self, context_engine):
        """Test code style pattern analysis."""
        mock_files = [
            Mock(path="test.py", content='''
def function():
    if True:
        print("Hello")
        print('World')
    return "result"
            ''')
        ]
        
        style = context_engine._analyze_code_style(mock_files)
        
        assert 'indentation' in style
        assert 'quote_style' in style
        assert 'avg_line_length' in style
        assert 'max_line_length' in style
        assert style['avg_line_length'] > 0
        assert style['max_line_length'] > 0
    
    def test_architectural_pattern_detection(self, context_engine):
        """Test architectural pattern detection."""
        # Test MVC pattern
        mvc_structure = {
            'models': {'file_count': 5},
            'views': {'file_count': 3},
            'controllers': {'file_count': 4}
        }
        patterns = context_engine._detect_architectural_patterns(mvc_structure)
        assert 'MVC' in patterns
        
        # Test microservices pattern
        microservices_structure = {
            'user-service': {'file_count': 10},
            'order-service': {'file_count': 8},
            'payment-service': {'file_count': 6}
        }
        patterns = context_engine._detect_architectural_patterns(microservices_structure)
        assert 'Microservices' in patterns
        
        # Test component-based pattern
        component_structure = {
            'components': {'file_count': 15},
            'src': {'file_count': 20}
        }
        patterns = context_engine._detect_architectural_patterns(component_structure)
        assert 'Component-based' in patterns
    
    def test_test_file_detection(self, context_engine):
        """Test test file detection."""
        test_files = [
            "test_utils.py",
            "utils_test.py",
            "test/test_main.py",
            "spec/utils.spec.js",
            "tests/integration.test.js"
        ]
        
        non_test_files = [
            "utils.py",
            "main.js",
            "config.json"
        ]
        
        for file_path in test_files:
            assert context_engine._is_test_file(file_path)
        
        for file_path in non_test_files:
            assert not context_engine._is_test_file(file_path)
    
    def test_context_caching(self, context_engine, temp_repo, task_context):
        """Test context caching functionality."""
        # First call should generate and cache context
        context1 = context_engine.gather_comprehensive_context(
            repo_path=temp_repo,
            task_context=task_context,
            use_cache=True
        )
        
        # Second call should use cached context
        context2 = context_engine.gather_comprehensive_context(
            repo_path=temp_repo,
            task_context=task_context,
            use_cache=True
        )
        
        # Contexts should be identical (from cache)
        assert context1['context_hash'] == context2['context_hash']
        assert context1['generated_at'] == context2['generated_at']
    
    def test_context_compression(self, context_engine, temp_repo, task_context):
        """Test context compression for large codebases."""
        context = context_engine.gather_comprehensive_context(
            repo_path=temp_repo,
            task_context=task_context,
            use_cache=False
        )
        
        compressed = context['compressed']
        assert isinstance(compressed, str)
        assert len(compressed) > 0
        assert 'CODEBASE:' in compressed
        assert 'LANGUAGES:' in compressed
        assert 'QUALITY:' in compressed
    
    def test_team_context_inference(self, context_engine, temp_repo):
        """Test team context inference from codebase."""
        # Create a mock codebase context
        codebase_context = CodebaseContext(
            repo_name="test-repo",
            repo_path=temp_repo,
            total_files=10,
            programming_languages=["Python"],
            file_extensions={".py": 8, ".md": 2},
            directory_structure={},
            largest_files=[],
            functions_with_docs=8,
            total_functions=10,
            avg_params_per_function=2.5,
            complexity_metrics={},
            dependencies={},
            import_patterns={},
            naming_conventions={"dominant_convention": "snake_case", "consistency_score": 0.8},
            code_style_patterns={},
            architectural_patterns=["MVC"],
            test_files=["test_utils.py"],
            test_coverage_estimate=80.0,
            recent_changes=[],
            change_hotspots=[],
            compressed_summary="Test summary",
            context_hash="test-hash"
        )
        
        team_context = context_engine._infer_team_context(codebase_context)
        
        assert 'inferred_coding_standards' in team_context
        assert 'inferred_patterns' in team_context
        assert 'inferred_testing_approach' in team_context
        
        standards = team_context['inferred_coding_standards']
        assert standards['naming_convention'] == "snake_case"
        assert standards['documentation_required'] == True  # 8/10 > 0.5


class TestTaskContext:
    """Test cases for TaskContext data class."""
    
    def test_task_context_creation(self):
        """Test TaskContext creation and attributes."""
        task = TaskContext(
            task_type="feature_generation",
            description="Add new feature",
            requirements=["Requirement 1", "Requirement 2"],
            constraints=["Constraint 1"],
            target_files=["file1.py", "file2.py"],
            related_issues=["ISSUE-123"],
            priority="high",
            estimated_complexity="medium"
        )
        
        assert task.task_type == "feature_generation"
        assert task.description == "Add new feature"
        assert len(task.requirements) == 2
        assert len(task.constraints) == 1
        assert len(task.target_files) == 2
        assert len(task.related_issues) == 1
        assert task.priority == "high"
        assert task.estimated_complexity == "medium"


class TestTeamContext:
    """Test cases for TeamContext data class."""
    
    def test_team_context_creation(self):
        """Test TeamContext creation and attributes."""
        team = TeamContext(
            coding_standards={"style": "black", "line_length": 88},
            preferred_patterns=["factory", "observer"],
            testing_requirements={"framework": "pytest", "coverage": 80},
            review_guidelines=["Review required"],
            deployment_constraints=["Docker"],
            technology_stack=["Python", "FastAPI"]
        )
        
        assert team.coding_standards["style"] == "black"
        assert len(team.preferred_patterns) == 2
        assert team.testing_requirements["framework"] == "pytest"
        assert len(team.review_guidelines) == 1
        assert len(team.deployment_constraints) == 1
        assert len(team.technology_stack) == 2


if __name__ == "__main__":
    pytest.main([__file__])

