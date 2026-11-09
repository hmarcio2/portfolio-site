#!/usr/bin/env python3
"""Gerador do site estático do portfólio.

Lê o conteúdo em Markdown (``content/``), aplica os templates (``templates/``) e escreve HTML puro em ``dist/``:

    content/home.md, content/curriculo.yml     -> index.html (quem sou, resumo do currículo, últimos projetos e estudos)
    content/estudos/*.md                       -> estudos/index.html (cards paginados, do mais recente ao mais antigo),
                                                  uma página por estudo, e uma página por categoria
    content/portfolio/*.md                     -> portfolio/index.html (cards paginados) e uma página por projeto
    content/roadmap.md                         -> portfolio/roadmap.html (projetos planejados)

Cada ``.md`` começa com um cabeçalho YAML (title, date, category, summary...). Veja o README para escrever um estudo
ou documentar um projeto novo. Uso:

    python build.py            # gera dist/
    python build.py --out ../public
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
SECTIONS = ("estudos", "portfolio")
REQUIRED = ("title", "date", "category", "summary")
_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class BuildError(Exception):
    """Conteúdo inválido; a mensagem diz qual arquivo e o que corrigir."""


@dataclass
class Entry:
    section: str
    slug: str
    title: str
    date: date
    seq: int
    category: str
    summary: str
    tags: list[str]
    body: str                      # Markdown (convertido para HTML na hora de gerar a página, com o prefixo certo)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:         # caminho relativo à raiz do site
        return f"{self.section}/{self.slug}.html"

    @property
    def minutes(self) -> int:
        return max(1, math.ceil(len(self.body.split()) / 200))


# ---------- leitura ----------

def split_front_matter(text: str, source: str) -> tuple[dict, str]:
    m = _FRONT.match(text)
    if not m:
        raise BuildError(f"{source}: falta o cabeçalho YAML entre '---' no início do arquivo")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise BuildError(f"{source}: cabeçalho YAML inválido ({exc})") from None
    if not isinstance(meta, dict):
        raise BuildError(f"{source}: o cabeçalho YAML deve ser um conjunto de chaves e valores")
    return meta, text[m.end():]


def load_site(content: Path) -> dict:
    try:
        cfg = yaml.safe_load((content / "site.yml").read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise BuildError(f"content/site.yml: YAML inválido (textos com ': ' precisam de aspas): {exc}") from None
    for key in ("name", "linkedin", "github", "categories"):
        if key not in cfg:
            raise BuildError(f"content/site.yml: falta a chave '{key}'")
    return cfg


def load_entries(content: Path, section: str, categories: list[dict]) -> list[Entry]:
    valid = {c["slug"] for c in categories}
    entries: list[Entry] = []
    seen: set[str] = set()
    for path in sorted((content / section).glob("*.md")):
        if path.name.startswith("_"):
            continue
        source = f"content/{section}/{path.name}"
        meta, body = split_front_matter(path.read_text(encoding="utf-8"), source)
        if meta.pop("draft", False):
            continue
        missing = [k for k in REQUIRED if not meta.get(k)]
        if missing:
            raise BuildError(f"{source}: faltam os campos {', '.join(missing)}")
        slug = path.stem
        if not _SLUG.match(slug):
            raise BuildError(f"{source}: o nome do arquivo deve usar só letras minúsculas, números e hífens")
        if slug in seen:
            raise BuildError(f"{source}: nome repetido na seção {section}")
        seen.add(slug)
        if meta["category"] not in valid:
            raise BuildError(f"{source}: categoria '{meta['category']}' não existe (use uma de: {', '.join(sorted(valid))})")
        d = meta["date"]
        if not isinstance(d, date):
            raise BuildError(f"{source}: 'date' deve ser AAAA-MM-DD")
        entries.append(Entry(
            section=section, slug=slug, title=str(meta["title"]), date=d, seq=int(meta.get("seq", 0)),
            category=meta["category"], summary=str(meta["summary"]).strip(), tags=list(meta.get("tags") or []), body=body,
            meta={k: v for k, v in meta.items() if k not in {"title", "date", "seq", "category", "summary", "tags"}},
        ))
    return sort_newest_first(entries)


def sort_newest_first(entries: list[Entry]) -> list[Entry]:
    """Do mais recente ao mais antigo; no mesmo dia, o de maior ``seq`` vem primeiro."""
    return sorted(entries, key=lambda e: (e.date, e.seq, e.title), reverse=True)


# ---------- paginação e endereços ----------

def paginate(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)] or [[]]


def list_path(section: str, number: int, category: str | None = None) -> str:
    """Caminho relativo da página ``number`` (1 = primeira) da listagem da seção, ou de uma categoria dela."""
    if category is None:
        return f"{section}/index.html" if number == 1 else f"{section}/pagina-{number}.html"
    return f"{section}/categoria/{category}.html" if number == 1 else f"{section}/categoria/{category}-pagina-{number}.html"


def fmt_date(d: date) -> str:
    return f"{d.day:02d} {MESES[d.month - 1]} {d.year}"


# ---------- geração ----------

class Builder:
    def __init__(self, content: Path, templates: Path, assets: Path, out: Path):
        self.content, self.assets, self.out = content, assets, out
        self.cfg = load_site(content)
        self.cats = {s: self.cfg["categories"][s] for s in SECTIONS}
        self.entries = {s: load_entries(content, s, self.cats[s]) for s in SECTIONS}
        self.env = Environment(loader=FileSystemLoader(str(templates)), autoescape=select_autoescape(["html"]),
                               trim_blocks=True, lstrip_blocks=True)
        self.env.filters["date_pt"] = fmt_date
        self.env.globals.update(cat_name=self.cat_name, list_path=list_path)
        self.written: list[str] = []

    # -- utilidades --
    def md(self, text: str, root: str) -> str:
        html = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"], output_format="html")
        return html.replace("@root/", root)  # links internos no Markdown: [texto](@root/portfolio/chat.html)

    def render(self, template: str, path: str, **ctx: Any) -> None:
        depth = path.count("/")
        root = "../" * depth
        html = self.env.get_template(template).render(site=self.cfg, root=root, path=path, fmt_date=fmt_date, **ctx)
        target = self.out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8", newline="\n")
        self.written.append(path)

    def cat_name(self, section: str, slug: str) -> str:
        return next(c["name"] for c in self.cats[section] if c["slug"] == slug)

    def sidebar(self, section: str, *, entry: Entry | None = None, category: str | None = None, roadmap: bool = False) -> dict:
        groups = []
        for c in self.cats[section]:
            items = [e for e in self.entries[section] if e.category == c["slug"]]
            if not items:
                continue  # categoria sem texto ainda não aparece
            groups.append({
                "name": c["name"], "url": list_path(section, 1, c["slug"]), "count": len(items),
                "open": category == c["slug"] or (entry is not None and entry.category == c["slug"]),
                "entries": [{"title": e.title, "url": e.path, "current": entry is not None and e.slug == entry.slug} for e in items],
            })
        return {"section": section, "title": self.cfg["section_titles"][section], "home_url": list_path(section, 1),
                "groups": groups, "extra": self.sidebar_extra(section, roadmap),
                "current_home": entry is None and category is None and not roadmap}

    # -- páginas --
    def build(self) -> list[str]:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copytree(self.assets, self.out / "assets")
        self.home()
        for section in SECTIONS:
            self.listings(section)
            for e in self.entries[section]:
                self.entry_page(e)
        self.roadmap()
        return self.written

    def home(self) -> None:
        about_text = (self.content / "home.md").read_text(encoding="utf-8")
        try:
            cv = yaml.safe_load((self.content / "curriculo.yml").read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise BuildError(f"content/curriculo.yml: YAML inválido ({exc})") from None
        self.render("home.html", "index.html", section="home", title=self.cfg["name"],
                    description=self.cfg.get("description", ""), about=self.md(about_text, ""), cv=cv,
                    latest_projects=self.entries["portfolio"][:3], latest_studies=self.entries["estudos"][:3],
                    counts={s: len(self.entries[s]) for s in SECTIONS})

    def listings(self, section: str) -> None:
        size = int(self.cfg.get("page_size", {}).get(section, 6))
        scopes: list[tuple[str | None, list[Entry]]] = [(None, self.entries[section])]
        scopes += [(c["slug"], [e for e in self.entries[section] if e.category == c["slug"]]) for c in self.cats[section]]
        for category, items in scopes:
            if category is not None and not items:
                continue
            pages = paginate(items, size)
            for n, chunk in enumerate(pages, 1):
                title = self.cfg["section_titles"][section] if category is None else self.cat_name(section, category)
                self.render(
                    "listing.html", list_path(section, n, category), section=section,
                    title=title if n == 1 else f"{title}: página {n}", heading=title,
                    intro=self.cfg["section_intro"][section] if category is None else None,
                    cards=chunk,
                    sidebar=self.sidebar(section, category=category),
                    pagination=[{"n": i, "url": list_path(section, i, category), "current": i == n} for i in range(1, len(pages) + 1)],
                    prev_url=list_path(section, n - 1, category) if n > 1 else None,
                    next_url=list_path(section, n + 1, category) if n < len(pages) else None,
                    total=len(items), category=category,
                )

    def sidebar_extra(self, section: str, current: bool = False) -> list[dict]:
        if section == "portfolio" and (self.content / "roadmap.md").exists():
            return [{"title": "Roadmap (planejados)", "url": "portfolio/roadmap.html", "current": current}]
        return []

    def entry_page(self, e: Entry) -> None:
        ordered = self.entries[e.section]
        i = ordered.index(e)
        self.render(
            "entry.html", e.path, section=e.section, title=e.title, description=e.summary, entry=e,
            body=self.md(e.body, "../"), category_name=self.cat_name(e.section, e.category),
            category_url=list_path(e.section, 1, e.category),
            newer=ordered[i - 1] if i > 0 else None, older=ordered[i + 1] if i + 1 < len(ordered) else None,
            sidebar=self.sidebar(e.section, entry=e), section_title=self.cfg["section_titles"][e.section],
        )

    def roadmap(self) -> None:
        path = self.content / "roadmap.md"
        if not path.exists():
            return
        meta, body = split_front_matter(path.read_text(encoding="utf-8"), "content/roadmap.md")
        self.render("roadmap.html", "portfolio/roadmap.html", section="portfolio", title=meta.get("title", "Roadmap"),
                    description=meta.get("summary", ""), body=self.md(body, "../"),
                    sidebar=self.sidebar("portfolio", roadmap=True))


def build_site(root: Path = ROOT, out: Path | None = None) -> list[str]:
    builder = Builder(root / "content", root / "templates", root / "assets", out or root / "dist")
    return builder.build()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(ROOT / "dist"), help="pasta de saída (padrão: dist/)")
    args = p.parse_args(argv)
    try:
        pages = build_site(ROOT, Path(args.out))
    except BuildError as exc:
        print(f"Erro no conteúdo: {exc}", file=sys.stderr)
        return 1
    print(f"{len(pages)} páginas geradas em {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
