"""Comandos da linha de comando."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import httpx
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from . import __version__, config
from .baixar import ErroDownload, baixar as baixar_doc, cliente, obter, separar_cabecalho, url
from .indice import ErroIndice, Indice, atualizar as atualizar_indice, listar_arvore
from .apelidos import APELIDOS
from .parser import TIPOS, TRIBUNAIS, Consulta, Documento, interpretar, normalizar, titulo

app = typer.Typer(
    help="Localiza e baixa normas, jurisprudência e tratados do repositório buenobs/leis-bbs.",
    no_args_is_help=True, add_completion=False, rich_markup_mode="rich",
)
console = Console()
erro = Console(stderr=True, style="red")


def _falhar(msg: str) -> None:
    erro.print(msg)
    raise typer.Exit(1)


def _abrir() -> Indice:
    try:
        return Indice.abrir()
    except ErroIndice as e:
        _falhar(str(e))


def _salvar_busca(docs: list[Documento]) -> None:
    config.arquivo_ultima_busca().write_text(
        json.dumps([d.caminho for d in docs], ensure_ascii=False), encoding="utf-8")


def _ultima_busca() -> list[str]:
    try:
        return json.loads(config.arquivo_ultima_busca().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _tabela(docs: list[Documento], total: int) -> None:
    t = Table(show_lines=False, header_style="bold")
    t.add_column("#", justify="right", style="cyan")
    t.add_column("Documento", style="bold")
    t.add_column("Data")
    t.add_column("Caminho", style="dim", overflow="fold")
    for i, d in enumerate(docs, 1):
        t.add_row(str(i), d.titulo, d.data or (str(d.ano) if d.ano else ""), d.caminho)
    console.print(t)
    if total > len(docs):
        console.print(f"[yellow]Mostrando {len(docs)} de {total}. Refine a busca ou use --limite.[/]")


def _consulta(termos: list[str] | None, tipo, numero, ano, tribunal, esfera) -> Consulta:
    c = interpretar(" ".join(termos or []))
    if tipo:
        if tipo not in TIPOS:
            _falhar(f"Tipo desconhecido: {tipo}. Válidos: {', '.join(TIPOS)}")
        c.tipo = tipo
    if tribunal:
        c.tribunal = tribunal.lower()
    for campo, valor in (("numero", numero), ("ano", ano), ("esfera", esfera)):
        if valor is not None:
            setattr(c, campo, valor)
    return c


def _resolver(termos: list[str], idx: Indice, todos: bool = False) -> list[str]:
    """Converte índices da última busca, caminhos ou uma consulta em caminhos do repositório."""
    if all(t.isdigit() for t in termos):
        anteriores = _ultima_busca()
        if not anteriores:
            _falhar("Não há busca anterior. Rode 'coleg buscar ...' ou informe a norma.")
        fora = [t for t in termos if not 1 <= int(t) <= len(anteriores)]
        if fora:
            _falhar(f"Índice fora da última busca (1 a {len(anteriores)}): {', '.join(fora)}")
        return [anteriores[int(t) - 1] for t in termos]
    if all("/" in t or t.endswith(".md") for t in termos):
        return [t.replace("\\", "/").strip("/") for t in termos]
    c = interpretar(" ".join(termos))
    docs, total = idx.buscar(c, limite=None if todos else 30)
    if not docs:
        _falhar("Nada encontrado.")
    if len(docs) > 1 and not todos:
        _salvar_busca(docs)
        _tabela(docs, total)
        console.print("[yellow]Mais de um resultado. Escolha pelo número, ex.: coleg baixar 1 — "
                      "ou use --todos.[/]")
        raise typer.Exit(2)
    return [d.caminho for d in docs]


@app.command()
def atualizar() -> None:
    """Cria ou atualiza o índice local (clone parcial, só a lista de arquivos)."""
    with console.status("Sincronizando a árvore do repositório..."):
        try:
            sha, n = atualizar_indice()
        except ErroIndice as e:
            _falhar(str(e))
    console.print(f"[green]Índice atualizado:[/] {n:,} documentos (commit {sha[:10]}).".replace(",", "."))


@app.command()
def buscar(
    termos: Annotated[Optional[list[str]], typer.Argument(help="Ex.: lei 8666, sv 13, sumula 7 stj")] = None,
    tipo: Annotated[Optional[str], typer.Option("--tipo", "-t", help="Tipo canônico (lei, lc, sv, tema...)")] = None,
    numero: Annotated[Optional[int], typer.Option("--numero", "-n")] = None,
    ano: Annotated[Optional[int], typer.Option("--ano", "-a")] = None,
    tribunal: Annotated[Optional[str], typer.Option("--tribunal", help=", ".join(TRIBUNAIS))] = None,
    esfera: Annotated[Optional[str], typer.Option("--esfera", help="federal, jurisprudencia, tratados")] = None,
    limite: Annotated[int, typer.Option("--limite", "-l")] = 30,
    como_json: Annotated[bool, typer.Option("--json", help="Saída em JSON")] = False,
) -> None:
    """Localiza documentos no índice local."""
    c = _consulta(termos, tipo, numero, ano, tribunal, esfera)
    if c.vazia():
        _falhar("Informe o que buscar. Ex.: coleg buscar lei 8666")
    idx = _abrir()
    docs, total = idx.buscar(c, limite=limite)
    _salvar_busca(docs)
    if como_json:
        print(json.dumps([{"titulo": d.titulo, **d.__dict__, "url": url(d.caminho, idx.commit)}
                          for d in docs], ensure_ascii=False, indent=2))
        return
    if not docs:
        _falhar("Nada encontrado.")
    _tabela(docs, total)


@app.command()
def info(
    alvo: Annotated[list[str], typer.Argument(help="Nº da última busca, caminho ou consulta")],
    texto: Annotated[bool, typer.Option("--texto", help="Exibe também o texto integral")] = False,
) -> None:
    """Mostra o cabeçalho (ementa, situação, fonte...) de um documento."""
    idx = _abrir()
    with cliente() as cli:
        for caminho in _resolver(alvo, idx):
            try:
                conteudo = obter(cli, caminho, idx.commit).decode("utf-8")
            except (ErroDownload, httpx.HTTPError) as e:
                _falhar(str(e))
            campos, corpo = separar_cabecalho(conteudo)
            t = Table.grid(padding=(0, 2))
            t.add_column(style="bold cyan", no_wrap=True)
            t.add_column(overflow="fold")
            t.add_row("caminho", caminho)
            for k, v in campos.items():
                t.add_row(k, v)
            console.rule(campos.get("titulo", caminho))
            console.print(t)
            if texto:
                console.print(Markdown(corpo))


@app.command()
def baixar(
    alvo: Annotated[list[str], typer.Argument(help="Nº(s) da última busca, caminho(s) ou consulta")],
    destino: Annotated[Path, typer.Option("--destino", "-o", help="Pasta de destino")] = Path("."),
    formato: Annotated[str, typer.Option("--formato", "-f", help="md (com cabeçalho) ou txt (só o texto)")] = "md",
    manter_pastas: Annotated[bool, typer.Option("--manter-pastas", help="Reproduz a estrutura de pastas do repositório")] = False,
    anexos: Annotated[bool, typer.Option("--anexos", help="Baixa imagens/PDFs referenciados no documento")] = False,
    todos: Annotated[bool, typer.Option("--todos", help="Baixa todos os resultados da consulta")] = False,
) -> None:
    """Baixa documentos para o disco."""
    if formato not in ("md", "txt"):
        _falhar("Formato deve ser md ou txt.")
    idx = _abrir()
    caminhos = _resolver(alvo, idx, todos=todos)
    falhas = 0
    with cliente() as cli:
        for caminho in caminhos:
            try:
                gravados, avisos = baixar_doc(cli, caminho, idx.commit, destino,
                                              manter_pastas=manter_pastas, formato=formato,
                                              anexos=anexos)
            except (ErroDownload, httpx.HTTPError) as e:
                erro.print(f"✗ {caminho}: {e}")
                falhas += 1
                continue
            console.print(f"[green]✓[/] {gravados[0]}", soft_wrap=True, highlight=False)
            for extra in gravados[1:]:
                console.print(f"  [dim]+ {extra}[/]", soft_wrap=True, highlight=False)
            for aviso in avisos:
                erro.print(f"  ! {aviso}")
    if falhas:
        raise typer.Exit(1)


@app.command("apelidos")
def listar_apelidos(
    filtro: Annotated[Optional[str], typer.Argument(help="Parte da sigla ou do nome")] = None,
) -> None:
    """Lista as normas conhecidas pela sigla (ex.: CPC, CLT, LGPD)."""
    termo = normalizar(filtro or "")
    t = Table(header_style="bold")
    t.add_column("Sigla", style="cyan", no_wrap=True)
    t.add_column("Nome")
    t.add_column("Norma", style="bold")
    t.add_column("Também aceita", style="dim")
    for a in APELIDOS:
        if termo and not any(termo in chave for chave in a.chaves):
            continue
        t.add_row(a.sigla, a.nome, titulo(a.tipo, a.numero, None, a.ano, None, "").split(" — ")[0],
                  ", ".join(c for c in a.chaves if c != a.sigla.lower() and c != normalizar(a.nome)))
    if not t.row_count:
        _falhar(f"Nenhum apelido corresponde a: {filtro}")
    console.print(t)


@app.command()
def listar(pasta: Annotated[str, typer.Argument(help="Ex.: jurisprudencia/stf")] = "") -> None:
    """Lista o conteúdo de uma pasta do repositório."""
    idx = _abrir()
    try:
        itens = listar_arvore(idx.commit, pasta.replace("\\", "/"))
    except ErroIndice as e:
        _falhar(str(e))
    if not itens:
        _falhar(f"Pasta vazia ou inexistente: {pasta}")
    for tipo_item, caminho in sorted(itens, key=lambda x: (x[0] != "tree", x[1])):
        nome = caminho.rsplit("/", 1)[-1]
        console.print(f"[bold blue]{nome}/[/]" if tipo_item == "tree" else nome, highlight=False)


def _versao(valor: bool) -> None:
    if valor:
        console.print(f"coleg {__version__}")
        raise typer.Exit()


@app.callback()
def principal(
    versao: Annotated[bool, typer.Option("--version", callback=_versao, is_eager=True)] = False,
) -> None:
    pass
