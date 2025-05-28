#!/usr/bin/env python
"""
Refactoring Prompt Templates

This module contains specialized prompt templates for code refactoring
with focus on maintainability, performance, and code quality improvements.
"""

from typing import Dict, Any, List, Optional


class RefactoringPrompts:
    """Prompt templates for refactoring tasks."""
    
    @staticmethod
    def get_base_template() -> str:
        """Get the base template for refactoring."""
        return """
# Code Refactoring Task

## Refactoring Objectives
{refactoring_objectives}

### Current Code Analysis
{current_code_analysis}

### Target Improvements
{target_improvements}

## Refactoring Methodology

### Phase 1: Analysis and Planning
1. **Code Assessment**
   - Analyze current code structure and patterns
   - Identify code smells and technical debt
   - Assess complexity and maintainability metrics
   - Review dependencies and coupling

2. **Refactoring Strategy**
   - Define specific refactoring goals
   - Plan incremental refactoring steps
   - Identify potential risks and mitigation strategies
   - Establish success criteria and metrics

3. **Impact Analysis**
   - Assess impact on existing functionality
   - Identify affected tests and documentation
   - Plan for backward compatibility
   - Consider deployment and rollback strategies

### Phase 2: Incremental Refactoring
1. **Preparation**
   - Ensure comprehensive test coverage
   - Create baseline performance metrics
   - Set up monitoring and validation
   - Plan rollback procedures

2. **Systematic Refactoring**
   - Apply refactoring patterns incrementally
   - Maintain functionality throughout the process
   - Run tests after each significant change
   - Monitor for performance regressions

3. **Quality Validation**
   - Verify all tests continue to pass
   - Check performance metrics
   - Validate code quality improvements
   - Ensure no functionality is lost

### Phase 3: Optimization and Cleanup
1. **Code Optimization**
   - Optimize performance where identified
   - Improve error handling and resilience
   - Enhance logging and monitoring
   - Update documentation and comments

2. **Final Validation**
   - Comprehensive testing across all scenarios
   - Performance benchmarking
   - Security review if applicable
   - Stakeholder validation

## Refactoring Principles

### Code Quality Standards
- Follow {naming_convention} naming conventions
- Maintain or improve test coverage above {test_coverage_threshold}%
- Reduce complexity metrics where possible
- Improve code readability and maintainability

### Architectural Guidelines
- Respect existing architectural patterns: {architectural_patterns}
- Maintain clear separation of concerns
- Reduce coupling and increase cohesion
- Follow SOLID principles where applicable

### Performance Considerations
- Maintain or improve current performance
- Optimize critical code paths
- Consider memory usage and efficiency
- Implement appropriate caching strategies

## Success Criteria
- All existing functionality is preserved
- Code quality metrics are improved
- Performance is maintained or enhanced
- Test coverage is maintained or increased
- Documentation is updated and accurate

{additional_instructions}
        """.strip()
    
    @staticmethod
    def get_legacy_code_template() -> str:
        """Template for legacy code refactoring."""
        return """
# Legacy Code Refactoring

## Legacy Code Challenges
- Understand existing functionality without breaking it
- Deal with minimal or outdated documentation
- Work with potentially outdated patterns and practices
- Maintain compatibility with dependent systems

## Modernization Strategy
- Gradually introduce modern patterns and practices
- Improve error handling and resilience
- Add comprehensive test coverage
- Update to current language features and libraries

## Risk Mitigation
- Implement comprehensive testing before changes
- Use feature flags for gradual rollout
- Maintain detailed change logs
- Plan for quick rollback if issues arise

## Documentation Improvement
- Document existing functionality as understood
- Add inline comments for complex logic
- Create architectural documentation
- Update API documentation and examples
        """.strip()
    
    @staticmethod
    def get_performance_refactoring_template() -> str:
        """Template for performance-focused refactoring."""
        return """
# Performance Refactoring

## Performance Analysis
- Profile current performance bottlenecks
- Identify resource-intensive operations
- Analyze algorithm complexity and efficiency
- Measure memory usage and allocation patterns

## Optimization Targets
- Optimize critical code paths
- Improve algorithm efficiency
- Reduce memory allocations
- Implement effective caching strategies

## Benchmarking Requirements
- Establish baseline performance metrics
- Create realistic performance tests
- Measure improvements after changes
- Monitor for performance regressions

## Scalability Considerations
- Design for horizontal and vertical scaling
- Consider load distribution strategies
- Implement efficient data structures
- Plan for future growth and usage patterns
        """.strip()
    
    @staticmethod
    def get_security_refactoring_template() -> str:
        """Template for security-focused refactoring."""
        return """
# Security Refactoring

## Security Assessment
- Identify potential security vulnerabilities
- Review input validation and sanitization
- Assess authentication and authorization
- Evaluate data protection and encryption

## Security Improvements
- Implement secure coding practices
- Add comprehensive input validation
- Improve error handling to prevent information leakage
- Update to secure libraries and dependencies

## Compliance Considerations
- Ensure compliance with relevant standards
- Implement audit logging where required
- Add security monitoring and alerting
- Document security measures and procedures

## Validation and Testing
- Perform security testing and penetration testing
- Validate against security best practices
- Review with security team if available
- Monitor for security issues post-deployment
        """.strip()
    
    @staticmethod
    def generate_refactoring_prompt(
        refactoring_type: str,
        current_code_issues: List[str],
        target_improvements: List[str],
        context: Dict[str, Any],
        constraints: Optional[List[str]] = None
    ) -> str:
        """Generate a context-aware prompt for refactoring.
        
        Args:
            refactoring_type: Type of refactoring (legacy, performance, security, etc.)
            current_code_issues: List of current code issues to address
            target_improvements: List of target improvements
            context: Codebase and project context
            constraints: Optional constraints and limitations
            
        Returns:
            Complete prompt for refactoring
        """
        # Get base template
        base_template = RefactoringPrompts.get_base_template()
        
        # Get refactoring-specific template
        refactoring_templates = {
            'legacy': RefactoringPrompts.get_legacy_code_template(),
            'performance': RefactoringPrompts.get_performance_refactoring_template(),
            'security': RefactoringPrompts.get_security_refactoring_template()
        }
        
        refactoring_template = refactoring_templates.get(refactoring_type, "")
        
        # Extract context information
        codebase_context = context.get('codebase', {})
        quality_context = context.get('quality', {})
        
        # Build refactoring objectives
        refactoring_objectives = f"""
**Primary Goal**: {refactoring_type.title()} Refactoring

**Current Issues to Address**:
{chr(10).join(f"- {issue}" for issue in current_code_issues)}

**Target Improvements**:
{chr(10).join(f"- {improvement}" for improvement in target_improvements)}
        """.strip()
        
        if constraints:
            refactoring_objectives += f"\n\n**Constraints**:\n"
            refactoring_objectives += "\n".join(f"- {constraint}" for constraint in constraints)
        
        # Build current code analysis
        current_code_analysis = f"""
### Codebase Metrics
- Repository: {codebase_context.get('repo_name', 'Unknown')}
- Total Files: {codebase_context.get('total_files', 0)}
- Primary Languages: {', '.join(codebase_context.get('programming_languages', [])[:3])}
- Architecture: {', '.join(codebase_context.get('architectural_patterns', ['Standard']))}

### Quality Metrics
- Maintainability Score: {quality_context.get('maintainability_score', 0):.1f}/100
- Documentation Coverage: {quality_context.get('documentation_coverage', 0):.1f}%
- Test Coverage: ~{quality_context.get('test_coverage_estimate', 0):.1f}%
- Average Complexity: {codebase_context.get('complexity_metrics', {}).get('avg_complexity', 0):.1f}

### Code Patterns
- Naming Convention: {codebase_context.get('naming_conventions', {}).get('dominant_convention', 'mixed')}
- Code Style: {codebase_context.get('code_style_patterns', {}).get('avg_line_length', 80):.0f} avg chars/line
- Dependencies: {len(codebase_context.get('dependencies', {}))} external dependencies
        """.strip()
        
        # Build target improvements section
        improvements_section = "\n".join(f"- {improvement}" for improvement in target_improvements)
        
        # Fill template variables
        template_vars = {
            'refactoring_objectives': refactoring_objectives,
            'current_code_analysis': current_code_analysis,
            'target_improvements': improvements_section,
            'naming_convention': codebase_context.get('naming_conventions', {}).get('dominant_convention', 'consistent'),
            'test_coverage_threshold': int(quality_context.get('test_coverage_estimate', 70)),
            'architectural_patterns': ', '.join(codebase_context.get('architectural_patterns', ['Standard'])),
            'additional_instructions': refactoring_template
        }
        
        return base_template.format(**template_vars)
    
    @staticmethod
    def get_extract_method_prompt(
        large_method: str,
        extraction_candidates: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for extract method refactoring.
        
        Args:
            large_method: Description of the large method to refactor
            extraction_candidates: List of code sections that could be extracted
            context: Codebase and project context
            
        Returns:
            Prompt for extract method refactoring
        """
        return f"""
# Extract Method Refactoring

## Target Method
{large_method}

## Extraction Candidates
{chr(10).join(f"- {candidate}" for candidate in extraction_candidates)}

## Refactoring Guidelines

### Method Extraction Principles
1. **Single Responsibility**
   - Each extracted method should have a single, clear purpose
   - Method names should clearly describe what they do
   - Avoid methods that do multiple unrelated things

2. **Parameter Management**
   - Minimize the number of parameters
   - Use objects to group related parameters
   - Consider return values vs. side effects

3. **Cohesion and Coupling**
   - Keep related functionality together
   - Minimize dependencies between methods
   - Maintain clear interfaces between methods

### Implementation Strategy
1. **Identify Extraction Points**
   - Look for logical code blocks
   - Identify repeated patterns
   - Find code with clear input/output
   - Consider error handling boundaries

2. **Extract Incrementally**
   - Start with the most obvious extractions
   - Test after each extraction
   - Maintain original functionality
   - Improve naming and structure

3. **Optimize Structure**
   - Group related methods logically
   - Consider creating helper classes if needed
   - Improve overall method organization
   - Add appropriate documentation

## Quality Improvements
- Reduce method complexity and length
- Improve code readability and maintainability
- Enable better testing of individual components
- Make code more reusable and modular

## Validation Requirements
- All existing tests continue to pass
- New methods can be tested independently
- Overall functionality remains unchanged
- Code quality metrics are improved
        """.strip()
    
    @staticmethod
    def get_eliminate_duplication_prompt(
        duplicate_code_sections: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for eliminating code duplication.
        
        Args:
            duplicate_code_sections: List of duplicate code sections
            context: Codebase and project context
            
        Returns:
            Prompt for duplication elimination refactoring
        """
        return f"""
# Eliminate Code Duplication Refactoring

## Duplicate Code Sections
{chr(10).join(f"- {section}" for section in duplicate_code_sections)}

## Duplication Elimination Strategy

### Analysis Phase
1. **Identify Duplication Types**
   - Exact duplicates (copy-paste code)
   - Similar code with minor variations
   - Conceptual duplicates (same logic, different implementation)
   - Data structure duplicates

2. **Assess Extraction Opportunities**
   - Common functionality that can be extracted
   - Parameterizable differences
   - Opportunities for inheritance or composition
   - Utility functions and helper methods

### Refactoring Approaches
1. **Extract Method/Function**
   - Create common methods for duplicate logic
   - Parameterize differences where possible
   - Maintain clear and descriptive names
   - Consider return values vs. side effects

2. **Extract Class/Module**
   - Create utility classes for common functionality
   - Group related duplicate code together
   - Design clear interfaces and contracts
   - Consider dependency injection patterns

3. **Template Method Pattern**
   - Define common algorithm structure
   - Allow subclasses to override specific steps
   - Maintain consistency while allowing variation
   - Document the template and extension points

### Implementation Guidelines
1. **Preserve Behavior**
   - Ensure all duplicate code behaves identically after refactoring
   - Test each instance thoroughly
   - Maintain backward compatibility
   - Document any behavioral changes

2. **Improve Design**
   - Create more maintainable abstractions
   - Reduce coupling between components
   - Improve code organization and structure
   - Add appropriate documentation

## Quality Benefits
- Reduced maintenance burden
- Improved consistency across codebase
- Easier bug fixes and enhancements
- Better code organization and structure

## Validation Process
- Test all affected code paths
- Verify behavior is preserved
- Check for performance implications
- Validate with stakeholders if needed
        """.strip()
    
    @staticmethod
    def get_simplify_conditional_prompt(
        complex_conditionals: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for simplifying complex conditional expressions.
        
        Args:
            complex_conditionals: List of complex conditional expressions
            context: Codebase and project context
            
        Returns:
            Prompt for conditional simplification refactoring
        """
        return f"""
# Simplify Conditional Expressions Refactoring

## Complex Conditionals to Simplify
{chr(10).join(f"- {conditional}" for conditional in complex_conditionals)}

## Simplification Strategies

### Decompose Complex Conditions
1. **Extract Boolean Methods**
   - Create well-named methods for complex boolean expressions
   - Use descriptive names that explain the business logic
   - Group related conditions together
   - Make conditions self-documenting

2. **Use Guard Clauses**
   - Handle edge cases and error conditions early
   - Reduce nesting levels in main logic
   - Make the happy path more prominent
   - Improve code readability

3. **Consolidate Duplicate Conditions**
   - Identify repeated conditional logic
   - Extract common conditions to variables or methods
   - Use boolean algebra to simplify expressions
   - Eliminate redundant checks

### Pattern Applications
1. **Replace Nested Conditionals with Guard Clauses**
   - Check for error conditions first
   - Return early when possible
   - Reduce indentation levels
   - Make main logic flow clearer

2. **Replace Complex Conditionals with Polymorphism**
   - Use strategy pattern for complex branching
   - Create specific classes for different behaviors
   - Eliminate large if-else chains
   - Make code more extensible

3. **Introduce Explaining Variables**
   - Break complex expressions into named parts
   - Use intermediate variables with descriptive names
   - Make the logic flow more obvious
   - Improve debugging and maintenance

## Implementation Guidelines

### Readability Improvements
- Use clear, descriptive names for boolean methods
- Add comments for complex business rules
- Group related conditions logically
- Maintain consistent formatting

### Maintainability Enhancements
- Make conditions easier to modify
- Reduce the impact of business rule changes
- Improve testability of individual conditions
- Create reusable condition components

### Performance Considerations
- Optimize condition evaluation order
- Use short-circuit evaluation effectively
- Cache expensive condition calculations
- Consider lazy evaluation where appropriate

## Quality Benefits
- Improved code readability and understanding
- Easier maintenance and modification
- Better testability of individual conditions
- Reduced cognitive complexity

## Validation Requirements
- All existing behavior is preserved
- Edge cases continue to work correctly
- Performance is maintained or improved
- Code is more maintainable and readable
        """.strip()

