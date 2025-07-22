#!/usr/bin/env python3
"""
Test Report Generator
====================

Generates comprehensive test reports from multiple test artifacts,
combining results from different test suites into a unified HTML report.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import re


class TestReportGenerator:
    """Generates comprehensive test reports from multiple sources."""
    
    def __init__(self, artifacts_dir: Path, output_path: Path):
        self.artifacts_dir = artifacts_dir
        self.output_path = output_path
        self.test_results = {}
        self.coverage_data = {}
        self.performance_data = {}
        
    def collect_junit_results(self) -> Dict[str, Any]:
        """Collect results from JUnit XML files."""
        results = {}
        
        for xml_file in self.artifacts_dir.glob("**/*results*.xml"):
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                suite_name = xml_file.stem.replace('-results', '').replace('_', ' ').title()
                
                # Extract test suite information
                test_count = int(root.get('tests', 0))
                failure_count = int(root.get('failures', 0))
                error_count = int(root.get('errors', 0))
                skip_count = int(root.get('skipped', 0))
                time_taken = float(root.get('time', 0))
                
                results[suite_name] = {
                    'total': test_count,
                    'passed': test_count - failure_count - error_count - skip_count,
                    'failures': failure_count,
                    'errors': error_count,
                    'skipped': skip_count,
                    'duration': time_taken,
                    'success_rate': ((test_count - failure_count - error_count) / test_count * 100) if test_count > 0 else 0,
                    'status': '✅ PASS' if failure_count == 0 and error_count == 0 else '❌ FAIL'
                }
                
                # Extract individual test cases
                test_cases = []
                for testcase in root.findall('.//testcase'):
                    case_name = testcase.get('name', '')
                    class_name = testcase.get('classname', '')
                    case_time = float(testcase.get('time', 0))
                    
                    status = 'passed'
                    message = ''
                    
                    if testcase.find('failure') is not None:
                        status = 'failed'
                        failure_elem = testcase.find('failure')
                        message = failure_elem.get('message', '') if failure_elem is not None else ''
                    elif testcase.find('error') is not None:
                        status = 'error'
                        error_elem = testcase.find('error')
                        message = error_elem.get('message', '') if error_elem is not None else ''
                    elif testcase.find('skipped') is not None:
                        status = 'skipped'
                        skipped_elem = testcase.find('skipped')
                        message = skipped_elem.get('message', '') if skipped_elem is not None else ''
                    
                    test_cases.append({
                        'name': case_name,
                        'class': class_name,
                        'duration': case_time,
                        'status': status,
                        'message': message
                    })
                
                results[suite_name]['test_cases'] = test_cases
                
            except Exception as e:
                print(f"Warning: Could not parse {xml_file}: {e}")
                
        return results
    
    def collect_coverage_data(self) -> Dict[str, Any]:
        """Collect coverage data from XML files."""
        coverage_data = {}
        
        for coverage_file in self.artifacts_dir.glob("**/*coverage*.xml"):
            try:
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                # Extract overall coverage
                coverage_elem = root.find('.//coverage')
                if coverage_elem is not None:
                    line_rate = float(coverage_elem.get('line-rate', 0)) * 100
                    branch_rate = float(coverage_elem.get('branch-rate', 0)) * 100
                    
                    coverage_data['overall'] = {
                        'line_coverage': line_rate,
                        'branch_coverage': branch_rate,
                        'combined_coverage': (line_rate + branch_rate) / 2
                    }
                
                # Extract per-package coverage
                packages = {}
                for package in root.findall('.//package'):
                    pkg_name = package.get('name', 'unknown')
                    pkg_line_rate = float(package.get('line-rate', 0)) * 100
                    pkg_branch_rate = float(package.get('branch-rate', 0)) * 100
                    
                    packages[pkg_name] = {
                        'line_coverage': pkg_line_rate,
                        'branch_coverage': pkg_branch_rate,
                        'combined_coverage': (pkg_line_rate + pkg_branch_rate) / 2
                    }
                
                coverage_data['packages'] = packages
                
            except Exception as e:
                print(f"Warning: Could not parse coverage file {coverage_file}: {e}")
                
        return coverage_data
    
    def collect_performance_data(self) -> Dict[str, Any]:
        """Collect performance benchmark data."""
        performance_data = {}
        
        for perf_file in self.artifacts_dir.glob("**/*benchmark*.json"):
            try:
                with open(perf_file, 'r') as f:
                    data = json.load(f)
                
                if 'benchmarks' in data:
                    benchmarks = []
                    for benchmark in data['benchmarks']:
                        benchmarks.append({
                            'name': benchmark.get('name', ''),
                            'mean': benchmark.get('stats', {}).get('mean', 0),
                            'stddev': benchmark.get('stats', {}).get('stddev', 0),
                            'min': benchmark.get('stats', {}).get('min', 0),
                            'max': benchmark.get('stats', {}).get('max', 0),
                            'rounds': benchmark.get('stats', {}).get('rounds', 0)
                        })
                    
                    performance_data['benchmarks'] = benchmarks
                    
            except Exception as e:
                print(f"Warning: Could not parse performance file {perf_file}: {e}")
                
        return performance_data
    
    def generate_html_report(self, include_coverage: bool = True, include_performance: bool = True) -> str:
        """Generate comprehensive HTML report."""
        
        # Collect all data
        test_results = self.collect_junit_results()
        coverage_data = self.collect_coverage_data() if include_coverage else {}
        performance_data = self.collect_performance_data() if include_performance else {}
        
        # Calculate summary statistics
        total_tests = sum(suite['total'] for suite in test_results.values())
        total_passed = sum(suite['passed'] for suite in test_results.values())
        total_failed = sum(suite['failures'] + suite['errors'] for suite in test_results.values())
        total_skipped = sum(suite['skipped'] for suite in test_results.values())
        total_duration = sum(suite['duration'] for suite in test_results.values())
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        overall_coverage = coverage_data.get('overall', {}).get('combined_coverage', 0)
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DSL to PNG Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card .number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .summary-card .label {{
            color: #666;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #ffc107; }}
        .coverage {{ color: #17a2b8; }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .test-suite {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .test-suite h3 {{
            margin: 0 0 15px 0;
            color: #333;
        }}
        .test-suite-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat .value {{
            font-size: 1.5em;
            font-weight: bold;
        }}
        .stat .label {{
            font-size: 0.9em;
            color: #666;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }}
        .test-cases {{
            margin-top: 20px;
        }}
        .test-case {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .test-case:last-child {{
            border-bottom: none;
        }}
        .test-name {{
            flex: 1;
            font-family: monospace;
            font-size: 0.9em;
        }}
        .test-status {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-error {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        .coverage-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        .coverage-package {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }}
        .performance-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .performance-table th,
        .performance-table td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }}
        .performance-table th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DSL to PNG Test Report</h1>
            <p>Comprehensive test results and analysis</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number passed">{total_passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card">
                <div class="number failed">{total_failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="number skipped">{total_skipped}</div>
                <div class="label">Skipped</div>
            </div>
            <div class="summary-card">
                <div class="number coverage">{overall_coverage:.1f}%</div>
                <div class="label">Coverage</div>
            </div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📊 Test Suite Results</h2>
        """
        
        # Add test suite details
        for suite_name, suite_data in test_results.items():
            html_content += f"""
                <div class="test-suite">
                    <h3>{suite_data['status']} {suite_name}</h3>
                    <div class="test-suite-stats">
                        <div class="stat">
                            <div class="value passed">{suite_data['passed']}</div>
                            <div class="label">Passed</div>
                        </div>
                        <div class="stat">
                            <div class="value failed">{suite_data['failures'] + suite_data['errors']}</div>
                            <div class="label">Failed</div>
                        </div>
                        <div class="stat">
                            <div class="value skipped">{suite_data['skipped']}</div>
                            <div class="label">Skipped</div>
                        </div>
                        <div class="stat">
                            <div class="value">{suite_data['duration']:.2f}s</div>
                            <div class="label">Duration</div>
                        </div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {suite_data['success_rate']:.1f}%"></div>
                    </div>
                    <div class="test-cases">
            """
            
            # Add individual test cases (limit to first 20 for readability)
            for test_case in suite_data.get('test_cases', [])[:20]:
                status_class = f"status-{test_case['status']}"
                html_content += f"""
                        <div class="test-case">
                            <div class="test-name">{test_case['name']}</div>
                            <div class="test-status {status_class}">{test_case['status'].upper()}</div>
                        </div>
                """
            
            if len(suite_data.get('test_cases', [])) > 20:
                remaining = len(suite_data['test_cases']) - 20
                html_content += f"""
                        <div class="test-case">
                            <div class="test-name"><em>... and {remaining} more tests</em></div>
                            <div class="test-status"></div>
                        </div>
                """
            
            html_content += """
                    </div>
                </div>
            """
        
        # Add coverage section
        if include_coverage and coverage_data:
            html_content += """
            </div>
            <div class="section">
                <h2>📈 Code Coverage</h2>
                <div class="coverage-grid">
            """
            
            for package, coverage in coverage_data.get('packages', {}).items():
                html_content += f"""
                    <div class="coverage-package">
                        <h4>{package}</h4>
                        <div class="stat">
                            <div class="value coverage">{coverage['combined_coverage']:.1f}%</div>
                            <div class="label">Overall Coverage</div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {coverage['combined_coverage']:.1f}%"></div>
                        </div>
                    </div>
                """
            
            html_content += """
                </div>
            """
        
        # Add performance section
        if include_performance and performance_data:
            html_content += """
            </div>
            <div class="section">
                <h2>⚡ Performance Benchmarks</h2>
                <table class="performance-table">
                    <thead>
                        <tr>
                            <th>Benchmark</th>
                            <th>Mean (ms)</th>
                            <th>Std Dev (ms)</th>
                            <th>Min (ms)</th>
                            <th>Max (ms)</th>
                            <th>Rounds</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for benchmark in performance_data.get('benchmarks', []):
                html_content += f"""
                        <tr>
                            <td>{benchmark['name']}</td>
                            <td>{benchmark['mean']*1000:.2f}</td>
                            <td>{benchmark['stddev']*1000:.2f}</td>
                            <td>{benchmark['min']*1000:.2f}</td>
                            <td>{benchmark['max']*1000:.2f}</td>
                            <td>{benchmark['rounds']}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            """
        
        # Close HTML
        html_content += f"""
            </div>
        </div>
        
        <div class="timestamp">
            <p>Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def generate_summary_json(self) -> Dict[str, Any]:
        """Generate summary data as JSON for CI/CD integration."""
        test_results = self.collect_junit_results()
        coverage_data = self.collect_coverage_data()
        
        summary = {}
        
        # Add test suite summaries
        for suite_name, suite_data in test_results.items():
            summary[suite_name.lower().replace(' ', '_')] = {
                'status': '✅ PASS' if suite_data['failures'] == 0 and suite_data['errors'] == 0 else '❌ FAIL',
                'total': suite_data['total'],
                'failures': suite_data['failures'] + suite_data['errors'],
                'duration': suite_data['duration']
            }
        
        # Add coverage summary
        summary['coverage'] = {
            'percentage': coverage_data.get('overall', {}).get('combined_coverage', 0)
        }
        
        return summary
    
    def generate_report(self, include_coverage: bool = True, include_performance: bool = True):
        """Generate complete test report."""
        # Generate HTML report
        html_content = self.generate_html_report(include_coverage, include_performance)
        
        # Write HTML report
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Generate summary JSON
        summary = self.generate_summary_json()
        summary_path = self.output_path.parent / 'test-summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✅ Test report generated: {self.output_path}")
        print(f"✅ Summary data generated: {summary_path}")


def main():
    """Main entry point for the test report generator."""
    parser = argparse.ArgumentParser(description='Generate comprehensive test reports')
    parser.add_argument('--input', required=True, help='Input directory containing test artifacts')
    parser.add_argument('--output', required=True, help='Output HTML file path')
    parser.add_argument('--include-coverage', action='store_true', help='Include coverage data')
    parser.add_argument('--include-performance', action='store_true', help='Include performance data')
    
    args = parser.parse_args()
    
    artifacts_dir = Path(args.input)
    output_path = Path(args.output)
    
    if not artifacts_dir.exists():
        print(f"❌ Artifacts directory does not exist: {artifacts_dir}")
        return 1
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate report
    generator = TestReportGenerator(artifacts_dir, output_path)
    generator.generate_report(args.include_coverage, args.include_performance)
    
    return 0


if __name__ == '__main__':
    exit(main())