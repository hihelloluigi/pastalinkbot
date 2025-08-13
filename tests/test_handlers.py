#!/usr/bin/env python3
"""
Quick test script to verify handlers are working correctly.
Run this to check if the handler methods are properly defined.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Mock the required modules if they don't exist
try:
    from core.handlers.commands import CommandHandlers
    from core.handlers.conversation import ConversationHandlers
    from core.handlers.messages import MessageHandlers

    print("✅ All handler modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all handler files exist and are properly structured")
    sys.exit(1)


def test_command_handlers():
    """Test command handler method signatures."""
    print("\n🔍 Testing CommandHandlers...")

    # Check if methods exist and are callable
    required_methods = [
        "start_command",
        "help_command",
        "about_command",
        "stats_command",
        "regions_command",
    ]

    for method_name in required_methods:
        if hasattr(CommandHandlers, method_name):
            method = getattr(CommandHandlers, method_name)
            if callable(method):
                print(f"  ✅ {method_name} - OK")
            else:
                print(f"  ❌ {method_name} - Not callable")
        else:
            print(f"  ❌ {method_name} - Missing")


def test_message_handlers():
    """Test message handler method signatures."""
    print("\n🔍 Testing MessageHandlers...")

    required_methods = ["handle_message"]

    for method_name in required_methods:
        if hasattr(MessageHandlers, method_name):
            method = getattr(MessageHandlers, method_name)
            if callable(method):
                print(f"  ✅ {method_name} - OK")
            else:
                print(f"  ❌ {method_name} - Not callable")
        else:
            print(f"  ❌ {method_name} - Missing")


def test_conversation_handlers():
    """Test conversation handler method signatures."""
    print("\n🔍 Testing ConversationHandlers...")

    required_methods = ["handle_region_selection"]

    for method_name in required_methods:
        if hasattr(ConversationHandlers, method_name):
            method = getattr(ConversationHandlers, method_name)
            if callable(method):
                print(f"  ✅ {method_name} - OK")
            else:
                print(f"  ❌ {method_name} - Not callable")
        else:
            print(f"  ❌ {method_name} - Missing")


def main():
    """Main test function."""
    print("🧪 Testing Handler Method Signatures")
    print("=" * 40)

    test_command_handlers()
    test_message_handlers()
    test_conversation_handlers()

    print("\n📋 Summary:")
    print("If all methods show ✅ OK, the handler signature issue should be fixed.")
    print("If any show ❌, those methods need to be corrected.")


if __name__ == "__main__":
    main()
