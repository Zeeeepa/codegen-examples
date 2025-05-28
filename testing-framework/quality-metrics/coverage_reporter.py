"""
Code coverage reporting and analysis tools.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import coverage
from datetime import datetime
import subprocess
import os


class CoverageReporter:
    """Comprehensive code coverage reporting and analysis."""
    
    def __init__(self, source_dirs: List[str] = None, omit_patterns: List[str] = None):
        """Initialize coverage reporter."""
        self.source_dirs = source_dirs or ['.']
        self.omit_patterns = omit_patterns or [
            '*/tests/*',
            '*/test_*',
            '*/__pycache__/*',
            '*/venv/*',
            '*/env/*',
            'setup.py',
            'conftest.py'
        ]
        self.cov = coverage.Coverage(
            source=self.source_dirs,
            omit=self.omit_patterns
        )
    
    def start_coverage(self) -> None:
        """Start coverage measurement."""
        self.cov.start()
    
    def stop_coverage(self) -> None:
        """Stop coverage measurement."""
        self.cov.stop()
        self.cov.save()
    
    def generate_reports(self, output_dir: str = "reports/coverage") -> Dict[str, str]:
        """Generate all coverage report formats."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        reports = {}
        
        # HTML report
        html_dir = os.path.join(output_dir, "html")
        self.cov.html_report(directory=html_dir)
        reports['html'] = html_dir
        
        # XML report
        xml_file = os.path.join(output_dir, "coverage.xml")
        self.cov.xml_report(outfile=xml_file)
        reports['xml'] = xml_file
        
        # JSON report
        json_file = os.path.join(output_dir, "coverage.json")
        self.cov.json_report(outfile=json_file)
        reports['json'] = json_file
        
        # Terminal report
        terminal_file = os.path.join(output_dir, "coverage.txt")
        with open(terminal_file, 'w') as f:
            self.cov.report(file=f)
        reports['terminal'] = terminal_file
        
        return reports
    
    def get_coverage_data(self) -> Dict:
        """Get detailed coverage data."""
        data = self.cov.get_data()
        
        coverage_info = {
            'files': {},
            'summary': {
                'total_statements': 0,
                'covered_statements': 0,
                'missing_statements': 0,
                'coverage_percentage': 0.0
            }
        }
        
        for filename in data.measured_files():
            analysis = self.cov.analysis2(filename)
            
            file_info = {
                'filename': filename,
                'statements': len(analysis.statements),
                'missing': len(analysis.missing),
                'covered': len(analysis.statements) - len(analysis.missing),
                'coverage_percentage': 0.0 if not analysis.statements else 
                    (len(analysis.statements) - len(analysis.missing)) / len(analysis.statements) * 100,
                'missing_lines': list(analysis.missing),
                'excluded_lines': list(analysis.excluded)
            }
            
            coverage_info['files'][filename] = file_info
            
            # Update summary
            coverage_info['summary']['total_statements'] += file_info['statements']
            coverage_info['summary']['covered_statements'] += file_info['covered']
            coverage_info['summary']['missing_statements'] += file_info['missing']
        
        # Calculate overall coverage percentage
        total = coverage_info['summary']['total_statements']
        if total > 0:
            coverage_info['summary']['coverage_percentage'] = (
                coverage_info['summary']['covered_statements'] / total * 100
            )
        
        return coverage_info
    
    def analyze_coverage_trends(self, historical_data: List[Dict]) -> Dict:
        """Analyze coverage trends over time."""
        if not historical_data:
            return {'trend': 'no_data', 'change': 0.0}
        
        # Sort by timestamp
        sorted_data = sorted(historical_data, key=lambda x: x.get('timestamp', ''))
        
        if len(sorted_data) < 2:
            return {'trend': 'insufficient_data', 'change': 0.0}
        
        latest = sorted_data[-1]['coverage_percentage']
        previous = sorted_data[-2]['coverage_percentage']
        
        change = latest - previous
        
        if change > 1.0:
            trend = 'improving'
        elif change < -1.0:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change': change,
            'latest_coverage': latest,
            'previous_coverage': previous,
            'data_points': len(sorted_data)
        }
    
    def identify_coverage_gaps(self, threshold: float = 80.0) -> List[Dict]:
        """Identify files with coverage below threshold."""
        coverage_data = self.get_coverage_data()
        gaps = []
        
        for filename, file_info in coverage_data['files'].items():
            if file_info['coverage_percentage'] < threshold:
                gaps.append({
                    'filename': filename,
                    'coverage_percentage': file_info['coverage_percentage'],
                    'missing_lines': file_info['missing_lines'],
                    'statements': file_info['statements'],
                    'priority': self._calculate_priority(file_info)
                })
        
        # Sort by priority (highest first)
        gaps.sort(key=lambda x: x['priority'], reverse=True)
        return gaps
    
    def _calculate_priority(self, file_info: Dict) -> float:
        """Calculate priority for coverage improvement."""
        # Priority based on file size and coverage gap
        statements = file_info['statements']
        coverage_gap = 100 - file_info['coverage_percentage']
        
        # Larger files with bigger gaps get higher priority
        priority = statements * (coverage_gap / 100)
        return priority
    
    def generate_coverage_badge(self, coverage_percentage: float) -> str:
        """Generate coverage badge SVG."""
        if coverage_percentage >= 90:
            color = "brightgreen"
        elif coverage_percentage >= 80:
            color = "green"
        elif coverage_percentage >= 70:
            color = "yellowgreen"
        elif coverage_percentage >= 60:
            color = "yellow"
        elif coverage_percentage >= 50:
            color = "orange"
        else:
            color = "red"
        
        badge_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="104" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="a">
        <rect width="104" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#a)">
        <path fill="#555" d="M0 0h63v20H0z"/>
        <path fill="{color}" d="M63 0h41v20H63z"/>
        <path fill="url(#b)" d="M0 0h104v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
        <text x="31.5" y="15" fill="#010101" fill-opacity=".3">coverage</text>
        <text x="31.5" y="14">coverage</text>
        <text x="82.5" y="15" fill="#010101" fill-opacity=".3">{coverage_percentage:.1f}%</text>
        <text x="82.5" y="14">{coverage_percentage:.1f}%</text>
    </g>
</svg>'''
        return badge_svg


class CoverageAnalyzer:
    """Advanced coverage analysis and reporting."""
    
    def __init__(self, coverage_file: str = ".coverage"):
        """Initialize coverage analyzer."""
        self.coverage_file = coverage_file
    
    def parse_coverage_xml(self, xml_file: str) -> Dict:
        """Parse coverage XML report."""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        coverage_data = {
            'timestamp': root.get('timestamp'),
            'version': root.get('version'),
            'packages': [],
            'summary': {}
        }
        
        # Parse packages
        for package in root.findall('.//package'):
            package_data = {
                'name': package.get('name'),
                'line_rate': float(package.get('line-rate', 0)),
                'branch_rate': float(package.get('branch-rate', 0)),
                'complexity': float(package.get('complexity', 0)),
                'classes': []
            }
            
            # Parse classes
            for cls in package.findall('.//class'):
                class_data = {
                    'name': cls.get('name'),
                    'filename': cls.get('filename'),
                    'line_rate': float(cls.get('line-rate', 0)),
                    'branch_rate': float(cls.get('branch-rate', 0)),
                    'complexity': float(cls.get('complexity', 0))
                }
                package_data['classes'].append(class_data)
            
            coverage_data['packages'].append(package_data)
        
        # Calculate summary
        if coverage_data['packages']:
            total_line_rate = sum(p['line_rate'] for p in coverage_data['packages'])
            total_branch_rate = sum(p['branch_rate'] for p in coverage_data['packages'])
            
            coverage_data['summary'] = {
                'line_coverage': total_line_rate / len(coverage_data['packages']) * 100,
                'branch_coverage': total_branch_rate / len(coverage_data['packages']) * 100,
                'total_packages': len(coverage_data['packages']),
                'total_classes': sum(len(p['classes']) for p in coverage_data['packages'])
            }
        
        return coverage_data
    
    def compare_coverage_reports(self, current_file: str, previous_file: str) -> Dict:
        """Compare two coverage reports."""
        current = self.parse_coverage_xml(current_file)
        previous = self.parse_coverage_xml(previous_file)
        
        comparison = {
            'current': current['summary'],
            'previous': previous['summary'],
            'changes': {},
            'file_changes': []
        }
        
        # Calculate overall changes
        comparison['changes'] = {
            'line_coverage_change': current['summary']['line_coverage'] - previous['summary']['line_coverage'],
            'branch_coverage_change': current['summary']['branch_coverage'] - previous['summary']['branch_coverage']
        }
        
        # Compare individual files
        current_files = {cls['filename']: cls for pkg in current['packages'] for cls in pkg['classes']}
        previous_files = {cls['filename']: cls for pkg in previous['packages'] for cls in pkg['classes']}
        
        for filename in set(current_files.keys()) | set(previous_files.keys()):
            current_cls = current_files.get(filename, {'line_rate': 0, 'branch_rate': 0})
            previous_cls = previous_files.get(filename, {'line_rate': 0, 'branch_rate': 0})
            
            change = {
                'filename': filename,
                'line_coverage_change': (current_cls['line_rate'] - previous_cls['line_rate']) * 100,
                'branch_coverage_change': (current_cls['branch_rate'] - previous_cls['branch_rate']) * 100,
                'status': 'new' if filename not in previous_files else 
                         'removed' if filename not in current_files else 'modified'
            }
            
            comparison['file_changes'].append(change)
        
        return comparison
    
    def generate_coverage_summary(self, coverage_data: Dict) -> str:
        """Generate human-readable coverage summary."""
        summary = coverage_data.get('summary', {})
        
        report = f"""
Coverage Summary Report
======================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Overall Coverage:
- Line Coverage: {summary.get('coverage_percentage', 0):.2f}%
- Total Statements: {summary.get('total_statements', 0)}
- Covered Statements: {summary.get('covered_statements', 0)}
- Missing Statements: {summary.get('missing_statements', 0)}

Files Analyzed: {len(coverage_data.get('files', {}))}
"""
        
        # Add file breakdown
        files = coverage_data.get('files', {})
        if files:
            report += "\nFile Coverage Breakdown:\n"
            report += "-" * 50 + "\n"
            
            for filename, file_info in sorted(files.items(), 
                                            key=lambda x: x[1]['coverage_percentage'], 
                                            reverse=True):
                report += f"{filename:<40} {file_info['coverage_percentage']:>6.1f}%\n"
        
        return report


class CoverageIntegration:
    """Integration with CI/CD and external tools."""
    
    @staticmethod
    def run_pytest_with_coverage(test_paths: List[str] = None, 
                                output_dir: str = "reports/coverage") -> Tuple[int, str]:
        """Run pytest with coverage collection."""
        test_paths = test_paths or ["tests/"]
        
        cmd = [
            "python", "-m", "pytest",
            "--cov=.",
            f"--cov-report=html:{output_dir}/html",
            f"--cov-report=xml:{output_dir}/coverage.xml",
            f"--cov-report=json:{output_dir}/coverage.json",
            "--cov-report=term-missing"
        ] + test_paths
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return 1, "Coverage collection timed out"
        except Exception as e:
            return 1, f"Coverage collection failed: {str(e)}"
    
    @staticmethod
    def upload_to_codecov(coverage_file: str, token: str = None) -> bool:
        """Upload coverage to Codecov."""
        cmd = ["codecov", "-f", coverage_file]
        
        if token:
            cmd.extend(["-t", token])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False
    
    @staticmethod
    def check_coverage_threshold(coverage_percentage: float, threshold: float = 80.0) -> bool:
        """Check if coverage meets threshold."""
        return coverage_percentage >= threshold


# Example usage and testing
if __name__ == "__main__":
    # Create coverage reporter
    reporter = CoverageReporter()
    
    # Example: Start coverage, run some code, stop coverage
    reporter.start_coverage()
    
    # Simulate some code execution
    def example_function(x, y):
        if x > 0:
            return x + y
        else:
            return y
    
    example_function(1, 2)
    example_function(-1, 2)
    
    reporter.stop_coverage()
    
    # Generate reports
    reports = reporter.generate_reports()
    print(f"Generated reports: {list(reports.keys())}")
    
    # Get coverage data
    coverage_data = reporter.get_coverage_data()
    print(f"Overall coverage: {coverage_data['summary']['coverage_percentage']:.2f}%")
    
    # Generate badge
    badge = reporter.generate_coverage_badge(coverage_data['summary']['coverage_percentage'])
    with open("reports/coverage/badge.svg", "w") as f:
        f.write(badge)
    
    print("Coverage analysis completed!")

