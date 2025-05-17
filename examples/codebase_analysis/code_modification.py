#!/usr/bin/env python
"""
Code Modification Example

This script demonstrates how to use the Codegen SDK's Codebase class to modify
code in a repository, including adding new functions, updating existing code,
and refactoring.
"""

import os
import sys
import tempfile
from typing import Dict, List, Optional

from codegen import Codebase
from codegen.shared.enums.programming_language import ProgrammingLanguage


def create_sample_python_file() -> str:
    """Create a sample Python file for demonstration.

    Returns:
        Path to the created file.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="codegen_example_")
    
    # Create a sample Python file
    file_path = os.path.join(temp_dir, "sample.py")
    
    with open(file_path, "w") as f:
        f.write("""
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

class Calculator:
    def multiply(self, a, b):
        return a * b
""")
    
    return temp_dir


def add_new_function(codebase: Codebase, file_path: str) -> None:
    """Add a new function to a file.

    Args:
        codebase: Initialized Codebase instance.
        file_path: Path to the file to modify.
    """
    print(f"Adding new function to {file_path}")
    
    # Get the file
    file = codebase.get_file(file_path)
    
    # Add a new function
    file.add_function(
        name="divide",
        parameters=["a", "b"],
        body="""if b == 0:
    raise ValueError("Cannot divide by zero")
return a / b""",
        docstring="""Divide two numbers.

Args:
    a: Numerator
    b: Denominator

Returns:
    Result of division

Raises:
    ValueError: If denominator is zero
"""
    )
    
    # Save the changes
    file.save()
    
    print("Function added successfully")
    print("\nUpdated file content:")
    print(file.content)


def add_method_to_class(codebase: Codebase, file_path: str) -> None:
    """Add a new method to an existing class.

    Args:
        codebase: Initialized Codebase instance.
        file_path: Path to the file containing the class.
    """
    print(f"Adding new method to class in {file_path}")
    
    # Get the file
    file = codebase.get_file(file_path)
    
    # Get the Calculator class
    calculator_class = file.get_class("Calculator")
    
    # Add a new method to the class
    calculator_class.add_method(
        name="power",
        parameters=["self", "base", "exponent"],
        body="return base ** exponent",
        docstring="""Calculate power of a number.

Args:
    base: Base number
    exponent: Exponent

Returns:
    base raised to the power of exponent
"""
    )
    
    # Save the changes
    file.save()
    
    print("Method added successfully")
    print("\nUpdated class:")
    print(calculator_class.content)


def update_existing_function(codebase: Codebase, file_path: str) -> None:
    """Update an existing function.

    Args:
        codebase: Initialized Codebase instance.
        file_path: Path to the file containing the function.
    """
    print(f"Updating existing function in {file_path}")
    
    # Get the file
    file = codebase.get_file(file_path)
    
    # Get the add function
    add_function = file.get_function("add")
    
    # Update the function
    add_function.update(
        parameters=["a: float", "b: float"],
        return_type="float",
        body="return a + b",
        docstring="""Add two numbers and return the result.

Args:
    a: First number
    b: Second number

Returns:
    Sum of a and b
"""
    )
    
    # Save the changes
    file.save()
    
    print("Function updated successfully")
    print("\nUpdated function:")
    print(add_function.content)


def create_new_file(codebase: Codebase, directory: str) -> str:
    """Create a new file in the codebase.

    Args:
        codebase: Initialized Codebase instance.
        directory: Directory to create the file in.

    Returns:
        Path to the created file.
    """
    print(f"Creating new file in {directory}")
    
    # Define the file path
    file_path = os.path.join(directory, "utils.py")
    
    # Create a new file
    file = codebase.create_file(
        path=file_path,
        content="""\"\"\"Utility functions for calculations.\"\"\"

def square(x: float) -> float:
    \"\"\"Calculate the square of a number.
    
    Args:
        x: Number to square
        
    Returns:
        Square of x
    \"\"\"
    return x * x

def cube(x: float) -> float:
    \"\"\"Calculate the cube of a number.
    
    Args:
        x: Number to cube
        
    Returns:
        Cube of x
    \"\"\"
    return x * x * x
"""
    )
    
    print("File created successfully")
    print("\nNew file content:")
    print(file.content)
    
    return file_path


def refactor_code(codebase: Codebase, file_path: str, new_file_path: str) -> None:
    """Refactor code by moving a function to a new file.

    Args:
        codebase: Initialized Codebase instance.
        file_path: Path to the source file.
        new_file_path: Path to the destination file.
    """
    print(f"Refactoring code: Moving function from {file_path} to {new_file_path}")
    
    # Get the source file
    source_file = codebase.get_file(file_path)
    
    # Get the destination file
    dest_file = codebase.get_file(new_file_path)
    
    # Get the subtract function
    subtract_function = source_file.get_function("subtract")
    
    # Add the function to the destination file
    dest_file.add_function(
        name=subtract_function.name,
        parameters=[p.name for p in subtract_function.parameters],
        body=subtract_function.body.strip(),
        docstring="Subtract second number from first number."
    )
    
    # Remove the function from the source file
    source_file.remove_function("subtract")
    
    # Save the changes
    source_file.save()
    dest_file.save()
    
    print("Refactoring completed successfully")
    print("\nSource file after refactoring:")
    print(source_file.content)
    print("\nDestination file after refactoring:")
    print(dest_file.content)


def main():
    """Main function to run the example."""
    # Create a sample Python project
    temp_dir = create_sample_python_file()
    sample_file = os.path.join(temp_dir, "sample.py")
    
    try:
        print(f"Created sample project in {temp_dir}")
        
        # Initialize the Codebase
        codebase = Codebase(temp_dir)
        
        # Perform code modifications
        add_new_function(codebase, sample_file)
        add_method_to_class(codebase, sample_file)
        update_existing_function(codebase, sample_file)
        
        # Create a new file
        new_file_path = create_new_file(codebase, temp_dir)
        
        # Refactor code
        refactor_code(codebase, sample_file, new_file_path)
        
        print(f"\nAll modifications completed. Modified files are in {temp_dir}")
        print("You can examine the files to see the changes.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

