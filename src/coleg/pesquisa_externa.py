"""Registro de fontes para continuar uma consulta nos portais de pesquisa."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote, urlencode

from .parser import TIPOS, Consulta, Documento

_VERBETES = {"sumula", "sv", "oj"}
_JULGADOS = {"tema", "adi", "adc", "ado", "adpf", "puil"}


@dataclass(frozen=True)
class DestinoPesquisa:
    fonte: str
    acervo: str
    montar_url: Callable[[str], str]


@dataclass(frozen=True)
class LinkPesquisa:
    fonte: str
    acervo: str
    url: str


def _url_legjur(texto: str, *, caminho: str) -> str:
    base = f"https://www.legjur.com/{caminho}"
    if texto:
        return f"{base}/busca?{urlencode({'q': texto})}"
    return f"{base}/inicio" if caminho == "jurisprudencia" else f"{base}/busca"


def _url_tcu(texto: str) -> str:
    base = "https://pesquisa.apps.tcu.gov.br"
    if not texto:
        return f"{base}/pesquisa/jurisprudencia"
    # A pesquisa integrada do TCU recebe o termo com dupla codificação no caminho.
    termo = quote(quote(texto, safe=""), safe="")
    return f"{base}/resultado/todas-bases/{termo}?pb=jurisprudencia-selecionada"


# Novas fontes registram seus acervos e as respectivas funções de URL aqui.
DESTINOS = (
    DestinoPesquisa("LegJur", "Legislação", partial(_url_legjur, caminho="legislacao")),
    DestinoPesquisa("LegJur", "Súmulas", partial(_url_legjur, caminho="sumula")),
    DestinoPesquisa("LegJur", "Jurisprudência", partial(_url_legjur, caminho="jurisprudencia")),
    DestinoPesquisa("TCU", "Jurisprudência", _url_tcu),
)


def _acervos(consulta: Consulta | Documento) -> set[str]:
    esfera, tipo = consulta.esfera, consulta.tipo
    if esfera == "tratados" or tipo == "tratado":
        return set()
    if esfera == "federal":
        return {"Legislação"}
    if tipo in _VERBETES:
        acervos = {"Súmulas"}
        if consulta.tribunal == "tcu" or (isinstance(consulta, Consulta) and esfera == "jurisprudencia"):
            acervos.add("Jurisprudência")
        return acervos
    if esfera == "jurisprudencia" or consulta.tribunal or tipo in _JULGADOS:
        return {"Jurisprudência"}
    if tipo in TIPOS:
        return {"Legislação"}
    return {"Legislação", "Jurisprudência"}


def links_busca(texto: str, consulta: Consulta | Documento) -> list[LinkPesquisa]:
    """Gera links para os acervos de pesquisa externos aplicáveis à consulta."""
    texto = texto.strip()
    if not (texto or consulta.esfera):
        return []
    acervos = _acervos(consulta)
    return [LinkPesquisa(destino.fonte, destino.acervo, destino.montar_url(texto))
            for destino in DESTINOS if destino.acervo in acervos]


def texto_dos_filtros(consulta: Consulta) -> str:
    """Representa os filtros estruturados da CLI como termos de busca."""
    tipo = TIPOS[consulta.tipo][0] if consulta.tipo else ""
    numero = str(consulta.numero) if consulta.numero is not None else ""
    complemento = consulta.complemento or ""
    if numero and complemento and consulta.tipo != "oj":
        numero, complemento = f"{numero}-{complemento}", ""
    ano = str(consulta.ano) if consulta.ano is not None else ""
    if numero and ano:
        numero, ano = f"{numero}/{ano}", ""
    tribunal = (consulta.tribunal or "").upper()
    return " ".join(filter(None, (tipo, numero, complemento, ano, tribunal, *consulta.palavras)))
