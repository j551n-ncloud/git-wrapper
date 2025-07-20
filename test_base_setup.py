#!/usr/bin/env python3
"""
Test script to verify the base setup for advanced Git features.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("Testing imports...")
    
    try:
        from git_wrapper import InteractiveGitWrapper
        print("✅ Main git wrapper imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import main git wrapper: {e}")
        return False
    
    try:
        from features.base_manager import BaseFeatureManager
        print("✅ Base manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import base manager: {e}")
        return False
    
    # Test feature manager imports
    feature_modules = [
        'stash_manager', 'commit_template_engine', 'branch_workflow_manager',
        'conflict_resolver', 'repository_health_dashboard', 'smart_backup_system'
    ]
    
    for module in feature_modules:
        try:
            exec(f"from features.{module} import *")
            print(f"✅ {module} imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import {module}: {e}")
            return False
    
    return True

def test_configuration():
    """Test configuration loading and advanced features setup."""
    print("\nTesting configuration...")
    
    try:
        from git_wrapper import InteractiveGitWrapper
        wrapper = InteractiveGitWrapper()
        
        # Check if advanced_features is in config
        if 'advanced_features' in wrapper.config:
            print("✅ Advanced features configuration loaded")
            
            # Check each feature config
            expected_features = [
                'stash_management', 'commit_templates', 'branch_workflows',
                'conflict_resolution', 'health_dashboard', 'backup_system'
            ]
            
            for feature in expected_features:
                if feature in wrapper.config['advanced_features']:
                    print(f"✅ {feature} configuration present")
                else:
                    print(f"❌ {feature} configuration missing")
                    return False
        else:
            print("❌ Advanced features configuration not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_feature_initialization():
    """Test feature manager initialization."""
    print("\nTesting feature initialization...")
    
    try:
        from git_wrapper import InteractiveGitWrapper
        wrapper = InteractiveGitWrapper()
        
        # Test lazy loading
        print("Testing lazy loading...")
        if not wrapper._features_initialized:
            print("✅ Features not initialized yet (lazy loading working)")
        else:
            print("⚠️ Features already initialized")
        
        # Test has_advanced_features
        has_features = wrapper.has_advanced_features()
        print(f"✅ has_advanced_features() returned: {has_features}")
        
        # Test feature manager access
        stash_manager = wrapper.get_feature_manager('stash')
        if stash_manager:
            print("✅ Stash manager accessible")
        else:
            print("❌ Stash manager not accessible")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Feature initialization test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Advanced Git Features Base Setup")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_feature_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Base setup is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the setup.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)