#!/usr/bin/env python3
"""
Test Framework Validation Script
===============================

Comprehensive validation of the DSL to PNG testing framework to ensure
completeness, quality, and proper configuration.
"""

import os
import sys
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
import importlib.util


class TestFrameworkValidator:
    """Validates the completeness and quality of the testing framework."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.src_dir = project_root / "src"
        self.docs_dir = project_root / "docs"
        self.scripts_dir = project_root / "scripts"
        self.validation_results = {}
        
    def validate_framework(self) -> Dict[str, Any]:
        """Run complete framework validation."""
        print("🔍 Starting comprehensive test framework validation...")
        
        # Core validation checks
        self.validation_results['structure'] = self.validate_test_structure()
        self.validation_results['coverage'] = self.validate_test_coverage()
        self.validation_results['configuration'] = self.validate_configuration()
        self.validation_results['ci_cd'] = self.validate_ci_cd_integration()
        self.validation_results['documentation'] = self.validate_documentation()
        self.validation_results['quality'] = self.validate_test_quality()
        
        # Generate summary
        self.validation_results['summary'] = self.generate_summary()
        
        return self.validation_results
    
    def validate_test_structure(self) -> Dict[str, Any]:
        """Validate test directory structure and files."""
        print("📁 Validating test structure...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'files_found': [],
            'missing_files': []
        }
        
        # Required test files and directories
        required_structure = {
            'tests/__init__.py': 'Test package initialization',
            'tests/conftest.py': 'Global test configuration',
            'tests/utils/__init__.py': 'Test utilities package',
            'tests/utils/assertions.py': 'Custom assertion helpers',
            'tests/utils/data_generators.py': 'Test data generators',
            'tests/utils/helpers.py': 'Test helper functions',
            'tests/utils/mocks.py': 'Mock implementations',
            'tests/data/__init__.py': 'Test data package',
            'tests/data/sample_dsl_documents.py': 'Sample DSL documents',
            'tests/data/sample_render_options.py': 'Sample render options',
            'tests/data/test_scenarios.py': 'Test scenarios',
            'tests/data/example_outputs.py': 'Expected output examples',
            'tests/unit/test_dsl_parser.py': 'DSL parser unit tests',
            'tests/unit/test_html_generator.py': 'HTML generator unit tests',
            'tests/unit/test_png_generator.py': 'PNG generator unit tests',
            'tests/unit/test_storage_manager.py': 'Storage manager unit tests',
            'tests/integration/test_end_to_end_pipeline.py': 'End-to-end tests',
            'tests/integration/test_api_contracts.py': 'API contract tests',
            'tests/integration/test_mcp_protocol.py': 'MCP protocol tests',
            'tests/performance/test_load_performance.py': 'Performance tests',
            'tests/security/test_security_validation.py': 'Security tests',
            'tests/deployment/test_docker_containers.py': 'Docker tests'
        }
        
        # Check for required files
        for file_path, description in required_structure.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                results['files_found'].append(f"✅ {file_path}: {description}")
            else:
                results['missing_files'].append(f"❌ {file_path}: {description}")
                results['issues'].append(f"Missing required file: {file_path}")
        
        # Check for test file content
        for test_file in self.tests_dir.rglob("test_*.py"):
            if self.is_valid_test_file(test_file):
                results['files_found'].append(f"✅ {test_file.relative_to(self.project_root)}")
            else:
                results['issues'].append(f"Invalid test file: {test_file.relative_to(self.project_root)}")
        
        if results['missing_files'] or results['issues']:
            results['status'] = 'fail'
        
        return results
    
    def validate_test_coverage(self) -> Dict[str, Any]:
        """Validate test coverage across all modules."""
        print("📊 Validating test coverage...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'coverage_by_module': {},
            'overall_coverage': 0
        }
        
        # Get list of source modules
        source_modules = []
        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name != "__init__.py":
                module_path = py_file.relative_to(self.src_dir)
                source_modules.append(str(module_path))
        
        # Check if each module has corresponding tests
        for module in source_modules:
            module_name = module.replace(".py", "").replace("/", "_")
            test_file = self.tests_dir / "unit" / f"test_{module_name}.py"
            
            coverage_info = {
                'has_unit_tests': test_file.exists(),
                'test_file': str(test_file.relative_to(self.project_root)) if test_file.exists() else None,
                'estimated_coverage': 0
            }
            
            if test_file.exists():
                coverage_info['estimated_coverage'] = self.estimate_test_coverage(
                    self.src_dir / module, test_file
                )
            else:
                results['issues'].append(f"No unit tests found for module: {module}")
            
            results['coverage_by_module'][module] = coverage_info
        
        # Calculate overall coverage estimate
        covered_modules = sum(1 for info in results['coverage_by_module'].values() if info['has_unit_tests'])
        total_modules = len(results['coverage_by_module'])
        results['overall_coverage'] = (covered_modules / total_modules * 100) if total_modules > 0 else 0
        
        if results['overall_coverage'] < 80:
            results['status'] = 'fail'
            results['issues'].append(f"Overall test coverage ({results['overall_coverage']:.1f}%) below 80% threshold")
        
        return results
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate test configuration files."""
        print("⚙️ Validating test configuration...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'configurations': {}
        }
        
        # Check pytest.ini
        pytest_ini = self.project_root / "pytest.ini"
        if pytest_ini.exists():
            results['configurations']['pytest.ini'] = self.validate_pytest_config(pytest_ini)
        else:
            results['issues'].append("Missing pytest.ini configuration")
            results['status'] = 'fail'
        
        # Check conftest.py
        conftest = self.tests_dir / "conftest.py"
        if conftest.exists():
            results['configurations']['conftest.py'] = self.validate_conftest(conftest)
        else:
            results['issues'].append("Missing tests/conftest.py")
            results['status'] = 'fail'
        
        # Check requirements files
        dev_requirements = self.project_root / "requirements" / "dev.txt"
        if dev_requirements.exists():
            results['configurations']['dev_requirements'] = self.validate_dev_requirements(dev_requirements)
        else:
            results['issues'].append("Missing requirements/dev.txt")
            results['status'] = 'fail'
        
        return results
    
    def validate_ci_cd_integration(self) -> Dict[str, Any]:
        """Validate CI/CD integration files."""
        print("🔄 Validating CI/CD integration...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'ci_files': {}
        }
        
        # Check GitHub Actions workflow
        workflow_file = self.project_root / ".github" / "workflows" / "test-suite.yml"
        if workflow_file.exists():
            results['ci_files']['github_actions'] = self.validate_github_workflow(workflow_file)
        else:
            results['issues'].append("Missing GitHub Actions workflow")
            results['status'] = 'fail'
        
        # Check Docker test configuration
        docker_test = self.project_root / "docker" / "docker compose.test.yml"
        if docker_test.exists():
            results['ci_files']['docker_test'] = "✅ Docker test configuration found"
        else:
            results['issues'].append("Missing Docker test configuration")
            results['status'] = 'fail'
        
        # Check test scripts
        required_scripts = [
            "generate_test_report.py",
            "merge_coverage_reports.py",
            "check_performance_regression.py"
        ]
        
        for script in required_scripts:
            script_path = self.scripts_dir / script
            if script_path.exists():
                results['ci_files'][script] = "✅ Script found"
            else:
                results['issues'].append(f"Missing script: {script}")
                results['status'] = 'fail'
        
        return results
    
    def validate_documentation(self) -> Dict[str, Any]:
        """Validate testing documentation."""
        print("📚 Validating documentation...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'docs_found': []
        }
        
        # Required documentation files
        required_docs = [
            "docs/testing/README.md",
            "docs/testing/test-framework-overview.md",
            "docs/testing/validation-guide.md"
        ]
        
        for doc_path in required_docs:
            full_path = self.project_root / doc_path
            if full_path.exists():
                results['docs_found'].append(f"✅ {doc_path}")
            else:
                results['issues'].append(f"Missing documentation: {doc_path}")
                results['status'] = 'fail'
        
        return results
    
    def validate_test_quality(self) -> Dict[str, Any]:
        """Validate test quality and best practices."""
        print("🔍 Validating test quality...")
        
        results = {
            'status': 'pass',
            'issues': [],
            'quality_metrics': {}
        }
        
        # Check for test markers
        marker_usage = self.check_test_markers()
        results['quality_metrics']['marker_usage'] = marker_usage
        
        # Check for async test handling
        async_test_usage = self.check_async_tests()
        results['quality_metrics']['async_tests'] = async_test_usage
        
        # Check for mock usage
        mock_usage = self.check_mock_usage()
        results['quality_metrics']['mock_usage'] = mock_usage
        
        # Check for fixture usage
        fixture_usage = self.check_fixture_usage()
        results['quality_metrics']['fixture_usage'] = fixture_usage
        
        return results
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        summary = {
            'overall_status': 'pass',
            'total_issues': 0,
            'categories': {},
            'recommendations': []
        }
        
        # Count issues by category
        for category, results in self.validation_results.items():
            if category == 'summary':
                continue
                
            category_issues = len(results.get('issues', []))
            summary['total_issues'] += category_issues
            summary['categories'][category] = {
                'status': results.get('status', 'unknown'),
                'issues': category_issues
            }
            
            if results.get('status') == 'fail':
                summary['overall_status'] = 'fail'
        
        # Generate recommendations
        if summary['total_issues'] > 0:
            summary['recommendations'].append(
                f"Address {summary['total_issues']} identified issues before release"
            )
        
        if summary['categories'].get('coverage', {}).get('status') == 'fail':
            summary['recommendations'].append(
                "Improve test coverage by adding missing unit tests"
            )
        
        if summary['categories'].get('ci_cd', {}).get('status') == 'fail':
            summary['recommendations'].append(
                "Complete CI/CD integration setup"
            )
        
        return summary
    
    # Helper methods
    
    def is_valid_test_file(self, file_path: Path) -> bool:
        """Check if a file is a valid test file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to check for test functions
            tree = ast.parse(content)
            
            # Look for test functions or classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    return True
                if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    return True
            
            return False
        except Exception:
            return False
    
    def estimate_test_coverage(self, source_file: Path, test_file: Path) -> int:
        """Estimate test coverage by comparing functions."""
        try:
            # Parse source file
            with open(source_file, 'r', encoding='utf-8') as f:
                source_content = f.read()
            source_tree = ast.parse(source_content)
            
            # Parse test file
            with open(test_file, 'r', encoding='utf-8') as f:
                test_content = f.read()
            test_tree = ast.parse(test_content)
            
            # Count functions in source
            source_functions = []
            for node in ast.walk(source_tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                    source_functions.append(node.name)
            
            # Count test functions
            test_functions = []
            for node in ast.walk(test_tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_functions.append(node.name)
            
            # Estimate coverage
            if len(source_functions) == 0:
                return 100
            
            # Simple heuristic: assume good coverage if test count >= source function count
            coverage = min(100, (len(test_functions) / len(source_functions)) * 100)
            return int(coverage)
            
        except Exception:
            return 0
    
    def validate_pytest_config(self, pytest_ini: Path) -> str:
        """Validate pytest.ini configuration."""
        try:
            with open(pytest_ini, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_settings = ['testpaths', 'addopts', 'markers']
            missing_settings = []
            
            for setting in required_settings:
                if setting not in content:
                    missing_settings.append(setting)
            
            if missing_settings:
                return f"❌ Missing settings: {', '.join(missing_settings)}"
            else:
                return "✅ Pytest configuration valid"
                
        except Exception as e:
            return f"❌ Error reading pytest.ini: {e}"
    
    def validate_conftest(self, conftest: Path) -> str:
        """Validate conftest.py."""
        try:
            with open(conftest, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'pytest' in content and 'fixture' in content:
                return "✅ Conftest configuration valid"
            else:
                return "❌ Conftest appears incomplete"
                
        except Exception as e:
            return f"❌ Error reading conftest.py: {e}"
    
    def validate_dev_requirements(self, requirements: Path) -> str:
        """Validate development requirements."""
        try:
            with open(requirements, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_packages = ['pytest', 'pytest-cov', 'pytest-asyncio']
            missing_packages = []
            
            for package in required_packages:
                if package not in content:
                    missing_packages.append(package)
            
            if missing_packages:
                return f"❌ Missing packages: {', '.join(missing_packages)}"
            else:
                return "✅ Development requirements valid"
                
        except Exception as e:
            return f"❌ Error reading requirements: {e}"
    
    def validate_github_workflow(self, workflow: Path) -> str:
        """Validate GitHub Actions workflow."""
        try:
            with open(workflow, 'r', encoding='utf-8') as f:
                content = f.read()
            
            required_elements = ['pytest', 'coverage', 'docker']
            missing_elements = []
            
            for element in required_elements:
                if element not in content.lower():
                    missing_elements.append(element)
            
            if missing_elements:
                return f"❌ Missing workflow elements: {', '.join(missing_elements)}"
            else:
                return "✅ GitHub workflow valid"
                
        except Exception as e:
            return f"❌ Error reading workflow: {e}"
    
    def check_test_markers(self) -> Dict[str, int]:
        """Check usage of pytest markers."""
        markers = {}
        
        for test_file in self.tests_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count marker usage
                if '@pytest.mark.smoke' in content:
                    markers['smoke'] = markers.get('smoke', 0) + 1
                if '@pytest.mark.unit' in content:
                    markers['unit'] = markers.get('unit', 0) + 1
                if '@pytest.mark.integration' in content:
                    markers['integration'] = markers.get('integration', 0) + 1
                if '@pytest.mark.performance' in content:
                    markers['performance'] = markers.get('performance', 0) + 1
                if '@pytest.mark.security' in content:
                    markers['security'] = markers.get('security', 0) + 1
                    
            except Exception:
                continue
        
        return markers
    
    def check_async_tests(self) -> int:
        """Check for async test usage."""
        async_count = 0
        
        for test_file in self.tests_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '@pytest.mark.asyncio' in content:
                    async_count += content.count('@pytest.mark.asyncio')
                    
            except Exception:
                continue
        
        return async_count
    
    def check_mock_usage(self) -> int:
        """Check for mock usage."""
        mock_count = 0
        
        for test_file in self.tests_dir.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'mock' in content.lower():
                    mock_count += 1
                    
            except Exception:
                continue
        
        return mock_count
    
    def check_fixture_usage(self) -> int:
        """Check for fixture usage."""
        fixture_count = 0
        
        for test_file in self.tests_dir.rglob("*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                fixture_count += content.count('@pytest.fixture')
                    
            except Exception:
                continue
        
        return fixture_count
    
    def print_validation_report(self):
        """Print comprehensive validation report."""
        print("\n" + "="*80)
        print("🧪 TEST FRAMEWORK VALIDATION REPORT")
        print("="*80)
        
        summary = self.validation_results.get('summary', {})
        overall_status = summary.get('overall_status', 'unknown')
        
        if overall_status == 'pass':
            print("✅ OVERALL STATUS: PASS")
        else:
            print("❌ OVERALL STATUS: FAIL")
        
        print(f"\n📊 Total Issues Found: {summary.get('total_issues', 0)}")
        
        # Print category results
        for category, results in self.validation_results.items():
            if category == 'summary':
                continue
                
            print(f"\n📁 {category.upper().replace('_', ' ')}")
            print("-" * 40)
            
            status = results.get('status', 'unknown')
            print(f"Status: {'✅ PASS' if status == 'pass' else '❌ FAIL'}")
            
            issues = results.get('issues', [])
            if issues:
                print("Issues:")
                for issue in issues:
                    print(f"  • {issue}")
            
            # Print category-specific information
            if category == 'structure':
                found = results.get('files_found', [])
                missing = results.get('missing_files', [])
                print(f"Files found: {len(found)}")
                print(f"Missing files: {len(missing)}")
                
            elif category == 'coverage':
                coverage = results.get('overall_coverage', 0)
                print(f"Estimated coverage: {coverage:.1f}%")
                
            elif category == 'quality':
                metrics = results.get('quality_metrics', {})
                for metric, value in metrics.items():
                    print(f"{metric}: {value}")
        
        # Print recommendations
        recommendations = summary.get('recommendations', [])
        if recommendations:
            print("\n💡 RECOMMENDATIONS")
            print("-" * 40)
            for rec in recommendations:
                print(f"  • {rec}")
        
        print("\n" + "="*80)


def main():
    """Main entry point for test framework validation."""
    project_root = Path(__file__).parent.parent
    
    validator = TestFrameworkValidator(project_root)
    results = validator.validate_framework()
    validator.print_validation_report()
    
    # Save results to file
    output_file = project_root / "test-framework-validation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    
    # Return appropriate exit code
    summary = results.get('summary', {})
    return 0 if summary.get('overall_status') == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())