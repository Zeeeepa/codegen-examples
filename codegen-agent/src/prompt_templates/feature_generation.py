#!/usr/bin/env python
"""
Feature Generation Prompt Templates

This module contains specialized prompt templates for feature development
with context-aware enhancements and best practices.
"""

from typing import Dict, Any, List, Optional


class FeatureGenerationPrompts:
    """Prompt templates for feature generation tasks."""
    
    @staticmethod
    def get_base_template() -> str:
        """Get the base template for feature generation."""
        return """
# Feature Development Task

## Objective
Develop a new feature that integrates seamlessly with the existing codebase while following established patterns and maintaining high code quality.

## Context Analysis
{context_section}

## Feature Requirements
{requirements_section}

## Implementation Guidelines

### Architecture Compliance
- Follow the existing architectural patterns: {architectural_patterns}
- Maintain consistency with current code organization
- Respect established module boundaries and dependencies

### Code Quality Standards
- Maintain documentation coverage above {doc_threshold}%
- Follow {naming_convention} naming conventions
- Keep function complexity below {complexity_threshold}
- Ensure test coverage for all new functionality

### Integration Requirements
- Integrate with existing {integration_points}
- Maintain backward compatibility where applicable
- Follow established error handling patterns
- Respect existing API contracts and interfaces

## Implementation Strategy

### Phase 1: Design and Planning
1. Analyze existing code patterns and interfaces
2. Design the feature architecture
3. Identify integration points and dependencies
4. Plan the implementation approach

### Phase 2: Core Implementation
1. Implement core functionality following established patterns
2. Add comprehensive error handling and validation
3. Ensure proper logging and monitoring
4. Optimize for performance and scalability

### Phase 3: Testing and Documentation
1. Write comprehensive unit tests
2. Add integration tests where appropriate
3. Document all public interfaces and APIs
4. Update relevant documentation and examples

### Phase 4: Integration and Validation
1. Integrate with existing systems
2. Validate against requirements
3. Perform security and performance testing
4. Ensure deployment readiness

## Success Criteria
- Feature meets all specified requirements
- Code quality metrics are maintained or improved
- All tests pass and coverage targets are met
- Documentation is complete and accurate
- Integration is seamless and non-breaking

## Deliverables
- Complete feature implementation
- Comprehensive test suite
- Updated documentation
- Integration examples
- Performance benchmarks (if applicable)

{additional_instructions}
        """.strip()
    
    @staticmethod
    def get_web_feature_template() -> str:
        """Template for web application features."""
        return """
# Web Feature Development

## Frontend Requirements
- Responsive design for mobile and desktop
- Accessibility compliance (WCAG 2.1 AA)
- Cross-browser compatibility
- Performance optimization (Core Web Vitals)

## Backend Requirements
- RESTful API design principles
- Proper HTTP status codes and error handling
- Input validation and sanitization
- Rate limiting and security measures

## Security Considerations
- Input validation and XSS prevention
- CSRF protection
- Authentication and authorization
- Secure data transmission (HTTPS)

## Performance Guidelines
- Optimize database queries
- Implement caching strategies
- Minimize bundle size and load times
- Use lazy loading where appropriate

## Testing Requirements
- Unit tests for business logic
- Integration tests for API endpoints
- End-to-end tests for critical user flows
- Performance and load testing
        """.strip()
    
    @staticmethod
    def get_api_feature_template() -> str:
        """Template for API feature development."""
        return """
# API Feature Development

## API Design Principles
- RESTful design with clear resource modeling
- Consistent naming conventions and URL patterns
- Proper HTTP methods and status codes
- Comprehensive error responses with details

## Documentation Requirements
- OpenAPI/Swagger specification
- Request/response examples
- Error code documentation
- Rate limiting information

## Security Implementation
- Authentication and authorization
- Input validation and sanitization
- Rate limiting and throttling
- Audit logging for sensitive operations

## Performance Considerations
- Efficient database queries
- Caching strategies
- Pagination for large datasets
- Asynchronous processing where appropriate

## Testing Strategy
- Unit tests for business logic
- Integration tests for endpoints
- Contract testing for API consumers
- Load testing for performance validation
        """.strip()
    
    @staticmethod
    def get_data_processing_template() -> str:
        """Template for data processing features."""
        return """
# Data Processing Feature Development

## Data Pipeline Design
- Scalable and fault-tolerant architecture
- Data validation and quality checks
- Error handling and recovery mechanisms
- Monitoring and alerting capabilities

## Performance Requirements
- Efficient data processing algorithms
- Memory optimization for large datasets
- Parallel processing where applicable
- Streaming vs batch processing considerations

## Data Quality Assurance
- Input validation and sanitization
- Data type checking and conversion
- Duplicate detection and handling
- Data integrity verification

## Monitoring and Observability
- Processing metrics and KPIs
- Error tracking and alerting
- Performance monitoring
- Data lineage tracking

## Testing Approach
- Unit tests for processing logic
- Integration tests with data sources
- Performance tests with realistic data volumes
- Data quality validation tests
        """.strip()
    
    @staticmethod
    def get_microservice_template() -> str:
        """Template for microservice features."""
        return """
# Microservice Feature Development

## Service Design Principles
- Single responsibility and bounded context
- Loose coupling and high cohesion
- Database per service pattern
- API-first design approach

## Communication Patterns
- Synchronous vs asynchronous communication
- Event-driven architecture considerations
- Circuit breaker and retry patterns
- Service discovery and load balancing

## Resilience and Reliability
- Health checks and readiness probes
- Graceful degradation strategies
- Timeout and retry configurations
- Bulkhead pattern implementation

## Observability Requirements
- Distributed tracing
- Centralized logging
- Metrics and monitoring
- Service dependency mapping

## Deployment Considerations
- Containerization (Docker)
- Configuration management
- Secret management
- Rolling deployment strategies
        """.strip()
    
    @staticmethod
    def generate_context_aware_prompt(
        feature_type: str,
        context: Dict[str, Any],
        requirements: List[str],
        constraints: List[str]
    ) -> str:
        """Generate a context-aware prompt for feature development.
        
        Args:
            feature_type: Type of feature (web, api, data, microservice, etc.)
            context: Codebase and project context
            requirements: List of feature requirements
            constraints: List of constraints and limitations
            
        Returns:
            Complete prompt for feature generation
        """
        # Get base template
        base_template = FeatureGenerationPrompts.get_base_template()
        
        # Get feature-specific template
        feature_templates = {
            'web': FeatureGenerationPrompts.get_web_feature_template(),
            'api': FeatureGenerationPrompts.get_api_feature_template(),
            'data': FeatureGenerationPrompts.get_data_processing_template(),
            'microservice': FeatureGenerationPrompts.get_microservice_template()
        }
        
        feature_template = feature_templates.get(feature_type, "")
        
        # Extract context information
        codebase_context = context.get('codebase', {})
        team_context = context.get('team', {})
        quality_context = context.get('quality', {})
        
        # Build context section
        context_section = f"""
### Codebase Information
- Repository: {codebase_context.get('repo_name', 'Unknown')}
- Primary Languages: {', '.join(codebase_context.get('programming_languages', [])[:3])}
- Architecture Patterns: {', '.join(codebase_context.get('architectural_patterns', ['Standard']))}
- Total Files: {codebase_context.get('total_files', 0)}
- Test Coverage: ~{quality_context.get('test_coverage_estimate', 0):.1f}%

### Code Quality Metrics
- Documentation Coverage: {quality_context.get('documentation_coverage', 0):.1f}%
- Maintainability Score: {quality_context.get('maintainability_score', 0):.1f}/100
- Average Complexity: {codebase_context.get('complexity_metrics', {}).get('avg_complexity', 0):.1f}

### Team Standards
- Naming Convention: {codebase_context.get('naming_conventions', {}).get('dominant_convention', 'mixed')}
- Code Style: {codebase_context.get('code_style_patterns', {}).get('avg_line_length', 80):.0f} avg chars/line
- Testing Approach: {team_context.get('inferred_testing_approach', 'standard')}
        """.strip()
        
        # Build requirements section
        requirements_section = "\n".join(f"- {req}" for req in requirements)
        if constraints:
            requirements_section += "\n\n### Constraints\n"
            requirements_section += "\n".join(f"- {constraint}" for constraint in constraints)
        
        # Fill template variables
        template_vars = {
            'context_section': context_section,
            'requirements_section': requirements_section,
            'architectural_patterns': ', '.join(codebase_context.get('architectural_patterns', ['Standard'])),
            'doc_threshold': int(quality_context.get('documentation_coverage', 70)),
            'naming_convention': codebase_context.get('naming_conventions', {}).get('dominant_convention', 'consistent'),
            'complexity_threshold': int(codebase_context.get('complexity_metrics', {}).get('avg_complexity', 10) * 1.5),
            'integration_points': ', '.join(codebase_context.get('dependencies', {}).keys()),
            'additional_instructions': feature_template
        }
        
        return base_template.format(**template_vars)
    
    @staticmethod
    def get_enhancement_prompt(
        existing_feature: str,
        enhancement_requirements: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for enhancing existing features.
        
        Args:
            existing_feature: Description of the existing feature
            enhancement_requirements: List of enhancement requirements
            context: Codebase and project context
            
        Returns:
            Prompt for feature enhancement
        """
        return f"""
# Feature Enhancement Task

## Existing Feature
{existing_feature}

## Enhancement Requirements
{chr(10).join(f"- {req}" for req in enhancement_requirements)}

## Enhancement Guidelines

### Backward Compatibility
- Maintain existing API contracts
- Preserve current functionality
- Provide migration path if breaking changes are necessary
- Document any behavioral changes

### Code Quality Improvement
- Refactor code to improve maintainability
- Add missing tests and documentation
- Optimize performance where possible
- Follow current coding standards

### Integration Considerations
- Ensure compatibility with dependent systems
- Update integration tests
- Consider impact on existing workflows
- Validate with stakeholders

## Implementation Approach

1. **Analysis Phase**
   - Review existing implementation
   - Identify enhancement points
   - Assess impact and dependencies
   - Plan implementation strategy

2. **Enhancement Phase**
   - Implement new functionality
   - Refactor existing code as needed
   - Maintain or improve code quality
   - Add comprehensive tests

3. **Validation Phase**
   - Test backward compatibility
   - Validate new functionality
   - Performance testing
   - Security review

4. **Documentation Phase**
   - Update API documentation
   - Add usage examples
   - Document migration steps
   - Update changelog

## Success Criteria
- All enhancement requirements are met
- Backward compatibility is maintained
- Code quality is improved or maintained
- Comprehensive test coverage
- Complete documentation updates
        """.strip()
    
    @staticmethod
    def get_integration_prompt(
        integration_type: str,
        external_system: str,
        requirements: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate prompt for system integration features.
        
        Args:
            integration_type: Type of integration (API, database, service, etc.)
            external_system: Name/description of external system
            requirements: Integration requirements
            context: Codebase and project context
            
        Returns:
            Prompt for integration development
        """
        return f"""
# System Integration Feature

## Integration Overview
- **Type**: {integration_type}
- **External System**: {external_system}
- **Integration Pattern**: {context.get('integration_pattern', 'Standard API Integration')}

## Requirements
{chr(10).join(f"- {req}" for req in requirements)}

## Integration Architecture

### Connection Management
- Implement connection pooling and reuse
- Handle connection timeouts and retries
- Implement circuit breaker pattern
- Add health checks and monitoring

### Data Transformation
- Define clear data mapping strategies
- Implement validation and sanitization
- Handle data format conversions
- Manage schema evolution

### Error Handling
- Implement comprehensive error handling
- Add retry logic with exponential backoff
- Provide meaningful error messages
- Log integration events and errors

### Security Considerations
- Implement proper authentication
- Secure credential management
- Data encryption in transit
- Audit logging for compliance

## Testing Strategy

### Unit Testing
- Test data transformation logic
- Mock external system responses
- Test error handling scenarios
- Validate retry mechanisms

### Integration Testing
- Test with actual external system
- Validate end-to-end workflows
- Test failure scenarios
- Performance and load testing

## Monitoring and Observability
- Add metrics for integration health
- Implement alerting for failures
- Track performance metrics
- Monitor data quality and consistency

## Documentation Requirements
- Integration architecture diagram
- API documentation and examples
- Configuration and setup guide
- Troubleshooting and FAQ
        """.strip()

