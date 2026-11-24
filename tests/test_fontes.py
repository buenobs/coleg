import httpx
import pytest

from coleg import web
from coleg.fontes import _converter
from coleg.leitor import estruturar
from coleg.parser import classificar


def test_texto_atualizado_distingue_dispositivos_citados():
    fonte = "https://www.planalto.gov.br/lei/atualizada.html"
    html = """
    <p align="center">CAPÍTULO I</p>
    <p>Art. 1º Texto da lei. <a href="alteracao.html">(Redação dada pela Lei X)</a></p>
    <blockquote><p>Art. 99. Texto de outra lei.</p></blockquote>
    <p><span style="text-decoration:line-through">Art. 2º Redação anterior.</span></p>
    <p>Art.
    2º Texto final.</p>
    """
    corpo = _converter(html, fonte, 2)
    assert [t.ancora for t in estruturar(corpo) if t.tipo == "artigo"] == ["art-1", "art-2"]
    assert "> Art. 99." in corpo
    assert "(https://www.planalto.gov.br/lei/alteracao.html)" in corpo
    assert "~~Art. 2º Redação anterior.~~" in corpo
    with pytest.raises(ValueError):
        _converter(html, fonte, 3)


def test_leitor_abre_artigo_da_versao_integral(monkeypatch):
    caminho = "federal/leis-ordinarias/2021/lei-14133-2021-04-01.md"
    documento = classificar(caminho)
    campos = {"versao_texto": "republicação/retificação", "fonte": "https://normas.leg.br/"}
    monkeypatch.setattr(web, "_carregar", lambda *_: (campos, "Art. 37. Republicação."))
    monkeypatch.setattr(web, "texto_integral", lambda _: ("https://www.planalto.gov.br/", "Art. 77. Texto integral."))
    leitura = web._leitura(documento, "commit", "art-77")
    assert 'id="art-77"' in leitura
    assert "Texto oficial no Planalto" in leitura
    assert "Republicação/retificação no acervo" in leitura
    assert "não foi identificado" not in leitura

    def indisponivel(_):
        raise httpx.ConnectError("Fonte indisponível")

    monkeypatch.setattr(web, "texto_integral", indisponivel)
    leitura = web._leitura(documento, "commit", "art-77")
    assert 'id="art-37"' in leitura
    assert "Texto oficial no Planalto" in leitura
    assert "pode trazer apenas parte da norma" in leitura
    assert "não foi identificado" in leitura
