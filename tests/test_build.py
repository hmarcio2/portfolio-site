import re
import shutil
from datetime import date
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parent.parent


def write_entry(folder: Path, slug: str, *, day: str, category: str, seq: int = 0, title: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{slug}.md").write_text(
        f"---\ntitle: {title or slug}\ndate: {day}\nseq: {seq}\ncategory: {category}\nsummary: Resumo de {slug}.\n---\nCorpo de {slug}.\n",
        encoding="utf-8",
    )


@pytest.fixture
def site(tmp_path):
    """Cópia do site real, sem os textos, para os testes controlarem o conteúdo."""
    for name in ("templates", "assets"):
        shutil.copytree(ROOT / name, tmp_path / name)
    content = tmp_path / "content"
    content.mkdir()
    for name in ("site.yml", "home.md", "curriculo.yml", "roadmap.md"):
        shutil.copy(ROOT / "content" / name, content / name)
    for section in ("estudos", "portfolio"):
        (content / section).mkdir()
    return tmp_path


def run(site: Path) -> Path:
    build.build_site(site, site / "dist")
    return site / "dist"


def card_slugs(html: str) -> list[str]:
    """Textos mostrados nos cards (a barra lateral também lista os títulos, então só olho dentro dos cards)."""
    return re.findall(r'<article class="card">.*?class="stretch" href="[^"]*?/([^/"]+)\.html"', html, re.S)


def read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


# ---------- o site real ----------

def test_real_content_builds_and_every_internal_link_resolves(tmp_path):
    pages = build.build_site(ROOT, tmp_path)
    assert "index.html" in pages and "estudos/index.html" in pages and "portfolio/index.html" in pages
    broken = []
    for page in pages:
        html = (tmp_path / page).read_text(encoding="utf-8")
        assert "@root/" not in html, f"{page}: link interno sem resolver"
        for target in re.findall(r'(?:href|src)="([^"#]+)"', html):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            if not (tmp_path / page).parent.joinpath(target).resolve().exists():
                broken.append(f"{page} -> {target}")
    assert not broken, broken


def test_linkedin_and_github_are_in_the_header_of_every_page(tmp_path):
    cfg = build.load_site(ROOT / "content")
    for page in build.build_site(ROOT, tmp_path):
        header = re.search(r"<header.*?</header>", (tmp_path / page).read_text(encoding="utf-8"), re.S).group(0)
        assert cfg["linkedin"] in header and cfg["github"] in header, page


def test_every_page_has_the_navbar_and_the_chat(tmp_path):
    for page in build.build_site(ROOT, tmp_path):
        html = (tmp_path / page).read_text(encoding="utf-8")
        assert html.count('class="main-nav"') == 1 and 'id="chat"' in html and "chat.js" in html, page


PUBLISHED_REPOS = {"portfolio-core", "portfolio-chat", "portfolio-filmes", "portfolio-planilhas", "portfolio-site",
                   "portfolio-edge", "portfolio-langfuse"}


def test_real_content_links_only_to_published_repositories(tmp_path):
    """Todo link para um repositório do portfólio tem de ser de um repositório que de fato existe no GitHub."""
    build.build_site(ROOT, tmp_path)
    for page in tmp_path.rglob("*.html"):
        for name in re.findall(r"github\.com/hmarcio2/([A-Za-z0-9_.-]+)", page.read_text(encoding="utf-8")):
            if name.startswith("portfolio-"):
                assert name in PUBLISHED_REPOS, f"{page.name}: repositório inexistente {name}"


def test_every_portfolio_page_with_a_repository_shows_the_github_button(tmp_path):
    build.build_site(ROOT, tmp_path)
    for page in (tmp_path / "portfolio").glob("*.html"):
        if page.name in {"index.html", "roadmap.html"} or page.name.startswith("pagina-") or "categoria" in str(page):
            continue
        assert "Código no GitHub" in page.read_text(encoding="utf-8"), page.name


# ---------- ordenação e paginação ----------

def test_sort_is_newest_first_and_seq_breaks_ties(site):
    write_entry(site / "content" / "estudos", "antigo", day="2026-01-05", category="conceitos")
    write_entry(site / "content" / "estudos", "novo", day="2026-03-01", category="conceitos")
    write_entry(site / "content" / "estudos", "mesmo-dia-a", day="2026-02-01", category="conceitos", seq=1)
    write_entry(site / "content" / "estudos", "mesmo-dia-b", day="2026-02-01", category="conceitos", seq=2)
    entries = build.load_entries(site / "content", "estudos", build.load_site(site / "content")["categories"]["estudos"])
    assert [e.slug for e in entries] == ["novo", "mesmo-dia-b", "mesmo-dia-a", "antigo"]


def test_listing_is_paginated_with_links_between_pages(site):
    for i in range(14):
        write_entry(site / "content" / "estudos", f"estudo-{i:02d}", day=f"2026-02-{i + 1:02d}", category="conceitos")
    out = run(site)
    first, second, third = (read(out, f) for f in ("estudos/index.html", "estudos/pagina-2.html", "estudos/pagina-3.html"))
    assert first.count('class="card"') == 6 and second.count('class="card"') == 6 and third.count('class="card"') == 2
    assert card_slugs(first) == [f"estudo-{i:02d}" for i in range(13, 7, -1)]  # mais recente primeiro
    assert card_slugs(second)[0] == "estudo-07" and card_slugs(third) == ["estudo-01", "estudo-00"]
    assert 'rel="next"' in first and 'rel="prev"' in third
    assert 'aria-current="page" aria-label="Página 2"' in second
    assert "pagina-4" not in third


def test_single_page_has_no_pagination(site):
    write_entry(site / "content" / "estudos", "unico", day="2026-02-01", category="conceitos")
    assert 'class="pager"' not in read(run(site), "estudos/index.html")


def test_category_pages_are_paginated_and_empty_categories_are_hidden(site):
    for i in range(8):
        write_entry(site / "content" / "estudos", f"c-{i}", day=f"2026-02-{i + 1:02d}", category="conceitos")
    write_entry(site / "content" / "estudos", "p-0", day="2026-03-01", category="papers")
    out = run(site)
    assert (out / "estudos/categoria/conceitos.html").exists() and (out / "estudos/categoria/conceitos-pagina-2.html").exists()
    assert not (out / "estudos/categoria/livros.html").exists()
    sidebar = re.search(r'<aside class="side">.*?</aside>', read(out, "estudos/index.html"), re.S).group(0)
    assert "Conceitos" in sidebar and "Papers" in sidebar and "Livros" not in sidebar


def test_sidebar_highlights_the_current_entry_and_opens_its_category(site):
    write_entry(site / "content" / "estudos", "a", day="2026-02-01", category="conceitos")
    write_entry(site / "content" / "estudos", "b", day="2026-02-02", category="papers")
    html = read(run(site), "estudos/a.html")
    assert re.search(r'<a href="../estudos/a.html" aria-current="page">a</a>', html)
    assert re.search(r"<details open>\s*<summary>Conceitos", html)
    assert re.search(r"<details>\s*<summary>Papers", html)


def test_entry_page_links_to_newer_and_older(site):
    for i, slug in enumerate(["um", "dois", "tres"], 1):
        write_entry(site / "content" / "estudos", slug, day=f"2026-02-{i:02d}", category="conceitos")
    html = read(run(site), "estudos/dois.html")
    assert 'rel="prev"' in html and "tres.html" in html and 'rel="next"' in html and "um.html" in html


def test_home_shows_the_latest_three_of_each_section(site):
    for i in range(5):
        write_entry(site / "content" / "estudos", f"e-{i}", day=f"2026-02-{i + 1:02d}", category="conceitos")
        write_entry(site / "content" / "portfolio", f"p-{i}", day=f"2026-03-{i + 1:02d}", category="agentes-rag")
    home = read(run(site), "index.html")
    for shown in ("e-4", "e-3", "e-2", "p-4", "p-3", "p-2"):
        assert f"{shown}.html" in home
    assert "e-1.html" not in home and "p-1.html" not in home
    assert "Todos os estudos (5)" in home and "Todos os projetos (5)" in home


def test_drafts_and_underscore_files_are_skipped(site):
    write_entry(site / "content" / "estudos", "visivel", day="2026-02-01", category="conceitos")
    write_entry(site / "content" / "estudos", "_modelo", day="2026-02-02", category="conceitos")
    (site / "content" / "estudos" / "rascunho.md").write_text(
        "---\ntitle: R\ndate: 2026-02-03\ncategory: conceitos\nsummary: s\ndraft: true\n---\ncorpo", encoding="utf-8")
    out = run(site)
    assert (out / "estudos/visivel.html").exists()
    assert not (out / "estudos/_modelo.html").exists() and not (out / "estudos/rascunho.html").exists()


def test_html_in_titles_is_escaped(site):
    write_entry(site / "content" / "estudos", "x", day="2026-02-01", category="conceitos", title='"<script>alert(1)</script>"')
    assert "<script>alert(1)</script>" not in read(run(site), "estudos/index.html")


# ---------- erros de conteúdo ----------

@pytest.mark.parametrize("text, message", [
    ("sem cabeçalho", "falta o cabeçalho YAML"),
    ("---\ntitle: T\ndate: 2026-01-01\ncategory: conceitos\n---\nx", "faltam os campos summary"),
    ("---\ntitle: T\ndate: 2026-01-01\ncategory: nao-existe\nsummary: s\n---\nx", "categoria 'nao-existe'"),
    ("---\ntitle: T\ndate: ontem\ncategory: conceitos\nsummary: s\n---\nx", "AAAA-MM-DD"),
])
def test_invalid_content_gives_a_clear_error(site, text, message):
    (site / "content" / "estudos" / "ruim.md").write_text(text, encoding="utf-8")
    with pytest.raises(build.BuildError, match=message):
        run(site)


def test_bad_file_name_is_rejected(site):
    write_entry(site / "content" / "estudos", "Nome Ruim", day="2026-02-01", category="conceitos")
    with pytest.raises(build.BuildError, match="minúsculas"):
        run(site)


def test_helpers():
    assert build.fmt_date(date(2026, 11, 1)) == "01 nov 2026"
    assert build.list_path("estudos", 1) == "estudos/index.html" and build.list_path("estudos", 3) == "estudos/pagina-3.html"
    assert build.list_path("estudos", 2, "papers") == "estudos/categoria/papers-pagina-2.html"
    assert build.paginate([], 6) == [[]] and len(build.paginate(list(range(13)), 6)) == 3
