"""Dicionário de normas conhecidas: nome, sigla usual e a norma correspondente.

Cada entrada: (siglas, nome, tipo, número, ano, outros nomes). A primeira sigla é a exibida.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

_ENTRADAS = [
    # Constituição e códigos
    (("cf", "cf88", "cf/88", "crfb"), "Constituição Federal de 1988", "constituicao", None, 1988,
     ("constituicao federal", "constituicao de 1988")),
    (("cc", "cc2002"), "Código Civil", "lei", 10406, 2002, ("novo codigo civil",)),
    (("cc1916", "cc16"), "Código Civil de 1916", "lei", 3071, 1916, ()),
    (("cpc", "ncpc", "cpc2015", "cpc15"), "Código de Processo Civil", "lei", 13105, 2015,
     ("novo codigo de processo civil",)),
    (("cpc1973", "cpc73"), "Código de Processo Civil de 1973", "lei", 5869, 1973, ()),
    (("cp",), "Código Penal", "dl", 2848, 1940, ()),
    (("cpp",), "Código de Processo Penal", "dl", 3689, 1941, ()),
    (("cpm",), "Código Penal Militar", "dl", 1001, 1969, ()),
    (("cppm",), "Código de Processo Penal Militar", "dl", 1002, 1969, ()),
    (("clt",), "Consolidação das Leis do Trabalho", "dl", 5452, 1943, ()),
    (("ctn",), "Código Tributário Nacional", "lei", 5172, 1966, ()),
    (("cdc",), "Código de Defesa do Consumidor", "lei", 8078, 1990, ()),
    (("ctb",), "Código de Trânsito Brasileiro", "lei", 9503, 1997, ()),
    (("ce",), "Código Eleitoral", "lei", 4737, 1965, ()),
    (("cba",), "Código Brasileiro de Aeronáutica", "lei", 7565, 1986, ()),
    (("cflo", "codflo"), "Código Florestal", "lei", 12651, 2012, ()),
    (("ccom",), "Código Comercial", "lei", 556, 1850, ()),
    (("cagua",), "Código de Águas", "decreto", 24643, 1934, ()),
    (("cmin",), "Código de Mineração", "dl", 227, 1967, ()),
    (("lindb", "licc"), "Lei de Introdução às Normas do Direito Brasileiro", "dl", 4657, 1942,
     ("lei de introducao ao codigo civil",)),
    # Estatutos
    (("eca",), "Estatuto da Criança e do Adolescente", "lei", 8069, 1990, ()),
    (("epi", "eidoso"), "Estatuto da Pessoa Idosa", "lei", 10741, 2003, ("estatuto do idoso",)),
    (("lbi", "epd"), "Estatuto da Pessoa com Deficiência", "lei", 13146, 2015,
     ("lei brasileira de inclusao",)),
    (("ecid",), "Estatuto da Cidade", "lei", 10257, 2001, ()),
    (("edesarm",), "Estatuto do Desarmamento", "lei", 10826, 2003, ()),
    (("eoab",), "Estatuto da Advocacia e da OAB", "lei", 8906, 1994, ("estatuto da oab",)),
    (("rju",), "Regime Jurídico dos Servidores Públicos Federais", "lei", 8112, 1990,
     ("estatuto dos servidores",)),
    (("emil",), "Estatuto dos Militares", "lei", 6880, 1980, ()),
    (("ejuv",), "Estatuto da Juventude", "lei", 12852, 2013, ()),
    (("eir",), "Estatuto da Igualdade Racial", "lei", 12288, 2010, ()),
    (("lmig",), "Lei de Migração", "lei", 13445, 2017, ()),
    # Direito público e administrativo
    (("nllc", "lldc", "llc"), "Lei de Licitações e Contratos", "lei", 14133, 2021,
     ("nova lei de licitacoes", "lei de licitacoes")),
    (("lpreg",), "Lei do Pregão", "lei", 10520, 2002, ()),
    (("lest",), "Lei das Estatais", "lei", 13303, 2016, ()),
    (("lconc",), "Lei de Concessões", "lei", 8987, 1995, ()),
    (("lppp", "ppp"), "Lei das Parcerias Público-Privadas", "lei", 11079, 2004, ()),
    (("lpa",), "Lei do Processo Administrativo Federal", "lei", 9784, 1999, ()),
    (("lia",), "Lei de Improbidade Administrativa", "lei", 8429, 1992, ()),
    (("lai",), "Lei de Acesso à Informação", "lei", 12527, 2011, ()),
    (("lac",), "Lei Anticorrupção", "lei", 12846, 2013, ()),
    (("lrf",), "Lei de Responsabilidade Fiscal", "lc", 101, 2000, ()),
    (("lotcu",), "Lei Orgânica do TCU", "lei", 8443, 1992, ()),
    (("lgd",), "Lei do Governo Digital", "lei", 14129, 2021, ()),
    (("lle",), "Lei da Liberdade Econômica", "lei", 13874, 2019, ()),
    (("lgpd",), "Lei Geral de Proteção de Dados", "lei", 13709, 2018, ()),
    (("mci",), "Marco Civil da Internet", "lei", 12965, 2014, ()),
    (("lgt",), "Lei Geral de Telecomunicações", "lei", 9472, 1997, ()),
    (("ldb",), "Lei de Diretrizes e Bases da Educação", "lei", 9394, 1996, ()),
    (("los", "lsus"), "Lei Orgânica da Saúde", "lei", 8080, 1990, ("lei do sus",)),
    (("loas",), "Lei Orgânica da Assistência Social", "lei", 8742, 1993, ()),
    (("pbps",), "Plano de Benefícios da Previdência Social", "lei", 8213, 1991, ()),
    (("pcss",), "Plano de Custeio da Seguridade Social", "lei", 8212, 1991, ()),
    (("lsimples", "lcme"), "Estatuto Nacional da Microempresa", "lc", 123, 2006,
     ("lei do simples",)),
    (("lkandir",), "Lei Kandir", "lc", 87, 1996, ()),
    (("pnma",), "Política Nacional do Meio Ambiente", "lei", 6938, 1981, ()),
    (("lca",), "Lei de Crimes Ambientais", "lei", 9605, 1998, ()),
    # Processo e jurisdição constitucional
    (("lacp",), "Lei da Ação Civil Pública", "lei", 7347, 1985, ()),
    (("lap",), "Lei da Ação Popular", "lei", 4717, 1965, ()),
    (("lms",), "Lei do Mandado de Segurança", "lei", 12016, 2009, ()),
    (("lmi",), "Lei do Mandado de Injunção", "lei", 13300, 2016, ()),
    (("lhd",), "Lei do Habeas Data", "lei", 9507, 1997, ()),
    (("ladi",), "Lei da ADI e da ADC", "lei", 9868, 1999, ()),
    (("ladpf",), "Lei da ADPF", "lei", 9882, 1999, ()),
    (("lje",), "Lei dos Juizados Especiais", "lei", 9099, 1995, ()),
    (("ljef",), "Lei dos Juizados Especiais Federais", "lei", 10259, 2001, ()),
    (("lef",), "Lei de Execução Fiscal", "lei", 6830, 1980, ()),
    (("larb",), "Lei de Arbitragem", "lei", 9307, 1996, ()),
    (("lmed",), "Lei de Mediação", "lei", 13140, 2015, ()),
    (("lpe",), "Lei do Processo Eletrônico", "lei", 11419, 2006, ()),
    (("loman",), "Lei Orgânica da Magistratura Nacional", "lc", 35, 1979, ()),
    (("lompu",), "Lei Orgânica do Ministério Público da União", "lc", 75, 1993, ()),
    (("lonmp",), "Lei Orgânica Nacional do Ministério Público", "lei", 8625, 1993, ()),
    # Penal
    (("lep",), "Lei de Execução Penal", "lei", 7210, 1984, ()),
    (("lcp",), "Lei das Contravenções Penais", "dl", 3688, 1941, ()),
    (("lch",), "Lei dos Crimes Hediondos", "lei", 8072, 1990, ()),
    (("ldrogas",), "Lei de Drogas", "lei", 11343, 2006, ("lei antidrogas",)),
    (("lmp",), "Lei Maria da Penha", "lei", 11340, 2006, ()),
    (("lorcrim", "lco"), "Lei das Organizações Criminosas", "lei", 12850, 2013, ()),
    (("llav",), "Lei de Lavagem de Dinheiro", "lei", 9613, 1998, ()),
    (("labuso",), "Lei de Abuso de Autoridade", "lei", 13869, 2019, ()),
    (("lit",), "Lei de Interceptação Telefônica", "lei", 9296, 1996, ()),
    (("ltort",), "Lei de Tortura", "lei", 9455, 1997, ()),
    (("lrac",), "Lei do Racismo", "lei", 7716, 1989, ()),
    (("pac",), "Pacote Anticrime", "lei", 13964, 2019, ()),
    # Civil, empresarial e trabalho
    (("lsa",), "Lei das Sociedades por Ações", "lei", 6404, 1976, ("lei das sa",)),
    (("lre", "lrf2005"), "Lei de Recuperação Judicial e Falências", "lei", 11101, 2005,
     ("lei de falencias",)),
    (("linq",), "Lei do Inquilinato", "lei", 8245, 1991, ()),
    (("lbf",), "Lei do Bem de Família", "lei", 8009, 1990, ()),
    (("lrp",), "Lei de Registros Públicos", "lei", 6015, 1973, ()),
    (("lalim",), "Lei de Alimentos", "lei", 5478, 1968, ()),
    (("lalpar",), "Lei da Alienação Parental", "lei", 12318, 2010, ()),
    (("lda",), "Lei de Direitos Autorais", "lei", 9610, 1998, ()),
    (("lpi",), "Lei de Propriedade Industrial", "lei", 9279, 1996, ()),
    (("lsoft",), "Lei do Software", "lei", 9609, 1998, ()),
    (("lrt",), "Reforma Trabalhista", "lei", 13467, 2017, ()),
    # Eleitoral
    (("lele", "lelei"), "Lei das Eleições", "lei", 9504, 1997, ()),
    (("lpp",), "Lei dos Partidos Políticos", "lei", 9096, 1995, ()),
    (("li", "linel"), "Lei de Inelegibilidade", "lc", 64, 1990, ()),
    (("lfl",), "Lei da Ficha Limpa", "lc", 135, 2010, ()),
]


@dataclass(frozen=True)
class Apelido:
    sigla: str
    nome: str
    tipo: str
    numero: int | None
    ano: int
    chaves: tuple[str, ...]  # siglas e nomes normalizados (sem acento, minúsculas)


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _norm(texto: str) -> str:
    return " ".join(normalizar(texto).split())


def _montar() -> list[Apelido]:
    return [
        Apelido(siglas[0].upper(), nome, tipo, numero, ano,
                tuple(dict.fromkeys(_norm(x) for x in (*siglas, nome, *outros))))
        for siglas, nome, tipo, numero, ano, outros in _ENTRADAS
    ]


APELIDOS = _montar()
_POR_CHAVE = {chave: a for a in APELIDOS for chave in a.chaves}
_POR_NORMA = {(a.tipo, a.numero, a.ano): a for a in APELIDOS}


def procurar(texto: str) -> Apelido | None:
    """Apelido cuja sigla ou nome corresponde ao texto inteiro da consulta."""
    return _POR_CHAVE.get(_norm(texto))


def da_norma(tipo, numero, ano) -> Apelido | None:
    return _POR_NORMA.get((tipo, numero, ano))
