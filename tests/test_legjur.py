import json
import sqlite3
from contextlib import closing
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from typer.testing import CliRunner

from coleg import config, web
from coleg.cli import app
from coleg.indice import ESQUEMA, _linha
from coleg.parser import Consulta, classificar, interpretar
from coleg.pesquisa_externa import links_busca


@pytest.fixture
def indice_local(tmp_path, monkeypatch):
    monkeypatch.setenv("COLEG_HOME", str(tmp_path))
    norma = classificar("federal/leis-ordinarias/2015/lei-13105-2015-03-16.md")
    sumula = classificar("jurisprudencia/stj/sumulas/sumula-7.md")
    with closing(sqlite3.connect(config.arquivo_indice())) as con, con:
        con.executescript(ESQUEMA)
        con.execute("INSERT INTO meta VALUES ('commit', 'teste')")
        con.executemany("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?)", map(_linha, (norma, sumula)))


@pytest.mark.parametrize(("texto", "destino"), [
    ("Lei 14.133/2021", "legislacao"),
    ("repetitivo 903", "jurisprudencia"),
    ("súmula 7 STJ", "sumula"),
])
def test_links_usam_acervo_e_preservam_consulta(texto, destino):
    link, = (link for link in links_busca(texto, interpretar(texto)) if link.fonte == "LegJur")
    partes = urlsplit(link.url)
    assert partes.netloc == "www.legjur.com"
    assert partes.path == f"/{destino}/busca"
    assert parse_qs(partes.query) == {"q": [texto]}


def test_web_oferece_legjur_sem_resultado_e_preserva_dispositivo(indice_local):
    html = web.pagina({"q": ["LGPD, art. 5º, § 2º"]})
    assert "Nenhum documento corresponde" in html
    assert 'href="https://www.legjur.com/legislacao/busca?q=LGPD%2C+art.+5%C2%BA%2C+%C2%A7+2%C2%BA"' in html
    assert ">Legislação no LegJur</a>" in html
    assert "/jurisprudencia/busca" not in html
    for acervo in ("Legislação", "Jurisprudências", "Artigos", "Modelos"):
        assert f">{acervo} no Modelo Inicial</a>" in html


def test_cli_mantem_json_e_vincula_cada_resultado(indice_local):
    resultado = CliRunner().invoke(app, ["buscar", "--tipo", "sumula", "--numero", "7", "--json"])
    assert resultado.exit_code == 0
    documento, = json.loads(resultado.stdout)
    assert documento["url"].startswith("https://raw.githubusercontent.com/")
    assert urlsplit(documento["url_legjur"]).path == "/sumula/busca"
    assert [link for link in documento["links_externos"] if link["fonte"] == "LegJur"] == [
        {"fonte": "LegJur", "acervo": "Súmulas", "url": documento["url_legjur"]},
    ]
    assert [link["acervo"] for link in documento["links_externos"] if link["fonte"] == "Modelo Inicial"] == [
        "Legislação", "Jurisprudências", "Artigos", "Modelos",
    ]


def test_cli_mostra_link_com_filtros_mesmo_sem_resultados(indice_local):
    resultado = CliRunner().invoke(app, ["buscar", "--tipo", "lei", "--numero", "14133", "--ano", "2021"])
    assert resultado.exit_code == 1
    assert "https://www.legjur.com/legislacao/busca?q=Lei+14133%2F2021" in resultado.stderr


def test_jurisprudencia_preserva_consulta_no_legjur_e_tcu():
    texto = '"dispensa de licitação" 1211/2021 & aditivo'
    legjur, tcu = (link for link in links_busca(texto, Consulta(esfera="jurisprudencia"))
                   if link.fonte in {"LegJur", "TCU"})
    assert (legjur.fonte, tcu.fonte) == ("LegJur", "TCU")
    assert parse_qs(urlsplit(legjur.url).query) == {"q": [texto]}
    partes_tcu = urlsplit(tcu.url)
    assert partes_tcu.netloc == "pesquisa.apps.tcu.gov.br"
    assert partes_tcu.path.startswith("/resultado/todas-bases/")
    termo = partes_tcu.path.rsplit("/", 1)[-1]
    assert "%252F" in termo
    assert unquote(unquote(termo)) == texto
    assert parse_qs(partes_tcu.query) == {"pb": ["jurisprudencia-selecionada"]}


def test_web_exibe_legjur_e_tcu_sem_resultados_locais(indice_local):
    html = web.pagina({"q": ["dispensa de licitação"], "esfera": ["jurisprudencia"]})
    assert "Nenhum documento corresponde" in html
    assert ">Jurisprudência no LegJur</a>" in html
    assert ">Jurisprudência no TCU</a>" in html
    assert "dispensa%2520de%2520licita%25C3%25A7%25C3%25A3o?pb=jurisprudencia-selecionada" in html


def test_jurisprudencia_sem_termos_abre_as_paginas_de_pesquisa():
    assert [link.url for link in links_busca("", Consulta(esfera="jurisprudencia"))] == [
        "https://www.legjur.com/jurisprudencia/inicio",
        "https://pesquisa.apps.tcu.gov.br/pesquisa/jurisprudencia",
        "https://modeloinicial.com.br/lei",
        "https://modeloinicial.com.br/jurisprudencia",
        "https://modeloinicial.com.br/artigos",
        "https://modeloinicial.com.br/modelos-peticao",
    ]


def test_cli_oferece_legjur_e_tcu_para_jurisprudencia(indice_local):
    resultado = CliRunner().invoke(app, ["buscar", "dispensa de licitação", "--esfera", "jurisprudencia"])
    assert resultado.exit_code == 1
    assert "LegJur (Jurisprudência): https://www.legjur.com/jurisprudencia/busca?q=" in resultado.stderr
    assert "TCU (Jurisprudência): https://pesquisa.apps.tcu.gov.br/resultado/todas-bases/" in resultado.stderr


def test_modelo_inicial_preserva_consulta_nos_quatro_acervos():
    texto = '"locação" & art. 5º/2021'
    links = [link for link in links_busca(texto, Consulta(esfera="federal"))
             if link.fonte == "Modelo Inicial"]
    assert [(link.acervo, urlsplit(link.url).path) for link in links] == [
        ("Legislação", "/buscar-lei"),
        ("Jurisprudências", "/buscar-jurisprudencia"),
        ("Artigos", "/buscar-artigos"),
        ("Modelos", "/buscar"),
    ]
    for link in links:
        partes = urlsplit(link.url)
        assert (partes.scheme, partes.netloc) == ("https", "modeloinicial.com.br")
        assert parse_qs(partes.query) == {"q": [texto]}
