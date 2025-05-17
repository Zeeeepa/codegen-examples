#!/usr/bin/env python
"""
Basic Function Example

This script demonstrates how to use the Codegen SDK's function decorator to create
custom functions that can be deployed and run in the Codegen environment.
"""

import os
import sys
from typing import Dict, List, Optional

from codegen import Codebase, function
from codegen.shared.enums.programming_language import ProgrammingLanguage


@function('analyze-code')
def analyze_code(codebase: Codebase) -> Dict:
    """Analyze code in a repository.
    
    This function analyzes a codebase and returns statistics about the code,
    including file counts, lines of code, and complexity metrics.
    
    Args:
        codebase: The Codebase instance to analyze.
        
    Returns:
        Dictionary containing analysis results.
    """
    # Get all files
    all_files = codebase.get_files()
    
    # Get Python and TypeScript files
    python_files = codebase.get_files(extension=".py")
    typescript_files = codebase.get_files(extension=[".ts", ".tsx"])
    
    # Count lines of code
    python_loc = sum(len(file.content.splitlines()) for file in python_files)
    typescript_loc = sum(len(file.content.splitlines()) for file in typescript_files)
    total_loc = python_loc + typescript_loc
    
    # Count functions and classes
    python_functions = []
    python_classes = []
    
    for file in python_files:
        python_functions.extend(file.get_functions())
        python_classes.extend(file.get_classes())
    
    # Calculate average function complexity
    function_loc = [len(func.body.splitlines()) for func in python_functions]
    avg_function_loc = sum(function_loc) / len(function_loc) if function_loc else 0
    
    # Count functions with docstrings
    functions_with_docs = sum(1 for func in python_functions if func.docstring)
    doc_percentage = (functions_with_docs / len(python_functions) * 100) if python_functions else 0
    
    return {
        "total_files": len(all_files),
        "python_files": len(python_files),
        "typescript_files": len(typescript_files),
        "total_loc": total_loc,
        "python_loc": python_loc,
        "typescript_loc": typescript_loc,
        "python_functions": len(python_functions),
        "python_classes": len(python_classes),
        "avg_function_loc": avg_function_loc,
        "functions_with_docs": functions_with_docs,
        "doc_percentage": doc_percentage
    }


@function('find-security-issues')
def find_security_issues(codebase: Codebase) -> List[Dict]:
    """Find potential security issues in a codebase.
    
    This function scans a codebase for common security issues and vulnerabilities,
    such as hardcoded credentials, insecure functions, and SQL injection risks.
    
    Args:
        codebase: The Codebase instance to analyze.
        
    Returns:
        List of dictionaries containing security issues found.
    """
    security_issues = []
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    # Patterns to look for
    security_patterns = [
        {
            "name": "Hardcoded Password",
            "pattern": "password.*=.*['\"]\\w+['\"]",
            "severity": "High",
            "description": "Hardcoded password found"
        },
        {
            "name": "Insecure Hash",
            "pattern": "md5|sha1",
            "severity": "Medium",
            "description": "Insecure hash algorithm used"
        },
        {
            "name": "SQL Injection Risk",
            "pattern": "execute\\(['\"].*%s.*['\"].*%",
            "severity": "High",
            "description": "Potential SQL injection vulnerability"
        },
        {
            "name": "Debug Mode",
            "pattern": "DEBUG.*=.*True",
            "severity": "Low",
            "description": "Debug mode enabled in production code"
        }
    ]
    
    # Scan each file for security patterns
    for file in python_files:
        file_content = file.content
        file_lines = file_content.splitlines()
        
        for pattern_info in security_patterns:
            pattern = pattern_info["pattern"]
            
            # Use the codebase search functionality
            matches = file.search(pattern)
            
            for match in matches:
                line_number = match.line
                line_content = file_lines[line_number - 1] if line_number <= len(file_lines) else ""
                
                security_issues.append({
                    "file": file.path,
                    "line": line_number,
                    "content": line_content.strip(),
                    "issue_type": pattern_info["name"],
                    "severity": pattern_info["severity"],
                    "description": pattern_info["description"]
                })
    
    return security_issues


@function('generate-documentation')
def generate_documentation(codebase: Codebase, output_dir: str = "./docs") -> Dict:
    """Generate documentation for a codebase.
    
    This function analyzes a codebase and generates Markdown documentation
    for its modules, classes, and functions.
    
    Args:
        codebase: The Codebase instance to document.
        output_dir: Directory to save the generated documentation.
        
    Returns:
        Dictionary containing documentation generation results.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    # Track documentation statistics
    stats = {
        "files_documented": 0,
        "classes_documented": 0,
        "functions_documented": 0,
        "total_files": len(python_files)
    }
    
    # Generate documentation for each file
    for file in python_files:
        # Create a Markdown file for this module
        module_path = file.path
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        doc_path = os.path.join(output_dir, f"{module_name}.md")
        
        with open(doc_path, "w") as doc_file:
            # Write module header
            doc_file.write(f"# Module: {module_name}\n\n")
            
            # Write module docstring if available
            if file.docstring:
                doc_file.write(f"{file.docstring}\n\n")
            
            # Document classes
            classes = file.get_classes()
            if classes:
                doc_file.write("## Classes\n\n")
                
                for cls in classes:
                    doc_file.write(f"### {cls.name}\n\n")
                    
                    if cls.docstring:
                        doc_file.write(f"{cls.docstring}\n\n")
                    
                    # Document methods
                    methods = cls.get_methods()
                    if methods:
                        for method in methods:
                            doc_file.write(f"#### {method.name}\n\n")
                            
                            if method.docstring:
                                doc_file.write(f"{method.docstring}\n\n")
                            
                            # Document parameters
                            params = method.parameters
                            if params:
                                doc_file.write("**Parameters:**\n\n")
                                for param in params:
                                    if param.name != "self":
                                        doc_file.write(f"- `{param.name}`")
                                        if param.type_annotation:
                                            doc_file.write(f" ({param.type_annotation})")
                                        doc_file.write("\n")
                                doc_file.write("\n")
                            
                            # Document return type
                            if method.return_type:
                                doc_file.write(f"**Returns:** {method.return_type}\n\n")
                    
                    stats["classes_documented"] += 1
            
            # Document functions
            functions = file.get_functions()
            if functions:
                doc_file.write("## Functions\n\n")
                
                for func in functions:
                    doc_file.write(f"### {func.name}\n\n")
                    
                    if func.docstring:
                        doc_file.write(f"{func.docstring}\n\n")
                    
                    # Document parameters
                    params = func.parameters
                    if params:
                        doc_file.write("**Parameters:**\n\n")
                        for param in params:
                            doc_file.write(f"- `{param.name}`")
                            if param.type_annotation:
                                doc_file.write(f" ({param.type_annotation})")
                            doc_file.write("\n")
                        doc_file.write("\n")
                    
                    # Document return type
                    if func.return_type:
                        doc_file.write(f"**Returns:** {func.return_type}\n\n")
                    
                    stats["functions_documented"] += 1
        
        stats["files_documented"] += 1
    
    # Generate index file
    with open(os.path.join(output_dir, "index.md"), "w") as index_file:
        index_file.write("# API Documentation\n\n")
        index_file.write("## Modules\n\n")
        
        for file in python_files:
            module_name = os.path.splitext(os.path.basename(file.path))[0]
            index_file.write(f"- [{module_name}](./{module_name}.md)\n")
    
    return stats


def simulate_function_run(function_name: str, repo_path: str) -> None:
    """Simulate running a function on a local repository.

    Args:
        function_name: Name of the function to run.
        repo_path: Path to the local repository.
    """
    print(f"Simulating function: {function_name}")
    print(f"Repository: {repo_path}")
    
    # Initialize the Codebase
    codebase = Codebase(repo_path)
    
    # Run the appropriate function
    if function_name == "analyze-code":
        result = analyze_code(codebase)
        
        print("\nAnalysis results:")
        print(f"- Total files: {result['total_files']}")
        print(f"- Python files: {result['python_files']}")
        print(f"- TypeScript files: {result['typescript_files']}")
        print(f"- Total lines of code: {result['total_loc']:,}")
        print(f"- Python functions: {result['python_functions']}")
        print(f"- Python classes: {result['python_classes']}")
        print(f"- Average function length: {result['avg_function_loc']:.1f} lines")
        print(f"- Functions with docstrings: {result['functions_with_docs']} ({result['doc_percentage']:.1f}%)")
        
    elif function_name == "find-security-issues":
        issues = find_security_issues(codebase)
        
        print(f"\nFound {len(issues)} potential security issues:")
        for i, issue in enumerate(issues, 1):
            print(f"\n{i}. {issue['issue_type']} ({issue['severity']})")
            print(f"   File: {issue['file']}, Line: {issue['line']}")
            print(f"   Description: {issue['description']}")
            print(f"   Code: {issue['content']}")
        
    elif function_name == "generate-documentation":
        output_dir = "./docs"
        stats = generate_documentation(codebase, output_dir)
        
        print("\nDocumentation generation results:")
        print(f"- Files documented: {stats['files_documented']} of {stats['total_files']}")
        print(f"- Classes documented: {stats['classes_documented']}")
        print(f"- Functions documented: {stats['functions_documented']}")
        print(f"- Documentation saved to: {os.path.abspath(output_dir)}")
        
    else:
        print(f"Unknown function: {function_name}")


def main():
    """Main function to run the example."""
    if len(sys.argv) < 3:
        print("Usage: python basic_function.py <function_name> <repo_path>")
        print("  function_name: Name of the function to run (analyze-code, find-security-issues, generate-documentation)")
        print("  repo_path: Path to the local repository")
        sys.exit(1)
    
    function_name = sys.argv[1]
    repo_path = sys.argv[2]
    
    try:
        simulate_function_run(function_name, repo_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

