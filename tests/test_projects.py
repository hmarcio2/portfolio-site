"""Projetos do portfólio com documentação em várias páginas (content/portfolio/<projeto>/*.md)."""

import re
import shutil
from pathlib import Path

import pytest

import build

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def site(tmp_path):
    """Cópia do site real, sem os textos de estudos e projetos, para cada teste controlar o conteúdo."""
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


def read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


def write_project(site: Path, slug: str, docs: dict, *, day="2026-03-01", category="agentes-rag") -> None:
    """``docs``: nome do arquivo -> (order ou None, título)."""
    folder = site / "content" / "portfolio" / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.md").write_text(
        f"---\ntitle: Projeto {slug}\ndate: {day}\ncategory: {category}\nstatus: local\nsummary: Resumo de {slug}.\n---\n"
        "## Objetivo\n\nTexto.\n\n## Estado\n\nTexto.\n\n## Limites\n\nTexto.\n", encoding="utf-8")
    for name, (order, title) in docs.items():
        order_line = f"order: {order}\n" if order is not None else ""
        (folder / f"{name}.md").write_text(
            f"---\ntitle: {title}\n{order_line}summary: Sobre {title}.\n---\nCorpo de {name}.\n", encoding="utf-8")


def test_project_folder_builds_an_overview_and_one_page_per_doc(site):
    write_project(site, "meu-app", {"arquitetura": (2, "Arquitetura"), "api": (3, "API"), "decisoes": (1, "Decisões")})
    out = run(site)
    for name in ("index", "arquitetura", "api", "decisoes"):
        assert (out / "portfolio" / "meu-app" / f"{name}.html").exists()
    assert not (out / "portfolio" / "meu-app.html").exists()
    cards = read(out, "portfolio/index.html")
    assert 'href="../portfolio/meu-app/index.html"' in cards and "4 páginas de documentação" in cards


def test_project_docs_are_ordered_by_order_then_name_and_the_sidebar_follows(site):
    write_project(site, "meu-app", {"zeta": (None, "Zeta"), "beta": (2, "Beta"), "alfa": (1, "Alfa"), "outra": (2, "Outra")})
    html = read(run(site), "portfolio/meu-app/index.html")
    side = re.search(r'<aside class="side">.*?</aside>', html, re.S).group(0)
    titles = re.findall(r">([^<]+)</a></li>", side)
    assert titles == ["Visão geral", "Alfa", "Beta", "Outra", "Zeta"]  # sem order vai por último; empate por nome
    assert "Todos os projetos" in side and 'aria-current="page">Visão geral' in side


def test_doc_page_has_project_sidebar_breadcrumb_and_prev_next(site):
    write_project(site, "meu-app", {"arquitetura": (1, "Arquitetura"), "api": (2, "API"), "testes": (3, "Testes")})
    out = run(site)
    html = read(out, "portfolio/meu-app/api.html")
    assert 'aria-current="page">API' in html
    assert 'href="../../portfolio/meu-app/index.html">Projeto meu-app' in html  # a migalha volta ao projeto
    assert 'rel="prev"' in html and "Arquitetura" in html and 'rel="next"' in html and "Testes" in html
    first = read(out, "portfolio/meu-app/index.html")
    assert 'rel="prev"' not in first and 'rel="next"' in first  # a visão geral só tem "próxima"
    assert "Documentação completa" in first and "Sobre Arquitetura." in first  # lista as páginas com o resumo


def test_internal_links_in_doc_pages_resolve_with_the_deeper_root(site):
    write_project(site, "meu-app", {"a": (1, "A")})
    page = site / "content" / "portfolio" / "meu-app" / "a.md"
    page.write_text(page.read_text(encoding="utf-8") + "\nVeja [o projeto](@root/portfolio/meu-app/index.html).\n", encoding="utf-8")
    html = read(run(site), "portfolio/meu-app/a.html")
    assert 'href="../../portfolio/meu-app/index.html"' in html and "@root/" not in html


def test_long_pages_get_a_table_of_contents_and_short_ones_do_not(site):
    write_project(site, "meu-app", {"curta": (1, "Curta")})
    out = run(site)
    index, short = read(out, "portfolio/meu-app/index.html"), read(out, "portfolio/meu-app/curta.html")
    assert 'class="toc"' in index and 'href="#objetivo"' in index and 'href="#limites"' in index
    assert 'class="toc"' not in short


def test_project_folder_errors_are_clear(site):
    folder = site / "content" / "portfolio" / "sem-indice"
    folder.mkdir()
    (folder / "x.md").write_text("---\ntitle: X\n---\ncorpo", encoding="utf-8")
    with pytest.raises(build.BuildError, match="index.md"):
        run(site)
    (folder / "index.md").write_text(
        "---\ntitle: P\ndate: 2026-01-01\ncategory: agentes-rag\nsummary: s\n---\ncorpo", encoding="utf-8")
    (folder / "x.md").write_text("---\nsummary: sem titulo\n---\ncorpo", encoding="utf-8")
    with pytest.raises(build.BuildError, match="falta o campo title"):
        run(site)
    (folder / "x.md").write_text("---\ntitle: X\norder: primeiro\n---\ncorpo", encoding="utf-8")
    with pytest.raises(build.BuildError, match="order"):
        run(site)


def test_file_and_folder_with_the_same_name_conflict(site):
    write_project(site, "duplo", {})
    (site / "content" / "portfolio" / "duplo.md").write_text(
        "---\ntitle: D\ndate: 2026-01-01\ncategory: agentes-rag\nsummary: s\n---\ncorpo", encoding="utf-8")
    with pytest.raises(build.BuildError, match="nome repetido"):
        run(site)


def test_folders_are_not_allowed_in_the_studies_section(site):
    (site / "content" / "estudos" / "pasta").mkdir()
    with pytest.raises(build.BuildError, match="só existem no portfólio"):
        run(site)


def test_draft_docs_are_skipped(site):
    write_project(site, "meu-app", {"visivel": (1, "Visível")})
    (site / "content" / "portfolio" / "meu-app" / "rascunho.md").write_text(
        "---\ntitle: R\ndraft: true\n---\ncorpo", encoding="utf-8")
    assert not (run(site) / "portfolio" / "meu-app" / "rascunho.html").exists()
