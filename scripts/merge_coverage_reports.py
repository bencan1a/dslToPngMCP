#!/usr/bin/env python3
"""
Coverage Report Merger
=====================

Merges multiple coverage reports from different test runs into a unified report.
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List
import subprocess
import sys


class CoverageMerger:
    """Merges coverage reports from multiple sources."""
    
    def __init__(self, artifacts_dir: Path):
        self.artifacts_dir = artifacts_dir
        self.coverage_files = []
        
    def find_coverage_files(self) -> List[Path]:
        """Find all coverage XML files in the artifacts directory."""
        coverage_files = []
        
        # Look for coverage XML files
        for xml_file in self.artifacts_dir.glob("**/*coverage*.xml"):
            if xml_file.is_file() and xml_file.stat().st_size > 0:
                coverage_files.append(xml_file)
        
        return coverage_files
    
    def merge_xml_reports(self, output_path: Path) -> bool:
        """Merge XML coverage reports using coverage.py."""
        coverage_files = self.find_coverage_files()
        
        if not coverage_files:
            print("No coverage files found to merge")
            return False
        
        print(f"Found {len(coverage_files)} coverage files:")
        for file in coverage_files:
            print(f"  - {file}")
        
        try:
            # Use coverage combine to merge .coverage files if they exist
            coverage_data_files = list(self.artifacts_dir.glob("**/.coverage*"))
            
            if coverage_data_files:
                print(f"Found {len(coverage_data_files)} .coverage data files")
                
                # Copy all .coverage files to current directory
                for coverage_file in coverage_data_files:
                    subprocess.run(['cp', str(coverage_file), '.'], check=True)
                
                # Combine coverage data
                subprocess.run(['coverage', 'combine'], check=True)
                
                # Generate XML report
                subprocess.run(['coverage', 'xml', '-o', str(output_path)], check=True)
                
                # Generate HTML report
                html_output = output_path.parent / 'combined-coverage.html'
                subprocess.run(['coverage', 'html', '-d', str(html_output)], check=True)
                
                print(f"✅ Combined coverage report generated: {output_path}")
                print(f"✅ Combined HTML report generated: {html_output}")
                
                return True
            else:
                # Fallback: merge XML files manually
                return self.merge_xml_files_manually(coverage_files, output_path)
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error merging coverage reports: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def merge_xml_files_manually(self, coverage_files: List[Path], output_path: Path) -> bool:
        """Manually merge XML coverage files."""
        if not coverage_files:
            return False
        
        try:
            # Start with the first file as base
            base_tree = ET.parse(coverage_files[0])
            base_root = base_tree.getroot()
            
            # Extract packages from base file
            base_packages = {}
            packages_elem = base_root.find('packages')
            if packages_elem is not None:
                for package in packages_elem.findall('package'):
                    pkg_name = package.get('name')
                    base_packages[pkg_name] = package
            
            # Merge additional files
            for coverage_file in coverage_files[1:]:
                try:
                    tree = ET.parse(coverage_file)
                    root = tree.getroot()
                    
                    packages_elem = root.find('packages')
                    if packages_elem is not None:
                        for package in packages_elem.findall('package'):
                            pkg_name = package.get('name')
                            if pkg_name not in base_packages:
                                # Add new package
                                base_root.find('packages').append(package)
                                base_packages[pkg_name] = package
                            else:
                                # Merge classes within existing package
                                base_pkg = base_packages[pkg_name]
                                base_classes = {cls.get('name'): cls for cls in base_pkg.find('classes').findall('class')}
                                
                                for cls in package.find('classes').findall('class'):
                                    cls_name = cls.get('name')
                                    if cls_name not in base_classes:
                                        base_pkg.find('classes').append(cls)
                
                except Exception as e:
                    print(f"Warning: Could not merge {coverage_file}: {e}")
                    continue
            
            # Recalculate overall statistics
            self.recalculate_coverage_stats(base_root)
            
            # Write merged file
            base_tree.write(str(output_path), encoding='utf-8', xml_declaration=True)
            print(f"✅ Manually merged coverage report: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in manual merge: {e}")
            return False
    
    def recalculate_coverage_stats(self, root: ET.Element):
        """Recalculate coverage statistics for the merged report."""
        try:
            packages_elem = root.find('packages')
            if packages_elem is None:
                return
            
            total_lines = 0
            covered_lines = 0
            total_branches = 0
            covered_branches = 0
            
            for package in packages_elem.findall('package'):
                pkg_lines = 0
                pkg_covered_lines = 0
                pkg_branches = 0
                pkg_covered_branches = 0
                
                classes_elem = package.find('classes')
                if classes_elem is not None:
                    for cls in classes_elem.findall('class'):
                        cls_lines = 0
                        cls_covered_lines = 0
                        cls_branches = 0
                        cls_covered_branches = 0
                        
                        lines_elem = cls.find('lines')
                        if lines_elem is not None:
                            for line in lines_elem.findall('line'):
                                cls_lines += 1
                                if line.get('hits', '0') != '0':
                                    cls_covered_lines += 1
                                
                                if line.get('branch') == 'true':
                                    cls_branches += 1
                                    if line.get('condition-coverage', '0%') != '0%':
                                        cls_covered_branches += 1
                        
                        # Update class attributes
                        if cls_lines > 0:
                            cls.set('line-rate', f"{cls_covered_lines / cls_lines:.4f}")
                        if cls_branches > 0:
                            cls.set('branch-rate', f"{cls_covered_branches / cls_branches:.4f}")
                        
                        pkg_lines += cls_lines
                        pkg_covered_lines += cls_covered_lines
                        pkg_branches += cls_branches
                        pkg_covered_branches += cls_covered_branches
                
                # Update package attributes
                if pkg_lines > 0:
                    package.set('line-rate', f"{pkg_covered_lines / pkg_lines:.4f}")
                if pkg_branches > 0:
                    package.set('branch-rate', f"{pkg_covered_branches / pkg_branches:.4f}")
                
                total_lines += pkg_lines
                covered_lines += pkg_covered_lines
                total_branches += pkg_branches
                covered_branches += pkg_covered_branches
            
            # Update root coverage element
            coverage_elem = root.find('coverage') or root
            if total_lines > 0:
                coverage_elem.set('line-rate', f"{covered_lines / total_lines:.4f}")
            if total_branches > 0:
                coverage_elem.set('branch-rate', f"{covered_branches / total_branches:.4f}")
            
            coverage_elem.set('lines-covered', str(covered_lines))
            coverage_elem.set('lines-valid', str(total_lines))
            coverage_elem.set('branches-covered', str(covered_branches))
            coverage_elem.set('branches-valid', str(total_branches))
            
        except Exception as e:
            print(f"Warning: Could not recalculate coverage stats: {e}")


def main():
    """Main entry point for coverage merging."""
    parser = argparse.ArgumentParser(description='Merge coverage reports')
    parser.add_argument('artifacts_dir', help='Directory containing coverage artifacts')
    parser.add_argument('--output', default='combined-coverage.xml', help='Output XML file')
    
    args = parser.parse_args()
    
    artifacts_dir = Path(args.artifacts_dir)
    output_path = Path(args.output)
    
    if not artifacts_dir.exists():
        print(f"❌ Artifacts directory does not exist: {artifacts_dir}")
        return 1
    
    merger = CoverageMerger(artifacts_dir)
    success = merger.merge_xml_reports(output_path)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())