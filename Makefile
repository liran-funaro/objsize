# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINX_OPTS    ?=
SPHINX_BUILD   ?= sphinx-build
SOURCE_DIR      = docs
BUILD_DIR       = docs-build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINX_BUILD) -M help "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)

.PHONY: help Makefile

clean:
	rm -rf "$(BUILD_DIR)" "$(SOURCE_DIR)/library"

# Catch-all target: route all unknown targets to Sphinx using the new "make mode" option.
# $(O) is meant as a shortcut for $(SPHINX_OPTS).
doc-%:
	@$(SPHINX_BUILD) -M $* "$(SOURCE_DIR)" "$(BUILD_DIR)" $(SPHINX_OPTS) $(O)


docs: doc-html doc-markdown


readme: doc-markdown
	cp "$(BUILD_DIR)/markdown/index.md" README.md $(SPHINX_OPTS) $(O)


server:
	python3 -m http.server --directory "$(BUILD_DIR)/html"


release:
	@rm -rf dist/*
	python3 -m build || exit
	python3 -m twine upload --repository objsize dist/*

lint:
	black objsize --check --diff
	black ./*.py --check --diff
	flake8 objsize --count --select=E,F,W,C --show-source --max-complexity=10 --max-line-length=120 --statistics  --per-file-ignores='__init__.py:F401'
	pylint objsize -v
	mypy objsize --check-untyped-defs
