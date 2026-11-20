"""Interpretação de caminhos do repositório e de consultas em texto livre."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from . import apelidos
from .apelidos import normalizar
from .config import CONSTITUICAO

# tipo canônico -> (rótulo, apelidos aceitos na consulta, já sem acento)
TIPOS: dict[str, tuple[str, tuple[str, ...]]] = {
    "lei": ("Lei", ("lei", "lei ordinaria")),
    "lc": ("Lei Complementar", ("lc", "lcp", "lei complementar")),
    "dl": ("Decreto-Lei", ("dl", "del", "decreto lei")),
    "decreto": ("Decreto", ("decreto", "dec")),
    "dleg": ("Decreto Legislativo", ("decreto legislativo", "dleg", "dlg", "dpl")),
    "ec": ("Emenda Constitucional", ("ec", "emc", "emenda constitucional", "emenda")),
    "ecr": ("Emenda Constitucional de Revisão", ("ecr", "emr", "emenda de revisao")),
    "lct": ("Lei Constitucional", ("lct", "lei constitucional")),
    "ldl": ("Lei Delegada", ("ldl", "lei delegada")),
    "mp": ("Medida Provisória", ("mp", "mpv", "medida provisoria")),
    "resolucao": ("Resolução", ("resolucao", "res", "rsf", "rcd", "rcn")),
    "constituicao": ("Constituição", ("constituicao",)),
    "regimento": ("Regimento", ("regimento", "regimento interno")),
    "regulamento": ("Regulamento", ("regulamento",)),
    "sv": ("Súmula Vinculante", ("sv", "sumula vinculante")),
    "sumula": ("Súmula", ("sumula", "sum")),
    "tema": ("Tema", ("tema", "repercussao geral", "rg", "repetitivo", "recurso repetitivo")),
    "adi": ("ADI", ("adi",)),
    "adc": ("ADC", ("adc",)),
    "ado": ("ADO", ("ado",)),
    "adpf": ("ADPF", ("adpf",)),
    "oj": ("Orientação Jurisprudencial", ("oj", "orientacao jurisprudencial")),
    "puil": ("PUIL", ("puil",)),
    "tratado": ("Tratado", ("tratado", "convencao", "acordo")),
}

# Apelidos que também fixam o tribunal.
TRIBUNAL_IMPLICITO = {"repercussao geral": "stf", "rg": "stf", "repetitivo": "stj", "recurso repetitivo": "stj"}

TRIBUNAIS = ("stf", "stj", "tst", "tnu", "trf4", "tcu", "stm")
ORDEM_TRIBUNAL = {t: i for i, t in enumerate(TRIBUNAIS)}

# Órgãos das OJs do TST, usados como complemento.
COMPLEMENTOS_OJ = ("sdi1t", "sdi1", "sdi2", "sdc")

# sigla do nome de arquivo federal -> tipo canônico
SIGLAS_FEDERAIS = {
    "lei": "lei", "lcp": "lc", "del": "dl", "dec": "decreto", "dlg": "dleg", "dpl": "dleg",
    "emc": "ec", "emr": "ecr", "lct": "lct", "ldl": "ldl", "mpv": "mp",
    "rcd": "resolucao", "rcn": "resolucao", "rrc": "resolucao", "rsf": "resolucao",
}

PALAVRAS_VAZIAS = {"de", "da", "do", "das", "dos", "n", "no", "nr", "numero", "o", "a", "e"}

_RE_FEDERAL = re.compile(
    r"^(?P<sigla>[a-z]+)-(?:(?P<sn>sn)|(?P<num>\d+)(?:-(?P<comp>[a-z]|\d+))?)"
    r"-(?P<data>\d{4}-\d{2}-\d{2})(?:-s(?P<seq>\d+))?$"
)
_RE_JURIS = re.compile(
    r"^(?P<tipo>sumula-vinculante|sumula|tema|adi|adc|ado|adpf|puil|oj-(?P<oj>[a-z0-9]+))-(?P<num>\d+)$"
)
_RE_OIT = re.compile(r"^oit_?(?P<num>\d+)$", re.I)


@dataclass
class Documento:
    caminho: str
    esfera: str
    colecao: str
    tipo: str | None = None
    tribunal: str | None = None
    numero: int | None = None
    complemento: str | None = None
    ano: int | None = None
    data: str | None = None

    @property
    def nome(self) -> str:
        return PurePosixPath(self.caminho).stem

    @property
    def titulo(self) -> str:
        return titulo(self.tipo, self.numero, self.complemento, self.ano, self.tribunal, self.nome)


def titulo(tipo, numero, complemento, ano, tribunal, nome) -> str:
    """Rótulo legível, ex.: 'Lei nº 13.105/2015 — CPC' ou 'Súmula Vinculante 13 (STF)'."""
    base = _titulo(tipo, numero, complemento, ano, tribunal, nome)
    conhecido = None if tribunal or complemento else apelidos.da_norma(tipo, numero, ano)
    return f"{base} — {conhecido.sigla}" if conhecido else base


def _titulo(tipo, numero, complemento, ano, tribunal, nome) -> str:
    if tipo in (None, "tratado") or (numero is None and tipo not in ("constituicao", "lei", "decreto")):
        base = nome.replace("_", " ").replace("-", " ")
        return f"{base} ({tribunal.upper()})" if tribunal else base
    rotulo = TIPOS[tipo][0]
    if tipo == "constituicao":
        return f"Constituição de {ano}" if ano else rotulo
    if tribunal:
        oj = f" {complemento.upper()}" if tipo == "oj" and complemento else ""
        return f"{rotulo}{oj} {numero} ({tribunal.upper()})"
    if numero is None:
        return f"{rotulo} s/nº de {ano}" if ano else rotulo
    num = f"{numero:,}".replace(",", ".")
    if complemento:
        num += f"-{complemento.upper()}" if complemento.isalpha() else f"-{complemento}"
    return f"{rotulo} nº {num}/{ano}" if ano else f"{rotulo} nº {num}"


def classificar(caminho: str) -> Documento | None:
    """Extrai os campos de um caminho do repositório; None se não for documento do escopo."""
    if caminho == CONSTITUICAO:
        return Documento(caminho, "federal", "constituicao", "constituicao", ano=1988, data="1988-10-05")
    if not caminho.endswith(".md"):
        return None
    partes = caminho.split("/")
    if any(p.startswith("_") for p in partes) or "anexos" in partes:
        return None
    nome = PurePosixPath(caminho).stem.lower()
    esfera = partes[0]

    if esfera == "federal" and len(partes) >= 3:
        colecao = partes[1]
        doc = Documento(caminho, esfera, colecao)
        if m := _RE_FEDERAL.match(nome):
            doc.tipo = SIGLAS_FEDERAIS.get(m["sigla"])
            doc.numero = int(m["num"]) if m["num"] else None
            doc.complemento = m["comp"]
            doc.data = m["data"]
            doc.ano = int(m["data"][:4])
        elif colecao == "constituicoes-historicas":
            doc.tipo = "constituicao"
            doc.ano = int(partes[2]) if partes[2].isdigit() else None
        elif colecao == "regimentos":
            doc.tipo = "regimento"
        elif colecao == "regulamentos":
            doc.tipo = "regulamento"
        return doc

    if esfera == "jurisprudencia" and len(partes) >= 3:
        tribunal = partes[2] if partes[1] == "outros-tribunais" else partes[1]
        colecao = partes[-2]
        doc = Documento(caminho, esfera, colecao, tribunal=tribunal if tribunal in TRIBUNAIS else None)
        if m := _RE_JURIS.match(nome):
            bruto = m["tipo"]
            doc.tipo = "sv" if bruto == "sumula-vinculante" else "oj" if m["oj"] else bruto
            doc.complemento = m["oj"]
            doc.numero = int(m["num"])
        elif nome.startswith("regimento-"):
            doc.tipo = "regimento"
            doc.tribunal = nome.removeprefix("regimento-")
        return doc

    if esfera == "tratados" and len(partes) >= 2:
        doc = Documento(caminho, esfera, partes[1], "tratado")
        if m := _RE_OIT.match(nome):
            doc.numero = int(m["num"])
        return doc
    return None


# ---------------------------------------------------------------- consultas


@dataclass
class Consulta:
    tipo: str | None = None
    numero: int | None = None
    complemento: str | None = None
    ano: int | None = None
    tribunal: str | None = None
    esfera: str | None = None
    caminho: str | None = None
    palavras: list[str] = field(default_factory=list)

    def vazia(self) -> bool:
        return not any((self.tipo, self.numero, self.complemento, self.ano, self.tribunal,
                        self.esfera, self.caminho, self.palavras))


def _ano_curto(aa: str) -> int:
    n = int(aa)
    return 2000 + n if n <= dt.date.today().year % 100 else 1900 + n


_APELIDOS = sorted(
    ((tuple(a.split()), tipo) for tipo, (_, nomes) in TIPOS.items() for a in nomes),
    key=lambda par: -len(par[0]),
)


def interpretar(texto: str) -> Consulta:
    """Converte 'cpc', 'lei 8.666/93', 'sv 13', 'sumula 7 stj', 'oj sdi1 336'... em filtros."""
    if conhecido := apelidos.procurar(texto):  # 'cpc' -> lei 13105/2015
        return Consulta(tipo=conhecido.tipo, numero=conhecido.numero, ano=conhecido.ano)
    c = Consulta()
    t = normalizar(texto)
    t = re.sub(r"\bn[º°o]\.?\s*", " ", t)
    t = re.sub(r"(\d)\.(?=\d{3}\b)", r"\1", t)  # 8.666 -> 8666
    t = re.sub(r"(\d+)\s*/\s*(\d{4}|\d{2})\b", lambda m: f"{m[1]} ano:{m[2]}", t)
    t = re.sub(r"\b(\d+)-([a-z]|\d{1,2})\b", r"\1+\2", t)  # mp 2200-2, dpl 44-a: não separar
    tokens = [tk for tk in re.split(r"[\s\-,;]+", t) if tk]

    i = 0
    while i < len(tokens):
        for chave, tipo in _APELIDOS:
            if tuple(tokens[i:i + len(chave)]) == chave and c.tipo is None:
                c.tipo = tipo
                c.tribunal = c.tribunal or TRIBUNAL_IMPLICITO.get(" ".join(chave))
                i += len(chave)
                break
        else:
            tk = tokens[i]
            if tk.startswith("ano:"):
                aa = tk[4:]
                c.ano = int(aa) if len(aa) == 4 else _ano_curto(aa)
            elif tk in TRIBUNAIS:
                c.tribunal = tk
            elif tk in COMPLEMENTOS_OJ:
                c.complemento = tk
            elif tk.isdigit():
                n = int(tk)
                if c.numero is None:
                    c.numero = n
                elif c.ano is None and 1800 <= n <= 2100:
                    c.ano = n
                else:
                    c.palavras.append(tk)
            elif m := re.fullmatch(r"(\d+)(?:\+?([a-z])|\+(\d{1,2}))", tk):  # 44a, 44+a, 2200+2
                c.numero, c.complemento = int(m[1]), m[2] or m[3]
            elif tk not in PALAVRAS_VAZIAS:
                c.palavras.append(tk)
            i += 1
    if c.tribunal and c.tipo is None and c.numero is not None:
        c.tipo = "sumula"  # 'stj 7' -> Súmula 7 do STJ
    return c
