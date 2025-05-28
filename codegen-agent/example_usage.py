#!/usr/bin/env python
"""
Example Usage of Advanced Codegen Agent

This script demonstrates various usage patterns of the Advanced Codegen Agent
with comprehensive context awareness and intelligent retry logic.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import AdvancedCodegenAgent
from context_engine import TaskContext, TeamContext


def main():
    """Main example function demonstrating agent usage."""
    
    # Get API token from environment
    api_token = os.getenv("CODEGEN_API_TOKEN")
    if not api_token:
        print("❌ Please set CODEGEN_API_TOKEN environment variable")
        return
    
    # Initialize the agent
    print("🚀 Initializing Advanced Codegen Agent...")
    agent = AdvancedCodegenAgent(
        api_token=api_token,
        org_id=1,
        config_path="config/agent_config.yaml"
    )
    print("✅ Agent initialized successfully!")
    
    # Example repository path (use current directory for demo)
    repo_path = str(Path.cwd())
    
    # Example 1: Feature Generation
    print("\n" + "="*60)
    print("📝 Example 1: Feature Generation")
    print("="*60)
    
    try:
        result = agent.generate_feature(
            description="Add a user authentication system with JWT tokens",
            requirements=[
                "Support email/password login",
                "Include JWT token generation and validation",
                "Add password hashing with bcrypt",
                "Include rate limiting for login attempts",
                "Add user registration endpoint",
                "Include email verification"
            ],
            repo_path=repo_path,
            feature_type="web",
            constraints=[
                "Must be compatible with existing FastAPI framework",
                "Use PostgreSQL for user storage",
                "Follow existing code style and patterns"
            ],
            quality_threshold=0.8
        )
        
        if result.success:
            print(f"✅ Feature generated successfully!")
            print(f"📊 Quality Score: {result.quality_score:.2f}")
            print(f"🔄 Retry Count: {result.retry_count}")
            print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
            print(f"📁 Files Modified: {', '.join(result.files_modified)}")
            print(f"🔗 Task URL: {result.task_url}")
            print(f"💡 Feedback: {', '.join(result.feedback[:3])}")
        else:
            print(f"❌ Feature generation failed: {result.error_message}")
            print(f"💡 Feedback: {', '.join(result.feedback)}")
            
    except Exception as e:
        print(f"❌ Error during feature generation: {e}")
    
    # Example 2: Bug Fixing
    print("\n" + "="*60)
    print("🐛 Example 2: Bug Fixing")
    print("="*60)
    
    try:
        result = agent.fix_bug(
            bug_description="Login endpoint returns 500 error for valid credentials",
            repo_path=repo_path,
            bug_type="security",
            error_logs=[
                "AttributeError: 'NoneType' object has no attribute 'password'",
                "File '/app/auth.py', line 45, in authenticate_user",
                "Traceback (most recent call last):"
            ],
            reproduction_steps=[
                "POST /api/login with valid email/password",
                "Observe 500 Internal Server Error",
                "Check logs for AttributeError",
                "Verify user exists in database"
            ],
            quality_threshold=0.8
        )
        
        if result.success:
            print(f"✅ Bug fixed successfully!")
            print(f"📊 Quality Score: {result.quality_score:.2f}")
            print(f"🔄 Retry Count: {result.retry_count}")
            print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
            print(f"🔗 Task URL: {result.task_url}")
        else:
            print(f"❌ Bug fix failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error during bug fixing: {e}")
    
    # Example 3: Code Refactoring
    print("\n" + "="*60)
    print("🔧 Example 3: Code Refactoring")
    print("="*60)
    
    try:
        result = agent.refactor_code(
            refactoring_description="Modernize legacy authentication module",
            target_files=["src/auth/legacy_auth.py", "src/auth/utils.py"],
            repo_path=repo_path,
            refactoring_type="legacy",
            current_issues=[
                "Uses deprecated authentication methods",
                "Poor error handling and logging",
                "No input validation or sanitization",
                "High cyclomatic complexity (>15)",
                "Inconsistent naming conventions",
                "Missing type hints and documentation"
            ],
            target_improvements=[
                "Implement modern authentication patterns",
                "Add comprehensive error handling and logging",
                "Include input validation and sanitization",
                "Reduce complexity and improve readability",
                "Add type hints and comprehensive documentation",
                "Follow current coding standards"
            ],
            quality_threshold=0.85
        )
        
        if result.success:
            print(f"✅ Code refactored successfully!")
            print(f"📊 Quality Score: {result.quality_score:.2f}")
            print(f"🔄 Retry Count: {result.retry_count}")
            print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
            print(f"🔗 Task URL: {result.task_url}")
        else:
            print(f"❌ Refactoring failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error during refactoring: {e}")
    
    # Example 4: Code Quality Assessment
    print("\n" + "="*60)
    print("📊 Example 4: Code Quality Assessment")
    print("="*60)
    
    sample_code = '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number using recursion.
    
    Args:
        n: The position in the Fibonacci sequence
        
    Returns:
        The nth Fibonacci number
    """
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def factorial(n):
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
    '''
    
    try:
        quality_report = agent.assess_code_quality(
            code=sample_code,
            repo_path=repo_path
        )
        
        print(f"📊 Overall Quality Score: {quality_report['overall_score']:.2f}")
        print(f"📖 Readability: {quality_report['detailed_metrics']['readability']:.2f}")
        print(f"🔧 Maintainability: {quality_report['detailed_metrics']['maintainability']:.2f}")
        print(f"✅ Correctness: {quality_report['detailed_metrics']['correctness']:.2f}")
        print(f"⚡ Performance: {quality_report['detailed_metrics']['performance']:.2f}")
        print(f"🔒 Security: {quality_report['detailed_metrics']['security']:.2f}")
        
        if quality_report['recommendations']:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(quality_report['recommendations'][:3], 1):
                print(f"   {i}. {rec}")
        
        if quality_report['critical_issues']:
            print(f"\n⚠️  Critical Issues:")
            for i, issue in enumerate(quality_report['critical_issues'][:3], 1):
                print(f"   {i}. {issue}")
                
    except Exception as e:
        print(f"❌ Error during quality assessment: {e}")
    
    # Example 5: Team Context Configuration
    print("\n" + "="*60)
    print("👥 Example 5: Team Context Configuration")
    print("="*60)
    
    team_context = TeamContext(
        coding_standards={
            "naming_convention": "snake_case",
            "line_length": 88,
            "documentation_required": True,
            "type_hints_required": True
        },
        preferred_patterns=[
            "dependency_injection",
            "factory_pattern",
            "observer_pattern",
            "repository_pattern"
        ],
        testing_requirements={
            "framework": "pytest",
            "coverage": 85,
            "integration_tests": True,
            "unit_tests": True
        },
        review_guidelines=[
            "Code review required for all changes",
            "Security review for authentication changes",
            "Performance review for database changes",
            "Documentation review for API changes"
        ],
        deployment_constraints=[
            "Docker compatible",
            "No external dependencies without approval",
            "Environment variable configuration",
            "Health check endpoints required"
        ],
        technology_stack=[
            "Python 3.9+",
            "FastAPI",
            "PostgreSQL",
            "Redis",
            "Docker",
            "Kubernetes"
        ]
    )
    
    try:
        result = agent.generate_feature(
            description="Add caching layer with Redis",
            requirements=[
                "Implement Redis caching for API responses",
                "Add cache invalidation strategies",
                "Include cache warming for critical data",
                "Add cache monitoring and metrics"
            ],
            repo_path=repo_path,
            feature_type="api",
            team_context=team_context,
            quality_threshold=0.85
        )
        
        print(f"✅ Feature with team context: {'Success' if result.success else 'Failed'}")
        if result.success:
            print(f"📊 Quality Score: {result.quality_score:.2f}")
            print(f"🔗 Task URL: {result.task_url}")
            
    except Exception as e:
        print(f"❌ Error with team context: {e}")
    
    # Example 6: Session Statistics
    print("\n" + "="*60)
    print("📈 Example 6: Session Statistics")
    print("="*60)
    
    try:
        stats = agent.get_session_statistics()
        
        print(f"📊 Session Statistics:")
        print(f"   • Duration: {stats['session']['duration_seconds']:.1f}s")
        print(f"   • Requests Processed: {stats['session']['requests_processed']}")
        print(f"   • Success Rate: {stats['session']['success_rate']:.2%}")
        print(f"   • Average Quality Score: {stats['session']['avg_quality_score']:.2f}")
        print(f"   • Average Execution Time: {stats['session']['avg_execution_time']:.2f}s")
        
        print(f"\n🤖 Codegen Client Metrics:")
        print(f"   • Total Requests: {stats['codegen_client']['total_requests']}")
        print(f"   • Successful Requests: {stats['codegen_client']['successful_requests']}")
        print(f"   • Success Rate: {stats['codegen_client']['success_rate']:.2%}")
        print(f"   • Learned Patterns: {stats['codegen_client']['learned_patterns']}")
        
        print(f"\n💬 Feedback Analytics:")
        feedback_stats = stats['feedback_analytics']
        print(f"   • Total Feedback Processed: {feedback_stats['total_feedback_processed']}")
        if feedback_stats['most_common_issues']:
            print(f"   • Most Common Issues: {list(feedback_stats['most_common_issues'].keys())[:3]}")
            
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
    
    print("\n" + "="*60)
    print("🎉 Advanced Codegen Agent Demo Complete!")
    print("="*60)
    print("💡 This demo showcased:")
    print("   • Context-aware feature generation")
    print("   • Systematic bug fixing")
    print("   • Intelligent code refactoring")
    print("   • Comprehensive quality assessment")
    print("   • Team context integration")
    print("   • Performance monitoring")
    print("\n🚀 Ready to integrate into your development workflow!")


if __name__ == "__main__":
    main()

