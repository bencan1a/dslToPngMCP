#!/usr/bin/env python3
"""
Performance Regression Checker
=============================

Compares current performance benchmarks with baseline to detect regressions.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


class PerformanceChecker:
    """Checks for performance regressions in benchmark results."""
    
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold  # 10% regression threshold by default
        
    def load_benchmark_data(self, file_path: Path) -> Dict[str, Any]:
        """Load benchmark data from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Benchmark file not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {file_path}: {e}")
            return {}
    
    def extract_benchmarks(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Extract benchmark metrics from data."""
        benchmarks = {}
        
        if 'benchmarks' in data:
            for benchmark in data['benchmarks']:
                name = benchmark.get('name', '')
                stats = benchmark.get('stats', {})
                mean_time = stats.get('mean', 0)
                benchmarks[name] = mean_time
        
        return benchmarks
    
    def compare_benchmarks(
        self, 
        current: Dict[str, float], 
        baseline: Dict[str, float]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Compare current benchmarks with baseline."""
        results = []
        has_regressions = False
        
        for name, current_time in current.items():
            if name in baseline:
                baseline_time = baseline[name]
                
                if baseline_time > 0:
                    change_ratio = (current_time - baseline_time) / baseline_time
                    change_percent = change_ratio * 100
                    
                    is_regression = change_ratio > self.threshold
                    if is_regression:
                        has_regressions = True
                    
                    status = "❌ REGRESSION" if is_regression else "✅ OK"
                    if change_ratio < -0.05:  # 5% improvement
                        status = "🚀 IMPROVEMENT"
                    
                    results.append({
                        'name': name,
                        'current_time': current_time,
                        'baseline_time': baseline_time,
                        'change_percent': change_percent,
                        'is_regression': is_regression,
                        'status': status
                    })
                else:
                    results.append({
                        'name': name,
                        'current_time': current_time,
                        'baseline_time': baseline_time,
                        'change_percent': 0,
                        'is_regression': False,
                        'status': "⚠️ BASELINE_ZERO"
                    })
            else:
                results.append({
                    'name': name,
                    'current_time': current_time,
                    'baseline_time': None,
                    'change_percent': 0,
                    'is_regression': False,
                    'status': "🆕 NEW"
                })
        
        # Check for missing benchmarks
        for name in baseline:
            if name not in current:
                results.append({
                    'name': name,
                    'current_time': None,
                    'baseline_time': baseline[name],
                    'change_percent': 0,
                    'is_regression': False,
                    'status': "❌ MISSING"
                })
                has_regressions = True
        
        return results, has_regressions
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate a formatted report of the comparison."""
        report = []
        report.append("# Performance Regression Report")
        report.append("")
        report.append("| Benchmark | Current (s) | Baseline (s) | Change | Status |")
        report.append("|-----------|-------------|--------------|--------|--------|")
        
        for result in sorted(results, key=lambda x: x['name']):
            name = result['name']
            current = f"{result['current_time']:.4f}" if result['current_time'] is not None else "N/A"
            baseline = f"{result['baseline_time']:.4f}" if result['baseline_time'] is not None else "N/A"
            
            if result['change_percent'] != 0:
                change = f"{result['change_percent']:+.1f}%"
            else:
                change = "N/A"
            
            status = result['status']
            
            report.append(f"| {name} | {current} | {baseline} | {change} | {status} |")
        
        return "\n".join(report)
    
    def check_regression(
        self, 
        current_file: Path, 
        baseline_file: Path
    ) -> Tuple[bool, str]:
        """Check for performance regressions."""
        current_data = self.load_benchmark_data(current_file)
        baseline_data = self.load_benchmark_data(baseline_file)
        
        if not current_data:
            return True, "❌ No current benchmark data available"
        
        if not baseline_data:
            print("⚠️ No baseline data available, treating as new benchmarks")
            return False, "✅ No baseline to compare against"
        
        current_benchmarks = self.extract_benchmarks(current_data)
        baseline_benchmarks = self.extract_benchmarks(baseline_data)
        
        if not current_benchmarks:
            return True, "❌ No benchmarks found in current data"
        
        results, has_regressions = self.compare_benchmarks(current_benchmarks, baseline_benchmarks)
        report = self.generate_report(results)
        
        return has_regressions, report


def main():
    """Main entry point for performance regression checking."""
    parser = argparse.ArgumentParser(description='Check for performance regressions')
    parser.add_argument('--current', required=True, help='Current benchmark JSON file')
    parser.add_argument('--baseline', required=True, help='Baseline benchmark JSON file')
    parser.add_argument('--threshold', type=float, default=0.1, 
                       help='Regression threshold (default: 0.1 = 10%)')
    parser.add_argument('--output', help='Output report file (optional)')
    
    args = parser.parse_args()
    
    current_file = Path(args.current)
    baseline_file = Path(args.baseline)
    
    if not current_file.exists():
        print(f"❌ Current benchmark file does not exist: {current_file}")
        return 1
    
    if not baseline_file.exists():
        print(f"⚠️ Baseline benchmark file does not exist: {baseline_file}")
        print("This might be the first run or baseline needs to be established.")
        # Copy current as baseline for future runs
        try:
            import shutil
            shutil.copy2(current_file, baseline_file)
            print(f"✅ Created baseline from current benchmarks: {baseline_file}")
            return 0
        except Exception as e:
            print(f"❌ Could not create baseline: {e}")
            return 1
    
    checker = PerformanceChecker(threshold=args.threshold)
    has_regressions, report = checker.check_regression(current_file, baseline_file)
    
    print(report)
    
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {output_file}")
    
    if has_regressions:
        print(f"\n❌ Performance regressions detected (threshold: {args.threshold*100:.1f}%)")
        return 1
    else:
        print(f"\n✅ No performance regressions detected (threshold: {args.threshold*100:.1f}%)")
        return 0


if __name__ == '__main__':
    sys.exit(main())