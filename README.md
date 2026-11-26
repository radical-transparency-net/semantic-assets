# Radical Transparency — Semantic Assets

Canonical RDF vocabularies, JSON-LD serializations, RFC 9264 content-negotiation linksets (`RT-P03`), and dereferenceable namespace documentation for the **Radical Transparency Network**.

- **Canonical `rtwl:` Namespace:** `https://w3id.org/rt/ns/weblink#`
- **Human Documentation (GitHub Pages):** `https://radical-transparency-net.github.io/semantic-assets/weblink/`

---

## Contents

- [`weblink/`](weblink/) — First draft (`v0.1.0-draft`) of the **Radical Transparency Web Linking Vocabulary (`rtwl:`)**, providing lossless RDF reification for RFC 8288 Web Links and RFC 9264 Linksets (`weblink.ttl`, `weblink.jsonld`, `weblink.linkset.json`, `weblink.linkset`, `index.html`, and `examples/observed-links.ttl`).
- [`assets/`](assets/) — Official Radical Transparency monochrome lace logo and favicon.
- **Persistent Identifier Routing (`w3id.org`):** Managed in [`radical-transparency-net/w3id.org`](https://github.com/radical-transparency-net/w3id.org/tree/master/ids/rt) (`ids/rt/`, upstream [`perma-id/w3id.org`](https://github.com/perma-id/w3id.org/tree/master/ids/rt)) with `303 See Other` content negotiation and `Link` headers exposing the `RT-P03` variant menu.

---

## Local Preview

```bash
python3 -m http.server 8080
```

Open `http://127.0.0.1:8080/weblink/` to inspect the human-readable vocabulary documentation and machine-readable `<link rel="alternate">` / `<link rel="linkset">` declarations.
