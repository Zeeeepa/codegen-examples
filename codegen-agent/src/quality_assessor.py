#!/usr/bin/env python
"""
Code Quality Assessment Module

This module provides comprehensive code quality assessment capabilities
for evaluating generated code against various metrics and standards.
"""

import ast
import re
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import Counter, defaultdict
import json


@dataclass
class QualityMetrics:
    """Comprehensive quality metrics for generated code."""
    
    # Overall score (0.0 - 1.0)
    overall_score: float
    
    # Individual metric scores
    readability_score: float
    maintainability_score: float
    correctness_score: float
    performance_score: float
    security_score: float
    documentation_score: float
    testing_score: float
    
    # Detailed analysis
    complexity_metrics: Dict[str, Any]
    style_metrics: Dict[str, Any]
    security_issues: List[str]
    performance_issues: List[str]
    maintainability_issues: List[str]
    
    # Recommendations
    recommendations: List[str]
    critical_issues: List[str]
    
    # Metadata
    analysis_timestamp: float
    code_language: str
    code_length: int


class QualityAssessor:
    """Advanced code quality assessment engine."""
    
    def __init__(self):
        """Initialize the quality assessor."""
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds
        self.thresholds = {
            'complexity_threshold': 10,
            'function_length_threshold': 50,
            'class_length_threshold': 200,
            'parameter_count_threshold': 5,
            'nesting_depth_threshold': 4,
            'documentation_coverage_threshold': 0.8
        }
        
        # Security patterns to detect
        self.security_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*["\'].*%.*["\']',
                r'query\s*\(\s*["\'].*\+.*["\']',
                r'SELECT.*\+.*FROM'
            ],
            'xss_vulnerability': [
                r'innerHTML\s*=.*\+',
                r'document\.write\s*\(.*\+',
                r'eval\s*\('
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']'
            ],
            'unsafe_deserialization': [
                r'pickle\.loads?',
                r'yaml\.load\s*\(',
                r'eval\s*\('
            ]
        }
        
        # Performance anti-patterns
        self.performance_patterns = {
            'inefficient_loops': [
                r'for.*in.*range\(len\(',
                r'while.*len\('
            ],
            'string_concatenation': [
                r'\+\s*=\s*["\']',
                r'["\'].*\+.*["\']'
            ],
            'repeated_calculations': [
                r'for.*in.*:.*\n.*for.*in.*:.*\n.*for.*in.*:'
            ]
        }
    
    def assess_quality(
        self,
        code: str,
        context: Dict[str, Any],
        request: Any = None
    ) -> float:
        """Assess the overall quality of generated code.
        
        Args:
            code: The generated code to assess
            context: Context information about the codebase
            request: Original generation request
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        try:
            # Detect programming language
            language = self._detect_language(code, context)
            
            # Perform comprehensive analysis
            metrics = self._analyze_code_quality(code, language, context)
            
            # Calculate weighted overall score
            weights = {
                'readability': 0.20,
                'maintainability': 0.20,
                'correctness': 0.25,
                'performance': 0.15,
                'security': 0.10,
                'documentation': 0.05,
                'testing': 0.05
            }
            
            overall_score = (
                metrics.readability_score * weights['readability'] +
                metrics.maintainability_score * weights['maintainability'] +
                metrics.correctness_score * weights['correctness'] +
                metrics.performance_score * weights['performance'] +
                metrics.security_score * weights['security'] +
                metrics.documentation_score * weights['documentation'] +
                metrics.testing_score * weights['testing']
            )
            
            self.logger.info(f"Quality assessment complete: {overall_score:.2f}")
            return overall_score
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return 0.0
    
    def get_detailed_metrics(
        self,
        code: str,
        context: Dict[str, Any],
        request: Any = None
    ) -> QualityMetrics:
        """Get detailed quality metrics for the code.
        
        Args:
            code: The generated code to assess
            context: Context information about the codebase
            request: Original generation request
            
        Returns:
            Detailed quality metrics
        """
        import time
        
        language = self._detect_language(code, context)
        
        # Analyze each quality dimension
        readability = self._assess_readability(code, language)
        maintainability = self._assess_maintainability(code, language)
        correctness = self._assess_correctness(code, language)
        performance = self._assess_performance(code, language)
        security = self._assess_security(code, language)
        documentation = self._assess_documentation(code, language)
        testing = self._assess_testing(code, language)
        
        # Calculate overall score
        weights = {
            'readability': 0.20,
            'maintainability': 0.20,
            'correctness': 0.25,
            'performance': 0.15,
            'security': 0.10,
            'documentation': 0.05,
            'testing': 0.05
        }
        
        overall_score = (
            readability['score'] * weights['readability'] +
            maintainability['score'] * weights['maintainability'] +
            correctness['score'] * weights['correctness'] +
            performance['score'] * weights['performance'] +
            security['score'] * weights['security'] +
            documentation['score'] * weights['documentation'] +
            testing['score'] * weights['testing']
        )
        
        # Collect all recommendations and issues
        recommendations = []
        critical_issues = []
        
        for metric in [readability, maintainability, correctness, performance, security, documentation, testing]:
            recommendations.extend(metric.get('recommendations', []))
            critical_issues.extend(metric.get('critical_issues', []))
        
        return QualityMetrics(
            overall_score=overall_score,
            readability_score=readability['score'],
            maintainability_score=maintainability['score'],
            correctness_score=correctness['score'],
            performance_score=performance['score'],
            security_score=security['score'],
            documentation_score=documentation['score'],
            testing_score=testing['score'],
            complexity_metrics=maintainability.get('complexity', {}),
            style_metrics=readability.get('style', {}),
            security_issues=security.get('issues', []),
            performance_issues=performance.get('issues', []),
            maintainability_issues=maintainability.get('issues', []),
            recommendations=recommendations,
            critical_issues=critical_issues,
            analysis_timestamp=time.time(),
            code_language=language,
            code_length=len(code.split('\n'))
        )
    
    def _detect_language(self, code: str, context: Dict[str, Any]) -> str:
        """Detect the programming language of the code."""
        # Check context first
        codebase_context = context.get('codebase', {})
        languages = codebase_context.get('programming_languages', [])
        
        if languages:
            primary_language = languages[0].lower()
        else:
            # Detect from code patterns
            if 'def ' in code and 'import ' in code:
                primary_language = 'python'
            elif 'function ' in code or 'const ' in code or 'let ' in code:
                primary_language = 'javascript'
            elif 'func ' in code and 'package ' in code:
                primary_language = 'go'
            elif 'public class ' in code or 'private ' in code:
                primary_language = 'java'
            else:
                primary_language = 'unknown'
        
        return primary_language
    
    def _analyze_code_quality(self, code: str, language: str, context: Dict[str, Any]) -> QualityMetrics:
        """Perform comprehensive code quality analysis."""
        # This is a simplified version - in practice, you'd use language-specific parsers
        return self.get_detailed_metrics(code, context)
    
    def _assess_readability(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code readability."""
        score = 1.0
        recommendations = []
        style_metrics = {}
        
        lines = code.split('\n')
        
        # Line length analysis
        long_lines = [i for i, line in enumerate(lines) if len(line) > 100]
        if long_lines:
            score -= min(0.2, len(long_lines) * 0.02)
            recommendations.append(f"Consider breaking long lines (found {len(long_lines)} lines > 100 chars)")
        
        style_metrics['avg_line_length'] = sum(len(line) for line in lines) / len(lines) if lines else 0
        style_metrics['max_line_length'] = max(len(line) for line in lines) if lines else 0
        
        # Naming conventions
        if language == 'python':
            # Check for snake_case functions
            function_names = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', code)
            non_snake_case = [name for name in function_names if not re.match(r'^[a-z_][a-z0-9_]*$', name)]
            if non_snake_case:
                score -= min(0.1, len(non_snake_case) * 0.02)
                recommendations.append("Use snake_case for function names in Python")
        
        # Comment density
        comment_lines = len([line for line in lines if line.strip().startswith('#') or line.strip().startswith('//')])
        comment_ratio = comment_lines / len(lines) if lines else 0
        style_metrics['comment_ratio'] = comment_ratio
        
        if comment_ratio < 0.1:
            score -= 0.1
            recommendations.append("Consider adding more comments to explain complex logic")
        
        # Indentation consistency
        indented_lines = [line for line in lines if line.startswith(' ') or line.startswith('\t')]
        if indented_lines:
            space_indented = len([line for line in indented_lines if line.startswith(' ')])
            tab_indented = len([line for line in indented_lines if line.startswith('\t')])
            
            if space_indented > 0 and tab_indented > 0:
                score -= 0.15
                recommendations.append("Use consistent indentation (either spaces or tabs, not both)")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations,
            'style': style_metrics
        }
    
    def _assess_maintainability(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code maintainability."""
        score = 1.0
        recommendations = []
        issues = []
        complexity_metrics = {}
        
        lines = code.split('\n')
        
        # Function length analysis
        if language == 'python':
            functions = self._extract_python_functions(code)
            long_functions = [f for f in functions if f['length'] > self.thresholds['function_length_threshold']]
            
            if long_functions:
                score -= min(0.3, len(long_functions) * 0.1)
                recommendations.append(f"Consider breaking down long functions (found {len(long_functions)} functions > {self.thresholds['function_length_threshold']} lines)")
                issues.extend([f"Function '{f['name']}' is {f['length']} lines long" for f in long_functions])
            
            complexity_metrics['avg_function_length'] = sum(f['length'] for f in functions) / len(functions) if functions else 0
            complexity_metrics['max_function_length'] = max(f['length'] for f in functions) if functions else 0
        
        # Nesting depth analysis
        max_nesting = self._calculate_max_nesting_depth(code)
        complexity_metrics['max_nesting_depth'] = max_nesting
        
        if max_nesting > self.thresholds['nesting_depth_threshold']:
            score -= min(0.2, (max_nesting - self.thresholds['nesting_depth_threshold']) * 0.05)
            recommendations.append(f"Reduce nesting depth (max depth: {max_nesting})")
            issues.append(f"Maximum nesting depth of {max_nesting} exceeds threshold")
        
        # Duplicate code detection (simple)
        duplicate_lines = self._find_duplicate_lines(lines)
        if duplicate_lines:
            score -= min(0.15, len(duplicate_lines) * 0.01)
            recommendations.append("Consider extracting duplicate code into functions")
            issues.extend([f"Duplicate line found: '{line}'" for line in duplicate_lines[:3]])
        
        # Magic numbers detection
        magic_numbers = re.findall(r'\b\d{2,}\b', code)
        if len(magic_numbers) > 3:
            score -= min(0.1, len(magic_numbers) * 0.01)
            recommendations.append("Consider using named constants instead of magic numbers")
        
        complexity_metrics['magic_numbers_count'] = len(magic_numbers)
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations,
            'issues': issues,
            'complexity': complexity_metrics
        }
    
    def _assess_correctness(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code correctness."""
        score = 1.0
        recommendations = []
        critical_issues = []
        
        # Syntax checking
        if language == 'python':
            try:
                ast.parse(code)
            except SyntaxError as e:
                score = 0.0
                critical_issues.append(f"Syntax error: {str(e)}")
                return {
                    'score': score,
                    'recommendations': recommendations,
                    'critical_issues': critical_issues
                }
        
        # Error handling analysis
        if language == 'python':
            try_blocks = len(re.findall(r'\btry\s*:', code))
            except_blocks = len(re.findall(r'\bexcept\s+', code))
            
            if try_blocks != except_blocks:
                score -= 0.2
                recommendations.append("Ensure all try blocks have corresponding except blocks")
        
        # Null/None checking
        if language == 'python':
            # Look for potential None access without checking
            none_access_patterns = [
                r'\.(?!None)\w+\s*\(',  # Method calls without None check
                r'\[\s*\w+\s*\]'       # Index access without None check
            ]
            
            for pattern in none_access_patterns:
                matches = re.findall(pattern, code)
                if matches:
                    score -= min(0.1, len(matches) * 0.02)
                    recommendations.append("Consider adding None checks before accessing object methods/attributes")
        
        # Return statement consistency
        functions = self._extract_python_functions(code) if language == 'python' else []
        for func in functions:
            returns = re.findall(r'\breturn\b', func['body'])
            if len(returns) > 1:
                # Check if all paths return values
                return_statements = re.findall(r'return\s+(.+)', func['body'])
                none_returns = [r for r in return_statements if r.strip() == '']
                
                if none_returns and len(none_returns) != len(return_statements):
                    score -= 0.1
                    recommendations.append(f"Function '{func['name']}' has inconsistent return statements")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations,
            'critical_issues': critical_issues
        }
    
    def _assess_performance(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code performance."""
        score = 1.0
        recommendations = []
        issues = []
        
        # Check for performance anti-patterns
        for pattern_type, patterns in self.performance_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, code, re.IGNORECASE | re.MULTILINE)
                if matches:
                    score -= min(0.2, len(matches) * 0.05)
                    recommendations.append(f"Avoid {pattern_type.replace('_', ' ')}")
                    issues.append(f"Found {pattern_type}: {len(matches)} occurrences")
        
        # Nested loops analysis
        nested_loops = len(re.findall(r'for.*:.*\n.*for.*:', code, re.MULTILINE))
        if nested_loops > 2:
            score -= min(0.15, nested_loops * 0.03)
            recommendations.append("Consider optimizing nested loops")
            issues.append(f"Found {nested_loops} nested loop patterns")
        
        # Large data structure operations
        if language == 'python':
            # Check for inefficient list operations
            list_operations = re.findall(r'\.append\(.*\)', code)
            if len(list_operations) > 10:
                score -= 0.1
                recommendations.append("Consider using list comprehensions or more efficient data structures")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations,
            'issues': issues
        }
    
    def _assess_security(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code security."""
        score = 1.0
        recommendations = []
        issues = []
        critical_issues = []
        
        # Check for security vulnerabilities
        for vulnerability_type, patterns in self.security_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, code, re.IGNORECASE | re.MULTILINE)
                if matches:
                    severity = 0.3 if vulnerability_type in ['sql_injection', 'xss_vulnerability'] else 0.2
                    score -= min(severity, len(matches) * 0.1)
                    
                    issue_msg = f"Potential {vulnerability_type.replace('_', ' ')}: {len(matches)} occurrences"
                    issues.append(issue_msg)
                    
                    if vulnerability_type in ['sql_injection', 'xss_vulnerability']:
                        critical_issues.append(issue_msg)
                    
                    recommendations.append(f"Review and fix potential {vulnerability_type.replace('_', ' ')}")
        
        # Input validation
        if language == 'python':
            # Check for input() usage without validation
            input_usage = re.findall(r'input\s*\(', code)
            if input_usage:
                score -= min(0.1, len(input_usage) * 0.05)
                recommendations.append("Validate user input to prevent security issues")
        
        # File operations security
        file_operations = re.findall(r'open\s*\(.*["\']w["\']', code)
        if file_operations:
            score -= min(0.1, len(file_operations) * 0.03)
            recommendations.append("Ensure file operations are secure and validate file paths")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations,
            'issues': issues,
            'critical_issues': critical_issues
        }
    
    def _assess_documentation(self, code: str, language: str) -> Dict[str, Any]:
        """Assess code documentation."""
        score = 1.0
        recommendations = []
        
        if language == 'python':
            functions = self._extract_python_functions(code)
            documented_functions = [f for f in functions if f.get('docstring')]
            
            if functions:
                doc_coverage = len(documented_functions) / len(functions)
                if doc_coverage < self.thresholds['documentation_coverage_threshold']:
                    score -= (self.thresholds['documentation_coverage_threshold'] - doc_coverage) * 0.5
                    recommendations.append(f"Improve documentation coverage (current: {doc_coverage:.1%})")
            
            # Check for class documentation
            classes = re.findall(r'class\s+\w+.*?:', code)
            if classes:
                class_docs = re.findall(r'class\s+\w+.*?:\s*""".*?"""', code, re.DOTALL)
                if len(class_docs) < len(classes):
                    score -= 0.1
                    recommendations.append("Add docstrings to classes")
        
        # Check for inline comments
        lines = code.split('\n')
        comment_lines = [line for line in lines if '#' in line or '//' in line]
        
        if len(comment_lines) / len(lines) < 0.1:
            score -= 0.1
            recommendations.append("Add more inline comments to explain complex logic")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations
        }
    
    def _assess_testing(self, code: str, language: str) -> Dict[str, Any]:
        """Assess testing aspects of the code."""
        score = 0.5  # Start with neutral score since testing is often separate
        recommendations = []
        
        # Check if test code is included
        test_indicators = ['test_', 'Test', 'assert', 'unittest', 'pytest', 'describe', 'it(']
        test_found = any(indicator in code for indicator in test_indicators)
        
        if test_found:
            score = 1.0
            
            # Analyze test quality
            if language == 'python':
                assertions = len(re.findall(r'assert\s+', code))
                test_functions = len(re.findall(r'def\s+test_\w+', code))
                
                if test_functions > 0:
                    assertions_per_test = assertions / test_functions
                    if assertions_per_test < 1:
                        score -= 0.2
                        recommendations.append("Add more assertions to test functions")
                    elif assertions_per_test > 5:
                        score -= 0.1
                        recommendations.append("Consider breaking down complex test functions")
        else:
            recommendations.append("Consider adding unit tests for the implemented functionality")
        
        return {
            'score': max(0.0, score),
            'recommendations': recommendations
        }
    
    def _extract_python_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract Python function information."""
        functions = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Calculate function length
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    length = end_line - start_line + 1
                    
                    # Extract docstring
                    docstring = ast.get_docstring(node)
                    
                    # Get function body
                    func_lines = code.split('\n')[start_line-1:end_line]
                    body = '\n'.join(func_lines)
                    
                    functions.append({
                        'name': node.name,
                        'length': length,
                        'docstring': docstring,
                        'body': body,
                        'args': len(node.args.args)
                    })
                    
        except SyntaxError:
            # Fallback to regex if AST parsing fails
            function_matches = re.finditer(r'def\s+(\w+)\s*\([^)]*\):', code)
            for match in function_matches:
                name = match.group(1)
                start_pos = match.start()
                
                # Estimate function length (simple heuristic)
                lines_after = code[start_pos:].split('\n')
                length = 1
                indent_level = len(lines_after[0]) - len(lines_after[0].lstrip())
                
                for i, line in enumerate(lines_after[1:], 1):
                    if line.strip() and (len(line) - len(line.lstrip())) <= indent_level:
                        break
                    length = i + 1
                
                functions.append({
                    'name': name,
                    'length': length,
                    'docstring': None,
                    'body': '\n'.join(lines_after[:length]),
                    'args': 0  # Can't easily determine without parsing
                })
        
        return functions
    
    def _calculate_max_nesting_depth(self, code: str) -> int:
        """Calculate maximum nesting depth in the code."""
        lines = code.split('\n')
        max_depth = 0
        current_depth = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Count indentation level
            indent = len(line) - len(line.lstrip())
            
            # Estimate nesting based on keywords
            if any(keyword in stripped for keyword in ['if ', 'for ', 'while ', 'with ', 'try:', 'def ', 'class ']):
                current_depth = indent // 4 + 1  # Assuming 4-space indentation
                max_depth = max(max_depth, current_depth)
        
        return max_depth
    
    def _find_duplicate_lines(self, lines: List[str]) -> List[str]:
        """Find duplicate lines in the code."""
        line_counts = Counter()
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and len(stripped) > 10:
                line_counts[stripped] += 1
        
        return [line for line, count in line_counts.items() if count > 1]

