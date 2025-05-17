"""
A Modal application that uses Codegen to analyze GitHub repositories.
"""

import os
import tempfile
import subprocess
from typing import Dict, List, Optional

import modal
from modal import web

# Define the Modal app
app = modal.App("code-analyzer")

# Create an image with Python dependencies
image = modal.Image.debian_slim().pip_install(
    [
        "codegen>=0.1.0",
        "gitpython>=3.1.30",
        "pydantic>=2.0.0",
    ]
)

# Add environment variables for Codegen
image = image.env({
    "CODEGEN_API_KEY": "{{CODEGEN_API_KEY}}",  # Replace with your actual API key or use Modal secrets
})

# Define a function to clone a GitHub repository
@app.function(image=image)
def clone_repo(repo_url: str, branch: Optional[str] = None) -> str:
    """Clone a GitHub repository to a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        clone_cmd = ["git", "clone"]
        
        if branch:
            clone_cmd.extend(["--branch", branch])
            
        clone_cmd.extend([repo_url, temp_dir])
        
        subprocess.run(clone_cmd, check=True)
        return temp_dir

# Define a function to analyze a repository using Codegen
@app.function(image=image)
def analyze_repo(repo_path: str) -> Dict:
    """Analyze a repository using Codegen."""
    import codegen
    
    # Initialize Codegen with the repository path
    codebase = codegen.Codebase(repo_path)
    
    # Get basic repository statistics
    stats = {
        "num_files": len(codebase.files),
        "num_functions": len(codebase.functions),
        "num_classes": len(codebase.classes),
        "languages": list(set(f.language for f in codebase.files if f.language)),
        "file_extensions": list(set(os.path.splitext(f.path)[1] for f in codebase.files if os.path.splitext(f.path)[1])),
    }
    
    # Get the most complex functions
    complex_functions = []
    for func in sorted(codebase.functions, key=lambda f: f.complexity or 0, reverse=True)[:5]:
        complex_functions.append({
            "name": func.name,
            "path": func.filepath,
            "complexity": func.complexity,
            "line_count": func.end_line - func.start_line if func.end_line and func.start_line else None,
        })
    
    # Get the most complex classes
    complex_classes = []
    for cls in sorted(codebase.classes, key=lambda c: len(c.methods), reverse=True)[:5]:
        complex_classes.append({
            "name": cls.name,
            "path": cls.filepath,
            "method_count": len(cls.methods),
            "line_count": cls.end_line - cls.start_line if cls.end_line and cls.start_line else None,
        })
    
    return {
        "stats": stats,
        "complex_functions": complex_functions,
        "complex_classes": complex_classes,
    }

# Define a web endpoint to analyze a GitHub repository
@app.function(image=image, keep_warm=1)
@modal.web_endpoint(method="POST")
def analyze_github_repo(repo_url: str, branch: Optional[str] = None) -> Dict:
    """Analyze a GitHub repository."""
    # Clone the repository
    repo_path = clone_repo.remote(repo_url, branch)
    
    # Analyze the repository
    analysis = analyze_repo.remote(repo_path)
    
    return {
        "repo_url": repo_url,
        "branch": branch,
        "analysis": analysis,
    }

if __name__ == "__main__":
    # This block is executed when running the script directly
    with app.run():
        # Example: Analyze the Modal repository
        result = analyze_github_repo.remote(
            repo_url="https://github.com/modal-labs/modal-client.git",
            branch="main"
        )
        print(f"Analysis result: {result}")

