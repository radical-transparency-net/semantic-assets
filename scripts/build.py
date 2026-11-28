#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "rdflib>=7.0.0",
#   "jinja2>=3.1.0",
# ]
# ///
"""Build deterministic JSON-LD, RT-P03 Linksets, HTML docs, and RT-P06 Sitemap from *.ttl sources.

Single source of truth:
  <vocab>/<vocab>.ttl
  <vocab>/examples/*.ttl

Generated artifacts:
  <vocab>/<vocab>.jsonld
  <vocab>/<vocab>.context.jsonld
  <vocab>/<vocab>.linkset.json
  <vocab>/<vocab>.linkset
  <vocab>/examples/*.jsonld
  <vocab>/index.html
  index.html
  sitemap-semantic-assets.xml
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, OWL, URIRef, XSD
from rdflib.compare import isomorphic
from rdflib.namespace import DCTERMS, SKOS

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
DEFAULT_BASE_URL = "https://radical-transparency.net/semantic-assets"

VANN = Namespace("http://purl.org/vocab/vann/")
SKIP_DIRS = {"scripts", "assets", ".git", ".github", ".agents"}


def discover_vocabularies() -> list[tuple[str, Path]]:
    """Find all <slug>/<slug>.ttl vocabulary directories."""
    vocabs: list[tuple[str, Path]] = []
    for entry in sorted(ROOT_DIR.iterdir()):
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        ttl_file = entry / f"{entry.name}.ttl"
        if ttl_file.is_file():
            vocabs.append((entry.name, ttl_file))
    return vocabs


def local_name(uri: str, ns_uri: str) -> str:
    if uri.startswith(ns_uri):
        return uri[len(ns_uri):]
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def compact_uri(uri: Any, g: Graph) -> str:
    if uri is None:
        return "rdfs:Resource"
    s = str(uri)
    try:
        prefix, _, name = g.namespace_manager.compute_qname(s, generate=False)
        return f"{prefix}:{name}" if prefix else name
    except Exception:
        return s


def first_literal(g: Graph, subj: Any, pred: Any, default: str = "") -> str:
    vals = [str(o) for o in g.objects(subj, pred)]
    return sorted(vals)[0] if vals else default


def license_display(uri: str) -> str:
    if "creativecommons.org/licenses/by/4.0" in uri:
        return "CC BY 4.0"
    return uri


def build_jsonld(g: Graph, ontology_uri: str, prefix: str, ns_uri: str) -> str:
    """Serialize graph to deterministic, compacted JSON-LD."""
    context = {
        prefix: ns_uri,
        "owl": str(OWL),
        "rdf": str(RDF),
        "rdfs": str(RDFS),
        "xsd": str(XSD),
        "dcterms": str(DCTERMS),
        "vann": str(VANN),
        "skos": str(SKOS),
    }
    raw = g.serialize(format="json-ld", context=context, auto_compact=True)
    doc = json.loads(raw)

    # Normalize @graph order deterministically: ontology first, then sorted by @id
    if "@graph" in doc and isinstance(doc["@graph"], list):
        def sort_key(node: dict[str, Any]) -> tuple[int, str]:
            nid = str(node.get("@id", ""))
            return (0 if nid == ontology_uri else 1, nid)

        for node in doc["@graph"]:
            for k, v in list(node.items()):
                if isinstance(v, list) and all(isinstance(x, str) for x in v):
                    node[k] = sorted(v)
                elif isinstance(v, list) and all(isinstance(x, dict) and "@id" in x for x in v):
                    node[k] = sorted(v, key=lambda d: str(d["@id"]))
        doc["@graph"] = sorted(doc["@graph"], key=sort_key)

    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build_context_dict(vocab_data: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON-LD 1.1 @context mapping dictionary for a vocabulary."""
    ctx: dict[str, Any] = {
        "@version": 1.1,
        vocab_data["prefix"]: vocab_data["namespace_uri"],
        "xsd": str(XSD),
    }
    for cls in vocab_data["classes"]:
        ctx[cls["local_name"]] = cls["qname"]
    for prop in vocab_data["properties"]:
        if prop["kind_tag"] == "owl:ObjectProperty":
            ctx[prop["local_name"]] = {"@id": prop["qname"], "@type": "@id"}
        else:
            ctx[prop["local_name"]] = prop["qname"]
    return ctx


def build_context_jsonld(vocab_data: dict[str, Any]) -> str:
    """Generate a deterministic JSON-LD 1.1 @context document for instance data."""
    return json.dumps({"@context": build_context_dict(vocab_data)}, indent=2, ensure_ascii=False) + "\n"


def build_example_jsonld(
    ex_g: Graph,
    vocab_data: dict[str, Any],
    vocab_ctx: dict[str, Any],
    source_name: str,
) -> str:
    """Compile a Turtle example into nested JSON-LD using @context and assert RDF isomorphism."""
    ns_uri = vocab_data["namespace_uri"]
    context_url = f"{vocab_data['concept_uri']}.context.jsonld"

    term_map: dict[str, str] = {}
    id_terms: set[str] = set()
    for cls in vocab_data["classes"]:
        term_map[cls["uri"]] = cls["local_name"]
    for prop in vocab_data["properties"]:
        term_map[prop["uri"]] = prop["local_name"]
        if prop["kind_tag"] == "owl:ObjectProperty":
            id_terms.add(prop["local_name"])

    # Collect bound prefixes used in non-rdf:type positions outside vocab_ctx
    extra_ctx: dict[str, str] = {}
    used_uris: set[str] = set()
    for s, p, o in ex_g:
        if isinstance(s, URIRef):
            used_uris.add(str(s))
        if p != RDF.type:
            used_uris.add(str(p))
        if isinstance(o, URIRef) and p != RDF.type:
            used_uris.add(str(o))
        elif isinstance(o, Literal) and o.datatype:
            used_uris.add(str(o.datatype))

    for pfx, ns in sorted(ex_g.namespaces(), key=lambda x: x[0]):
        ns_s = str(ns)
        if not pfx or pfx in vocab_ctx:
            continue
        if any(u.startswith(ns_s) for u in used_uris):
            extra_ctx[pfx] = ns_s

    def compact_ref(uri_str: str) -> str:
        if uri_str in term_map:
            return term_map[uri_str]
        if uri_str.startswith(ns_uri):
            return f"{vocab_data['prefix']}:{uri_str[len(ns_uri):]}"
        if uri_str.startswith(str(XSD)):
            return f"xsd:{uri_str[len(str(XSD)):]}"
        for pfx, ns_s in sorted(extra_ctx.items(), key=lambda kv: -len(kv[1])):
            if uri_str.startswith(ns_s):
                return f"{pfx}:{uri_str[len(ns_s):]}"
        return uri_str

    bnode_refs: Counter[BNode] = Counter()
    for _, _, o in ex_g:
        if isinstance(o, BNode):
            bnode_refs[o] += 1

    # Assign deterministic labels only to blank nodes referenced multiple times
    shared_bnode_ids: dict[BNode, str] = {}

    def shared_bnode_id(bnode: BNode) -> str:
        if bnode not in shared_bnode_ids:
            shared_bnode_ids[bnode] = f"_:b{len(shared_bnode_ids)}"
        return shared_bnode_ids[bnode]

    def serialize_obj(pred_term: str, obj: Any) -> Any:
        if isinstance(obj, BNode):
            if bnode_refs[obj] == 1:
                return serialize_node(obj)
            return {"@id": shared_bnode_id(obj)}
        if isinstance(obj, URIRef):
            if pred_term in id_terms:
                return str(obj)
            return {"@id": str(obj)}
        if isinstance(obj, Literal):
            if obj.language:
                return {"@value": str(obj), "@language": obj.language}
            if obj.datatype and str(obj.datatype) != str(XSD.string):
                return {"@value": str(obj), "@type": compact_ref(str(obj.datatype))}
            return str(obj)
        return str(obj)

    def serialize_node(subj: Any) -> dict[str, Any]:
        node: dict[str, Any] = {}
        if isinstance(subj, URIRef):
            node["@id"] = str(subj)
        elif isinstance(subj, BNode) and bnode_refs[subj] > 1:
            node["@id"] = shared_bnode_id(subj)

        types = sorted(compact_ref(str(t)) for t in ex_g.objects(subj, RDF.type))
        if types:
            node["@type"] = types[0] if len(types) == 1 else types

        by_pred: dict[str, list[Any]] = {}
        for p, o in ex_g.predicate_objects(subj):
            if p == RDF.type:
                continue
            p_term = compact_ref(str(p))
            by_pred.setdefault(p_term, []).append(serialize_obj(p_term, o))

        for p_term in sorted(by_pred.keys(), key=lambda k: (0 if k in term_map.values() else 1, k)):
            vals = sorted(by_pred[p_term], key=lambda v: json.dumps(v, sort_keys=True))
            node[p_term] = vals[0] if len(vals) == 1 else vals
        return node

    roots = [
        s for s in set(ex_g.subjects())
        if not (isinstance(s, BNode) and bnode_refs[s] == 1)
    ]

    def root_sort_key(node: dict[str, Any]) -> tuple[int, str]:
        t = node.get("@type", "")
        rank = 0 if t == "WebLink" else (1 if t == "Linkset" else 2)
        return (rank, json.dumps(node, sort_keys=True))

    graph_nodes = sorted((serialize_node(r) for r in roots), key=root_sort_key)
    ctx_ref: Any = [context_url, extra_ctx] if extra_ctx else context_url
    doc = {"@context": ctx_ref, "@graph": graph_nodes}

    # Verify lossless round-trip against the local context dictionary
    roundtrip_doc = {
        "@context": [vocab_ctx, extra_ctx] if extra_ctx else vocab_ctx,
        "@graph": graph_nodes,
    }
    g_roundtrip = Graph().parse(data=json.dumps(roundtrip_doc), format="json-ld")
    if not isomorphic(g_roundtrip, ex_g):
        raise ValueError(
            f"{source_name}: JSON-LD round-trip failed RDF isomorphism check "
            f"({len(g_roundtrip)} vs {len(ex_g)} triples)."
        )

    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build_linksets(slug: str, concept_uri: str, base_url: str) -> tuple[str, str]:
    """Generate RFC 9264 application/linkset+json and application/linkset for RT-P03."""
    vocab_base = f"{base_url.rstrip('/')}/{slug}"
    ttl_url = f"{vocab_base}/{slug}.ttl"
    jsonld_url = f"{vocab_base}/{slug}.jsonld"
    context_url = f"{vocab_base}/{slug}.context.jsonld"
    html_url = f"{vocab_base}/index.html"
    ls_json_url = f"{concept_uri}.linkset.json"
    ls_text_url = f"{concept_uri}.linkset"

    linkset_refs = [
        {"href": ls_json_url, "type": "application/linkset+json"},
        {"href": ls_text_url, "type": "application/linkset"},
    ]

    linkset_json = {
        "linkset": [
            {
                "anchor": concept_uri,
                "alternate": [
                    {"href": ttl_url, "type": "text/turtle; charset=utf-8"},
                    {"href": jsonld_url, "type": "application/ld+json"},
                    {"href": html_url, "type": "text/html; charset=utf-8"},
                ],
                "http://www.w3.org/ns/json-ld#context": [
                    {"href": context_url, "type": "application/ld+json"},
                ],
                "linkset": linkset_refs,
            },
            {
                "anchor": ttl_url,
                "self": [{"href": concept_uri}],
                "linkset": linkset_refs,
            },
            {
                "anchor": jsonld_url,
                "self": [{"href": concept_uri}],
                "linkset": linkset_refs,
            },
            {
                "anchor": html_url,
                "self": [{"href": concept_uri}],
                "linkset": linkset_refs,
            },
        ]
    }
    json_str = json.dumps(linkset_json, indent=2, ensure_ascii=False) + "\n"

    # RFC 9264 application/linkset textual format
    entries = [
        f'<{ttl_url}>\n   ; rel="alternate"\n   ; type="text/turtle; charset=utf-8"\n   ; anchor="{concept_uri}"',
        f'<{jsonld_url}>\n   ; rel="alternate"\n   ; type="application/ld+json"\n   ; anchor="{concept_uri}"',
        f'<{html_url}>\n   ; rel="alternate"\n   ; type="text/html; charset=utf-8"\n   ; anchor="{concept_uri}"',
        f'<{context_url}>\n   ; rel="http://www.w3.org/ns/json-ld#context"\n   ; type="application/ld+json"\n   ; anchor="{concept_uri}"',
        f'<{ls_json_url}>\n   ; rel="linkset"\n   ; type="application/linkset+json"\n   ; anchor="{concept_uri}"',
        f'<{ls_text_url}>\n   ; rel="linkset"\n   ; type="application/linkset"\n   ; anchor="{concept_uri}"',
        f'<{concept_uri}>\n   ; rel="self"\n   ; anchor="{ttl_url}"',
        f'<{concept_uri}>\n   ; rel="self"\n   ; anchor="{jsonld_url}"',
        f'<{concept_uri}>\n   ; rel="self"\n   ; anchor="{html_url}"',
    ]
    text_str = ",\n".join(entries) + "\n"
    return json_str, text_str


def parse_vocabulary(slug: str, ttl_path: Path, base_url: str) -> tuple[dict[str, Any], Graph]:
    ttl_text = ttl_path.read_text(encoding="utf-8")
    g = Graph()
    g.parse(ttl_path, format="turtle")

    ontologies = sorted(str(s) for s in g.subjects(RDF.type, OWL.Ontology))
    if not ontologies:
        raise ValueError(f"{ttl_path}: missing owl:Ontology subject")
    concept_uri = ontologies[0]

    from rdflib import URIRef
    ont_ref = URIRef(concept_uri)
    prefix = first_literal(g, ont_ref, VANN.preferredNamespacePrefix, default=slug)
    ns_uri = first_literal(g, ont_ref, VANN.preferredNamespaceUri, default=f"{concept_uri}#")

    # Preserve order of appearance in TTL for clean human reading
    order_matches = re.findall(rf"\b{re.escape(prefix)}:([A-Za-z0-9_-]+)\b", ttl_text)
    order_index: dict[str, int] = {}
    for name in order_matches:
        order_index.setdefault(name, len(order_index))

    def term_sort_key(uri_str: str) -> tuple[int, str]:
        lname = local_name(uri_str, ns_uri)
        return (order_index.get(lname, 10_000), lname)

    classes = []
    editorial_notes = []
    for cls_ref in sorted(
        {s for s in g.subjects(RDF.type, OWL.Class) if str(s).startswith(ns_uri)}
        | {s for s in g.subjects(RDF.type, RDFS.Class) if str(s).startswith(ns_uri)},
        key=lambda s: term_sort_key(str(s)),
    ):
        uri_str = str(cls_ref)
        lname = local_name(uri_str, ns_uri)
        ed_note = first_literal(g, cls_ref, SKOS.editorialNote)
        is_draft = "draft" in ed_note.lower()
        if ed_note:
            editorial_notes.append({"local_name": lname, "qname": f"{prefix}:{lname}", "note": ed_note})
        classes.append({
            "uri": uri_str,
            "local_name": lname,
            "qname": f"{prefix}:{lname}",
            "kind_tag": "owl:Class",
            "comment": first_literal(g, cls_ref, RDFS.comment),
            "scope_note": first_literal(g, cls_ref, SKOS.scopeNote),
            "editorial_note": ed_note,
            "is_draft": is_draft,
        })

    prop_subjects = (
        set(g.subjects(RDF.type, RDF.Property))
        | set(g.subjects(RDF.type, OWL.ObjectProperty))
        | set(g.subjects(RDF.type, OWL.DatatypeProperty))
    )
    properties = []
    for prop_ref in sorted(
        {s for s in prop_subjects if str(s).startswith(ns_uri)},
        key=lambda s: term_sort_key(str(s)),
    ):
        uri_str = str(prop_ref)
        lname = local_name(uri_str, ns_uri)
        types = set(g.objects(prop_ref, RDF.type))
        if OWL.ObjectProperty in types:
            kind_tag, kind_short = "owl:ObjectProperty", "ObjectProperty"
        elif OWL.DatatypeProperty in types:
            kind_tag, kind_short = "owl:DatatypeProperty", "DatatypeProperty"
        else:
            kind_tag, kind_short = "rdf:Property", "rdf:Property"

        domain_obj = next(g.objects(prop_ref, RDFS.domain), None)
        range_obj = next(g.objects(prop_ref, RDFS.range), None)
        domain_short = compact_uri(domain_obj, g)
        if range_obj is not None:
            range_short = compact_uri(range_obj, g)
        elif lname == "rel":
            range_short = "Token or IRI"
        elif lname == "value":
            range_short = "Literal or IRI"
        else:
            range_short = "rdfs:Resource"

        ed_note = first_literal(g, prop_ref, SKOS.editorialNote)
        is_draft = "draft" in ed_note.lower()
        if ed_note:
            editorial_notes.append({"local_name": lname, "qname": f"{prefix}:{lname}", "note": ed_note})

        properties.append({
            "uri": uri_str,
            "local_name": lname,
            "qname": f"{prefix}:{lname}",
            "kind_tag": kind_tag,
            "kind_short": kind_short,
            "domain_short": domain_short,
            "range_short": range_short,
            "comment": first_literal(g, prop_ref, RDFS.comment),
            "editorial_note": ed_note,
            "is_draft": is_draft,
        })

    # Validate & load examples/*.ttl
    examples = []
    ex_dir = ttl_path.parent / "examples"
    if ex_dir.is_dir():
        for ex_file in sorted(ex_dir.glob("*.ttl")):
            ex_g = Graph()
            ex_g.parse(ex_file, format="turtle")
            jsonld_file = ex_file.with_suffix(".jsonld")
            examples.append({
                "filename": ex_file.name,
                "rel_path": f"examples/{ex_file.name}",
                "content": ex_file.read_text(encoding="utf-8").rstrip(),
                "jsonld_filename": jsonld_file.name,
                "jsonld_rel_path": f"examples/{jsonld_file.name}",
                "graph": ex_g,
                "jsonld_path": jsonld_file,
            })

    license_uri = first_literal(g, ont_ref, DCTERMS.license)
    vocab_data = {
        "slug": slug,
        "concept_uri": concept_uri,
        "prefix": prefix,
        "namespace_uri": ns_uri,
        "title": first_literal(g, ont_ref, DCTERMS.title, default=slug),
        "description": first_literal(g, ont_ref, DCTERMS.description),
        "version": first_literal(g, ont_ref, OWL.versionInfo, default="draft"),
        "modified": first_literal(g, ont_ref, DCTERMS.modified),
        "license_uri": license_uri,
        "license_label": license_display(license_uri) if license_uri else "",
        "see_also": sorted(str(o) for o in g.objects(ont_ref, RDFS.seeAlso)),
        "classes": classes,
        "properties": properties,
        "editorial_notes": editorial_notes,
        "examples": examples,
        "url_html": f"{base_url.rstrip('/')}/{slug}/index.html",
        "url_linkset_json": f"{base_url.rstrip('/')}/{slug}/{slug}.linkset.json",
        "url_linkset_text": f"{base_url.rstrip('/')}/{slug}/{slug}.linkset",
    }
    return vocab_data, g


def build_sitemap(vocabs: list[dict[str, Any]]) -> str:
    """Generate RT-P06 Hostwide Discovery sitemap with ResourceSync <rs:ln> links."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:rs="http://www.openarchives.org/rs/terms/">',
    ]
    for v in vocabs:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(v['url_html'])}</loc>")
        if v["modified"]:
            lines.append(f"    <lastmod>{html.escape(v['modified'])}</lastmod>")
        lines.append(
            f'    <rs:ln rel="self" href="{html.escape(v["concept_uri"])}" />'
        )
        lines.append(
            f'    <rs:ln rel="linkset" href="{html.escape(v["url_linkset_json"])}" '
            'type="application/linkset+json" />'
        )
        lines.append(
            f'    <rs:ln rel="linkset" href="{html.escape(v["url_linkset_text"])}" '
            'type="application/linkset" />'
        )
        lines.append("  </url>")
    lines.append("</urlset>\n")
    return "\n".join(lines)


def write_or_check(outputs: dict[Path, str], check_only: bool) -> int:
    drifted: list[Path] = []
    for path, content in outputs.items():
        if check_only:
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            if current != content:
                drifted.append(path)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"Wrote {path.relative_to(ROOT_DIR)} ({len(content)} bytes)")

    if check_only:
        if drifted:
            print("Generated files are out of sync with Turtle sources:", file=sys.stderr)
            for p in drifted:
                print(f"  - {p.relative_to(ROOT_DIR)}", file=sys.stderr)
            return 1
        print(f"OK: {len(outputs)} generated files are in sync.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build semantic-assets from *.ttl sources.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Hosted base URL for Pages/sitemap.")
    parser.add_argument("--vocab", default=None, help="Build or check only a single vocabulary folder slug.")
    parser.add_argument("--check", action="store_true", help="Verify generated files match disk without writing.")
    args = parser.parse_args()

    discovered = discover_vocabularies()
    if args.vocab is not None:
        selected = [(slug, ttl_path) for slug, ttl_path in discovered if slug == args.vocab]
        if not selected:
            known = ", ".join(slug for slug, _ in discovered) or "(none)"
            print(
                f"Error: unknown vocabulary '{args.vocab}' (expected {args.vocab}/{args.vocab}.ttl; available: {known}).",
                file=sys.stderr,
            )
            return 1
    else:
        selected = discovered

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    vocab_tpl = env.get_template("vocabulary.html.j2")
    portal_tpl = env.get_template("portal-index.html.j2")

    outputs: dict[Path, str] = {}
    vocabs: list[dict[str, Any]] = []

    for slug, ttl_path in selected:
        vocab_data, g = parse_vocabulary(slug, ttl_path, args.base_url)
        vocabs.append(vocab_data)
        vocab_dir = ttl_path.parent

        outputs[vocab_dir / f"{slug}.jsonld"] = build_jsonld(
            g, vocab_data["concept_uri"], vocab_data["prefix"], vocab_data["namespace_uri"]
        )
        vocab_ctx = build_context_dict(vocab_data)
        outputs[vocab_dir / f"{slug}.context.jsonld"] = (
            json.dumps({"@context": vocab_ctx}, indent=2, ensure_ascii=False) + "\n"
        )
        for ex in vocab_data["examples"]:
            ex_jsonld = build_example_jsonld(ex["graph"], vocab_data, vocab_ctx, ex["rel_path"])
            outputs[ex["jsonld_path"]] = ex_jsonld
            ex["jsonld_content"] = ex_jsonld.rstrip()
        ls_json, ls_text = build_linksets(slug, vocab_data["concept_uri"], args.base_url)
        outputs[vocab_dir / f"{slug}.linkset.json"] = ls_json
        outputs[vocab_dir / f"{slug}.linkset"] = ls_text
        outputs[vocab_dir / "index.html"] = vocab_tpl.render(vocab=vocab_data).rstrip() + "\n"

    if args.vocab is None:
        outputs[ROOT_DIR / "index.html"] = portal_tpl.render(vocabs=vocabs).rstrip() + "\n"
        outputs[ROOT_DIR / "sitemap-semantic-assets.xml"] = build_sitemap(vocabs)

    return write_or_check(outputs, check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
