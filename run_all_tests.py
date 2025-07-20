#!/usr/bin/env python3
"""
Comprehensive test runner for advanced Git features
"""

import unittest
import sys
import os
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse


class TestResult:
    """Container for test results"""
    
    def __init__(self, name: str, success: bool, duration: float, 
                 errors: List[str] = None, failures: List[str] = None):
        self.name = name
        self.success = success
        self.duration = duration
        self.errors = errors or []
        self.failures = failures or []


class ComprehensiveTestRunner:
    """Comprehensive test runner for all advanced Git features"""
    
    def __init__(self):
        """Initialize the test runner"""
        self.test_modules = [
            # Integration tests
            'test_integration_feature_interactions',
            'test_end_to_end_workflows',
            'test_git_command_integration',
            
            # Performance tests
            'test_performance_large_repositories',
            
            # Existing unit tests
            'test_base_setup',
            'test_feature_initialization',
            'test_menu_integration',
            'test_stash_manager',
            'test_commit_template_engine',
            'test_branch_workflow_manager',
            'test_conflict_resolver',
            'test_repository_health_dashboard',
            'test_smart_backup_system',
            'test_configuration_management',
            'test_interactive_configuration',
            'test_debug_logging',
            'test_error_handling',
            'test_emoji_compatibility'
        ]
        
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def run_single_test_module(self, module_name: str, verbose: bool = False) -> TestResult:
        """
        Run a single test module.
        
        Args:
            module_name: Name of the test module
            verbose: Whether to show verbose output
            
        Returns:
            TestResult object
        """
        print(f"Running {module_name}...")
        start_time = time.time()
        
        try:
            # Import the test module
            test_module = __import__(module_name)
            
            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Run tests
            runner = unittest.TextTestRunner(
                verbosity=2 if verbose else 1,
                stream=sys.stdout if verbose else open(os.devnull, 'w')
            )
            
            result = runner.run(suite)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Collect errors and failures
            errors = [str(error[1]) for error in result.errors]
            failures = [str(failure[1]) for failure in result.failures]
            
            success = len(errors) == 0 and len(failures) == 0
            
            return TestResult(
                name=module_name,
                success=success,
                duration=duration,
                errors=errors,
                failures=failures
            )
            
        except ImportError as e:
            end_time = time.time()
            duration = end_time - start_time
            
            return TestResult(
                name=module_name,
                success=False,
                duration=duration,
                errors=[f"Import error: {str(e)}"]
            )
        
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            return TestResult(
                name=module_name,
                success=False,
                duration=duration,
                errors=[f"Unexpected error: {str(e)}"]
            )
    
    def run_all_tests(self, verbose: bool = False, 
                     include_performance: bool = True,
                     include_integration: bool = True,
                     modules_filter: List[str] = None) -> Dict[str, Any]:
        """
        Run all test modules.
        
        Args:
            verbose: Whether to show verbose output
            include_performance: Whether to include performance tests
            include_integration: Whether to include integration tests
            modules_filter: Optional list of specific modules to run
            
        Returns:
            Dictionary with test results summary
        """
        self.start_time = time.time()
        
        # Filter test modules based on parameters
        modules_to_run = self.test_modules.copy()
        
        if not include_performance:
            modules_to_run = [m for m in modules_to_run if 'performance' not in m]
        
        if not include_integration:
            modules_to_run = [m for m in modules_to_run 
                            if not any(keyword in m for keyword in ['integration', 'end_to_end'])]
        
        if modules_filter:
            modules_to_run = [m for m in modules_to_run if m in modules_filter]
        
        print(f"Running {len(modules_to_run)} test modules...")
        print("=" * 60)
        
        # Run each test module
        for module_name in modules_to_run:
            result = self.run_single_test_module(module_name, verbose)
            self.results.append(result)
            
            # Print immediate result
            status = "✅ PASS" if result.success else "❌ FAIL"
            print(f"{status} {module_name} ({result.duration:.2f}s)")
            
            if not result.success and not verbose:
                # Show errors/failures even in non-verbose mode
                for error in result.errors:
                    print(f"  ERROR: {error}")
                for failure in result.failures:
                    print(f"  FAILURE: {failure}")
        
        self.end_time = time.time()
        
        # Generate summary
        return self.generate_summary()
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate test results summary"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        summary = {
            'total_modules': total_tests,
            'passed_modules': passed_tests,
            'failed_modules': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'total_duration': total_duration,
            'results': self.results
        }
        
        return summary
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total modules: {summary['total_modules']}")
        print(f"Passed: {summary['passed_modules']}")
        print(f"Failed: {summary['failed_modules']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        print(f"Total duration: {summary['total_duration']:.2f}s")
        
        if summary['failed_modules'] > 0:
            print("\nFAILED MODULES:")
            for result in summary['results']:
                if not result.success:
                    print(f"  ❌ {result.name} ({result.duration:.2f}s)")
                    for error in result.errors:
                        print(f"    ERROR: {error}")
                    for failure in result.failures:
                        print(f"    FAILURE: {failure}")
        
        print("\nPERFORMANCE BREAKDOWN:")
        for result in sorted(summary['results'], key=lambda x: x.duration, reverse=True):
            status = "✅" if result.success else "❌"
            print(f"  {status} {result.name}: {result.duration:.2f}s")
    
    def run_git_availability_check(self) -> bool:
        """Check if Git is available for testing"""
        try:
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"Git available: {result.stdout.strip()}")
                return True
            else:
                print("Git not available or not working properly")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Git not found or not accessible")
            return False
    
    def run_python_environment_check(self) -> Dict[str, Any]:
        """Check Python environment for testing"""
        env_info = {
            'python_version': sys.version,
            'python_executable': sys.executable,
            'current_directory': os.getcwd(),
            'path_entries': sys.path[:5],  # First 5 entries
            'available_modules': []
        }
        
        # Check for required modules
        required_modules = ['unittest', 'subprocess', 'pathlib', 'json', 'tempfile']
        for module in required_modules:
            try:
                __import__(module)
                env_info['available_modules'].append(module)
            except ImportError:
                pass
        
        return env_info
    
    def run_feature_availability_check(self) -> Dict[str, bool]:
        """Check which features are available for testing"""
        feature_availability = {}
        
        try:
            # Add current directory to path for imports
            sys.path.insert(0, os.getcwd())
            
            from git_wrapper import InteractiveGitWrapper
            wrapper = InteractiveGitWrapper()
            
            # Mock print methods to avoid output
            wrapper.print_info = lambda x: None
            wrapper.print_success = lambda x: None
            wrapper.print_error = lambda x: None
            
            # Check each feature
            feature_names = ['stash', 'templates', 'workflows', 'conflicts', 'health', 'backup']
            for feature_name in feature_names:
                try:
                    manager = wrapper.get_feature_manager(feature_name)
                    feature_availability[feature_name] = manager is not None
                except Exception:
                    feature_availability[feature_name] = False
            
        except Exception as e:
            print(f"Error checking feature availability: {e}")
            for feature_name in ['stash', 'templates', 'workflows', 'conflicts', 'health', 'backup']:
                feature_availability[feature_name] = False
        
        return feature_availability
    
    def run_pre_test_checks(self) -> bool:
        """Run pre-test environment checks"""
        print("Running pre-test environment checks...")
        print("-" * 40)
        
        # Check Git availability
        git_available = self.run_git_availability_check()
        
        # Check Python environment
        env_info = self.run_python_environment_check()
        print(f"Python version: {env_info['python_version'].split()[0]}")
        print(f"Working directory: {env_info['current_directory']}")
        
        # Check feature availability
        feature_availability = self.run_feature_availability_check()
        available_features = [name for name, available in feature_availability.items() if available]
        unavailable_features = [name for name, available in feature_availability.items() if not available]
        
        print(f"Available features: {', '.join(available_features) if available_features else 'None'}")
        if unavailable_features:
            print(f"Unavailable features: {', '.join(unavailable_features)}")
        
        print("-" * 40)
        
        # Determine if we can proceed
        can_proceed = git_available and len(available_features) > 0
        
        if not can_proceed:
            print("❌ Pre-test checks failed. Cannot proceed with testing.")
            if not git_available:
                print("  - Git is not available")
            if len(available_features) == 0:
                print("  - No features are available")
        else:
            print("✅ Pre-test checks passed. Ready to run tests.")
        
        return can_proceed


def main():
    """Main function for test runner"""
    parser = argparse.ArgumentParser(description='Run comprehensive tests for advanced Git features')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Show verbose test output')
    parser.add_argument('--no-performance', action='store_true',
                       help='Skip performance tests')
    parser.add_argument('--no-integration', action='store_true',
                       help='Skip integration tests')
    parser.add_argument('--modules', nargs='+', 
                       help='Run only specific test modules')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip pre-test environment checks')
    parser.add_argument('--list-modules', action='store_true',
                       help='List available test modules and exit')
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    # List modules if requested
    if args.list_modules:
        print("Available test modules:")
        for module in runner.test_modules:
            print(f"  - {module}")
        return 0
    
    # Run pre-test checks unless skipped
    if not args.skip_checks:
        if not runner.run_pre_test_checks():
            return 1
        print()
    
    # Run tests
    try:
        summary = runner.run_all_tests(
            verbose=args.verbose,
            include_performance=not args.no_performance,
            include_integration=not args.no_integration,
            modules_filter=args.modules
        )
        
        # Print summary
        runner.print_summary(summary)
        
        # Return appropriate exit code
        return 0 if summary['failed_modules'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error during test run: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)