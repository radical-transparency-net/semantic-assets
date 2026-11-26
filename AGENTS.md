# AI Agent Guidelines & Repository Directives (`AGENTS.md`)

This repository (`radical-transparency-net/semantic-assets`) hosts the canonical RDF vocabularies, JSON-LD serializations, `RT-P03` linksets, `RT-P06` ResourceSync sitemaps, and HTML documentation for the **Radical Transparency Network**.

---

## 1. Authoritative Directives

- **Strictly English Repository Artifacts:** All vocabulary labels, comments, documentation, templates, scripts, and commit-ready notes must be written in clear, factual English.
- **Turtle as Single Source of Truth (Source-Only Git Repository):** Only edit `<vocab>/<vocab>.ttl`, `<vocab>/examples/*.ttl`, or generator code under `scripts/`. Derived outputs (`index.html`, `*/index.html`, `*/*.jsonld`, `*/*.linkset`, `*/*.linkset.json`, `sitemap-semantic-assets.xml`) are **`.gitignore`d and must never be committed**. Always generate and verify them locally via `make all && make check` (or `make <vocab>` for a single vocabulary). See [`.agents/rules/source-of-truth-and-build.md`](.agents/rules/source-of-truth-and-build.md).
- **Keep `w3id.org` Redirects Aligned:** When adding a new `<vocab>/` or changing namespace IRIs, ensure the external `w3id.org` (`ids/rt/ns/.htaccess`) routing rules stay synchronized.
- **Standards Fidelity:** Preserve accurate references to IETF RFC 8288 (Web Linking), RFC 9264 (Linksets), ResourceSync (`xmlns:rs`), RDFS/OWL semantics, and `perma-id/w3id.org` conventions.
- **Zero Secrets:** Never commit API tokens, personal credentials, or private server details. Keep personal developer directives out of public commits via `.agents/local/**`.

---

## 2. Verification Before Completion

Before declaring vocabulary, template, or build-script edits complete:

1. Run the generator and drift check:
   ```bash
   make all && make check
   ```
2. Visually inspect the rendered HTML pages (`index.html`, `<vocab>/index.html`) in a browser or headless Chromium screenshot.
