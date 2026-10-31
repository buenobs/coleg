import pytest

from coleg.baixar import links_relativos, nome_local, separar_cabecalho
from coleg.apelidos import APELIDOS
from coleg.parser import classificar, interpretar


@pytest.mark.parametrize(
    "caminho, esperado",
    [
        ("federal/leis-ordinarias/1993/lei-8666-1993-06-21.md",
         dict(tipo="lei", numero=8666, ano=1993, titulo="Lei nº 8.666/1993")),
        ("federal/leis-complementares/2000/lcp-101-2000-05-04.md", dict(tipo="lc", numero=101)),
        ("federal/decretos-lei/1940/del-2848-1940-12-07.md", dict(tipo="dl", numero=2848)),
        ("federal/medidas-provisorias/2001/mpv-2200-2-2001-08-24.md",
         dict(tipo="mp", numero=2200, complemento="2")),
        ("federal/decretos-legislativos/1892/dpl-44-a-1892-05-24.md",
         dict(tipo="dleg", numero=44, complemento="a")),
        ("federal/leis-ordinarias/1823/lei-sn-1823-10-20-s3.md", dict(tipo="lei", numero=None, ano=1823)),
        ("federal/constituicoes-historicas/1891/constituicao-1891.md", dict(tipo="constituicao", ano=1891)),
        ("constituicao.md", dict(tipo="constituicao", ano=1988)),
        ("jurisprudencia/stf/sumulas-vinculantes/sumula-vinculante-13.md",
         dict(tipo="sv", numero=13, tribunal="stf", titulo="Súmula Vinculante 13 (STF)")),
        ("jurisprudencia/stj/repetitivos/tema-903.md", dict(tipo="tema", tribunal="stj", numero=903)),
        ("jurisprudencia/stf/controle-concentrado/adi-4277.md", dict(tipo="adi", numero=4277)),
        ("jurisprudencia/tst/orientacoes-jurisprudenciais/oj-sdi1-336.md",
         dict(tipo="oj", complemento="sdi1", numero=336, tribunal="tst")),
        ("jurisprudencia/outros-tribunais/tcu/sumula-75.md", dict(tipo="sumula", tribunal="tcu")),
        ("jurisprudencia/regimentos/regimento-tst.md", dict(tipo="regimento", tribunal="tst")),
        ("tratados/oit/OIT_029.md", dict(tipo="tratado", numero=29)),
    ],
)
def test_classificar(caminho, esperado):
    d = classificar(caminho)
    for campo, valor in esperado.items():
        assert getattr(d, campo) == valor, campo


@pytest.mark.parametrize("caminho", [
    "federal/_fonte/x.md", "federal/anexos/decretos/1944/a.png",
    "federal/anexos/decretos/1944/a.md", "estaduais/SP/leis-ordinarias/2000/lei-1-2000-01-01.md",
    "README.md",
])
def test_classificar_fora_do_escopo(caminho):
    assert classificar(caminho) is None


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("lei 8666", dict(tipo="lei", numero=8666)),
        ("Lei nº 8.666/93", dict(tipo="lei", numero=8666, ano=1993)),
        ("lei 14133/2021", dict(tipo="lei", numero=14133, ano=2021)),
        ("lei 8666 1993", dict(tipo="lei", numero=8666, ano=1993)),
        ("lc 101", dict(tipo="lc", numero=101)),
        ("Lei Complementar 101", dict(tipo="lc", numero=101)),
        ("decreto-lei 2848", dict(tipo="dl", numero=2848)),
        ("decreto 9203", dict(tipo="decreto", numero=9203)),
        ("decreto legislativo 6", dict(tipo="dleg", numero=6)),
        ("sv 13", dict(tipo="sv", numero=13)),
        ("Súmula Vinculante 13", dict(tipo="sv", numero=13)),
        ("sumula 7 stj", dict(tipo="sumula", numero=7, tribunal="stj")),
        ("stj 7", dict(tipo="sumula", numero=7, tribunal="stj")),
        ("tema 1046 stf", dict(tipo="tema", numero=1046, tribunal="stf")),
        ("repercussão geral 1046", dict(tipo="tema", numero=1046, tribunal="stf")),
        ("repetitivo 903", dict(tipo="tema", numero=903, tribunal="stj")),
        ("oj sdi1 336", dict(tipo="oj", complemento="sdi1", numero=336)),
        ("adi 4277", dict(tipo="adi", numero=4277)),
        ("oit 29", dict(tipo=None, numero=29, palavras=["oit"])),
        ("cf", dict(tipo="constituicao", numero=None, ano=1988)),
        ("CPC", dict(tipo="lei", numero=13105, ano=2015)),
        ("Código Penal", dict(tipo="dl", numero=2848, ano=1940)),
        ("  lgpd ", dict(tipo="lei", numero=13709, ano=2018)),
        ("LRF", dict(tipo="lc", numero=101, ano=2000)),
        ("cpc 2015", dict(tipo=None, numero=2015, palavras=["cpc"])),  # só o texto inteiro vira apelido
    ],
)
def test_interpretar(texto, esperado):
    c = interpretar(texto)
    for campo, valor in esperado.items():
        assert getattr(c, campo) == valor, campo


def test_titulo_com_sigla():
    d = classificar("federal/leis-ordinarias/2015/lei-13105-2015-03-16.md")
    assert d.titulo == "Lei nº 13.105/2015 — CPC"


def test_apelidos_sem_chave_repetida():
    chaves = [c for a in APELIDOS for c in a.chaves]
    assert len(chaves) == len(set(chaves))


def test_separar_cabecalho():
    campos, corpo = separar_cabecalho('---\ntitulo: "Lei nº 1"\nnumero: "1"\n---\n# Lei nº 1\n\nTexto')
    assert campos == {"titulo": "Lei nº 1", "numero": "1"}
    assert corpo == "# Lei nº 1\n\nTexto"


@pytest.mark.parametrize("caminho, nome", [
    ("jurisprudencia/stj/sumulas/sumula-7.md", "stj-sumula-7"),
    ("jurisprudencia/outros-tribunais/tcu/sumula-7.md", "tcu-sumula-7"),
    ("federal/leis-ordinarias/1993/lei-8666-1993-06-21.md", "lei-8666-1993-06-21"),
])
def test_nome_local(caminho, nome):
    assert nome_local(caminho) == nome


def test_links_relativos():
    texto = "![a](../../anexos/x.png) [b](https://x.y) [c](#ancora) ![d](img/y.pdf)"
    assert links_relativos(texto) == ["../../anexos/x.png", "img/y.pdf"]
