#!/usr/bin/env python
"""
Symbol Analysis Example

This script demonstrates how to use the Codegen SDK's Codebase class to analyze
symbols in a codebase, including finding usages, exploring dependencies, and
visualizing relationships.
"""

import os
import sys
import tempfile
from typing import Dict, List, Optional, Set, Tuple

from codegen import Codebase
from codegen.shared.enums.programming_language import ProgrammingLanguage


def create_sample_project() -> str:
    """Create a sample Python project for demonstration.

    Returns:
        Path to the created project directory.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="codegen_example_")
    
    # Create project structure
    os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "tests"), exist_ok=True)
    
    # Create main module file
    with open(os.path.join(temp_dir, "src", "calculator.py"), "w") as f:
        f.write("""\"\"\"Calculator module for basic arithmetic operations.\"\"\"

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    
    def __init__(self, initial_value=0):
        \"\"\"Initialize the calculator with an optional initial value.\"\"\"
        self.value = initial_value
    
    def add(self, x):
        \"\"\"Add a number to the current value.\"\"\"
        self.value += x
        return self.value
    
    def subtract(self, x):
        \"\"\"Subtract a number from the current value.\"\"\"
        self.value -= x
        return self.value
    
    def multiply(self, x):
        \"\"\"Multiply the current value by a number.\"\"\"
        self.value *= x
        return self.value
    
    def divide(self, x):
        \"\"\"Divide the current value by a number.\"\"\"
        if x == 0:
            raise ValueError("Cannot divide by zero")
        self.value /= x
        return self.value
    
    def clear(self):
        \"\"\"Reset the calculator to zero.\"\"\"
        self.value = 0
        return self.value


def create_calculator(initial_value=0):
    \"\"\"Factory function to create a calculator instance.\"\"\"
    return Calculator(initial_value)
""")
    
    # Create utility module
    with open(os.path.join(temp_dir, "src", "utils.py"), "w") as f:
        f.write("""\"\"\"Utility functions for the calculator.\"\"\"

from .calculator import Calculator

def perform_operations(operations):
    \"\"\"Perform a sequence of operations using a calculator.
    
    Args:
        operations: List of (operation, value) tuples
        
    Returns:
        Final calculator value
    \"\"\"
    calc = Calculator()
    
    for op, value in operations:
        if op == 'add':
            calc.add(value)
        elif op == 'subtract':
            calc.subtract(value)
        elif op == 'multiply':
            calc.multiply(value)
        elif op == 'divide':
            calc.divide(value)
    
    return calc.value


def calculate_expression(expression):
    \"\"\"Calculate the result of a simple expression.
    
    Args:
        expression: String expression like "5 + 3 * 2"
        
    Returns:
        Result of the expression
    \"\"\"
    # This is a simplified implementation
    # In a real application, you would use a proper parser
    tokens = expression.split()
    calc = Calculator(float(tokens[0]))
    
    i = 1
    while i < len(tokens):
        op = tokens[i]
        value = float(tokens[i+1])
        
        if op == '+':
            calc.add(value)
        elif op == '-':
            calc.subtract(value)
        elif op == '*':
            calc.multiply(value)
        elif op == '/':
            calc.divide(value)
        
        i += 2
    
    return calc.value
""")
    
    # Create main application file
    with open(os.path.join(temp_dir, "src", "app.py"), "w") as f:
        f.write("""\"\"\"Main application module.\"\"\"

from .calculator import Calculator, create_calculator
from .utils import perform_operations, calculate_expression

def run_calculator_demo():
    \"\"\"Run a demonstration of the calculator functionality.\"\"\"
    # Create a calculator
    calc = create_calculator(10)
    print(f"Initial value: {calc.value}")
    
    # Perform some operations
    calc.add(5)
    print(f"After adding 5: {calc.value}")
    
    calc.multiply(2)
    print(f"After multiplying by 2: {calc.value}")
    
    calc.subtract(7)
    print(f"After subtracting 7: {calc.value}")
    
    calc.divide(2)
    print(f"After dividing by 2: {calc.value}")
    
    # Use utility functions
    operations = [
        ('add', 10),
        ('multiply', 2),
        ('subtract', 5),
        ('divide', 3)
    ]
    result = perform_operations(operations)
    print(f"Result of operations: {result}")
    
    # Calculate an expression
    expr_result = calculate_expression("5 + 10 * 2 - 7 / 2")
    print(f"Expression result: {expr_result}")


if __name__ == "__main__":
    run_calculator_demo()
""")
    
    # Create a test file
    with open(os.path.join(temp_dir, "tests", "test_calculator.py"), "w") as f:
        f.write("""\"\"\"Tests for the calculator module.\"\"\"

import unittest
from src.calculator import Calculator, create_calculator

class TestCalculator(unittest.TestCase):
    \"\"\"Test cases for the Calculator class.\"\"\"
    
    def setUp(self):
        \"\"\"Set up a calculator instance for each test.\"\"\"
        self.calc = Calculator(10)
    
    def test_add(self):
        \"\"\"Test the add method.\"\"\"
        self.assertEqual(self.calc.add(5), 15)
    
    def test_subtract(self):
        \"\"\"Test the subtract method.\"\"\"
        self.assertEqual(self.calc.subtract(5), 5)
    
    def test_multiply(self):
        \"\"\"Test the multiply method.\"\"\"
        self.assertEqual(self.calc.multiply(2), 20)
    
    def test_divide(self):
        \"\"\"Test the divide method.\"\"\"
        self.assertEqual(self.calc.divide(2), 5)
    
    def test_divide_by_zero(self):
        \"\"\"Test division by zero raises an error.\"\"\"
        with self.assertRaises(ValueError):
            self.calc.divide(0)
    
    def test_clear(self):
        \"\"\"Test the clear method.\"\"\"
        self.calc.add(5)  # value is now 15
        self.assertEqual(self.calc.clear(), 0)
    
    def test_factory_function(self):
        \"\"\"Test the create_calculator factory function.\"\"\"
        calc = create_calculator(5)
        self.assertEqual(calc.value, 5)
        self.assertIsInstance(calc, Calculator)


if __name__ == "__main__":
    unittest.main()
""")
    
    return temp_dir


def find_symbol_usages(codebase: Codebase, symbol_name: str) -> List[Dict]:
    """Find all usages of a symbol in the codebase.

    Args:
        codebase: Initialized Codebase instance.
        symbol_name: Name of the symbol to find usages for.

    Returns:
        List of dictionaries containing usage information.
    """
    print(f"Finding usages of symbol: {symbol_name}")
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    usages = []
    
    for file in python_files:
        # Find the symbol in this file
        symbols = [s for s in file.get_symbols() if s.name == symbol_name]
        
        if symbols:
            # If the symbol is defined in this file, find its usages
            for symbol in symbols:
                refs = symbol.get_references()
                for ref in refs:
                    usages.append({
                        "file": ref.file.path,
                        "line": ref.line,
                        "column": ref.column,
                        "context": ref.context
                    })
    
    return usages


def analyze_dependencies(codebase: Codebase) -> Dict[str, Set[str]]:
    """Analyze module dependencies in the codebase.

    Args:
        codebase: Initialized Codebase instance.

    Returns:
        Dictionary mapping module names to sets of imported modules.
    """
    print("Analyzing module dependencies")
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    dependencies = {}
    
    for file in python_files:
        # Get the module name (convert path to module notation)
        module_path = os.path.splitext(file.path)[0]
        module_name = module_path.replace("/", ".").replace("\\", ".")
        
        # Get all imports in this file
        imports = file.get_imports()
        
        # Extract imported modules
        imported_modules = set()
        for imp in imports:
            imported_modules.add(imp.module)
        
        dependencies[module_name] = imported_modules
    
    return dependencies


def analyze_class_hierarchy(codebase: Codebase) -> Dict[str, List[str]]:
    """Analyze class inheritance hierarchy in the codebase.

    Args:
        codebase: Initialized Codebase instance.

    Returns:
        Dictionary mapping class names to lists of parent class names.
    """
    print("Analyzing class hierarchy")
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    hierarchy = {}
    
    for file in python_files:
        # Get all classes in this file
        classes = file.get_classes()
        
        for cls in classes:
            # Get parent classes
            parent_classes = [base.name for base in cls.bases if base.name != "object"]
            hierarchy[cls.name] = parent_classes
    
    return hierarchy


def analyze_function_complexity(codebase: Codebase) -> Dict[str, Dict]:
    """Analyze function complexity in the codebase.

    Args:
        codebase: Initialized Codebase instance.

    Returns:
        Dictionary mapping function names to complexity metrics.
    """
    print("Analyzing function complexity")
    
    # Get all Python files
    python_files = codebase.get_files(extension=".py")
    
    complexity = {}
    
    for file in python_files:
        # Get all functions in this file
        functions = file.get_functions()
        
        for func in functions:
            # Calculate complexity metrics
            lines_of_code = len(func.body.splitlines())
            parameter_count = len(func.parameters)
            has_docstring = bool(func.docstring)
            
            complexity[func.name] = {
                "file": file.path,
                "lines_of_code": lines_of_code,
                "parameter_count": parameter_count,
                "has_docstring": has_docstring,
                # In a real application, you might calculate cyclomatic complexity
                # and other metrics here
            }
    
    return complexity


def visualize_dependencies(dependencies: Dict[str, Set[str]]) -> None:
    """Visualize module dependencies.

    Args:
        dependencies: Dictionary mapping module names to sets of imported modules.
    """
    print("\nModule Dependencies:")
    
    for module, imports in dependencies.items():
        print(f"  {module}:")
        for imp in sorted(imports):
            print(f"    → {imp}")


def visualize_class_hierarchy(hierarchy: Dict[str, List[str]]) -> None:
    """Visualize class hierarchy.

    Args:
        hierarchy: Dictionary mapping class names to lists of parent class names.
    """
    print("\nClass Hierarchy:")
    
    for cls, parents in hierarchy.items():
        if parents:
            parent_str = ", ".join(parents)
            print(f"  {cls} → inherits from → {parent_str}")
        else:
            print(f"  {cls} (no inheritance)")


def visualize_function_complexity(complexity: Dict[str, Dict]) -> None:
    """Visualize function complexity.

    Args:
        complexity: Dictionary mapping function names to complexity metrics.
    """
    print("\nFunction Complexity:")
    
    # Sort functions by lines of code
    sorted_funcs = sorted(complexity.items(), key=lambda x: x[1]["lines_of_code"], reverse=True)
    
    for func_name, metrics in sorted_funcs:
        doc_status = "✓" if metrics["has_docstring"] else "✗"
        print(f"  {func_name}:")
        print(f"    File: {metrics['file']}")
        print(f"    Lines of code: {metrics['lines_of_code']}")
        print(f"    Parameters: {metrics['parameter_count']}")
        print(f"    Has docstring: {doc_status}")


def main():
    """Main function to run the example."""
    # Create a sample Python project
    project_dir = create_sample_project()
    
    try:
        print(f"Created sample project in {project_dir}")
        
        # Initialize the Codebase
        codebase = Codebase(project_dir)
        
        # Find usages of the Calculator class
        calculator_usages = find_symbol_usages(codebase, "Calculator")
        print(f"\nFound {len(calculator_usages)} usages of Calculator:")
        for usage in calculator_usages:
            print(f"  {usage['file']}:{usage['line']}:{usage['column']}")
        
        # Analyze module dependencies
        dependencies = analyze_dependencies(codebase)
        visualize_dependencies(dependencies)
        
        # Analyze class hierarchy
        hierarchy = analyze_class_hierarchy(codebase)
        visualize_class_hierarchy(hierarchy)
        
        # Analyze function complexity
        complexity = analyze_function_complexity(codebase)
        visualize_function_complexity(complexity)
        
        print(f"\nAnalysis completed. Sample project is in {project_dir}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

