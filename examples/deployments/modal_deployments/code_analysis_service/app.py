"""
Code Analysis Service
A Modal application that provides a web API for analyzing GitHub repositories using the Codegen API.
"""

import os
import json
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import modal
from modal import web_endpoint, Image, Stub, Secret
from codegen import Codebase, Agent

# Define the Modal image with required dependencies
image = Image.debian_slim().pip_install(
    "codegen>=0.52.19",
    "gitpython>=3.1.30",
    "python-dotenv>=1.0.0",
)

# Create a Modal Stub
stub = Stub(
    name="code-analysis-service",
    image=image,
    secrets=[
        Secret.from_name("codegen-secrets"),  # Contains CODEGEN_API_TOKEN
        Secret.from_name("github-secrets"),   # Contains GITHUB_TOKEN (optional)
    ]
)

def clone_repository(repo_url: str, target_dir: str) -> bool:
    """
    Clone a GitHub repository to the target directory.
    
    Args:
        repo_url: URL of the GitHub repository
        target_dir: Directory to clone the repository to
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Add GitHub token to URL if available
        github_token = os.environ.get("GITHUB_TOKEN")
        if github_token and "github.com" in repo_url:
            # Insert token into URL for private repo access
            if repo_url.startswith("https://"):
                repo_url = repo_url.replace(
                    "https://", f"https://{github_token}@"
                )
        
        # Clone the repository
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_basic_stats(codebase: Codebase) -> Dict[str, Any]:
    """
    Get basic statistics about the codebase.
    
    Args:
        codebase: Codegen Codebase object
        
    Returns:
        Dict containing basic statistics
    """
    # Get all files
    all_files = codebase.get_files()
    
    # Count lines of code
    total_lines = 0
    language_counts = {}
    
    for file in all_files:
        # Skip non-text files
        try:
            content = file.content
            lines = content.splitlines()
            total_lines += len(lines)
            
            # Determine language based on file extension
            ext = os.path.splitext(file.path)[1].lower()
            lang = {
                ".py": "Python",
                ".js": "JavaScript",
                ".ts": "TypeScript",
                ".jsx": "JavaScript",
                ".tsx": "TypeScript",
                ".java": "Java",
                ".c": "C",
                ".cpp": "C++",
                ".cs": "C#",
                ".go": "Go",
                ".rb": "Ruby",
                ".php": "PHP",
                ".swift": "Swift",
                ".kt": "Kotlin",
                ".rs": "Rust",
                ".html": "HTML",
                ".css": "CSS",
                ".scss": "SCSS",
                ".json": "JSON",
                ".md": "Markdown",
                ".yml": "YAML",
                ".yaml": "YAML",
                ".xml": "XML",
                ".sh": "Shell",
                ".bat": "Batch",
                ".ps1": "PowerShell",
            }.get(ext, "Other")
            
            language_counts[lang] = language_counts.get(lang, 0) + 1
        except:
            # Skip binary files or files that can't be read
            continue
    
    return {
        "files": len(all_files),
        "lines_of_code": total_lines,
        "languages": language_counts,
    }

def analyze_code_quality(codebase: Codebase, agent: Agent) -> Dict[str, Any]:
    """
    Analyze code quality using the Codegen Agent.
    
    Args:
        codebase: Codegen Codebase object
        agent: Codegen Agent object
        
    Returns:
        Dict containing code quality metrics
    """
    # Use the agent to analyze code quality
    prompt = """
    Analyze the codebase and provide the following metrics:
    1. Complexity (1-5 scale, where 1 is simple and 5 is very complex)
    2. Maintainability (1-5 scale, where 1 is hard to maintain and 5 is easy to maintain)
    3. Test coverage (0-1 scale, where 0 is no tests and 1 is full coverage)
    
    Format your response as a JSON object with the following structure:
    {
        "complexity": float,
        "maintainability": float,
        "test_coverage": float
    }
    """
    
    response = agent.run(prompt)
    
    try:
        # Parse the JSON response
        metrics = json.loads(response)
        return metrics
    except:
        # Return default metrics if parsing fails
        return {
            "complexity": 3.0,
            "maintainability": 3.0,
            "test_coverage": 0.5,
        }

def identify_issues(codebase: Codebase, agent: Agent, analysis_type: str) -> List[Dict[str, Any]]:
    """
    Identify issues in the codebase using the Codegen Agent.
    
    Args:
        codebase: Codegen Codebase object
        agent: Codegen Agent object
        analysis_type: Type of analysis to perform
        
    Returns:
        List of issues
    """
    # Customize the prompt based on the analysis type
    if analysis_type == "security":
        focus = "security vulnerabilities, such as SQL injection, XSS, CSRF, etc."
    elif analysis_type == "performance":
        focus = "performance issues, such as inefficient algorithms, N+1 queries, etc."
    else:
        focus = "code quality issues, security vulnerabilities, and performance problems"
    
    prompt = f"""
    Analyze the codebase and identify the top 5 most critical {focus}
    
    For each issue, provide:
    1. Type (security, performance, quality)
    2. Severity (low, medium, high)
    3. Description
    4. File path
    5. Line number (approximate)
    
    Format your response as a JSON array of objects with the following structure:
    [
        {{
            "type": string,
            "severity": string,
            "description": string,
            "file": string,
            "line": int
        }}
    ]
    """
    
    response = agent.run(prompt)
    
    try:
        # Parse the JSON response
        issues = json.loads(response)
        return issues
    except:
        # Return empty list if parsing fails
        return []

def generate_recommendations(codebase: Codebase, agent: Agent, issues: List[Dict[str, Any]]) -> List[str]:
    """
    Generate recommendations based on the identified issues.
    
    Args:
        codebase: Codegen Codebase object
        agent: Codegen Agent object
        issues: List of identified issues
        
    Returns:
        List of recommendations
    """
    # Create a prompt based on the identified issues
    issues_text = "\n".join([
        f"- {issue['type']} ({issue['severity']}): {issue['description']} in {issue['file']}"
        for issue in issues
    ])
    
    prompt = f"""
    Based on the following issues identified in the codebase:
    
    {issues_text}
    
    Provide 3-5 actionable recommendations to improve the codebase.
    
    Format your response as a JSON array of strings.
    """
    
    response = agent.run(prompt)
    
    try:
        # Parse the JSON response
        recommendations = json.loads(response)
        return recommendations
    except:
        # Return empty list if parsing fails
        return []

@stub.function
@web_endpoint(method="POST")
def analyze(repo_url: str, analysis_type: str = "basic") -> Dict[str, Any]:
    """
    Analyze a GitHub repository and return insights.
    
    Args:
        repo_url: URL of the GitHub repository
        analysis_type: Type of analysis to perform (basic, full, security, performance)
        
    Returns:
        Dict containing analysis results
    """
    # Validate input
    if not repo_url or not repo_url.startswith("https://github.com/"):
        return {"error": "Invalid GitHub repository URL"}
    
    # Extract repo name from URL
    repo_parts = repo_url.split("github.com/")
    if len(repo_parts) != 2:
        return {"error": "Invalid GitHub repository URL"}
    
    repo_name = repo_parts[1].strip("/")
    
    # Create a temporary directory for the repository
    with tempfile.TemporaryDirectory() as temp_dir:
        # Clone the repository
        if not clone_repository(repo_url, temp_dir):
            return {"error": "Failed to clone repository"}
        
        # Initialize Codegen Codebase
        codebase = Codebase(temp_dir)
        
        # Initialize Codegen Agent if needed
        agent = None
        if analysis_type != "basic":
            agent = Agent(
                token=os.environ.get("CODEGEN_API_TOKEN"),
                codebase=codebase,
            )
        
        # Get basic statistics
        summary = get_basic_stats(codebase)
        
        # Initialize result
        result = {
            "repo": repo_name,
            "analysis_type": analysis_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
        }
        
        # Perform additional analysis based on the analysis type
        if analysis_type != "basic":
            # Analyze code quality
            metrics = analyze_code_quality(codebase, agent)
            result["metrics"] = metrics
            
            # Identify issues
            issues = identify_issues(codebase, agent, analysis_type)
            result["issues"] = issues
            
            # Generate recommendations
            recommendations = generate_recommendations(codebase, agent, issues)
            result["recommendations"] = recommendations
        
        return result

if __name__ == "__main__":
    # This will be executed when running the script locally
    stub.deploy("code-analysis-service")
    print("Code Analysis Service deployed successfully!")

