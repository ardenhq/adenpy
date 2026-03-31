#!/usr/bin/env python3
"""
Basic test runner for ArdenPy library.
Designed for GitHub Actions CI/CD pipeline - runs only essential tests without external dependencies.
"""

import unittest
import sys
import os

def run_basic_tests():
    """Run basic tests and return exit code."""
    
    # Add the current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # Import and run only the basic test module
    try:
        import tests.test_basic as test_basic
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(test_basic)
        
        # Run tests with verbose output
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            buffer=True,
            failfast=False
        )
        
        print("=" * 70)
        print("ARDENPY BASIC TEST SUITE")
        print("=" * 70)
        print(f"Python version: {sys.version}")
        print("=" * 70)
        
        result = runner.run(suite)
        
        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print(f"\nFAILURES ({len(result.failures)}):")
            for test, traceback in result.failures:
                print(f"  - {test}")
                print(f"    {traceback.split('AssertionError:')[-1].strip() if 'AssertionError:' in traceback else 'See details above'}")
        
        if result.errors:
            print(f"\nERRORS ({len(result.errors)}):")
            for test, traceback in result.errors:
                print(f"  - {test}")
                print(f"    {traceback.split('Exception:')[-1].strip() if 'Exception:' in traceback else 'See details above'}")
        
        success = len(result.failures) == 0 and len(result.errors) == 0
        
        if success:
            print("\n✅ ALL BASIC TESTS PASSED!")
            print("ArdenPy library is ready for GitHub Actions!")
            return 0
        else:
            print("\n❌ SOME BASIC TESTS FAILED!")
            return 1
            
    except ImportError as e:
        print(f"❌ Failed to import test module: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error running tests: {e}")
        return 1

if __name__ == '__main__':
    exit_code = run_basic_tests()
    sys.exit(exit_code)
