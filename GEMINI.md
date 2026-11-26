# Gemini CLI Project Directives

Please consult and strictly adhere to the authoritative repository directives defined in [AGENTS.md](AGENTS.md) and [`.agents/rules/source-of-truth-and-build.md`](.agents/rules/source-of-truth-and-build.md).

Key Directives:
- Keep all repository documentation, vocabulary annotations, templates, and scripts in concise, factual English.
- Follow the source-only policy: treat `*.ttl` as the single source of truth; derived outputs are `.gitignore`d and deployed via GitHub Actions.
- Generate and verify outputs locally via `make all && make check` (or `make <vocab>`) and inspect rendered HTML pages (`index.html`, `<vocab>/index.html`) before completion.
