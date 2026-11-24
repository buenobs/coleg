"""Textos integrais oficiais disponíveis para documentos parciais do acervo."""

from __future__ import annotations

import re
from functools import lru_cache
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import quote, urljoin, urlsplit

import httpx

from .leitor import estruturar

_NLLC = "federal/leis-ordinarias/2021/lei-14133-2021-04-01.md"
_PLANALTO_NLLC = "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm"
_FONTES = {_NLLC: (_PLANALTO_NLLC, 194)}
_TITULO = re.compile(r"^(?:TÍTULO|CAPÍTULO|SUBSEÇÃO|SEÇÃO)\b", re.IGNORECASE)
_TACHADO = re.compile(r"text-decoration\s*:\s*line-through\b", re.IGNORECASE)
_MARCA_TACHADO = re.compile(r"\ue000(.*?)\ue001")
_CABECALHOS = {
    "Accept": "text/html,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
}


def _escapar(texto: str) -> str:
    return re.sub(r"([\\\x60*_\[\]<>~])", r"\\\1", texto)


class _TextoPlanalto(HTMLParser):
    """Converte o HTML do Planalto, preservando links, citações e redações tachadas."""

    def __init__(self, fonte: str) -> None:
        super().__init__()
        self.fonte = fonte
        self.blocos: list[str] = []
        self.paragrafo: list[str] | None = None
        self.atributos: dict[str, str | None] = {}
        self.link = ""
        self.citacao = 0
        self.tachados: list[str] = []
        self.inline: list[tuple[str, bool]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "blockquote":
            self.citacao += 1
        elif tag == "p":
            self.paragrafo = []
            self.atributos = attrs
            self.link = ""
            self.tachados.clear()
            self.inline.clear()
        elif self.paragrafo is not None:
            if tag in {"span", "font", "s", "strike", "del"}:
                tachado = tag in {"s", "strike", "del"} or bool(_TACHADO.search(attrs.get("style") or ""))
                self.inline.append((tag, tachado))
                if tachado:
                    if not self.tachados:
                        self.paragrafo.append("\ue000")
                    self.tachados.append(tag)
            if tag == "a" and attrs.get("href"):
                link = urljoin(self.fonte, attrs["href"])
                if urlsplit(link).scheme in {"http", "https"}:
                    self.link = quote(link, safe=":/?&=;%#+,@!$'*-._")
                    self.paragrafo.append("[")
            elif tag == "br":
                self.paragrafo.append(" ")

    def handle_data(self, data):
        if self.paragrafo is not None:
            self.paragrafo.append(_escapar(data))

    def handle_endtag(self, tag):
        if tag == "blockquote":
            self.citacao = max(0, self.citacao - 1)
        if self.paragrafo is None:
            return
        if tag == "a" and self.link:
            self.paragrafo.append(f"]({self.link})")
            self.link = ""
        elif self.inline and self.inline[-1][0] == tag:
            _, tachado = self.inline.pop()
            if tachado:
                self.tachados.pop()
                if not self.tachados:
                    self.paragrafo.append("\ue001")
        elif tag == "p":
            if self.tachados:
                self.paragrafo.append("\ue001")
            texto = _MARCA_TACHADO.sub(_renderizar_tachado, " ".join("".join(self.paragrafo).split())).strip()
            if texto:
                if self.citacao:
                    texto = f"> {texto}"
                elif _TITULO.match(texto) and (
                    self.atributos.get("align") == "center"
                    or "text-align: center" in (self.atributos.get("style") or "")
                ):
                    texto = f"## {texto}"
                self.blocos.append(texto)
            self.paragrafo = None


def _renderizar_tachado(marca: re.Match[str]) -> str:
    trecho = marca[1]
    if not trecho.strip():
        return " " if trecho else ""
    return (" " if trecho.startswith(" ") else "") + f"~~{trecho.strip()}~~" + (" " if trecho.endswith(" ") else "")


def _converter(html: str, fonte: str, ultimo_artigo: int) -> str:
    leitor = _TextoPlanalto(fonte)
    leitor.feed(html)
    leitor.close()
    corpo = "\n\n".join(leitor.blocos)
    numeros = [
        int(t.ancora[4:]) for t in estruturar(corpo)
        if t.tipo == "artigo" and t.ancora[4:].isdecimal()
    ]
    if numeros != list(range(1, ultimo_artigo + 1)):
        raise ValueError("A fonte oficial não retornou a sequência esperada de artigos.")
    return corpo


@lru_cache(maxsize=4)
def _buscar(fonte: str, ultimo_artigo: int, periodo: int) -> str:
    resposta = httpx.get(fonte, timeout=12, follow_redirects=True, headers=_CABECALHOS)
    resposta.raise_for_status()
    try:
        html = resposta.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        html = resposta.content.decode("cp1252")
    return _converter(html, fonte, ultimo_artigo)


def texto_integral(caminho: str) -> tuple[str, str] | None:
    if caminho not in _FONTES:
        return None
    fonte, ultimo_artigo = _FONTES[caminho]
    return fonte, _buscar(fonte, ultimo_artigo, int(monotonic() // 900))


def fonte_integral(caminho: str) -> str | None:
    entrada = _FONTES.get(caminho)
    return entrada[0] if entrada else None
