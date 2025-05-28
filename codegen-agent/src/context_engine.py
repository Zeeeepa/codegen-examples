#!/usr/bin/env python
"""
Advanced Context Engine for Codegen Agent

This module provides comprehensive context gathering capabilities from multiple sources
including codebase analysis, team preferences, project requirements, and historical patterns.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict, Counter
import logging

from codegen import Codebase
from codegen.shared.enums.programming_language import ProgrammingLanguage


@dataclass
class CodebaseContext:
    """Comprehensive codebase context information."""
    
    # Basic metadata
    repo_name: str
    repo_path: str
    total_files: int
    programming_languages: List[str]
    
    # File structure analysis
    file_extensions: Dict[str, int]
    directory_structure: Dict[str, Any]
    largest_files: List[Tuple[str, int]]
    
    # Code quality metrics
    functions_with_docs: int
    total_functions: int
    avg_params_per_function: float
    complexity_metrics: Dict[str, Any]
    
    # Dependencies and imports
    dependencies: Dict[str, List[str]]
    import_patterns: Dict[str, int]
    
    # Coding patterns and conventions
    naming_conventions: Dict[str, Any]
    code_style_patterns: Dict[str, Any]
    architectural_patterns: List[str]
    
    # Test coverage and quality
    test_files: List[str]
    test_coverage_estimate: float
    
    # Recent changes and hotspots
    recent_changes: List[Dict[str, Any]]
    change_hotspots: List[str]
    
    # Context compression for large codebases
    compressed_summary: str
    context_hash: str
    
    # Timestamp for cache invalidation
    generated_at: float = field(default_factory=time.time)


@dataclass
class TaskContext:
    """Context specific to the current task."""
    
    task_type: str  # feature_generation, bug_fixing, refactoring, etc.
    description: str
    requirements: List[str]
    constraints: List[str]
    target_files: List[str]
    related_issues: List[str]
    priority: str
    estimated_complexity: str


@dataclass
class TeamContext:
    """Team preferences and organizational context."""
    
    coding_standards: Dict[str, Any]
    preferred_patterns: List[str]
    testing_requirements: Dict[str, Any]
    review_guidelines: List[str]
    deployment_constraints: List[str]
    technology_stack: List[str]


class ContextEngine:
    """Advanced context gathering and management engine."""
    
    def __init__(self, cache_dir: str = ".codegen_cache"):
        """Initialize the context engine.
        
        Args:
            cache_dir: Directory for caching context data
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Context providers
        self._codebase_analyzer = CodebaseAnalyzer()
        self._pattern_detector = PatternDetector()
        self._dependency_analyzer = DependencyAnalyzer()
        self._style_analyzer = StyleAnalyzer()
        
    def gather_comprehensive_context(
        self,
        repo_path: str,
        task_context: TaskContext,
        team_context: Optional[TeamContext] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Gather comprehensive context from all available sources.
        
        Args:
            repo_path: Path to the repository
            task_context: Current task information
            team_context: Team preferences and guidelines
            use_cache: Whether to use cached context data
            
        Returns:
            Comprehensive context dictionary
        """
        self.logger.info(f"Gathering context for {repo_path}")
        
        # Generate context hash for caching
        context_hash = self._generate_context_hash(repo_path, task_context)
        cache_file = self.cache_dir / f"context_{context_hash}.json"
        
        # Try to load from cache
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_context = json.load(f)
                    
                # Check if cache is still valid (24 hours)
                if time.time() - cached_context.get('generated_at', 0) < 86400:
                    self.logger.info("Using cached context")
                    return cached_context
            except Exception as e:
                self.logger.warning(f"Failed to load cached context: {e}")
        
        # Gather fresh context
        context = {}
        
        # 1. Codebase analysis
        self.logger.info("Analyzing codebase structure...")
        codebase_context = self._analyze_codebase(repo_path)
        context['codebase'] = codebase_context.__dict__
        
        # 2. Task-specific context
        context['task'] = task_context.__dict__
        
        # 3. Team context
        if team_context:
            context['team'] = team_context.__dict__
        else:
            context['team'] = self._infer_team_context(codebase_context)
        
        # 4. Historical patterns
        self.logger.info("Analyzing historical patterns...")
        context['patterns'] = self._analyze_historical_patterns(repo_path)
        
        # 5. Dependency context
        self.logger.info("Analyzing dependencies...")
        context['dependencies'] = self._analyze_dependencies(repo_path)
        
        # 6. Quality metrics
        self.logger.info("Computing quality metrics...")
        context['quality'] = self._compute_quality_metrics(codebase_context)
        
        # 7. Compression for large contexts
        context['compressed'] = self._compress_context(context)
        
        # Add metadata
        context['generated_at'] = time.time()
        context['context_hash'] = context_hash
        
        # Cache the context
        try:
            with open(cache_file, 'w') as f:
                json.dump(context, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Failed to cache context: {e}")
        
        return context
    
    def _analyze_codebase(self, repo_path: str) -> CodebaseContext:
        """Perform comprehensive codebase analysis."""
        codebase = Codebase(repo_path)
        
        # Basic file analysis
        all_files = codebase.get_files()
        file_extensions = Counter([Path(f.path).suffix for f in all_files])
        
        # Language detection
        languages = self._detect_languages(file_extensions)
        
        # Directory structure
        directory_structure = self._analyze_directory_structure(all_files)
        
        # File size analysis
        file_sizes = [(f.path, len(f.content.splitlines())) for f in all_files]
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        largest_files = file_sizes[:10]
        
        # Function analysis
        functions = []
        for file in all_files:
            if Path(file.path).suffix in ['.py', '.js', '.ts', '.tsx']:
                try:
                    functions.extend(file.get_functions())
                except:
                    continue
        
        # Calculate function metrics
        param_counts = [len(func.parameters) for func in functions]
        avg_params = sum(param_counts) / len(param_counts) if param_counts else 0
        funcs_with_docs = sum(1 for func in functions if func.docstring)
        
        # Dependencies and imports
        dependencies = self._extract_dependencies(all_files)
        import_patterns = self._analyze_import_patterns(all_files)
        
        # Coding patterns
        naming_conventions = self._analyze_naming_conventions(functions)
        code_style_patterns = self._analyze_code_style(all_files)
        architectural_patterns = self._detect_architectural_patterns(directory_structure)
        
        # Test analysis
        test_files = [f.path for f in all_files if self._is_test_file(f.path)]
        test_coverage_estimate = len(test_files) / len(all_files) * 100 if all_files else 0
        
        # Complexity metrics
        complexity_metrics = self._compute_complexity_metrics(functions)
        
        # Generate compressed summary
        compressed_summary = self._generate_compressed_summary(
            len(all_files), languages, largest_files, complexity_metrics
        )
        
        # Generate context hash
        context_hash = hashlib.md5(
            f"{repo_path}_{len(all_files)}_{time.time()//3600}".encode()
        ).hexdigest()
        
        return CodebaseContext(
            repo_name=Path(repo_path).name,
            repo_path=repo_path,
            total_files=len(all_files),
            programming_languages=languages,
            file_extensions=dict(file_extensions),
            directory_structure=directory_structure,
            largest_files=largest_files,
            functions_with_docs=funcs_with_docs,
            total_functions=len(functions),
            avg_params_per_function=avg_params,
            complexity_metrics=complexity_metrics,
            dependencies=dependencies,
            import_patterns=import_patterns,
            naming_conventions=naming_conventions,
            code_style_patterns=code_style_patterns,
            architectural_patterns=architectural_patterns,
            test_files=test_files,
            test_coverage_estimate=test_coverage_estimate,
            recent_changes=[],  # Would require git analysis
            change_hotspots=[],  # Would require git analysis
            compressed_summary=compressed_summary,
            context_hash=context_hash
        )
    
    def _detect_languages(self, file_extensions: Counter) -> List[str]:
        """Detect programming languages from file extensions."""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.jsx': 'JavaScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }
        
        detected = []
        for ext, count in file_extensions.most_common():
            if ext in language_map and count > 0:
                detected.append(language_map[ext])
        
        return detected[:5]  # Top 5 languages
    
    def _analyze_directory_structure(self, files: List[Any]) -> Dict[str, Any]:
        """Analyze directory structure and organization patterns."""
        structure = defaultdict(list)
        
        for file in files:
            parts = Path(file.path).parts
            if len(parts) > 1:
                structure[parts[0]].append('/'.join(parts[1:]))
        
        # Convert to regular dict and analyze patterns
        result = {}
        for dir_name, file_list in structure.items():
            result[dir_name] = {
                'file_count': len(file_list),
                'subdirs': len(set(Path(f).parts[0] for f in file_list if '/' in f)),
                'common_patterns': self._detect_directory_patterns(dir_name, file_list)
            }
        
        return result
    
    def _detect_directory_patterns(self, dir_name: str, files: List[str]) -> List[str]:
        """Detect common directory organization patterns."""
        patterns = []
        
        # Common patterns
        if dir_name in ['src', 'lib', 'app']:
            patterns.append('source_code')
        elif dir_name in ['test', 'tests', '__tests__', 'spec']:
            patterns.append('testing')
        elif dir_name in ['docs', 'documentation']:
            patterns.append('documentation')
        elif dir_name in ['config', 'configs', 'settings']:
            patterns.append('configuration')
        elif dir_name in ['utils', 'helpers', 'common']:
            patterns.append('utilities')
        elif dir_name in ['components', 'widgets']:
            patterns.append('ui_components')
        elif dir_name in ['models', 'entities', 'schemas']:
            patterns.append('data_models')
        elif dir_name in ['services', 'api', 'endpoints']:
            patterns.append('services')
        
        return patterns
    
    def _extract_dependencies(self, files: List[Any]) -> Dict[str, List[str]]:
        """Extract dependency information from files."""
        dependencies = defaultdict(list)
        
        for file in files:
            file_path = file.path
            content = file.content
            
            # Python imports
            if file_path.endswith('.py'):
                deps = self._extract_python_imports(content)
                dependencies['python'].extend(deps)
            
            # JavaScript/TypeScript imports
            elif file_path.endswith(('.js', '.ts', '.tsx', '.jsx')):
                deps = self._extract_js_imports(content)
                dependencies['javascript'].extend(deps)
        
        # Remove duplicates and sort
        for lang in dependencies:
            dependencies[lang] = sorted(list(set(dependencies[lang])))
        
        return dict(dependencies)
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python import statements."""
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                # Extract module name
                if line.startswith('import '):
                    module = line.replace('import ', '').split(' as ')[0].split(',')[0].strip()
                else:  # from ... import ...
                    module = line.split(' import ')[0].replace('from ', '').strip()
                
                if module and not module.startswith('.'):
                    imports.append(module)
        
        return imports
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript import statements."""
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') and ' from ' in line:
                # Extract module name from 'from "module"' or "from 'module'"
                from_part = line.split(' from ')[-1].strip()
                if from_part.startswith('"') or from_part.startswith("'"):
                    module = from_part[1:].split(from_part[0])[0]
                    if module and not module.startswith('.'):
                        imports.append(module)
        
        return imports
    
    def _analyze_import_patterns(self, files: List[Any]) -> Dict[str, int]:
        """Analyze import patterns and frequency."""
        patterns = Counter()
        
        for file in files:
            content = file.content
            
            # Count relative vs absolute imports
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    if ' from .' in line or line.startswith('from .'):
                        patterns['relative_imports'] += 1
                    else:
                        patterns['absolute_imports'] += 1
        
        return dict(patterns)
    
    def _analyze_naming_conventions(self, functions: List[Any]) -> Dict[str, Any]:
        """Analyze naming conventions used in the codebase."""
        conventions = {
            'snake_case': 0,
            'camelCase': 0,
            'PascalCase': 0,
            'kebab-case': 0
        }
        
        for func in functions:
            name = func.name
            if '_' in name and name.islower():
                conventions['snake_case'] += 1
            elif name[0].islower() and any(c.isupper() for c in name[1:]):
                conventions['camelCase'] += 1
            elif name[0].isupper():
                conventions['PascalCase'] += 1
            elif '-' in name:
                conventions['kebab-case'] += 1
        
        # Determine dominant convention
        dominant = max(conventions.items(), key=lambda x: x[1])
        
        return {
            'counts': conventions,
            'dominant_convention': dominant[0],
            'consistency_score': dominant[1] / len(functions) if functions else 0
        }
    
    def _analyze_code_style(self, files: List[Any]) -> Dict[str, Any]:
        """Analyze code style patterns."""
        style_patterns = {
            'indentation': defaultdict(int),
            'quote_style': defaultdict(int),
            'line_length': []
        }
        
        for file in files:
            if not file.path.endswith(('.py', '.js', '.ts', '.tsx', '.jsx')):
                continue
                
            lines = file.content.split('\n')
            
            for line in lines:
                # Analyze indentation
                if line.strip():
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 0:
                        if leading_spaces % 4 == 0:
                            style_patterns['indentation']['4_spaces'] += 1
                        elif leading_spaces % 2 == 0:
                            style_patterns['indentation']['2_spaces'] += 1
                        elif '\t' in line[:leading_spaces]:
                            style_patterns['indentation']['tabs'] += 1
                
                # Analyze quote style
                if '"' in line:
                    style_patterns['quote_style']['double_quotes'] += line.count('"') // 2
                if "'" in line:
                    style_patterns['quote_style']['single_quotes'] += line.count("'") // 2
                
                # Line length
                style_patterns['line_length'].append(len(line))
        
        # Calculate averages and dominant patterns
        avg_line_length = sum(style_patterns['line_length']) / len(style_patterns['line_length']) if style_patterns['line_length'] else 0
        
        return {
            'indentation': dict(style_patterns['indentation']),
            'quote_style': dict(style_patterns['quote_style']),
            'avg_line_length': avg_line_length,
            'max_line_length': max(style_patterns['line_length']) if style_patterns['line_length'] else 0
        }
    
    def _detect_architectural_patterns(self, directory_structure: Dict[str, Any]) -> List[str]:
        """Detect architectural patterns from directory structure."""
        patterns = []
        
        dirs = set(directory_structure.keys())
        
        # MVC pattern
        if {'models', 'views', 'controllers'}.issubset(dirs):
            patterns.append('MVC')
        
        # Clean Architecture
        if {'domain', 'infrastructure', 'application'}.intersection(dirs):
            patterns.append('Clean Architecture')
        
        # Microservices
        if len([d for d in dirs if 'service' in d.lower()]) > 1:
            patterns.append('Microservices')
        
        # Component-based
        if 'components' in dirs:
            patterns.append('Component-based')
        
        # Layered architecture
        if {'api', 'business', 'data'}.intersection(dirs):
            patterns.append('Layered')
        
        return patterns
    
    def _is_test_file(self, file_path: str) -> bool:
        """Determine if a file is a test file."""
        path_lower = file_path.lower()
        return (
            'test' in path_lower or
            'spec' in path_lower or
            file_path.endswith('_test.py') or
            file_path.endswith('.test.js') or
            file_path.endswith('.spec.js')
        )
    
    def _compute_complexity_metrics(self, functions: List[Any]) -> Dict[str, Any]:
        """Compute code complexity metrics."""
        if not functions:
            return {'avg_complexity': 0, 'max_complexity': 0, 'total_functions': 0}
        
        # Simple complexity estimation based on function length and parameters
        complexities = []
        for func in functions:
            # Estimate complexity based on parameters and body length
            param_complexity = len(func.parameters) * 2
            body_complexity = len(func.body.split('\n')) if hasattr(func, 'body') else 10
            total_complexity = param_complexity + body_complexity
            complexities.append(total_complexity)
        
        return {
            'avg_complexity': sum(complexities) / len(complexities),
            'max_complexity': max(complexities),
            'min_complexity': min(complexities),
            'total_functions': len(functions),
            'high_complexity_functions': len([c for c in complexities if c > 50])
        }
    
    def _generate_compressed_summary(
        self,
        total_files: int,
        languages: List[str],
        largest_files: List[Tuple[str, int]],
        complexity_metrics: Dict[str, Any]
    ) -> str:
        """Generate a compressed summary for large codebases."""
        summary = f"""
Codebase Summary:
- {total_files} total files
- Primary languages: {', '.join(languages[:3])}
- Largest files: {', '.join([f[0] for f in largest_files[:3]])}
- Avg complexity: {complexity_metrics.get('avg_complexity', 0):.1f}
- High complexity functions: {complexity_metrics.get('high_complexity_functions', 0)}
        """.strip()
        
        return summary
    
    def _analyze_historical_patterns(self, repo_path: str) -> Dict[str, Any]:
        """Analyze historical patterns from git history (placeholder)."""
        # This would require git analysis - placeholder implementation
        return {
            'recent_commits': [],
            'frequent_contributors': [],
            'change_patterns': {},
            'hotspot_files': []
        }
    
    def _analyze_dependencies(self, repo_path: str) -> Dict[str, Any]:
        """Analyze project dependencies."""
        dependencies = {}
        
        # Check for common dependency files
        dep_files = {
            'requirements.txt': 'python',
            'package.json': 'javascript',
            'Pipfile': 'python',
            'poetry.lock': 'python',
            'yarn.lock': 'javascript',
            'go.mod': 'go',
            'Cargo.toml': 'rust'
        }
        
        for dep_file, lang in dep_files.items():
            file_path = Path(repo_path) / dep_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        dependencies[lang] = self._parse_dependency_file(dep_file, content)
                except Exception as e:
                    self.logger.warning(f"Failed to parse {dep_file}: {e}")
        
        return dependencies
    
    def _parse_dependency_file(self, filename: str, content: str) -> List[str]:
        """Parse dependency file content."""
        deps = []
        
        if filename == 'requirements.txt':
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    dep = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    deps.append(dep)
        
        elif filename == 'package.json':
            try:
                import json
                data = json.loads(content)
                deps.extend(data.get('dependencies', {}).keys())
                deps.extend(data.get('devDependencies', {}).keys())
            except:
                pass
        
        return deps
    
    def _compute_quality_metrics(self, codebase_context: CodebaseContext) -> Dict[str, Any]:
        """Compute overall code quality metrics."""
        return {
            'documentation_coverage': (
                codebase_context.functions_with_docs / codebase_context.total_functions * 100
                if codebase_context.total_functions > 0 else 0
            ),
            'test_coverage_estimate': codebase_context.test_coverage_estimate,
            'complexity_score': codebase_context.complexity_metrics.get('avg_complexity', 0),
            'maintainability_score': self._calculate_maintainability_score(codebase_context)
        }
    
    def _calculate_maintainability_score(self, context: CodebaseContext) -> float:
        """Calculate a maintainability score based on various factors."""
        score = 100.0
        
        # Penalize high complexity
        if context.complexity_metrics.get('avg_complexity', 0) > 30:
            score -= 20
        
        # Reward good documentation
        doc_coverage = context.functions_with_docs / context.total_functions if context.total_functions > 0 else 0
        score += doc_coverage * 20
        
        # Reward test coverage
        score += context.test_coverage_estimate * 0.3
        
        # Penalize inconsistent naming
        naming_consistency = context.naming_conventions.get('consistency_score', 0)
        score += naming_consistency * 10
        
        return max(0, min(100, score))
    
    def _compress_context(self, context: Dict[str, Any]) -> str:
        """Compress context for large codebases to fit in prompt windows."""
        # Extract key information for compression
        codebase = context.get('codebase', {})
        
        compressed = f"""
CODEBASE: {codebase.get('repo_name', 'Unknown')} ({codebase.get('total_files', 0)} files)
LANGUAGES: {', '.join(codebase.get('programming_languages', [])[:3])}
ARCHITECTURE: {', '.join(codebase.get('architectural_patterns', []))}
QUALITY: Doc coverage {context.get('quality', {}).get('documentation_coverage', 0):.1f}%, Test coverage ~{context.get('quality', {}).get('test_coverage_estimate', 0):.1f}%
STYLE: {codebase.get('naming_conventions', {}).get('dominant_convention', 'mixed')} naming, {codebase.get('code_style_patterns', {}).get('avg_line_length', 0):.0f} avg line length
        """.strip()
        
        return compressed
    
    def _infer_team_context(self, codebase_context: CodebaseContext) -> Dict[str, Any]:
        """Infer team context from codebase patterns."""
        return {
            'inferred_coding_standards': {
                'naming_convention': codebase_context.naming_conventions.get('dominant_convention'),
                'indentation': 'inferred_from_codebase',
                'documentation_required': codebase_context.functions_with_docs > codebase_context.total_functions * 0.5
            },
            'inferred_patterns': codebase_context.architectural_patterns,
            'inferred_testing_approach': 'unit_tests' if codebase_context.test_files else 'minimal_testing'
        }
    
    def _generate_context_hash(self, repo_path: str, task_context: TaskContext) -> str:
        """Generate a hash for context caching."""
        hash_input = f"{repo_path}_{task_context.task_type}_{task_context.description}_{int(time.time() // 3600)}"
        return hashlib.md5(hash_input.encode()).hexdigest()


class CodebaseAnalyzer:
    """Specialized codebase analysis component."""
    
    def analyze_file_relationships(self, files: List[Any]) -> Dict[str, List[str]]:
        """Analyze relationships between files."""
        # Implementation for file relationship analysis
        return {}


class PatternDetector:
    """Detects coding patterns and conventions."""
    
    def detect_design_patterns(self, codebase: Codebase) -> List[str]:
        """Detect common design patterns in the codebase."""
        # Implementation for design pattern detection
        return []


class DependencyAnalyzer:
    """Analyzes project dependencies and their relationships."""
    
    def analyze_dependency_graph(self, repo_path: str) -> Dict[str, Any]:
        """Analyze dependency relationships."""
        # Implementation for dependency graph analysis
        return {}


class StyleAnalyzer:
    """Analyzes code style and formatting patterns."""
    
    def analyze_formatting_patterns(self, files: List[Any]) -> Dict[str, Any]:
        """Analyze code formatting patterns."""
        # Implementation for style analysis
        return {}

