"""
Intelligent Fix Suggestion Engine

Generates context-aware fix suggestions using Claude's reasoning capabilities,
historical fix patterns, and machine learning-based success prediction.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import difflib
from pathlib import Path

from .claude_client import ClaudeClient


class FixType(Enum):
    """Types of fixes that can be suggested."""
    CODE_CHANGE = "code_change"
    CONFIGURATION_UPDATE = "configuration_update"
    DEPENDENCY_UPDATE = "dependency_update"
    REFACTORING = "refactoring"
    SECURITY_PATCH = "security_patch"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    TEST_ADDITION = "test_addition"
    DOCUMENTATION_UPDATE = "documentation_update"


class FixComplexity(Enum):
    """Complexity levels for fixes."""
    TRIVIAL = "trivial"      # Single line change
    SIMPLE = "simple"        # Few lines, single file
    MODERATE = "moderate"    # Multiple files or complex logic
    COMPLEX = "complex"      # Architectural changes
    MAJOR = "major"          # Breaking changes or major refactoring


@dataclass
class CodeChange:
    """Represents a specific code change."""
    file_path: str
    line_start: int
    line_end: int
    old_code: str
    new_code: str
    description: str
    confidence: float = 1.0


@dataclass
class FixSuggestion:
    """Comprehensive fix suggestion with metadata."""
    id: str = field(default_factory=lambda: hashlib.md5(str(asyncio.get_event_loop().time()).encode()).hexdigest()[:8])
    title: str = ""
    description: str = ""
    fix_type: FixType = FixType.CODE_CHANGE
    complexity: FixComplexity = FixComplexity.SIMPLE
    confidence: float = 1.0
    success_probability: float = 0.8
    estimated_time_minutes: int = 15
    code_changes: List[CodeChange] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    test_suggestions: List[str] = field(default_factory=list)
    rollback_instructions: str = ""
    side_effects: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    validation_steps: List[str] = field(default_factory=list)
    related_issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FixTemplate:
    """Template for common fix patterns."""
    pattern_id: str
    name: str
    description: str
    applicable_errors: List[str]
    template_code: str
    variables: Dict[str, str]
    success_rate: float
    usage_count: int = 0


class FixSuggester:
    """
    Advanced fix suggestion engine with ML-powered success prediction.
    
    Features:
    - Context-aware fix generation using Claude
    - Historical fix pattern learning and reuse
    - Success probability prediction
    - Multi-file change coordination
    - Automated test suggestion generation
    - Rollback and validation planning
    - Side effect analysis and mitigation
    """
    
    def __init__(
        self,
        claude_client: ClaudeClient,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize fix suggester with Claude integration and learning capabilities."""
        self.claude_client = claude_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Fix pattern database
        self.fix_templates = {}
        self.fix_history = []
        self.success_patterns = {}
        
        # Load historical data
        self._load_fix_templates()
        self._load_fix_history()
        
        # Common fix patterns
        self._initialize_common_patterns()
        
        # Success prediction model (simplified)
        self.success_factors = {
            'error_type_match': 0.3,
            'historical_success': 0.25,
            'code_complexity': 0.2,
            'test_coverage': 0.15,
            'claude_confidence': 0.1
        }
    
    async def suggest_fixes(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate comprehensive fix suggestions for validation issues.
        
        Args:
            issues: List of validation issues
            context: Additional context for fix generation
            
        Returns:
            List of fix suggestions with metadata
        """
        if not issues:
            return []
        
        self.logger.info(f"Generating fix suggestions for {len(issues)} issues")
        
        all_fixes = []
        
        try:
            # Group related issues for coordinated fixes
            issue_groups = self._group_related_issues(issues)
            
            for group in issue_groups:
                # Generate fixes for each group
                group_fixes = await self._generate_group_fixes(group, context)
                all_fixes.extend(group_fixes)
            
            # Rank and filter fixes
            ranked_fixes = self._rank_fixes(all_fixes)
            
            # Convert to serializable format
            serializable_fixes = []
            for fix in ranked_fixes:
                serializable_fixes.append({
                    'id': fix.id,
                    'title': fix.title,
                    'description': fix.description,
                    'type': fix.fix_type.value,
                    'complexity': fix.complexity.value,
                    'confidence': fix.confidence,
                    'success_probability': fix.success_probability,
                    'estimated_time_minutes': fix.estimated_time_minutes,
                    'code_changes': [
                        {
                            'file_path': change.file_path,
                            'line_start': change.line_start,
                            'line_end': change.line_end,
                            'old_code': change.old_code,
                            'new_code': change.new_code,
                            'description': change.description,
                            'confidence': change.confidence
                        }
                        for change in fix.code_changes
                    ],
                    'dependencies': fix.dependencies,
                    'test_suggestions': fix.test_suggestions,
                    'rollback_instructions': fix.rollback_instructions,
                    'side_effects': fix.side_effects,
                    'prerequisites': fix.prerequisites,
                    'validation_steps': fix.validation_steps,
                    'related_issues': fix.related_issues,
                    'metadata': fix.metadata
                })
            
            # Learn from generated fixes
            await self._update_fix_patterns(ranked_fixes, issues)
            
            return serializable_fixes
            
        except Exception as e:
            self.logger.error(f"Fix suggestion generation failed: {e}")
            return []
    
    async def _generate_group_fixes(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FixSuggestion]:
        """Generate fixes for a group of related issues."""
        fixes = []
        
        # Try template-based fixes first
        template_fixes = await self._generate_template_fixes(issues)
        fixes.extend(template_fixes)
        
        # Generate Claude-powered custom fixes
        claude_fixes = await self._generate_claude_fixes(issues, context)
        fixes.extend(claude_fixes)
        
        # Generate composite fixes for multiple issues
        if len(issues) > 1:
            composite_fixes = await self._generate_composite_fixes(issues, context)
            fixes.extend(composite_fixes)
        
        return fixes
    
    async def _generate_template_fixes(self, issues: List[Any]) -> List[FixSuggestion]:
        """Generate fixes using pre-defined templates."""
        fixes = []
        
        for issue in issues:
            issue_type = getattr(issue, 'type', '')
            issue_message = getattr(issue, 'message', '')
            
            # Find matching templates
            matching_templates = []
            for template in self.fix_templates.values():
                if any(error_pattern in issue_message.lower() or error_pattern in issue_type.lower() 
                      for error_pattern in template.applicable_errors):
                    matching_templates.append(template)
            
            # Generate fixes from templates
            for template in matching_templates:
                fix = await self._apply_template(template, issue)
                if fix:
                    fixes.append(fix)
        
        return fixes
    
    async def _generate_claude_fixes(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FixSuggestion]:
        """Generate custom fixes using Claude's reasoning."""
        fixes = []
        
        for issue in issues:
            try:
                # Build comprehensive prompt for fix generation
                prompt = self._build_fix_prompt(issue, context)
                
                # Get Claude's fix suggestions
                response = await self.claude_client._make_request(prompt, "fix_suggestion")
                
                # Parse Claude's response
                claude_fixes = self._parse_claude_fix_response(response.content, issue)
                
                # Enhance with metadata
                for fix in claude_fixes:
                    fix.confidence *= response.confidence
                    fix.metadata['claude_response'] = True
                    fix.metadata['claude_confidence'] = response.confidence
                
                fixes.extend(claude_fixes)
                
            except Exception as e:
                self.logger.error(f"Claude fix generation failed for issue {getattr(issue, 'id', 'unknown')}: {e}")
        
        return fixes
    
    async def _generate_composite_fixes(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[FixSuggestion]:
        """Generate composite fixes that address multiple related issues."""
        if len(issues) < 2:
            return []
        
        try:
            # Build prompt for composite fix
            prompt = self._build_composite_fix_prompt(issues, context)
            
            # Get Claude's composite fix suggestions
            response = await self.claude_client._make_request(prompt, "fix_suggestion")
            
            # Parse response
            composite_fixes = self._parse_claude_fix_response(response.content, issues[0])
            
            # Mark as composite fixes
            for fix in composite_fixes:
                fix.title = f"Composite Fix: {fix.title}"
                fix.related_issues = [getattr(issue, 'id', '') for issue in issues]
                fix.complexity = FixComplexity.MODERATE  # Composite fixes are typically more complex
                fix.metadata['composite_fix'] = True
                fix.metadata['addresses_issues'] = len(issues)
            
            return composite_fixes
            
        except Exception as e:
            self.logger.error(f"Composite fix generation failed: {e}")
            return []
    
    def _build_fix_prompt(
        self,
        issue: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build comprehensive prompt for Claude fix generation."""
        issue_message = getattr(issue, 'message', '')
        issue_type = getattr(issue, 'type', '')
        file_path = getattr(issue, 'file_path', '')
        line_number = getattr(issue, 'line_number', '')
        severity = getattr(issue, 'severity', '')
        category = getattr(issue, 'category', '')
        
        prompt = f"""
You are an expert software engineer specializing in bug fixes and code improvements. Generate comprehensive fix suggestions for the following issue.

Issue Details:
- Type: {issue_type}
- Message: {issue_message}
- File: {file_path}
- Line: {line_number}
- Severity: {severity}
- Category: {category}
"""
        
        if context:
            prompt += f"\nProject Context:\n{json.dumps(context, indent=2)}"
        
        # Add historical successful fixes if available
        similar_fixes = self._find_similar_fixes(issue)
        if similar_fixes:
            prompt += f"\nSimilar Successful Fixes:\n{json.dumps(similar_fixes, indent=2)}"
        
        prompt += """

Please provide detailed fix suggestions including:

1. **Primary Fix**: The main solution to address this issue
2. **Alternative Approaches**: Different ways to solve the problem
3. **Code Changes**: Specific code modifications needed
4. **Testing Strategy**: How to test the fix
5. **Potential Side Effects**: What might break or change
6. **Rollback Plan**: How to undo the fix if needed

Format your response as JSON:
{
  "fixes": [
    {
      "title": "Fix title",
      "description": "Detailed description of what this fix does",
      "type": "code_change|configuration_update|dependency_update|refactoring|security_patch|performance_optimization|test_addition|documentation_update",
      "complexity": "trivial|simple|moderate|complex|major",
      "confidence": 0.0-1.0,
      "estimated_time_minutes": number,
      "code_changes": [
        {
          "file_path": "path/to/file",
          "line_start": line_number,
          "line_end": line_number,
          "old_code": "current code",
          "new_code": "fixed code",
          "description": "what this change does"
        }
      ],
      "dependencies": ["dependency1", "dependency2"],
      "test_suggestions": ["test1", "test2"],
      "rollback_instructions": "how to rollback",
      "side_effects": ["effect1", "effect2"],
      "prerequisites": ["prereq1", "prereq2"],
      "validation_steps": ["step1", "step2"]
    }
  ]
}
"""
        return prompt
    
    def _build_composite_fix_prompt(
        self,
        issues: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for generating composite fixes."""
        prompt = """
You are an expert software engineer. Generate a comprehensive fix that addresses multiple related issues simultaneously.

Related Issues:
"""
        
        for i, issue in enumerate(issues, 1):
            prompt += f"""
Issue {i}:
- Type: {getattr(issue, 'type', '')}
- Message: {getattr(issue, 'message', '')}
- File: {getattr(issue, 'file_path', '')}
- Line: {getattr(issue, 'line_number', '')}
- Severity: {getattr(issue, 'severity', '')}
"""
        
        if context:
            prompt += f"\nProject Context:\n{json.dumps(context, indent=2)}"
        
        prompt += """

Generate a single comprehensive fix that addresses all these issues efficiently. Consider:
1. Common root causes
2. Shared code patterns
3. Coordinated changes across files
4. Minimal disruption approach

Use the same JSON format as single fixes, but ensure the fix addresses all listed issues.
"""
        return prompt
    
    def _parse_claude_fix_response(
        self,
        response_content: str,
        issue: Any
    ) -> List[FixSuggestion]:
        """Parse Claude's fix response into FixSuggestion objects."""
        fixes = []
        
        try:
            # Try JSON parsing first
            response_data = json.loads(response_content)
            fix_data_list = response_data.get('fixes', [])
            
            for fix_data in fix_data_list:
                fix = self._create_fix_from_data(fix_data, issue)
                if fix:
                    fixes.append(fix)
                    
        except json.JSONDecodeError:
            # Fallback to text parsing
            fix = self._parse_text_fix_response(response_content, issue)
            if fix:
                fixes.append(fix)
        
        return fixes
    
    def _create_fix_from_data(self, fix_data: Dict[str, Any], issue: Any) -> Optional[FixSuggestion]:
        """Create FixSuggestion from parsed data."""
        try:
            # Parse fix type and complexity
            fix_type = FixType(fix_data.get('type', 'code_change'))
            complexity = FixComplexity(fix_data.get('complexity', 'simple'))
            
            # Create code changes
            code_changes = []
            for change_data in fix_data.get('code_changes', []):
                code_change = CodeChange(
                    file_path=change_data.get('file_path', ''),
                    line_start=change_data.get('line_start', 0),
                    line_end=change_data.get('line_end', 0),
                    old_code=change_data.get('old_code', ''),
                    new_code=change_data.get('new_code', ''),
                    description=change_data.get('description', ''),
                    confidence=change_data.get('confidence', 1.0)
                )
                code_changes.append(code_change)
            
            # Calculate success probability
            success_probability = self._calculate_success_probability(fix_data, issue)
            
            fix = FixSuggestion(
                title=fix_data.get('title', 'Untitled Fix'),
                description=fix_data.get('description', ''),
                fix_type=fix_type,
                complexity=complexity,
                confidence=fix_data.get('confidence', 0.8),
                success_probability=success_probability,
                estimated_time_minutes=fix_data.get('estimated_time_minutes', 15),
                code_changes=code_changes,
                dependencies=fix_data.get('dependencies', []),
                test_suggestions=fix_data.get('test_suggestions', []),
                rollback_instructions=fix_data.get('rollback_instructions', ''),
                side_effects=fix_data.get('side_effects', []),
                prerequisites=fix_data.get('prerequisites', []),
                validation_steps=fix_data.get('validation_steps', []),
                metadata={
                    'source': 'claude',
                    'issue_id': getattr(issue, 'id', ''),
                    'issue_type': getattr(issue, 'type', ''),
                    'generated_at': asyncio.get_event_loop().time()
                }
            )
            
            return fix
            
        except Exception as e:
            self.logger.error(f"Failed to create fix from data: {e}")
            return None
    
    def _parse_text_fix_response(self, response_text: str, issue: Any) -> Optional[FixSuggestion]:
        """Parse text response when JSON parsing fails."""
        # Extract key information using regex
        title_match = re.search(r'title["\s:]+([^\n"]+)', response_text, re.IGNORECASE)
        description_match = re.search(r'description["\s:]+([^\n"]+)', response_text, re.IGNORECASE)
        
        fix = FixSuggestion(
            title=title_match.group(1).strip() if title_match else "Text-based Fix",
            description=description_match.group(1).strip() if description_match else response_text[:200],
            fix_type=FixType.CODE_CHANGE,
            complexity=FixComplexity.SIMPLE,
            confidence=0.6,  # Lower confidence for text parsing
            success_probability=0.7,
            metadata={
                'source': 'claude_text',
                'issue_id': getattr(issue, 'id', ''),
                'raw_response': response_text
            }
        )
        
        return fix
    
    def _calculate_success_probability(self, fix_data: Dict[str, Any], issue: Any) -> float:
        """Calculate success probability based on various factors."""
        base_probability = 0.8
        
        # Adjust based on complexity
        complexity = fix_data.get('complexity', 'simple')
        complexity_factors = {
            'trivial': 1.0,
            'simple': 0.95,
            'moderate': 0.85,
            'complex': 0.7,
            'major': 0.6
        }
        base_probability *= complexity_factors.get(complexity, 0.8)
        
        # Adjust based on confidence
        confidence = fix_data.get('confidence', 0.8)
        base_probability *= confidence
        
        # Adjust based on historical success for similar issues
        issue_type = getattr(issue, 'type', '')
        if issue_type in self.success_patterns:
            historical_success = self.success_patterns[issue_type].get('success_rate', 0.8)
            base_probability = (base_probability + historical_success) / 2
        
        # Adjust based on number of code changes
        num_changes = len(fix_data.get('code_changes', []))
        if num_changes > 5:
            base_probability *= 0.9  # More changes = slightly higher risk
        
        return min(1.0, max(0.1, base_probability))
    
    def _group_related_issues(self, issues: List[Any]) -> List[List[Any]]:
        """Group related issues for coordinated fixes."""
        if len(issues) <= 1:
            return [issues]
        
        # Simple grouping by file path and issue type
        groups = {}
        
        for issue in issues:
            file_path = getattr(issue, 'file_path', 'unknown')
            issue_type = getattr(issue, 'type', 'unknown')
            
            # Create group key
            group_key = f"{file_path}:{issue_type}"
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(issue)
        
        # Split large groups
        final_groups = []
        for group in groups.values():
            if len(group) <= 3:
                final_groups.append(group)
            else:
                # Split large groups into smaller ones
                for i in range(0, len(group), 3):
                    final_groups.append(group[i:i+3])
        
        return final_groups
    
    def _rank_fixes(self, fixes: List[FixSuggestion]) -> List[FixSuggestion]:
        """Rank fixes by effectiveness and feasibility."""
        def fix_score(fix: FixSuggestion) -> float:
            score = 0.0
            
            # Success probability (40% weight)
            score += fix.success_probability * 0.4
            
            # Confidence (30% weight)
            score += fix.confidence * 0.3
            
            # Complexity (20% weight, lower is better)
            complexity_scores = {
                FixComplexity.TRIVIAL: 1.0,
                FixComplexity.SIMPLE: 0.9,
                FixComplexity.MODERATE: 0.7,
                FixComplexity.COMPLEX: 0.5,
                FixComplexity.MAJOR: 0.3
            }
            score += complexity_scores.get(fix.complexity, 0.5) * 0.2
            
            # Time estimate (10% weight, lower is better)
            time_score = max(0.1, 1.0 - (fix.estimated_time_minutes / 120))  # Normalize to 2 hours
            score += time_score * 0.1
            
            return score
        
        # Sort by score (descending)
        ranked_fixes = sorted(fixes, key=fix_score, reverse=True)
        
        # Limit to top 10 fixes
        return ranked_fixes[:10]
    
    def _find_similar_fixes(self, issue: Any) -> List[Dict[str, Any]]:
        """Find similar successful fixes from history."""
        issue_type = getattr(issue, 'type', '')
        issue_message = getattr(issue, 'message', '').lower()
        
        similar_fixes = []
        
        for fix_record in self.fix_history:
            if (fix_record.get('issue_type') == issue_type and 
                fix_record.get('success', False)):
                
                # Check message similarity
                record_message = fix_record.get('issue_message', '').lower()
                if any(word in record_message for word in issue_message.split() if len(word) > 3):
                    similar_fixes.append({
                        'title': fix_record.get('fix_title', ''),
                        'description': fix_record.get('fix_description', ''),
                        'success_rate': fix_record.get('success_rate', 0.8)
                    })
        
        return similar_fixes[:3]  # Return top 3 similar fixes
    
    async def _apply_template(self, template: FixTemplate, issue: Any) -> Optional[FixSuggestion]:
        """Apply a fix template to an issue."""
        try:
            # Extract variables from issue
            variables = self._extract_template_variables(template, issue)
            
            # Apply template
            fix_code = template.template_code
            for var_name, var_value in variables.items():
                fix_code = fix_code.replace(f"{{{var_name}}}", var_value)
            
            # Create fix suggestion
            fix = FixSuggestion(
                title=f"Template Fix: {template.name}",
                description=template.description,
                fix_type=FixType.CODE_CHANGE,
                complexity=FixComplexity.SIMPLE,
                confidence=0.9,
                success_probability=template.success_rate,
                estimated_time_minutes=10,
                code_changes=[
                    CodeChange(
                        file_path=getattr(issue, 'file_path', ''),
                        line_start=getattr(issue, 'line_number', 0),
                        line_end=getattr(issue, 'line_number', 0),
                        old_code="",  # Template doesn't know old code
                        new_code=fix_code,
                        description=f"Applied template: {template.name}"
                    )
                ],
                metadata={
                    'source': 'template',
                    'template_id': template.pattern_id,
                    'template_name': template.name
                }
            )
            
            # Update template usage
            template.usage_count += 1
            
            return fix
            
        except Exception as e:
            self.logger.error(f"Failed to apply template {template.pattern_id}: {e}")
            return None
    
    def _extract_template_variables(self, template: FixTemplate, issue: Any) -> Dict[str, str]:
        """Extract variables needed for template application."""
        variables = {}
        
        # Common variables
        variables['file_path'] = getattr(issue, 'file_path', '')
        variables['line_number'] = str(getattr(issue, 'line_number', 0))
        variables['issue_message'] = getattr(issue, 'message', '')
        
        # Extract specific variables based on template requirements
        for var_name, var_pattern in template.variables.items():
            if var_pattern.startswith('regex:'):
                # Extract using regex
                regex_pattern = var_pattern[6:]  # Remove 'regex:' prefix
                match = re.search(regex_pattern, getattr(issue, 'message', ''))
                if match:
                    variables[var_name] = match.group(1) if match.groups() else match.group(0)
                else:
                    variables[var_name] = 'unknown'
            else:
                # Use default value
                variables[var_name] = var_pattern
        
        return variables
    
    def _initialize_common_patterns(self):
        """Initialize common fix patterns and templates."""
        # Null pointer fix template
        self.fix_templates['null_pointer'] = FixTemplate(
            pattern_id='null_pointer',
            name='Null Pointer Check',
            description='Add null pointer check before accessing object',
            applicable_errors=['nullpointerexception', 'null pointer', 'cannot read property', 'of null'],
            template_code='if ({variable} != null) {\n    // Original code here\n}',
            variables={'variable': 'regex:([a-zA-Z_][a-zA-Z0-9_]*)'},
            success_rate=0.9
        )
        
        # Array bounds check template
        self.fix_templates['array_bounds'] = FixTemplate(
            pattern_id='array_bounds',
            name='Array Bounds Check',
            description='Add array bounds checking',
            applicable_errors=['indexerror', 'arrayindexoutofbounds', 'index out of range'],
            template_code='if ({index} >= 0 && {index} < {array}.length) {\n    // Original code here\n}',
            variables={
                'index': 'regex:index\\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                'array': 'regex:([a-zA-Z_][a-zA-Z0-9_]*)\\[.*\\]'
            },
            success_rate=0.85
        )
        
        # Import fix template
        self.fix_templates['missing_import'] = FixTemplate(
            pattern_id='missing_import',
            name='Add Missing Import',
            description='Add missing import statement',
            applicable_errors=['modulenotfounderror', 'importerror', 'cannot resolve symbol'],
            template_code='import {module_name}',
            variables={'module_name': 'regex:No module named [\'"]([^\'"]+)[\'"]'},
            success_rate=0.95
        )
    
    def _load_fix_templates(self):
        """Load fix templates from storage."""
        # In a real implementation, this would load from a database or file
        pass
    
    def _load_fix_history(self):
        """Load fix history from storage."""
        # In a real implementation, this would load from a database
        pass
    
    async def _update_fix_patterns(self, fixes: List[FixSuggestion], issues: List[Any]):
        """Update fix patterns based on generated fixes."""
        # Record fix generation for learning
        for fix in fixes:
            self.fix_history.append({
                'timestamp': asyncio.get_event_loop().time(),
                'fix_id': fix.id,
                'fix_title': fix.title,
                'fix_type': fix.fix_type.value,
                'complexity': fix.complexity.value,
                'confidence': fix.confidence,
                'success_probability': fix.success_probability,
                'issue_count': len(issues),
                'source': fix.metadata.get('source', 'unknown')
            })
        
        # Update success patterns
        for issue in issues:
            issue_type = getattr(issue, 'type', '')
            if issue_type not in self.success_patterns:
                self.success_patterns[issue_type] = {
                    'total_fixes': 0,
                    'successful_fixes': 0,
                    'success_rate': 0.8
                }
            
            self.success_patterns[issue_type]['total_fixes'] += 1

