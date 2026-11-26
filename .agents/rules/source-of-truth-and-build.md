# Source-of-Truth & Build Architecture (`semantic-assets`)

This repository follows a strict **source-only tracking model (Option A)**.

## 1. Tracked Sources vs. Ignored Derived Artifacts

- **Authoritative sources tracked in git:**
  - `<vocab>/<vocab>.ttl` and `<vocab>/examples/*.ttl`
  - `scripts/` (`build.py` and `templates/*.j2`)
  - `assets/` (logo and favicon)
  - `Makefile`, `.github/workflows/build-and-deploy.yml`, and documentation (`README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/rules/`)
- **Derived build artifacts (`.gitignore`d, never committed):**
  - `index.html` and `<vocab>/index.html`
  - `<vocab>/<vocab>.jsonld`
  - `<vocab>/<vocab>.linkset.json` and `<vocab>/<vocab>.linkset`
  - `sitemap-semantic-assets.xml`

## 2. CI/CD Build & GitHub Pages Prerequisite

- Pull requests and pushes to `main` both execute `make all && make check` via [`.github/workflows/build-and-deploy.yml`](../../.github/workflows/build-and-deploy.yml) to validate RDF parsing, Jinja2 rendering, deterministic output, and `RT-P03`/`RT-P06` generation.
- On `main`, the workflow uploads the built site directly as a GitHub Pages artifact.
- **Operational prerequisite:** GitHub repository **Settings -> Pages -> Build and deployment -> Source** MUST be set to **GitHub Actions** (not *Deploy from a branch*).

## 3. Canonical vs. Hosting URL Separation

- **Canonical concept & namespace IRIs** (e.g., `https://w3id.org/rt/ns/weblink` and `https://w3id.org/rt/ns/weblink#`) come exclusively from `<vocab>/<vocab>.ttl` (`owl:Ontology` and `vann:preferredNamespaceUri`). They are never derived from `BASE_URL`.
- **`BASE_URL`** (`https://radical-transparency.net/semantic-assets` by default in `Makefile` and `scripts/build.py`) defines the physical hosting origin used for:
  - Concrete representation URLs (`*.ttl`, `*.jsonld`, `index.html`) inside `RT-P03` linksets.
  - Same-host `<loc>` entries in `RT-P06` (`sitemap-semantic-assets.xml`).
