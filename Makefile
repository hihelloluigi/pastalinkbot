PO_LANGS = it en
PO_DIRS  = $(addsuffix /LC_MESSAGES, $(addprefix locale/,$(PO_LANGS)))
PO_FILES = $(addsuffix /messages.po, $(PO_DIRS))
MO_FILES = $(addsuffix /messages.mo, $(PO_DIRS))

.PHONY: i18n-extract i18n-init i18n-compile i18n-refresh test test-unit test-integration test-coverage test-quick test-basic install-dev

# Extract translatable strings from .py files into a .pot template
i18n-extract:
	find . -path './.venv' -prune -o -name '*.py' -print \
	| xargs xgettext --from-code=UTF-8 --language=Python --keyword=_ \
	  --package-name="PAstaLinkBot" --package-version="0.1.0" \
	  --output=date/locale/messages.pot

# Initialize .po files for each language if not already created
i18n-init:
	for L in $(PO_LANGS); do \
	  mkdir -p date/locale/$$L/LC_MESSAGES; \
	  [ -f data/locale/$$L/LC_MESSAGES/messages.po ] || \
	  msginit --no-translator --locale=$$L \
	    --input=date/locale/messages.pot \
	    --output-file=date/locale/$$L/LC_MESSAGES/messages.po; \
	done

# Compile all .po into .mo for runtime
i18n-compile:
	for L in $(PO_LANGS); do \
	  msgfmt data/locale/$$L/LC_MESSAGES/messages.po \
	    -o data/locale/$$L/LC_MESSAGES/messages.mo; \
	done

# Refresh translations: extract and merge into existing .po files
i18n-refresh: i18n-extract
	for L in $(PO_LANGS); do \
	  msgmerge --update --backup=off date/locale/$$L/LC_MESSAGES/messages.po date/locale/messages.pot; \
	done

# Install dependencies for different environments
install-base:
	pip install -r requirements/base.txt

install-prod:
	pip install -r requirements/prod.txt

install-dev:
	pip install -r requirements/dev.txt

install-test:
	pip install -r requirements/test.txt

# Install using pyproject.toml (recommended)
install-dev-modern:
	pip install -e .[dev]

install-test-modern:
	pip install -e .[test]

# Setup development environment
setup-dev:
	python scripts/manage_deps.py setup-dev

# Run all tests
test:
	python scripts/run_tests.py --type all

# Run tests with coverage
test-coverage:
	python scripts/run_tests.py --type coverage
	
# Run tests and stop on first failure
test-fail-fast:
	python scripts/run_tests.py --type all --stop-on-failure

# Run tests with verbose output
test-verbose:
	python scripts/run_tests.py --type all --verbose

# Code quality and linting
lint:
	python scripts/manage_deps.py lint

format:
	black .
	isort .

check-types:
	mypy .

# Pre-commit hooks
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Dependency management
deps-help:
	python scripts/manage_deps.py help

deps-install:
	python scripts/manage_deps.py install dev

deps-upgrade:
	python scripts/manage_deps.py install dev --upgrade