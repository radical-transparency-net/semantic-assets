.DEFAULT_GOAL := help

UV ?= uv
PYTHON ?= python3
PORT ?= 8080
BASE_URL ?= https://radical-transparency.net/semantic-assets

# Auto-discover every vocabulary folder containing <vocab>/<vocab>.ttl
VOCABS := $(sort $(foreach d,$(wildcard */),$(if $(wildcard $(d)$(patsubst %/,%,$(d)).ttl),$(patsubst %/,%,$(d)))))
GENERATED_FILES := index.html sitemap-semantic-assets.xml $(foreach v,$(VOCABS),$(v)/$(v).jsonld $(v)/$(v).context.jsonld $(v)/$(v).linkset $(v)/$(v).linkset.json $(v)/index.html $(patsubst %.ttl,%.jsonld,$(wildcard $(v)/examples/*.ttl)))

.PHONY: help all clean check serve $(VOCABS)

help: ## List available build targets
	@echo "Radical Transparency — semantic-assets build targets"
	@echo ""
	@echo "Vocabularies (discovered from <vocab>/<vocab>.ttl):"
	@for v in $(VOCABS); do \
		printf "  make %-18s Build derived assets for '%s' only\n" "$$v" "$$v"; \
	done
	@echo ""
	@echo "Site-wide targets:"
	@echo "  make all               Build all vocabularies, root index.html, and sitemap-semantic-assets.xml"
	@echo "  make clean             Remove all generated build artifacts"
	@echo "  make check             Verify all generated files on disk match Turtle sources"
	@echo "  make serve             Serve the repository locally on http://127.0.0.1:$(PORT)/"
	@echo "  make help              Show this help message (default target)"
	@echo ""
	@echo "Variables:"
	@echo "  BASE_URL=<url>         Hosted base URL (default: $(BASE_URL))"
	@echo "  PORT=<port>            Port for 'make serve' (default: 8080)"

all: ## Build all vocabularies plus root portal index.html and sitemap-semantic-assets.xml
	$(UV) run scripts/build.py --base-url "$(BASE_URL)"

clean: ## Remove generated artifacts
	rm -f $(GENERATED_FILES)

check: ## Verify generated files match Turtle sources without modifying disk
	$(UV) run scripts/build.py --check --base-url "$(BASE_URL)"

serve: ## Serve the site locally for preview
	$(PYTHON) -m http.server $(PORT)

$(VOCABS):
	$(UV) run scripts/build.py --vocab $@ --base-url "$(BASE_URL)"
