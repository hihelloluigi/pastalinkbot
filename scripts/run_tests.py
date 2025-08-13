#!/usr/bin/env python3
"""
Test runner for PAstaLinkBot.

This script provides an easy way to run different types of tests
with various configurations.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print(f"\n✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"\n❌ Command not found: {cmd[0]}")
        print(
            "Make sure pytest is installed: pip install pytest pytest-asyncio pytest-cov pytest-mock"
        )
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="PAstaLinkBot Test Runner")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all", "coverage", "quick", "basic"],
        default="basic",
        help="Type of tests to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--slow", action="store_true", help="Include slow tests")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop on first failure")

    args = parser.parse_args()

    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]

    if args.verbose:
        base_cmd.append("-v")

    if args.stop_on_failure:
        base_cmd.append("-x")

    # Test type specific commands
    if args.type == "basic":
        cmd = base_cmd + ["../tests/test_basic.py"]
        success = run_command(cmd, "Basic Tests")

    elif args.type == "unit":
        cmd = base_cmd + ["-m", "unit", "--ignore=../tests/test_handlers_integration.py"]
        success = run_command(cmd, "Unit Tests")

    elif args.type == "integration":
        cmd = base_cmd + ["-m", "integration", "../tests/test_handlers_integration.py"]
        success = run_command(cmd, "Integration Tests")

    elif args.type == "coverage":
        cmd = base_cmd + [
            "--cov=core",
            "--cov=config",
            "--cov=utils",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=80",
        ]
        success = run_command(cmd, "Tests with Coverage")

    elif args.type == "quick":
        cmd = base_cmd + [
            "-m",
            "not slow",
            "--ignore=../tests/test_handlers_integration.py",
        ]
        success = run_command(cmd, "Quick Tests (excluding slow tests)")

    else:  # all
        cmd = base_cmd
        if not args.slow:
            cmd.extend(["-m", "not slow"])
        success = run_command(cmd, "All Tests")

    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
