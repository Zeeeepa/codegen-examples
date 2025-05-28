"""
ML-Powered Error Analysis and Classification Engine

Provides intelligent error pattern recognition, root cause analysis,
and automated classification using machine learning models and Claude's reasoning.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import hashlib

from .claude_client import ClaudeClient
from .ml.error_classifier import ErrorClassifier


class ErrorCategory(Enum):
    """Error categories for classification."""
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    LOGIC_ERROR = "logic_error"
    SECURITY_VULNERABILITY = "security_vulnerability"
    PERFORMANCE_ISSUE = "performance_issue"
    DEPENDENCY_ERROR = "dependency_error"
    CONFIGURATION_ERROR = "configuration_error"
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    API_ERROR = "api_error"
    UNKNOWN = "unknown"


class ErrorPattern(Enum):
    """Common error patterns."""
    NULL_POINTER = "null_pointer"
    ARRAY_INDEX_OUT_OF_BOUNDS = "array_index_out_of_bounds"
    TYPE_MISMATCH = "type_mismatch"
    UNDEFINED_VARIABLE = "undefined_variable"
    MISSING_IMPORT = "missing_import"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MEMORY_LEAK = "memory_leak"
    RACE_CONDITION = "race_condition"
    SQL_INJECTION = "sql_injection"
    XSS_VULNERABILITY = "xss_vulnerability"
    AUTHENTICATION_BYPASS = "authentication_bypass"
    INFINITE_LOOP = "infinite_loop"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@dataclass
class ErrorAnalysis:
    """Comprehensive error analysis result."""
    error_id: str
    category: ErrorCategory
    pattern: Optional[ErrorPattern]
    confidence: float
    root_cause: str
    impact_assessment: str
    suggested_fixes: List[str]
    similar_errors: List[str] = field(default_factory=list)
    learning_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorCluster:
    """Cluster of similar errors for pattern analysis."""
    cluster_id: str
    errors: List[str]
    pattern: ErrorPattern
    frequency: int
    severity_distribution: Dict[str, int]
    common_fixes: List[str]
    confidence: float


class ErrorAnalyzer:
    """
    Advanced error analysis engine with ML-powered pattern recognition.
    
    Features:
    - Intelligent error categorization and pattern matching
    - ML-based clustering of similar errors
    - Root cause analysis using Claude's reasoning
    - Historical error pattern learning
    - Automated fix suggestion generation
    - Performance impact assessment
    - Security vulnerability detection
    """
    
    def __init__(
        self,
        claude_client: ClaudeClient,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize error analyzer with ML models and Claude integration."""
        self.claude_client = claude_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize ML components
        self.error_classifier = ErrorClassifier(
            model_path=self.config.get("model_path", "./ml-models"),
            config=self.config.get("classifier", {})
        )
        
        # Text analysis components
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2,
            max_df=0.8
        )
        
        # Clustering for error pattern detection
        self.clusterer = DBSCAN(
            eps=0.3,
            min_samples=3,
            metric='cosine'
        )
        
        # Error pattern database
        self.error_patterns = {}
        self.error_history = []
        self.pattern_cache = {}
        
        # Load pre-trained models and patterns
        self._load_error_patterns()
        self._load_historical_data()
        
        # Regex patterns for common errors
        self.error_regexes = {
            ErrorPattern.NULL_POINTER: [
                r"NullPointerException",
                r"null pointer dereference",
                r"Cannot read property .* of null",
                r"TypeError: Cannot read property .* of null"
            ],
            ErrorPattern.ARRAY_INDEX_OUT_OF_BOUNDS: [
                r"IndexError: list index out of range",
                r"ArrayIndexOutOfBoundsException",
                r"Index .* out of bounds"
            ],
            ErrorPattern.TYPE_MISMATCH: [
                r"TypeError: .* is not a function",
                r"TypeError: unsupported operand type",
                r"ClassCastException"
            ],
            ErrorPattern.UNDEFINED_VARIABLE: [
                r"NameError: name .* is not defined",
                r"ReferenceError: .* is not defined",
                r"UnboundLocalError"
            ],
            ErrorPattern.MISSING_IMPORT: [
                r"ModuleNotFoundError: No module named",
                r"ImportError: cannot import name",
                r"Cannot resolve symbol"
            ],
            ErrorPattern.SQL_INJECTION: [
                r"SQL injection",
                r"Possible SQL injection vulnerability",
                r"Unsafe SQL query construction"
            ],
            ErrorPattern.XSS_VULNERABILITY: [
                r"Cross-site scripting",
                r"XSS vulnerability",
                r"Unsafe HTML rendering"
            ]
        }
    
    async def analyze_issues(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Analyze validation issues with ML-powered classification and Claude reasoning.
        
        Args:
            issues: List of validation issues to analyze
            context: Additional context for analysis
            
        Returns:
            Enhanced issues with analysis results
        """
        if not issues:
            return issues
        
        self.logger.info(f"Analyzing {len(issues)} validation issues")
        
        try:
            # Extract error messages and metadata
            error_data = []
            for issue in issues:
                error_data.append({
                    'id': getattr(issue, 'id', ''),
                    'message': getattr(issue, 'message', ''),
                    'type': getattr(issue, 'type', ''),
                    'severity': getattr(issue, 'severity', ''),
                    'file_path': getattr(issue, 'file_path', ''),
                    'category': getattr(issue, 'category', ''),
                    'metadata': getattr(issue, 'metadata', {})
                })
            
            # Perform batch analysis
            analyses = await self._batch_analyze_errors(error_data, context)
            
            # Enhance issues with analysis results
            enhanced_issues = []
            for i, issue in enumerate(issues):
                if i < len(analyses):
                    analysis = analyses[i]
                    
                    # Update issue with analysis results
                    if hasattr(issue, 'metadata'):
                        issue.metadata.update({
                            'error_analysis': {
                                'category': analysis.category.value,
                                'pattern': analysis.pattern.value if analysis.pattern else None,
                                'confidence': analysis.confidence,
                                'root_cause': analysis.root_cause,
                                'impact_assessment': analysis.impact_assessment,
                                'suggested_fixes': analysis.suggested_fixes,
                                'similar_errors': analysis.similar_errors
                            }
                        })
                    
                    # Update confidence score
                    if hasattr(issue, 'confidence'):
                        issue.confidence = min(issue.confidence, analysis.confidence)
                
                enhanced_issues.append(issue)
            
            # Learn from analysis results
            await self._update_learning_data(analyses)
            
            return enhanced_issues
            
        except Exception as e:
            self.logger.error(f"Error analysis failed: {e}")
            return issues
    
    async def _batch_analyze_errors(
        self,
        error_data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> List[ErrorAnalysis]:
        """Perform batch analysis of errors."""
        analyses = []
        
        # Group errors by similarity for efficient processing
        error_groups = await self._group_similar_errors(error_data)
        
        for group in error_groups:
            # Analyze representative error from each group
            representative_error = group[0]
            analysis = await self._analyze_single_error(representative_error, context)
            
            # Apply analysis to all errors in group
            for error in group:
                error_analysis = ErrorAnalysis(
                    error_id=error['id'],
                    category=analysis.category,
                    pattern=analysis.pattern,
                    confidence=analysis.confidence * (0.9 if len(group) > 1 else 1.0),
                    root_cause=analysis.root_cause,
                    impact_assessment=analysis.impact_assessment,
                    suggested_fixes=analysis.suggested_fixes,
                    similar_errors=[e['id'] for e in group if e['id'] != error['id']],
                    learning_data=analysis.learning_data,
                    metadata=analysis.metadata
                )
                analyses.append(error_analysis)
        
        return analyses
    
    async def _analyze_single_error(
        self,
        error_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorAnalysis:
        """Analyze a single error with comprehensive techniques."""
        error_message = error_data.get('message', '')
        error_type = error_data.get('type', '')
        file_path = error_data.get('file_path', '')
        
        # Step 1: Pattern matching
        detected_pattern = self._detect_error_pattern(error_message, error_type)
        
        # Step 2: ML classification
        ml_category, ml_confidence = await self.error_classifier.classify_error(
            error_message, error_type, file_path
        )
        
        # Step 3: Claude-powered analysis
        claude_analysis = await self._claude_error_analysis(error_data, context)
        
        # Step 4: Combine results
        final_category = self._combine_classifications(ml_category, claude_analysis.get('category'))
        final_confidence = min(ml_confidence, claude_analysis.get('confidence', 0.8))
        
        # Step 5: Generate comprehensive analysis
        analysis = ErrorAnalysis(
            error_id=error_data.get('id', ''),
            category=final_category,
            pattern=detected_pattern,
            confidence=final_confidence,
            root_cause=claude_analysis.get('root_cause', 'Unknown root cause'),
            impact_assessment=claude_analysis.get('impact_assessment', 'Impact assessment pending'),
            suggested_fixes=claude_analysis.get('suggested_fixes', []),
            learning_data={
                'ml_category': ml_category.value if ml_category else None,
                'ml_confidence': ml_confidence,
                'pattern_detected': detected_pattern.value if detected_pattern else None,
                'claude_analysis': claude_analysis
            },
            metadata={
                'analysis_timestamp': asyncio.get_event_loop().time(),
                'analyzer_version': '1.0.0'
            }
        )
        
        return analysis
    
    async def _claude_error_analysis(
        self,
        error_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use Claude for deep error analysis and reasoning."""
        try:
            # Build comprehensive prompt for error analysis
            prompt = self._build_error_analysis_prompt(error_data, context)
            
            # Get Claude's analysis
            response = await self.claude_client._make_request(prompt, "error_debugging")
            
            # Parse Claude's response
            try:
                analysis_result = json.loads(response.content)
                return {
                    'category': analysis_result.get('category', 'unknown'),
                    'confidence': analysis_result.get('confidence', 0.8),
                    'root_cause': analysis_result.get('root_cause', ''),
                    'impact_assessment': analysis_result.get('impact_assessment', ''),
                    'suggested_fixes': analysis_result.get('suggested_fixes', []),
                    'reasoning': analysis_result.get('reasoning', ''),
                    'claude_confidence': response.confidence
                }
            except json.JSONDecodeError:
                # Fallback to text parsing
                return self._parse_claude_text_response(response.content)
                
        except Exception as e:
            self.logger.error(f"Claude error analysis failed: {e}")
            return {
                'category': 'unknown',
                'confidence': 0.5,
                'root_cause': 'Analysis failed',
                'impact_assessment': 'Unable to assess impact',
                'suggested_fixes': [],
                'reasoning': f'Analysis error: {str(e)}'
            }
    
    def _build_error_analysis_prompt(
        self,
        error_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build comprehensive prompt for Claude error analysis."""
        prompt = f"""
You are an expert software engineer and debugging specialist. Analyze the following error and provide comprehensive insights.

Error Details:
- Message: {error_data.get('message', 'N/A')}
- Type: {error_data.get('type', 'N/A')}
- File: {error_data.get('file_path', 'N/A')}
- Category: {error_data.get('category', 'N/A')}
- Severity: {error_data.get('severity', 'N/A')}
"""
        
        if context:
            prompt += f"\nAdditional Context:\n{json.dumps(context, indent=2)}"
        
        if error_data.get('metadata'):
            prompt += f"\nMetadata:\n{json.dumps(error_data['metadata'], indent=2)}"
        
        prompt += """

Please provide a comprehensive analysis including:

1. **Error Category Classification**: Choose from:
   - syntax_error
   - runtime_error
   - logic_error
   - security_vulnerability
   - performance_issue
   - dependency_error
   - configuration_error
   - network_error
   - database_error
   - api_error
   - unknown

2. **Root Cause Analysis**: Detailed explanation of what caused this error

3. **Impact Assessment**: How this error affects the system/application

4. **Suggested Fixes**: Specific, actionable steps to resolve the error

5. **Confidence Score**: Your confidence in this analysis (0.0-1.0)

6. **Reasoning**: Your thought process and reasoning

Format your response as JSON:
{
  "category": "error_category",
  "confidence": 0.0-1.0,
  "root_cause": "detailed explanation",
  "impact_assessment": "impact description",
  "suggested_fixes": ["fix1", "fix2", "fix3"],
  "reasoning": "your analysis reasoning",
  "prevention_strategies": ["strategy1", "strategy2"],
  "related_patterns": ["pattern1", "pattern2"]
}
"""
        return prompt
    
    def _parse_claude_text_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's text response when JSON parsing fails."""
        # Extract key information using regex patterns
        result = {
            'category': 'unknown',
            'confidence': 0.7,
            'root_cause': '',
            'impact_assessment': '',
            'suggested_fixes': [],
            'reasoning': response_text
        }
        
        # Extract category
        category_match = re.search(r'category["\s:]+([a-z_]+)', response_text, re.IGNORECASE)
        if category_match:
            result['category'] = category_match.group(1).lower()
        
        # Extract confidence
        confidence_match = re.search(r'confidence["\s:]+([0-9.]+)', response_text, re.IGNORECASE)
        if confidence_match:
            try:
                result['confidence'] = float(confidence_match.group(1))
            except ValueError:
                pass
        
        # Extract root cause
        root_cause_match = re.search(r'root[_\s]cause["\s:]+([^"\n]+)', response_text, re.IGNORECASE)
        if root_cause_match:
            result['root_cause'] = root_cause_match.group(1).strip()
        
        # Extract suggested fixes
        fixes_section = re.search(r'suggested[_\s]fixes["\s:]*\[(.*?)\]', response_text, re.IGNORECASE | re.DOTALL)
        if fixes_section:
            fixes_text = fixes_section.group(1)
            fixes = re.findall(r'"([^"]+)"', fixes_text)
            result['suggested_fixes'] = fixes
        
        return result
    
    def _detect_error_pattern(self, error_message: str, error_type: str) -> Optional[ErrorPattern]:
        """Detect error patterns using regex matching."""
        combined_text = f"{error_message} {error_type}".lower()
        
        for pattern, regexes in self.error_regexes.items():
            for regex in regexes:
                if re.search(regex, combined_text, re.IGNORECASE):
                    return pattern
        
        return None
    
    def _combine_classifications(
        self,
        ml_category: Optional[ErrorCategory],
        claude_category: str
    ) -> ErrorCategory:
        """Combine ML and Claude classifications."""
        # Map Claude's string category to ErrorCategory enum
        try:
            claude_enum = ErrorCategory(claude_category.lower())
        except ValueError:
            claude_enum = ErrorCategory.UNKNOWN
        
        # If both agree, use that
        if ml_category == claude_enum:
            return ml_category
        
        # If ML is confident and Claude is unknown, use ML
        if claude_enum == ErrorCategory.UNKNOWN and ml_category:
            return ml_category
        
        # If Claude is confident and ML is unknown, use Claude
        if ml_category == ErrorCategory.UNKNOWN and claude_enum != ErrorCategory.UNKNOWN:
            return claude_enum
        
        # Default to Claude's classification (more reasoning-based)
        return claude_enum if claude_enum != ErrorCategory.UNKNOWN else (ml_category or ErrorCategory.UNKNOWN)
    
    async def _group_similar_errors(
        self,
        error_data: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group similar errors for efficient batch processing."""
        if len(error_data) <= 1:
            return [error_data]
        
        try:
            # Extract text features
            error_texts = [
                f"{error.get('message', '')} {error.get('type', '')} {error.get('category', '')}"
                for error in error_data
            ]
            
            # Vectorize error texts
            if not hasattr(self, '_fitted_vectorizer'):
                # Fit vectorizer on current data
                text_vectors = self.vectorizer.fit_transform(error_texts)
                self._fitted_vectorizer = True
            else:
                text_vectors = self.vectorizer.transform(error_texts)
            
            # Cluster similar errors
            if text_vectors.shape[0] > 2:
                clusters = self.clusterer.fit_predict(text_vectors.toarray())
            else:
                clusters = [0] * len(error_data)
            
            # Group errors by cluster
            cluster_groups = {}
            for i, cluster_id in enumerate(clusters):
                if cluster_id not in cluster_groups:
                    cluster_groups[cluster_id] = []
                cluster_groups[cluster_id].append(error_data[i])
            
            return list(cluster_groups.values())
            
        except Exception as e:
            self.logger.error(f"Error grouping failed: {e}")
            # Fallback: each error in its own group
            return [[error] for error in error_data]
    
    async def _update_learning_data(self, analyses: List[ErrorAnalysis]):
        """Update learning data with new analysis results."""
        for analysis in analyses:
            # Add to error history
            self.error_history.append({
                'timestamp': asyncio.get_event_loop().time(),
                'category': analysis.category.value,
                'pattern': analysis.pattern.value if analysis.pattern else None,
                'confidence': analysis.confidence,
                'root_cause_hash': hashlib.md5(analysis.root_cause.encode()).hexdigest()
            })
            
            # Update pattern frequency
            if analysis.pattern:
                pattern_key = analysis.pattern.value
                if pattern_key not in self.error_patterns:
                    self.error_patterns[pattern_key] = {
                        'frequency': 0,
                        'categories': {},
                        'common_fixes': []
                    }
                
                self.error_patterns[pattern_key]['frequency'] += 1
                
                category_key = analysis.category.value
                if category_key not in self.error_patterns[pattern_key]['categories']:
                    self.error_patterns[pattern_key]['categories'][category_key] = 0
                self.error_patterns[pattern_key]['categories'][category_key] += 1
        
        # Periodically save learning data
        if len(self.error_history) % 100 == 0:
            await self._save_learning_data()
    
    def _load_error_patterns(self):
        """Load pre-trained error patterns and models."""
        try:
            # Load from file if exists
            with open(self.config.get('patterns_file', 'error_patterns.pkl'), 'rb') as f:
                self.error_patterns = pickle.load(f)
        except FileNotFoundError:
            self.logger.info("No existing error patterns found, starting fresh")
            self.error_patterns = {}
        except Exception as e:
            self.logger.error(f"Failed to load error patterns: {e}")
            self.error_patterns = {}
    
    def _load_historical_data(self):
        """Load historical error analysis data."""
        try:
            with open(self.config.get('history_file', 'error_history.pkl'), 'rb') as f:
                self.error_history = pickle.load(f)
        except FileNotFoundError:
            self.logger.info("No historical data found, starting fresh")
            self.error_history = []
        except Exception as e:
            self.logger.error(f"Failed to load historical data: {e}")
            self.error_history = []
    
    async def _save_learning_data(self):
        """Save learning data to persistent storage."""
        try:
            # Save error patterns
            with open(self.config.get('patterns_file', 'error_patterns.pkl'), 'wb') as f:
                pickle.dump(self.error_patterns, f)
            
            # Save error history (keep only recent entries)
            recent_history = self.error_history[-10000:]  # Keep last 10k entries
            with open(self.config.get('history_file', 'error_history.pkl'), 'wb') as f:
                pickle.dump(recent_history, f)
            
            self.logger.info("Learning data saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save learning data: {e}")
    
    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error analysis statistics."""
        if not self.error_history:
            return {}
        
        # Calculate statistics
        total_errors = len(self.error_history)
        category_counts = {}
        pattern_counts = {}
        confidence_scores = []
        
        for entry in self.error_history:
            # Category distribution
            category = entry.get('category', 'unknown')
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Pattern distribution
            pattern = entry.get('pattern')
            if pattern:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            # Confidence scores
            confidence = entry.get('confidence', 0)
            confidence_scores.append(confidence)
        
        # Calculate averages and trends
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
        
        return {
            'total_errors_analyzed': total_errors,
            'category_distribution': category_counts,
            'pattern_distribution': pattern_counts,
            'average_confidence': avg_confidence,
            'most_common_category': max(category_counts, key=category_counts.get) if category_counts else None,
            'most_common_pattern': max(pattern_counts, key=pattern_counts.get) if pattern_counts else None,
            'analysis_accuracy': avg_confidence,
            'learning_data_size': len(self.error_patterns)
        }

