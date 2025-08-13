#!/usr/bin/env python3
"""
Dependency Management Script for PAstaLinkBot

This script helps manage dependencies for different environments.
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
        return False


def install_dependencies(env_type, upgrade=False, dev=False):
    """Install dependencies for the specified environment."""
    if env_type == "prod":
        cmd = ["pip", "install", "-r", "requirements/prod.txt"]
        if upgrade:
            cmd.append("--upgrade")
        return run_command(cmd, "Production Dependencies")

    elif env_type == "dev":
        if dev:
            # Use pyproject.toml for development
            cmd = ["pip", "install", "-e", ".[dev]"]
            if upgrade:
                cmd.append("--upgrade")
            return run_command(cmd, "Development Dependencies (pyproject.toml)")
        else:
            # Use requirements file
            cmd = ["pip", "install", "-r", "requirements/dev.txt"]
            if upgrade:
                cmd.append("--upgrade")
            return run_command(cmd, "Development Dependencies")

    elif env_type == "test":
        cmd = ["pip", "install", "-r", "requirements/test.txt"]
        if upgrade:
            cmd.append("--upgrade")
        return run_command(cmd, "Test Dependencies")

    elif env_type == "base":
        cmd = ["pip", "install", "-r", "requirements/base.txt"]
        if upgrade:
            cmd.append("--upgrade")
        return run_command(cmd, "Base Dependencies")

    else:
        print(f"❌ Unknown environment type: {env_type}")
        return False


def setup_pre_commit():
    """Set up pre-commit hooks."""
    cmd = ["pre-commit", "install"]
    return run_command(cmd, "Pre-commit Hooks Setup")


def run_linting():
    """Run code linting and formatting."""
    commands = [
        (["black", "."], "Code Formatting (Black)"),
        (["isort", "."], "Import Sorting (isort)"),
        (["flake8", "."], "Code Linting (flake8)"),
        # (["mypy", "."], "Type Checking (mypy)"),
    ]

    success = True
    for cmd, description in commands:
        if not run_command(cmd, description):
            success = False

    return success


def run_tests():
    """Run tests with coverage."""
    cmd = [
        "python",
        "-m",
        "pytest",
        "--cov=core",
        "--cov=config",
        "--cov=utils",
        "--cov-report=term-missing",
    ]
    return run_command(cmd, "Tests with Coverage")


def show_help():
    """Show help information."""
    help_text = """
PAstaLinkBot Dependency Management

Available commands:
  install <env>     Install dependencies for environment
  setup-dev         Set up development environment
  lint              Run code linting and formatting
  test              Run tests with coverage
  pre-commit        Set up pre-commit hooks

Environments:
  base              Base dependencies only
  prod              Production dependencies
  dev               Development dependencies (with tools)
  test              Test dependencies only

Examples:
  python scripts/manage_deps.py install dev
  python scripts/manage_deps.py setup-dev
  python scripts/manage_deps.py lint
  python scripts/manage_deps.py test
"""
    print(help_text)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="PAstaLinkBot Dependency Management")
    parser.add_argument(
        "command",
        choices=["install", "setup-dev", "lint", "test", "pre-commit", "help"],
    )
    parser.add_argument("env", nargs="?", choices=["base", "prod", "dev", "test"])
    parser.add_argument("--upgrade", "-u", action="store_true", help="Upgrade packages")
    parser.add_argument(
        "--dev", "-d", action="store_true", help="Use pyproject.toml for development"
    )

    args = parser.parse_args()

    if args.command == "help":
        show_help()
        return

    elif args.command == "install":
        if not args.env:
            print("❌ Environment type required for install command")
            print("Use: python scripts/manage_deps.py install <env>")
            return
        success = install_dependencies(args.env, args.upgrade, args.dev)

    elif args.command == "setup-dev":
        print("🚀 Setting up development environment...")
        success = True

        # Install development dependencies
        if not install_dependencies("dev", args.upgrade, True):
            success = False

        # Set up pre-commit hooks
        if success and not setup_pre_commit():
            success = False

        if success:
            print("\n🎉 Development environment setup complete!")
            print("\nNext steps:")
            print("1. Run tests: python scripts/manage_deps.py test")
            print("2. Format code: python scripts/manage_deps.py lint")
            print("3. Start development!")

    elif args.command == "lint":
        success = run_linting()

    elif args.command == "test":
        success = run_tests()

    elif args.command == "pre-commit":
        success = setup_pre_commit()

    else:
        print(f"❌ Unknown command: {args.command}")
        show_help()
        return

    if success:
        print("\n🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some operations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
