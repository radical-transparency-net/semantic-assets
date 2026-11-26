# AI Agent Guidelines & Repository Directives (`AGENTS.md`)

This repository (`radical-transparency-net/semantic-assets`) hosts the canonical RDF vocabularies, JSON-LD serializations, dereferenceable HTML documentation, and `w3id.org` redirect configurations for the **Radical Transparency Network**.

---

## 1. Authoritative Directives

- **Strictly English Repository Artifacts:** All vocabulary labels, comments, documentation, HTML pages, and commit-ready notes must be written in clear, factual English.
- **Turtle as Single Source of Truth:** Treat `weblink/weblink.ttl` (and future `*.ttl` vocabulary files) as the canonical ontology source. Keep `weblink.jsonld`, `weblink.linkset.json`, `weblink.linkset`, `weblink/index.html`, and the external `w3id.org` (`ids/rt/.htaccess`) redirects synchronized whenever classes, properties, or namespace IRIs change.
- **Standards Fidelity:** Preserve accurate references to IETF RFC 8288 (Web Linking), RFC 9264 (Linksets), RDFS/OWL semantics, and `perma-id/w3id.org` content-negotiation conventions. Clearly mark unresolved modeling choices with `skos:editorialNote`.
- **Zero Secrets:** Never commit API tokens, personal credentials, or private server details. Keep personal developer directives out of public commits via `.agents/local/**`.

---

## 2. Verification Before Completion

Before declaring vocabulary or documentation edits complete:

1. Validate JSON-LD syntax (`python3 -m json.tool weblink/weblink.jsonld > /dev/null`).
2. Verify Turtle syntax and prefix consistency across `weblink/weblink.ttl` and `weblink/examples/*.ttl`.
3. Verify fragment IDs in `weblink/index.html` match every class and property local name defined in `weblink.ttl`, and visually inspect the rendered HTML page.
