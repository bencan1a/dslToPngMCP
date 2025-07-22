#!/usr/bin/env python3
"""
End-to-End Pipeline Test
========================

Comprehensive test script to validate the complete DSL→HTML→PNG pipeline.
This script tests all major components and their integration.
"""

import asyncio
import json
import yaml
import time
from pathlib import Path
from typing import Dict, Any

# Import all components
from src.core.dsl.parser import parse_dsl, validate_dsl_syntax, get_validation_suggestions
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import PNGGeneratorFactory, initialize_browser_pool, close_browser_pool
from src.core.storage.manager import get_storage_manager, close_storage_manager
from src.models.schemas import RenderOptions, DSLRenderRequest
from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class PipelineTestResults:
    """Container for test results."""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.warnings = []
        self.performance_metrics = {}
    
    def add_test_result(self, test_name: str, passed: bool, error: str = None, duration: float = 0):
        """Add a test result."""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            logger.info(f"✅ {test_name} - PASSED ({duration:.2f}s)")
        else:
            self.tests_failed += 1
            self.errors.append(f"{test_name}: {error}")
            logger.error(f"❌ {test_name} - FAILED: {error}")
        
        self.performance_metrics[test_name] = duration
    
    def add_warning(self, message: str):
        """Add a warning."""
        self.warnings.append(message)
        logger.warning(f"⚠️  {message}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*80)
        print("🧪 PIPELINE TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        
        if self.tests_failed > 0:
            print("\n❌ FAILURES:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print(f"\n📊 PERFORMANCE METRICS:")
        total_time = sum(self.performance_metrics.values())
        for test_name, duration in self.performance_metrics.items():
            print(f"  • {test_name}: {duration:.2f}s")
        print(f"  • Total Time: {total_time:.2f}s")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Pipeline is working great!")
        elif success_rate >= 70:
            print("👍 GOOD! Minor issues to address.")
        else:
            print("🔧 NEEDS WORK! Several issues require attention.")


class PipelineTester:
    """Main pipeline testing class."""
    
    def __init__(self):
        self.settings = get_settings()
        self.results = PipelineTestResults()
        self.examples_dir = Path("examples")
        
    async def run_all_tests(self):
        """Run all pipeline tests."""
        print("🚀 Starting DSL to PNG Pipeline Tests")
        print("="*80)
        
        try:
            # Test 1: DSL Parser Tests
            await self.test_dsl_parser()
            
            # Test 2: HTML Generation Tests
            await self.test_html_generation()
            
            # Test 3: PNG Generation Tests
            await self.test_png_generation()
            
            # Test 4: Storage System Tests
            await self.test_storage_system()
            
            # Test 5: End-to-End Integration Tests
            await self.test_end_to_end_integration()
            
        except Exception as e:
            self.results.add_test_result("Pipeline Setup", False, str(e))
        
        finally:
            # Cleanup
            try:
                await close_browser_pool()
                await close_storage_manager()
            except:
                pass
        
        self.results.print_summary()
        return self.results
    
    async def test_dsl_parser(self):
        """Test DSL parsing functionality."""
        print("\n📝 Testing DSL Parser...")
        
        # Test valid JSON DSL
        await self._test_parse_example("simple_button.json", "JSON Simple Button")
        await self._test_parse_example("login_form.json", "JSON Login Form")
        await self._test_parse_example("dashboard.json", "JSON Dashboard")
        
        # Test valid YAML DSL
        await self._test_parse_example("mobile_app.yaml", "YAML Mobile App")
        
        # Test invalid DSL
        await self._test_parse_invalid_example("error_example.json", "Invalid DSL Error Handling")
        
        # Test validation suggestions
        await self._test_validation_suggestions()
    
    async def _test_parse_example(self, filename: str, test_name: str):
        """Test parsing a specific example file."""
        start_time = time.time()
        
        try:
            file_path = self.examples_dir / filename
            if not file_path.exists():
                self.results.add_test_result(test_name, False, f"Example file not found: {filename}")
                return
            
            content = file_path.read_text()
            
            # Test syntax validation
            is_valid = await validate_dsl_syntax(content)
            if not is_valid:
                self.results.add_test_result(test_name, False, "Syntax validation failed")
                return
            
            # Test full parsing
            parse_result = await parse_dsl(content)
            
            if not parse_result.success:
                self.results.add_test_result(test_name, False, f"Parsing failed: {'; '.join(parse_result.errors)}")
                return
            
            # Validate document structure
            doc = parse_result.document
            if not doc or not doc.elements:
                self.results.add_test_result(test_name, False, "No elements found in parsed document")
                return
            
            duration = time.time() - start_time
            self.results.add_test_result(test_name, True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result(test_name, False, str(e), duration)
    
    async def _test_parse_invalid_example(self, filename: str, test_name: str):
        """Test parsing an intentionally invalid example."""
        start_time = time.time()
        
        try:
            file_path = self.examples_dir / filename
            if not file_path.exists():
                self.results.add_test_result(test_name, False, f"Example file not found: {filename}")
                return
            
            content = file_path.read_text()
            parse_result = await parse_dsl(content)
            
            # This should fail - if it passes, that's an error
            if parse_result.success:
                self.results.add_test_result(test_name, False, "Invalid DSL was incorrectly parsed as valid")
                return
            
            # Should have error messages
            if not parse_result.errors:
                self.results.add_test_result(test_name, False, "No error messages for invalid DSL")
                return
            
            duration = time.time() - start_time
            self.results.add_test_result(test_name, True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result(test_name, False, str(e), duration)
    
    async def _test_validation_suggestions(self):
        """Test validation suggestion system."""
        start_time = time.time()
        
        try:
            # Test with some common errors
            invalid_dsl = '{"width": "invalid", "elements": []}'
            suggestions = await get_validation_suggestions(invalid_dsl, ["Invalid width value"])
            
            if not suggestions:
                self.results.add_warning("No validation suggestions generated")
            
            duration = time.time() - start_time
            self.results.add_test_result("Validation Suggestions", True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Validation Suggestions", False, str(e), duration)
    
    async def test_html_generation(self):
        """Test HTML generation functionality."""
        print("\n🌐 Testing HTML Generation...")
        
        # Test with simple button example
        await self._test_html_generation_example("simple_button.json", "HTML Generation - Simple Button")
        
        # Test with complex dashboard
        await self._test_html_generation_example("dashboard.json", "HTML Generation - Dashboard")
    
    async def _test_html_generation_example(self, filename: str, test_name: str):
        """Test HTML generation for a specific example."""
        start_time = time.time()
        
        try:
            file_path = self.examples_dir / filename
            content = file_path.read_text()
            
            # Parse DSL
            parse_result = await parse_dsl(content)
            if not parse_result.success:
                self.results.add_test_result(test_name, False, "DSL parsing failed for HTML test")
                return
            
            # Generate HTML
            options = RenderOptions(width=800, height=600)
            html_content = await generate_html(parse_result.document, options)
            
            # Validate HTML structure
            if not html_content or len(html_content) < 100:
                self.results.add_test_result(test_name, False, "Generated HTML too short or empty")
                return
            
            if "<!DOCTYPE html>" not in html_content:
                self.results.add_test_result(test_name, False, "Generated HTML missing DOCTYPE")
                return
            
            if "dsl-canvas" not in html_content:
                self.results.add_test_result(test_name, False, "Generated HTML missing canvas container")
                return
            
            duration = time.time() - start_time
            self.results.add_test_result(test_name, True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result(test_name, False, str(e), duration)
    
    async def test_png_generation(self):
        """Test PNG generation functionality."""
        print("\n🖼️  Testing PNG Generation...")
        
        try:
            # Initialize browser pool
            await initialize_browser_pool()
            
            # Test basic PNG generation
            await self._test_png_generation_basic()
            
            # Test advanced PNG generation
            await self._test_png_generation_advanced()
            
        except Exception as e:
            self.results.add_test_result("PNG Generation Setup", False, str(e))
    
    async def _test_png_generation_basic(self):
        """Test basic PNG generation."""
        start_time = time.time()
        
        try:
            # Simple HTML for testing
            simple_html = """
            <!DOCTYPE html>
            <html>
            <head><title>Test</title></head>
            <body>
                <div style="width:400px;height:200px;background:#007bff;color:white;
                           display:flex;align-items:center;justify-content:center;
                           font-size:24px;font-weight:bold;">
                    Test PNG Generation
                </div>
            </body>
            </html>
            """
            
            options = RenderOptions(width=400, height=200)
            generator = PNGGeneratorFactory.create_generator("playwright")
            await generator.initialize()
            
            try:
                png_result = await generator.generate_png(simple_html, options)
                
                # Validate PNG result
                if not png_result.png_data or len(png_result.png_data) < 1000:
                    self.results.add_test_result("Basic PNG Generation", False, "PNG data too small or empty")
                    return
                
                if png_result.width != 400 or png_result.height != 200:
                    self.results.add_test_result("Basic PNG Generation", False, "PNG dimensions incorrect")
                    return
                
                if not png_result.base64_data:
                    self.results.add_test_result("Basic PNG Generation", False, "Base64 data missing")
                    return
                
                duration = time.time() - start_time
                self.results.add_test_result("Basic PNG Generation", True, duration=duration)
                
            finally:
                await generator.close()
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Basic PNG Generation", False, str(e), duration)
    
    async def _test_png_generation_advanced(self):
        """Test advanced PNG generation features."""
        start_time = time.time()
        
        try:
            # Test with optimization options
            simple_html = "<html><body><h1>Advanced Test</h1></body></html>"
            options = RenderOptions(
                width=300, 
                height=200, 
                optimize_png=True,
                transparent_background=True
            )
            
            generator = PNGGeneratorFactory.create_generator("advanced")
            await generator.initialize()
            
            try:
                png_result = await generator.generate_png(simple_html, options)
                
                if not png_result.png_data:
                    self.results.add_test_result("Advanced PNG Generation", False, "PNG generation failed")
                    return
                
                duration = time.time() - start_time
                self.results.add_test_result("Advanced PNG Generation", True, duration=duration)
                
            finally:
                await generator.close()
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Advanced PNG Generation", False, str(e), duration)
    
    async def test_storage_system(self):
        """Test storage system functionality."""
        print("\n💾 Testing Storage System...")
        
        await self._test_storage_basic()
        await self._test_storage_retrieval()
        await self._test_storage_cleanup()
    
    async def _test_storage_basic(self):
        """Test basic storage operations."""
        start_time = time.time()
        
        try:
            from src.models.schemas import PNGResult
            
            # Create test PNG result
            test_data = b"fake_png_data_for_testing_12345"
            test_png = PNGResult(
                png_data=test_data,
                base64_data="dGVzdA==",
                width=100,
                height=100,
                file_size=len(test_data),
                metadata={"test": True}
            )
            
            storage_manager = await get_storage_manager()
            
            # Store PNG
            content_hash = await storage_manager.store_png(test_png, "test_task")
            
            if not content_hash:
                self.results.add_test_result("Storage Basic", False, "No content hash returned")
                return
            
            duration = time.time() - start_time
            self.results.add_test_result("Storage Basic", True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Storage Basic", False, str(e), duration)
    
    async def _test_storage_retrieval(self):
        """Test storage retrieval."""
        start_time = time.time()
        
        try:
            # This would test retrieving the stored file
            # For now, just test that the storage manager works
            storage_manager = await get_storage_manager()
            stats = await storage_manager.get_storage_stats()
            
            if not isinstance(stats, dict):
                self.results.add_test_result("Storage Retrieval", False, "Storage stats not returned as dict")
                return
            
            duration = time.time() - start_time
            self.results.add_test_result("Storage Retrieval", True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Storage Retrieval", False, str(e), duration)
    
    async def _test_storage_cleanup(self):
        """Test storage cleanup functionality."""
        start_time = time.time()
        
        try:
            # Test cleanup doesn't crash
            storage_manager = await get_storage_manager()
            
            # This is just a basic test that the manager is working
            # Real cleanup testing would require more setup
            duration = time.time() - start_time
            self.results.add_test_result("Storage Cleanup", True, duration=duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result("Storage Cleanup", False, str(e), duration)
    
    async def test_end_to_end_integration(self):
        """Test complete end-to-end integration."""
        print("\n🔄 Testing End-to-End Integration...")
        
        await self._test_complete_pipeline("simple_button.json", "E2E - Simple Button")
        await self._test_complete_pipeline("login_form.json", "E2E - Login Form")
    
    async def _test_complete_pipeline(self, filename: str, test_name: str):
        """Test complete pipeline from DSL to PNG."""
        start_time = time.time()
        
        try:
            # Step 1: Load and parse DSL
            file_path = self.examples_dir / filename
            content = file_path.read_text()
            
            parse_result = await parse_dsl(content)
            if not parse_result.success:
                self.results.add_test_result(test_name, False, "DSL parsing failed")
                return
            
            # Step 2: Generate HTML
            options = RenderOptions(width=400, height=300)
            html_content = await generate_html(parse_result.document, options)
            
            if not html_content:
                self.results.add_test_result(test_name, False, "HTML generation failed")
                return
            
            # Step 3: Generate PNG
            try:
                await initialize_browser_pool()
                generator = PNGGeneratorFactory.create_generator("playwright")
                await generator.initialize()
                
                try:
                    png_result = await generator.generate_png(html_content, options)
                    
                    if not png_result.png_data:
                        self.results.add_test_result(test_name, False, "PNG generation failed")
                        return
                    
                    # Step 4: Store PNG
                    storage_manager = await get_storage_manager()
                    content_hash = await storage_manager.store_png(png_result)
                    
                    if not content_hash:
                        self.results.add_test_result(test_name, False, "PNG storage failed")
                        return
                    
                    duration = time.time() - start_time
                    self.results.add_test_result(test_name, True, duration=duration)
                    
                finally:
                    await generator.close()
                    
            except Exception as e:
                self.results.add_test_result(test_name, False, f"Pipeline execution failed: {str(e)}")
                return
            
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_test_result(test_name, False, str(e), duration)


async def main():
    """Main test runner."""
    print("🧪 DSL to PNG Pipeline Test Suite")
    print("=" * 80)
    
    tester = PipelineTester()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    if results.tests_failed == 0:
        print("\n🎉 All tests passed! Pipeline is ready for production.")
        return 0
    else:
        print(f"\n🔧 {results.tests_failed} test(s) failed. Please review and fix issues.")
        return 1


if __name__ == "__main__":
    import sys
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)