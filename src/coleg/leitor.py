"""Reconhece dispositivos no Markdown do acervo e preserva os demais trechos."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from urllib.parse import urljoin

from markdown_it import MarkdownIt

_NUMERO = r"\d{1,5}(?:[. ]\d{3})*(?:\s*[º°ªo])?(?:[-–][a-z])?"
_ARTIGO = rf"Art(?:igo)?\.?\s+(?P<numero>{_NUMERO})(?!\w)"
_INICIO = re.compile(
    rf"^(?:{_ARTIGO}|(?P<paragrafo>§\s*{_NUMERO}|Parágrafo\s+único)(?!\w)"
    r"|(?P<inciso>[IVXLCDM]+)\s*[-–—]\s+"
    r"|(?P<alinea>[a-z])\)\s+|(?P<item>\d{1,2})[.)]\s+)", re.IGNORECASE,
)
_TITULO = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
_REFERENCIA = re.compile(rf"\b{_ARTIGO}", re.IGNORECASE)
_PARAGRAFO = re.compile(rf"^\s*,?\s*(?P<paragrafo>§\s*{_NUMERO}|Parágrafo\s+único)", re.IGNORECASE)


def _chave_numero(numero: str) -> str:
    return re.sub(r"[.\sº°ªo]", "", numero.lower()).replace("–", "-")


def _chave_paragrafo(rotulo: str) -> str:
    return _chave_numero(rotulo[1:]) if rotulo.startswith("§") else "unico"


def separar_referencia(consulta: str) -> tuple[str, str]:
    """Separa 'LGPD, art. 5º, § 1º' ou 'art. 5º da LGPD' antes da busca."""
    if not (referencia := _REFERENCIA.search(consulta)):
        return consulta, ""
    antes = consulta[:referencia.start()].strip(" ,")
    resto = consulta[referencia.end():].lstrip(".")
    ancora = f"art-{_chave_numero(referencia['numero'])}"
    if paragrafo := _PARAGRAFO.match(resto):
        ancora += f"-par-{_chave_paragrafo(paragrafo['paragrafo'])}"
        resto = resto[paragrafo.end():]
    depois = re.sub(r"^[\s,]+(?:(?:d[aoe]|d[ao]s)\s+)?", "", resto).strip()
    return " ".join(filter(None, (antes, depois))), ancora


@dataclass
class Trecho:
    tipo: str
    ancora: str
    rotulo: str
    markdown: str


def _marcador(linha: str) -> re.Match | None:
    linha = re.sub(r"\*\*|__", "", linha.strip()).lstrip('"“')
    return _INICIO.match(linha)


def _rotulo(inciso: str, alinea: str, item: str) -> tuple[str, str, str]:
    if inciso:
        return "inciso", f"inc-{inciso.lower()}", f"Inciso {inciso.upper()}"
    if alinea:
        return "alinea", f"alinea-{alinea.lower()}", f"Alínea {alinea.lower()}"
    return "item", f"item-{item}", f"Item {item}"


def estruturar(corpo: str) -> list[Trecho]:
    """Divide o texto em trechos sem modificar a redação do documento."""
    linhas = corpo.splitlines(keepends=True)
    blocos_literais = {
        posicao
        for token in MarkdownIt("commonmark").parse(corpo)
        if token.type in {"fence", "code_block", "table_open"} and token.map
        for posicao in range(*token.map)
    }
    trechos: list[Trecho] = []
    usados: Counter[str] = Counter()
    atual = ("texto", "", "")
    inicio = 0
    artigo = paragrafo = inciso = alinea = ""

    for posicao, linha in enumerate(linhas):
        if posicao in blocos_literais:
            continue
        if titulo := _TITULO.match(linha.strip()):
            artigo = paragrafo = inciso = alinea = ""
            proximo = ("secao", f"secao-{posicao + 1}", titulo[1])
        elif marcador := _marcador(linha):
            if marcador["numero"]:
                numero = _chave_numero(marcador["numero"])
                artigo = f"art-{numero}"
                paragrafo = inciso = alinea = ""
                proximo = ("artigo", artigo, f"Art. {marcador['numero']}")
            elif not artigo:
                continue
            elif marcador["paragrafo"]:
                rotulo = marcador["paragrafo"]
                paragrafo = f"{artigo}-par-{_chave_paragrafo(rotulo)}"
                inciso = alinea = ""
                proximo = ("paragrafo", paragrafo, rotulo)
            else:
                tipo, chave, rotulo = _rotulo(marcador["inciso"], marcador["alinea"], marcador["item"])
                if tipo == "inciso":
                    inciso = f"{paragrafo or artigo}-{chave}"
                    alinea = ""
                    proximo = (tipo, inciso, rotulo)
                elif tipo == "alinea":
                    alinea = f"{inciso or paragrafo or artigo}-{chave}"
                    proximo = (tipo, alinea, rotulo)
                else:
                    proximo = (tipo, f"{alinea or inciso or paragrafo or artigo}-{chave}", rotulo)
        else:
            continue

        if posicao > inicio:
            trechos.append(Trecho(*atual, "".join(linhas[inicio:posicao])))
        tipo, ancora, rotulo = proximo
        usados[ancora] += 1
        if usados[ancora] > 1:
            ancora += f"-{usados[ancora]}"
            if tipo == "artigo":
                artigo = ancora
            elif tipo == "paragrafo":
                paragrafo = ancora
            elif tipo == "inciso":
                inciso = ancora
            elif tipo == "alinea":
                alinea = ancora
        atual = (tipo, ancora, rotulo)
        inicio = posicao

    if inicio < len(linhas):
        trechos.append(Trecho(*atual, "".join(linhas[inicio:])))
    return trechos


def renderizador(origem: str) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable(["table", "strikethrough"])

    def link(tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href") or ""
        if href and not href.startswith("#"):
            token.attrSet("href", urljoin(origem, href))
            token.attrSet("rel", "noreferrer")
        return md.renderer.renderToken(tokens, idx, options, env)

    imagem = md.renderer.rules["image"]

    def imagem_relativa(tokens, idx, options, env):
        token = tokens[idx]
        token.attrSet("src", urljoin(origem, token.attrGet("src") or ""))
        token.attrSet("loading", "lazy")
        return imagem(tokens, idx, options, env)

    md.renderer.rules["link_open"] = link
    md.renderer.rules["image"] = imagem_relativa
    return md
