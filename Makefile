PO_LANGS = it en fr de es
PO_DIRS  = $(addsuffix /LC_MESSAGES, $(addprefix locale/,$(PO_LANGS)))
PO_FILES = $(addsuffix /messages.po, $(PO_DIRS))
MO_FILES = $(addsuffix /messages.mo, $(PO_DIRS))

.PHONY: i18n-extract i18n-init i18n-compile i18n-refresh

# Extract translatable strings from .py files into a .pot template
i18n-extract:
	find . -path './.venv' -prune -o -name '*.py' -print \
	| xargs xgettext --from-code=UTF-8 --language=Python --keyword=_ \
	  --package-name="PAstaLinkBot" --package-version="0.1.0" \
	  --output=locale/messages.pot

# Initialize .po files for each language if not already created
i18n-init:
	for L in $(PO_LANGS); do \
	  mkdir -p locale/$$L/LC_MESSAGES; \
	  [ -f locale/$$L/LC_MESSAGES/messages.po ] || \
	  msginit --no-translator --locale=$$L \
	    --input=locale/messages.pot \
	    --output-file=locale/$$L/LC_MESSAGES/messages.po; \
	done

# Compile all .po into .mo for runtime
i18n-compile:
	for L in $(PO_LANGS); do \
	  msgfmt locale/$$L/LC_MESSAGES/messages.po \
	    -o locale/$$L/LC_MESSAGES/messages.mo; \
	done

# Refresh translations: extract and merge into existing .po files
i18n-refresh: i18n-extract
	for L in $(PO_LANGS); do \
	  msgmerge --update --backup=off locale/$$L/LC_MESSAGES/messages.po locale/messages.pot; \
	done