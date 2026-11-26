# Radical Transparency — Semantic Assets

Canonical RDF vocabularies, JSON-LD serializations, RFC 9264 content-negotiation linksets (`RT-P03`), ResourceSync sitemaps (`RT-P06`), and dereferenceable namespace documentation for the **Radical Transparency Network**.

- **Canonical `rtwl:` Namespace:** `https://w3id.org/rt/ns/weblink#`
- **Portal & Human Documentation:** `https://radical-transparency.net/semantic-assets/`
- **Hostwide Discovery Sitemap (`RT-P06`):** `https://radical-transparency.net/semantic-assets/sitemap-semantic-assets.xml`
- **Persistent Identifier Routing (`w3id.org`):** Managed in [`radical-transparency-net/w3id.org`](https://github.com/radical-transparency-net/w3id.org/tree/master/ids/rt) (`ids/rt/`, upstream `perma-id/w3id.org`)

---

## Repository Structure

This repository is **source-only** (`*.ttl` as the single source of truth); all derived serialization, linkset, HTML, and sitemap files are `.gitignore`d and generated at build/deploy time:

- [`weblink/weblink.ttl`](weblink/weblink.ttl) & [`weblink/examples/`](weblink/examples/) — Authoritative Turtle source for `rtwl:` (`v0.1.0-draft`).
- [`Makefile`](Makefile) — Primary task runner exposing `make` (help), `make <vocab>` (single-vocabulary build), `make all`, `make clean`, `make check`, and `make serve`.
- [`scripts/build.py`](scripts/build.py) & [`scripts/templates/`](scripts/templates/) — Deterministic `uv` build pipeline (`rdflib` + `jinja2`) that validates all Turtle files and generates `.jsonld`, `.linkset.json`, `.linkset`, HTML pages (`weblink/index.html`, root `index.html`), and `sitemap-semantic-assets.xml`.
- [`.github/workflows/build-and-deploy.yml`](.github/workflows/build-and-deploy.yml) — Runs `make all && make check` on pull requests and `main`, deploying the built site to GitHub Pages.
- [`assets/`](assets/) — Official Radical Transparency monochrome lace logo and favicon.
- [`.agents/rules/source-of-truth-and-build.md`](.agents/rules/source-of-truth-and-build.md) — Architectural policy and agent guidelines for source-only tracking.

---

## Automated Build & Validation

All derived artifacts are generated from `<vocab>/<vocab>.ttl` and `<vocab>/examples/*.ttl` via the [`Makefile`](Makefile).

### Dependencies

- **GNU `make`** — Task entrypoint (`make`, `make <vocab>`, `make all`, `make clean`, `make check`, `make serve`).
- **`uv`** (`>= 0.5`) — Automatically provisions Python (`>= 3.11`) and the PEP 723 dependencies declared in [`scripts/build.py`](scripts/build.py) (`rdflib>=7.0.0`, `jinja2>=3.1.0`) in an isolated cache with no manual virtualenv setup required.
- **`python3`** — Only needed directly on your `PATH` for `make serve` (`python3 -m http.server`).

### Usage (`make` Targets)

```bash
# List all available targets and auto-discovered vocabulary folders (default)
make

# Build only a single vocabulary folder (<vocab>.jsonld, <vocab>.linkset*, <vocab>/index.html)
make weblink

# Build every discovered vocabulary plus root index.html and sitemap-semantic-assets.xml
make all

# Verify generated files on disk match Turtle sources
make check

# Remove generated build artifacts from the working tree
make clean

# Serve the generated site locally on http://127.0.0.1:8080/
make serve
```

Default `BASE_URL` in [`Makefile`](Makefile) is `https://radical-transparency.net/semantic-assets`. Optional overrides: `BASE_URL=https://example.org/semantic-assets make all` overrides the hosted base URL in linksets and the sitemap; `PORT=9000 make serve` changes the local preview port. Every folder matching `<vocab>/<vocab>.ttl` is automatically discovered as a `make <vocab>` target.

---

## Contributing

1. **Source-only git policy:** Only commit Turtle sources (`<vocab>/<vocab>.ttl`, `<vocab>/examples/*.ttl`), generator templates/scripts under `scripts/`, `assets/`, `Makefile`, workflow config, and documentation. Never force-add generated files (`*.jsonld`, `*.linkset`, `*.linkset.json`, `index.html`, `*/index.html`, `sitemap-semantic-assets.xml`) — they are excluded by [`.gitignore`](.gitignore) and built cleanly in CI.
2. **GitHub Pages setting:** Because derived HTML, JSON-LD, linkset, and sitemap files are generated at deploy time rather than committed to `main`, repository **Settings → Pages → Build and deployment → Source** MUST be configured to **GitHub Actions**.
3. **Adding a new vocabulary:** Create `<slug>/<slug>.ttl` (declaring `owl:Ontology` with its canonical `w3id.org` IRI and `vann:preferredNamespacePrefix` / `vann:preferredNamespaceUri`) and optional `<slug>/examples/*.ttl`. Both `make` and GitHub Actions will auto-discover `make <slug>` and include it in root `index.html` and `sitemap-semantic-assets.xml`.
4. **Canonical IRIs vs. `BASE_URL`:** Namespace and concept IRIs (`https://w3id.org/rt/ns/<vocab>#`) are always read from `<vocab>/<vocab>.ttl`. `BASE_URL` only controls physical representation URLs in `RT-P03` linksets and `RT-P06` sitemap `<loc>` entries.
5. **Local verification before opening a PR:**
   ```bash
   make clean && make all && make check
   make serve   # optional visual inspection at http://127.0.0.1:8080/
   ```

---

## Integrating `sitemap-semantic-assets.xml` at Root Level (`RT-P06`)

[`sitemap-semantic-assets.xml`](sitemap-semantic-assets.xml) implements `RT-P06` (ResourceSync Sitemap Discovery) for all assets hosted under `/semantic-assets/`. To surface it from the root domain (`https://radical-transparency.net/`), reference it in the root `sitemap-index.xml` and point the root `robots.txt` to that index:

1. **Publish or update `/sitemap-index.xml`** on the root site (`radical-transparency.net`):

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
     <sitemap>
       <loc>https://radical-transparency.net/semantic-assets/sitemap-semantic-assets.xml</loc>
     </sitemap>
   </sitemapindex>
   ```

2. **Point `/robots.txt` on the root site** to the root sitemap index (and optionally directly to sub-sitemaps):

   ```text
   User-agent: *
   Allow: /

   Sitemap: https://radical-transparency.net/sitemap-index.xml
   ```

Whenever a new vocabulary folder (`<vocab>/<vocab>.ttl`) is added and `make all` runs, `sitemap-semantic-assets.xml` updates automatically without needing edits to the root `sitemap-index.xml` or `robots.txt`.
