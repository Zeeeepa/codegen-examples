#!/usr/bin/env python
"""
Bug Fixing Prompt Templates

This module contains specialized prompt templates for bug fixing
with systematic debugging approaches and root cause analysis.
"""

from typing import Dict, Any, List, Optional


class BugFixingPrompts:
    """Prompt templates for bug fixing tasks."""
    
    @staticmethod
    def get_base_template() -> str:
        """Get the base template for bug fixing."""
        return """
# Bug Fixing Task

## Bug Analysis and Resolution

### Problem Description
{bug_description}

### Context Information
{context_section}

## Systematic Debugging Approach

### Phase 1: Problem Analysis
1. **Reproduce the Issue**
   - Understand the exact conditions that trigger the bug
   - Identify the expected vs actual behavior
   - Document the steps to reproduce consistently
   - Gather relevant logs and error messages

2. **Root Cause Investigation**
   - Analyze the code path leading to the issue
   - Identify potential causes and contributing factors
   - Review recent changes that might have introduced the bug
   - Check for similar issues in the codebase

3. **Impact Assessment**
   - Determine the scope and severity of the bug
   - Identify affected users and systems
   - Assess potential data integrity issues
   - Evaluate security implications

### Phase 2: Solution Design
1. **Fix Strategy**
   - Design a minimal, targeted fix
   - Consider multiple solution approaches
   - Evaluate trade-offs and side effects
   - Plan for backward compatibility

2. **Prevention Measures**
   - Identify why the bug wasn't caught earlier
   - Design tests to prevent regression
   - Consider process improvements
   - Update validation and error handling

### Phase 3: Implementation
1. **Code Changes**
   - Implement the minimal necessary fix
   - Follow established coding standards
   - Add comprehensive error handling
   - Include detailed comments explaining the fix

2. **Testing Strategy**
   - Write specific tests for the bug scenario
   - Test edge cases and boundary conditions
   - Verify the fix doesn't break existing functionality
   - Perform regression testing

### Phase 4: Validation
1. **Verification**
   - Confirm the bug is resolved
   - Test in multiple environments
   - Validate with original reporter if possible
   - Monitor for any new issues

2. **Documentation**
   - Document the root cause and fix
   - Update relevant documentation
   - Add to knowledge base for future reference
   - Communicate fix to stakeholders

## Code Quality Standards
- Maintain existing code style and patterns
- Follow {naming_convention} naming conventions
- Ensure fix doesn't reduce test coverage
- Add appropriate logging and monitoring

## Success Criteria
- Bug is completely resolved
- No regression in existing functionality
- Comprehensive test coverage for the fix
- Clear documentation of the solution
- Prevention measures are in place

{additional_instructions}
        """.strip()
    
    @staticmethod
    def get_performance_bug_template() -> str:
        """Template for performance-related bugs."""
        return """
# Performance Bug Analysis

## Performance Investigation
- Profile the application to identify bottlenecks
- Measure current performance metrics
- Identify resource usage patterns
- Analyze database query performance

## Optimization Strategy
- Target the most impactful performance issues
- Consider caching strategies
- Optimize database queries and indexes
- Review algorithm efficiency

## Validation Approach
- Establish performance benchmarks
- Measure improvement after fixes
- Test under realistic load conditions
- Monitor long-term performance trends

## Monitoring Implementation
- Add performance metrics and alerts
- Implement logging for slow operations
- Set up automated performance testing
- Create dashboards for ongoing monitoring
        """.strip()
    
    @staticmethod
    def get_security_bug_template() -> str:
        """Template for security-related bugs."""
        return """
# Security Bug Resolution

## Security Analysis
- Assess the security vulnerability thoroughly
- Determine potential attack vectors
- Evaluate data exposure risks
- Check for similar vulnerabilities

## Immediate Actions
- Implement temporary mitigations if needed
- Assess if incident response is required
- Document the security issue properly
- Notify relevant security stakeholders

## Fix Implementation
- Apply security best practices
- Use secure coding patterns
- Implement proper input validation
- Add security testing and verification

## Prevention Measures
- Review security testing processes
- Update security guidelines
- Implement additional security controls
- Schedule security code reviews
        """.strip()
    
    @staticmethod
    def get_data_corruption_template() -> str:
        """Template for data corruption bugs."""
        return """
# Data Corruption Bug Resolution

## Data Assessment
- Identify the scope of data corruption
- Determine the root cause of corruption
- Assess data recovery possibilities
- Evaluate impact on system integrity

## Recovery Strategy
- Plan data recovery approach
- Implement data validation checks
- Create backup and rollback procedures
- Test recovery processes thoroughly

## Prevention Implementation
- Add data integrity checks
- Implement transaction safeguards
- Create data validation pipelines
- Set up monitoring for data quality

## Validation and Testing
- Verify data integrity after fixes
- Test with realistic data volumes
- Validate backup and recovery procedures
- Monitor for ongoing data quality issues
        """.strip()
    
    @staticmethod
    def generate_bug_fixing_prompt(
        bug_description: str,
        bug_type: str,
        context: Dict[str, Any],
        error_logs: Optional[List[str]] = None,
        reproduction_steps: Optional[List[str]] = None
    ) -> str:
        """Generate a context-aware prompt for bug fixing.
        
        Args:
            bug_description: Description of the bug
            bug_type: Type of bug (performance, security, data, logic, etc.)
            context: Codebase and project context
            error_logs: Optional error logs related to the bug
            reproduction_steps: Optional steps to reproduce the bug
            
        Returns:
            Complete prompt for bug fixing
        """
        # Get base template
        base_template = BugFixingPrompts.get_base_template()
        
        # Get bug-specific template
        bug_templates = {
            'performance': BugFixingPrompts.get_performance_bug_template(),
            'security': BugFixingPrompts.get_security_bug_template(),
            'data': BugFixingPrompts.get_data_corruption_template()
        }
        
        bug_template = bug_templates.get(bug_type, "")
        
        # Extract context information
        codebase_context = context.get('codebase', {})
        quality_context = context.get('quality', {})
        
        # Build context section
        context_section = f"""
### Codebase Information
- Repository: {codebase_context.get('repo_name', 'Unknown')}
- Primary Languages: {', '.join(codebase_context.get('programming_languages', [])[:3])}
- Architecture: {', '.join(codebase_context.get('architectural_patterns', ['Standard']))}
- Code Quality Score: {quality_context.get('maintainability_score', 0):.1f}/100

### Bug Classification
- **Type**: {bug_type.title()} Bug
- **Severity**: {context.get('severity', 'Medium')}
- **Priority**: {context.get('priority', 'Medium')}
        """.strip()
        
        # Add error logs if provided
        if error_logs:
            context_section += "\n\n### Error Logs\n```\n"
            context_section += "\n".join(error_logs[:5])  # Limit to 5 most recent logs
            context_section += "\n```"
        
        # Add reproduction steps if provided
        if reproduction_steps:
            context_section += "\n\n### Reproduction Steps\n"
            context_section += "\n".join(f"{i+1}. {step}" for i, step in enumerate(reproduction_steps))
        
        # Fill template variables
        template_vars = {
            'bug_description': bug_description,
            'context_section': context_section,
            'naming_convention': codebase_context.get('naming_conventions', {}).get('dominant_convention', 'consistent'),
            'additional_instructions': bug_template
        }
        
        return base_template.format(**template_vars)
    
    @staticmethod
    def get_regression_bug_prompt(
        original_functionality: str,
        breaking_change: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for regression bug fixes.
        
        Args:
            original_functionality: Description of original working functionality
            breaking_change: Description of what broke the functionality
            context: Codebase and project context
            
        Returns:
            Prompt for regression bug fixing
        """
        return f"""
# Regression Bug Fix

## Regression Analysis

### Original Functionality
{original_functionality}

### Breaking Change
{breaking_change}

## Investigation Approach

### Change Analysis
1. **Identify the Breaking Change**
   - Review recent commits and changes
   - Identify the specific change that caused the regression
   - Understand the intent of the original change
   - Assess why the regression wasn't caught

2. **Impact Assessment**
   - Determine all affected functionality
   - Identify dependent systems and components
   - Assess user impact and business consequences
   - Evaluate data integrity implications

### Root Cause Analysis
1. **Code Path Investigation**
   - Trace the execution path of the broken functionality
   - Identify where the new change intersects with existing code
   - Find the specific point of failure
   - Understand the interaction between old and new code

2. **Test Coverage Analysis**
   - Review existing test coverage for the affected area
   - Identify gaps in test coverage that allowed the regression
   - Assess why existing tests didn't catch the issue
   - Plan improvements to prevent future regressions

## Fix Strategy

### Immediate Resolution
- Restore the original functionality
- Ensure the new feature still works as intended
- Find a solution that satisfies both requirements
- Implement with minimal risk and maximum compatibility

### Long-term Prevention
- Add comprehensive regression tests
- Improve test coverage for the affected area
- Implement better integration testing
- Consider architectural improvements

## Implementation Guidelines

### Code Changes
- Make minimal changes to fix the regression
- Preserve the intent of recent changes where possible
- Add clear comments explaining the fix
- Follow established patterns and conventions

### Testing Requirements
- Write specific tests for the regression scenario
- Add tests for the interaction between old and new functionality
- Ensure comprehensive coverage of edge cases
- Validate both original and new functionality work correctly

### Validation Process
- Test the fix thoroughly in multiple environments
- Verify no new regressions are introduced
- Validate with original stakeholders
- Monitor for any additional issues

## Success Criteria
- Original functionality is fully restored
- New functionality continues to work as designed
- Comprehensive test coverage prevents future regressions
- Clear documentation of the fix and prevention measures
        """.strip()
    
    @staticmethod
    def get_intermittent_bug_prompt(
        bug_description: str,
        occurrence_pattern: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for intermittent/hard-to-reproduce bugs.
        
        Args:
            bug_description: Description of the intermittent bug
            occurrence_pattern: Pattern of when the bug occurs
            context: Codebase and project context
            
        Returns:
            Prompt for intermittent bug fixing
        """
        return f"""
# Intermittent Bug Investigation and Fix

## Bug Overview
{bug_description}

## Occurrence Pattern
{occurrence_pattern}

## Investigation Strategy for Intermittent Issues

### Pattern Analysis
1. **Data Collection**
   - Gather all available logs and error reports
   - Identify common factors in bug occurrences
   - Look for timing patterns and correlations
   - Collect system metrics during bug occurrences

2. **Environment Analysis**
   - Compare environments where bug occurs vs doesn't occur
   - Analyze load conditions and resource usage
   - Check for race conditions and timing issues
   - Investigate external dependencies and their states

### Systematic Debugging
1. **Hypothesis Formation**
   - Develop theories about potential causes
   - Consider race conditions and concurrency issues
   - Evaluate resource contention scenarios
   - Assess external system dependencies

2. **Controlled Testing**
   - Create reproducible test scenarios
   - Implement stress testing and load simulation
   - Add extensive logging and monitoring
   - Use debugging tools and profilers

### Root Cause Identification
1. **Code Analysis**
   - Review code for potential race conditions
   - Check for improper error handling
   - Analyze resource management and cleanup
   - Look for timing-dependent logic

2. **System Analysis**
   - Monitor system resources during testing
   - Analyze network and database performance
   - Check for memory leaks and resource exhaustion
   - Evaluate caching and state management

## Fix Implementation

### Robust Solution Design
- Address the root cause, not just symptoms
- Implement defensive programming practices
- Add proper error handling and recovery
- Consider fail-safe mechanisms

### Enhanced Monitoring
- Add detailed logging for the problematic code path
- Implement health checks and alerts
- Create dashboards for ongoing monitoring
- Set up automated testing for the scenario

### Validation Approach
- Test under various load conditions
- Run extended stress tests
- Monitor in production with enhanced logging
- Implement gradual rollout with monitoring

## Prevention Measures
- Improve error handling and resilience
- Add comprehensive monitoring and alerting
- Implement better testing for edge cases
- Consider architectural improvements for reliability

## Success Criteria
- Bug occurrence is eliminated or significantly reduced
- Enhanced monitoring provides early warning of issues
- Comprehensive testing covers the problematic scenarios
- System resilience is improved overall
        """.strip()

