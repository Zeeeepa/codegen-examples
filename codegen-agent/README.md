# ⚡ Advanced Codegen Agent with Context Awareness

A sophisticated, context-aware code generation agent that leverages comprehensive codebase analysis, intelligent retry logic, and quality assessment to produce high-quality code that integrates seamlessly with existing projects.

## 🌟 Features

### 🧠 **Comprehensive Context Awareness**
- **Multi-source Context Gathering**: Analyzes codebase structure, dependencies, coding patterns, and quality metrics
- **Intelligent Caching**: Caches context data with TTL for improved performance
- **Context Compression**: Efficiently handles large codebases through smart compression
- **Pattern Detection**: Identifies architectural patterns, naming conventions, and code styles

### 🔄 **Intelligent Retry Logic**
- **Multiple Retry Strategies**: Exponential backoff, linear backoff, fixed delay, adaptive
- **Circuit Breaker Pattern**: Prevents cascading failures
- **Reason-Specific Configuration**: Different retry behavior for different failure types
- **Comprehensive Statistics**: Tracks retry patterns and success rates

### 📊 **Advanced Quality Assessment**
- **Multi-dimensional Analysis**: Readability, maintainability, correctness, performance, security
- **Language-Specific Assessment**: Tailored evaluation for different programming languages
- **Security Pattern Detection**: Identifies common security vulnerabilities
- **Performance Anti-Pattern Detection**: Finds inefficient code patterns

### 🔄 **Feedback Integration**
- **Pattern Recognition**: Learns from successful and failed generation attempts
- **Improvement Suggestions**: Generates actionable recommendations
- **Prompt Enhancement**: Improves prompts based on feedback
- **Continuous Learning**: Adapts and improves over time

### 🎯 **Multi-Mode Generation**
- **Feature Development**: New feature implementation with architectural compliance
- **Bug Fixing**: Systematic debugging and resolution
- **Code Refactoring**: Quality improvement and optimization
- **Testing**: Comprehensive test generation
- **Documentation**: API and code documentation
- **Performance Optimization**: Efficiency improvements

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Zeeeepa/codegen-examples.git
cd codegen-examples/codegen-agent

# Install dependencies
pip install -r requirements.txt

# Set up your Codegen API token
export CODEGEN_API_TOKEN="your-api-token-here"
```

### Basic Usage

```python
from src.agent import AdvancedCodegenAgent
from src.context_engine import TaskContext

# Initialize the agent
agent = AdvancedCodegenAgent(
    api_token="your-api-token",
    org_id=1
)

# Generate a new feature
result = agent.generate_feature(
    description="Add user authentication system",
    requirements=[
        "Support email/password login",
        "Include JWT token generation",
        "Add password hashing with bcrypt",
        "Include rate limiting for login attempts"
    ],
    repo_path="/path/to/your/repository",
    feature_type="web",
    quality_threshold=0.8
)

if result.success:
    print(f"✅ Feature generated successfully!")
    print(f"📊 Quality Score: {result.quality_score:.2f}")
    print(f"📁 Files Modified: {', '.join(result.files_modified)}")
    print(f"🔗 Task URL: {result.task_url}")
else:
    print(f"❌ Generation failed: {result.error_message}")
    print(f"💡 Feedback: {', '.join(result.feedback)}")
```

### Bug Fixing

```python
# Fix a bug with systematic approach
result = agent.fix_bug(
    bug_description="Login endpoint returns 500 error for valid credentials",
    repo_path="/path/to/your/repository",
    bug_type="security",
    error_logs=[
        "AttributeError: 'NoneType' object has no attribute 'password'",
        "File '/app/auth.py', line 45, in authenticate_user"
    ],
    reproduction_steps=[
        "POST /api/login with valid email/password",
        "Observe 500 Internal Server Error",
        "Check logs for AttributeError"
    ]
)
```

### Code Refactoring

```python
# Refactor legacy code
result = agent.refactor_code(
    refactoring_description="Modernize authentication module",
    target_files=["src/auth/legacy_auth.py", "src/auth/utils.py"],
    repo_path="/path/to/your/repository",
    refactoring_type="legacy",
    current_issues=[
        "Uses deprecated authentication methods",
        "Poor error handling",
        "No input validation",
        "High cyclomatic complexity"
    ],
    target_improvements=[
        "Implement modern authentication patterns",
        "Add comprehensive error handling",
        "Include input validation and sanitization",
        "Reduce complexity and improve readability"
    ]
)
```

## 📋 Configuration

### Agent Configuration

Create `config/agent_config.yaml`:

```yaml
agent:
  # API Configuration
  api:
    timeout: 300
    max_retries: 3
    retry_delay: 2.0
    
  # Context Engine Settings
  context:
    cache_enabled: true
    cache_ttl: 86400  # 24 hours
    max_context_size: 50000
    compression_enabled: true
    
  # Quality Assessment
  quality:
    threshold: 0.8
    weights:
      readability: 0.20
      maintainability: 0.20
      correctness: 0.25
      performance: 0.15
      security: 0.10
      documentation: 0.05
      testing: 0.05
      
  # Retry Logic
  retry:
    max_retries: 3
    base_delay: 1.0
    max_delay: 60.0
    exponential_base: 2.0
    jitter: true
    
  # Learning and Feedback
  learning:
    enabled: true
    pattern_storage_limit: 100
    feedback_retention_days: 30
```

### Language-Specific Configuration

Configure language-specific settings in `config/language_configs/`:

```yaml
# python.yaml
language:
  name: "Python"
  version: "3.8+"
  
style:
  naming:
    functions: "snake_case"
    classes: "PascalCase"
    constants: "UPPER_SNAKE_CASE"
  formatting:
    line_length: 88
    indentation: 4
    quote_style: "double"
    
quality:
  complexity:
    cyclomatic_complexity: 10
    max_function_length: 50
    max_parameters: 5
  documentation:
    require_docstrings: true
    docstring_style: "google"
    min_coverage: 80
```

## 🏗️ Architecture

### Core Components

1. **Context Engine**: Gathers comprehensive codebase context
2. **Codegen Client**: Orchestrates code generation with retry logic
3. **Quality Assessor**: Evaluates generated code quality
4. **Feedback Processor**: Processes validation feedback
5. **Retry Manager**: Handles intelligent retry strategies

### Data Flow

```
Request → Context Gathering → Prompt Generation → Code Generation
    ↓
Quality Assessment → Feedback Processing → Retry Logic (if needed)
    ↓
Success/Failure → Learning Update
```

## 🔧 Advanced Usage

### Custom Validation

```python
def custom_validator(generated_code, context):
    """Custom validation function."""
    # Check for specific patterns or requirements
    if "TODO" in generated_code:
        return {"valid": False, "message": "Generated code contains TODO comments"}
    
    # Check for required imports
    required_imports = ["logging", "typing"]
    for imp in required_imports:
        if f"import {imp}" not in generated_code:
            return {"valid": False, "message": f"Missing required import: {imp}"}
    
    return {"valid": True}

# Use custom validation
result = agent.generate_feature(
    description="Add logging system",
    requirements=["Use structured logging", "Include error tracking"],
    repo_path="/path/to/repo",
    validation_callback=custom_validator
)
```

### Team Context Configuration

```python
from src.context_engine import TeamContext

team_context = TeamContext(
    coding_standards={
        "naming_convention": "snake_case",
        "line_length": 88,
        "documentation_required": True
    },
    preferred_patterns=[
        "dependency_injection",
        "factory_pattern",
        "observer_pattern"
    ],
    testing_requirements={
        "framework": "pytest",
        "coverage": 85,
        "integration_tests": True
    },
    review_guidelines=[
        "Code review required for all changes",
        "Security review for authentication changes",
        "Performance review for database changes"
    ],
    deployment_constraints=[
        "Docker compatible",
        "No external dependencies without approval",
        "Environment variable configuration"
    ],
    technology_stack=[
        "Python 3.9+",
        "FastAPI",
        "PostgreSQL",
        "Redis",
        "Docker"
    ]
)

result = agent.generate_feature(
    description="Add caching layer",
    requirements=["Use Redis for caching", "Include cache invalidation"],
    repo_path="/path/to/repo",
    team_context=team_context
)
```

### Quality Assessment

```python
# Assess code quality
quality_report = agent.assess_code_quality(
    code="""
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
    """,
    repo_path="/path/to/repo"
)

print(f"Overall Score: {quality_report['overall_score']:.2f}")
print(f"Recommendations: {quality_report['recommendations']}")
print(f"Critical Issues: {quality_report['critical_issues']}")
```

### Session Statistics

```python
# Get performance statistics
stats = agent.get_session_statistics()
print(f"Success Rate: {stats['session']['success_rate']:.2%}")
print(f"Average Quality Score: {stats['session']['avg_quality_score']:.2f}")
print(f"Average Execution Time: {stats['session']['avg_execution_time']:.2f}s")
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_context_gathering.py
pytest tests/test_code_generation.py
pytest tests/test_feedback_loop.py

# Run with coverage
pytest --cov=src tests/
```

## 📚 Documentation

- [Architecture Overview](docs/agent-architecture.md)
- [Prompt Engineering Guide](docs/prompt-engineering.md)
- [Performance Tuning](docs/performance-tuning.md)
- [API Reference](docs/api-reference.md)

## 🔒 Security

### Security Features

- **Input Validation**: All inputs are validated and sanitized
- **Output Sanitization**: Generated code is checked for security issues
- **Secure Token Management**: API tokens are handled securely
- **Audit Logging**: All operations are logged for security monitoring

### Security Best Practices

- Store API tokens in environment variables
- Use secure communication channels (HTTPS)
- Regularly update dependencies
- Monitor for security vulnerabilities
- Follow principle of least privilege

## 🚀 Performance

### Optimization Features

- **Context Caching**: Intelligent caching with TTL
- **Prompt Optimization**: Efficient prompt generation
- **Parallel Processing**: Concurrent quality assessment
- **Resource Management**: Efficient memory and CPU usage

### Performance Tips

- Enable context caching for repeated operations
- Use appropriate quality thresholds
- Configure retry strategies based on your needs
- Monitor performance metrics regularly

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run linting
black src/ tests/
flake8 src/ tests/
mypy src/

# Run tests
pytest tests/ --cov=src
```

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Codegen SDK](https://docs.codegen.com) for the core code generation capabilities
- [Claude Code](https://github.com/anthropics/claude-code) for validation inspiration
- [Claude Task Master](https://github.com/eyaltoledano/claude-task-master) for task management patterns

## 📞 Support

- 📧 Email: support@codegen.com
- 💬 Discord: [Codegen Community](https://discord.gg/codegen)
- 📖 Documentation: [docs.codegen.com](https://docs.codegen.com)
- 🐛 Issues: [GitHub Issues](https://github.com/Zeeeepa/codegen-examples/issues)

---

**Built with ❤️ by the Codegen Team**

