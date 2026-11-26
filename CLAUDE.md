# Claude Code Project Guidelines

Please consult and strictly adhere to the repository directives defined in [AGENTS.md](AGENTS.md) and [`.agents/rules/source-of-truth-and-build.md`](.agents/rules/source-of-truth-and-build.md).

Key Highlights:
- Keep all committed files in factual English.
- Follow the source-only policy: edit `<vocab>/<vocab>.ttl`, `<vocab>/examples/*.ttl`, or `scripts/`; derived `.jsonld`, `.linkset*`, `.html`, and `sitemap-semantic-assets.xml` outputs are `.gitignore`d and built by GitHub Actions.
- Run `make all && make check` (or `make <vocab>` for single-vocabulary builds) and inspect rendered HTML before finishing.
