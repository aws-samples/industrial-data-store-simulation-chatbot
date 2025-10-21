#!/usr/bin/env python3
"""
Simple test runner for integration tests.
"""

import sys
import os

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(project_root)  # Go up one level from tests/ to project root
sys.path.insert(0, project_root)

def main():
    print("🧪 Running Integration Tests for Production Meeting Agents...")
    print("=" * 70)
    
    try:
        # Test 10.1: Agent tool functionality
        print("\n📋 Task 10.1: Testing Agent Tool Functionality")
        print("-" * 50)
        
        # Import and run agent tool tests
        import test_integration_agent_tools
        agent_success = test_integration_agent_tools.run_integration_tests()
        
        print("\n📋 Task 10.2: Testing Dashboard Integration")
        print("-" * 50)
        
        # Import and run dashboard integration tests
        import test_integration_dashboard
        dashboard_success = test_integration_dashboard.run_dashboard_integration_tests()
        
        # Overall results
        print("\n" + "=" * 70)
        print("🎯 INTEGRATION TEST SUMMARY")
        print("=" * 70)
        
        if agent_success and dashboard_success:
            print("✅ ALL INTEGRATION TESTS PASSED!")
            print("\n🎉 Task 10 'Integration testing and validation' completed successfully!")
            print("\nValidated:")
            print("  ✓ Agent tool functionality with database tools")
            print("  ✓ Query routing and multi-domain analysis coordination")
            print("  ✓ Error handling and graceful degradation scenarios")
            print("  ✓ AI insights replacement in dashboard tabs")
            print("  ✓ Contextual insights generation for different contexts")
            print("  ✓ Existing dashboard functionality preservation")
            return True
        else:
            print("❌ SOME INTEGRATION TESTS FAILED")
            print(f"  Agent Tools: {'✅ PASSED' if agent_success else '❌ FAILED'}")
            print(f"  Dashboard Integration: {'✅ PASSED' if dashboard_success else '❌ FAILED'}")
            return False
            
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)