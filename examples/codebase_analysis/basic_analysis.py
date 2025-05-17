#!/usr/bin/env python
"""
Basic Codebase Analysis Example

This script demonstrates how to use the Codegen SDK's Codebase class to analyze
a repository's structure, files, functions, and classes.
"""

import os
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

from codegen import Codebase
from codegen.shared.enums.programming_language import ProgrammingLanguage


def analyze_repository(repo_path: str) -> Dict:
    """Analyze a repository using the Codebase class.

    Args:
        repo_path: Path to the local repository.

    Returns:
        Dictionary containing analysis results.
    """
    print(f"Analyzing repository: {repo_path}")
    
    # Initialize the Codebase
    codebase = Codebase(repo_path)
    
    # Get all files
    all_files = codebase.get_files()
    
    # Count files by extension
    extensions = Counter([os.path.splitext(file.path)[1] for file in all_files])
    
    # Get Python and TypeScript files
    python_files = codebase.get_files(extension=".py")
    typescript_files = codebase.get_files(extension=[".ts", ".tsx"])
    
    # Analyze file sizes
    file_sizes = [(file.path, len(file.content.splitlines())) for file in all_files]
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    
    # Analyze functions
    functions = []
    for file in python_files:
        functions.extend(file.get_functions())
    
    # Count parameters per function
    param_counts = [len(func.parameters) for func in functions]
    avg_params = sum(param_counts) / len(param_counts) if param_counts else 0
    
    # Count functions with docstrings
    funcs_with_docs = sum(1 for func in functions if func.docstring)
    
    return {
        "total_files": len(all_files),
        "extensions": dict(extensions),
        "python_files": len(python_files),
        "typescript_files": len(typescript_files),
        "largest_files": file_sizes[:5],
        "total_functions": len(functions),
        "avg_params_per_function": avg_params,
        "functions_with_docs": funcs_with_docs,
        "functions_with_docs_percentage": (funcs_with_docs / len(functions) * 100) if functions else 0,
    }


def analyze_from_github(repo_name: str, access_token: Optional[str] = None) -> Dict:
    """Analyze a repository from GitHub.

    Args:
        repo_name: Repository name in format "owner/repo".
        access_token: GitHub access token (optional).

    Returns:
        Dictionary containing analysis results.
    """
    print(f"Analyzing GitHub repository: {repo_name}")
    
    # Use environment variable if token not provided
    token = access_token or os.environ.get("GITHUB_ACCESS_TOKEN")
    if not token:
        raise ValueError("GitHub access token is required. Provide it as an argument or set GITHUB_ACCESS_TOKEN environment variable.")
    
    # Initialize the Codebase from GitHub
    codebase = Codebase.from_repo(
        repo_full_name=repo_name,
        tmp_dir="/tmp/codegen",
        access_token=token
    )
    
    # Perform the same analysis as for local repositories
    all_files = codebase.get_files()
    extensions = Counter([os.path.splitext(file.path)[1] for file in all_files])
    
    python_files = codebase.get_files(extension=".py")
    typescript_files = codebase.get_files(extension=[".ts", ".tsx"])
    
    file_sizes = [(file.path, len(file.content.splitlines())) for file in all_files]
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    
    functions = []
    for file in python_files:
        functions.extend(file.get_functions())
    
    param_counts = [len(func.parameters) for func in functions]
    avg_params = sum(param_counts) / len(param_counts) if param_counts else 0
    
    funcs_with_docs = sum(1 for func in functions if func.docstring)
    
    return {
        "total_files": len(all_files),
        "extensions": dict(extensions),
        "python_files": len(python_files),
        "typescript_files": len(typescript_files),
        "largest_files": file_sizes[:5],
        "total_functions": len(functions),
        "avg_params_per_function": avg_params,
        "functions_with_docs": funcs_with_docs,
        "functions_with_docs_percentage": (funcs_with_docs / len(functions) * 100) if functions else 0,
    }


def analyze_from_string() -> None:
    """Demonstrate analyzing code from a string."""
    print("Analyzing code from string:")
    
    # Python code example
    python_code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers and return the result.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
    \"\"\"
    return a + b

def subtract(a: int, b: int) -> int:
    # Subtract b from a
    return a - b

class Calculator:
    def multiply(self, a: int, b: int) -> int:
        \"\"\"Multiply two numbers.\"\"\"
        return a * b
        
    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
"""
    
    # Initialize Codebase from string
    codebase = Codebase.from_string(code=python_code, language=ProgrammingLanguage.PYTHON)
    
    # Get the file (there's only one in this case)
    file = codebase.get_files()[0]
    
    # Analyze functions
    functions = file.get_functions()
    print(f"Found {len(functions)} functions:")
    for func in functions:
        print(f"  - {func.name}")
        print(f"    Parameters: {[p.name for p in func.parameters]}")
        print(f"    Return type: {func.return_type}")
        print(f"    Has docstring: {bool(func.docstring)}")
        print()
    
    # Analyze classes
    classes = file.get_classes()
    print(f"Found {len(classes)} classes:")
    for cls in classes:
        print(f"  - {cls.name}")
        methods = cls.get_methods()
        print(f"    Methods: {[m.name for m in methods]}")
        print()


def print_analysis_results(results: Dict) -> None:
    """Print the analysis results in a readable format.

    Args:
        results: Dictionary containing analysis results.
    """
    print("\nAnalysis Results:")
    print(f"Total files: {results['total_files']}")
    print(f"Python files: {results['python_files']}")
    print(f"TypeScript files: {results['typescript_files']}")
    
    print("\nTop 5 largest files:")
    for i, (path, lines) in enumerate(results['largest_files'], 1):
        print(f"{i}. {path} ({lines} lines)")
    
    print("\nFunction analysis:")
    print(f"- Total functions: {results['total_functions']}")
    print(f"- Average parameters per function: {results['avg_params_per_function']:.1f}")
    print(f"- Functions with docstrings: {results['functions_with_docs']} ({results['functions_with_docs_percentage']:.1f}%)")
    
    print("\nFile extensions:")
    for ext, count in results['extensions'].items():
        if ext:  # Skip empty extension
            print(f"- {ext}: {count} files")


def main():
    """Main function to run the example."""
    if len(sys.argv) < 2:
        print("Usage: python basic_analysis.py <repo_path_or_name> [github]")
        print("  repo_path_or_name: Path to local repository or GitHub repo name (owner/repo)")
        print("  github: Optional flag to indicate the repo is on GitHub")
        sys.exit(1)
    
    repo_path_or_name = sys.argv[1]
    is_github = len(sys.argv) > 2 and sys.argv[2].lower() == "github"
    
    try:
        if is_github:
            results = analyze_from_github(repo_path_or_name)
        else:
            results = analyze_repository(repo_path_or_name)
        
        print_analysis_results(results)
        
        # Demonstrate string analysis
        analyze_from_string()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

