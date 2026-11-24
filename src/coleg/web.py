"""Interface web local para o índice e os documentos usados pela CLI."""

from __future__ import annotations

import socket
import sqlite3
from contextlib import closing
from functools import lru_cache
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, quote, urlencode, urlsplit

import httpx

from .apelidos import APELIDOS
from .baixar import ErroDownload, cliente, obter, separar_cabecalho, url
from .fontes import fonte_integral, texto_integral
from .indice import ErroIndice, Indice
from .leitor import renderizador, separar_referencia, estruturar
from .parser import TIPOS, Documento, interpretar
from .pesquisa_externa import LinkPesquisa, links_busca

_ESFERAS = {"federal": "Legislação federal", "jurisprudencia": "Jurisprudência", "tratados": "Tratados"}
_ATALHOS = (("Constituição", "CF"), ("CPC", "CPC"), ("LGPD", "LGPD"), ("Lei 14.133/2021", "Lei 14.133/2021"))
_LIMITE = 20
_TIPOS_ESTRUTURA = {"artigo", "paragrafo", "inciso", "alinea", "item"}


def _href(consulta: str, esfera: str = "", doc: str = "", pagina: int = 1, ancora: str = "") -> str:
    params = {"q": consulta}
    if esfera:
        params["esfera"] = esfera
    if doc:
        params["doc"] = doc
    if pagina > 1:
        params["pagina"] = str(pagina)
    return escape("/?" + urlencode(params) + (f"#{quote(ancora)}" if ancora else ""))


def _fonte(valor: str) -> str:
    try:
        link = urlsplit(valor)
    except ValueError:
        return ""
    return escape(valor) if link.scheme in {"https", "http"} and link.netloc else ""


@lru_cache(maxsize=16)
def _carregar(caminho: str, commit: str) -> tuple[dict[str, str], str]:
    with cliente() as http:
        texto = obter(http, caminho, commit).decode("utf-8-sig")
    return separar_cabecalho(texto.replace("\r\n", "\n"))


def _aviso(titulo: str, texto: str) -> str:
    return f'<div class="aviso"><h2>{titulo}</h2><p>{texto}</p></div>'


def _resultados(docs: list[Documento], total: int, consulta: str, esfera: str,
                selecionado: str, pagina: int, ancora: str, links_externos: list[LinkPesquisa],
                acesso: tuple[str, str]) -> str:
    rotulo = "resultado" if total == 1 else "resultados"
    cabecalho = f'<div class="painel-topo"><h2>Resultados</h2><span>{total:,} {rotulo}</span></div>'.replace(",", ".")
    itens = []
    for doc in docs:
        href = _href(consulta, esfera, doc.caminho, pagina, ancora)
        atual = ' aria-current="page"' if doc.caminho == selecionado else ""
        tipo = TIPOS.get(doc.tipo, (_ESFERAS.get(doc.esfera, "Documento"),))[0]
        metadados = " · ".join(filter(None, (tipo, (doc.tribunal or "").upper(), str(doc.ano or ""))))
        itens.append(
            f'<li><a href="{href}"{atual}><span>{escape(metadados)}</span>'
            f'<strong>{escape(doc.titulo)}</strong></a></li>'
        )
    navegacao = []
    if pagina > 1:
        navegacao.append(f'<a href="{_href(consulta, esfera, pagina=pagina - 1)}">Anterior</a>')
    if pagina * _LIMITE < total:
        navegacao.append(f'<a href="{_href(consulta, esfera, pagina=pagina + 1)}">Próxima</a>')
    paginas = f'<nav class="paginacao" aria-label="Páginas">{"".join(navegacao)}</nav>' if navegacao else ""
    if itens:
        lista = f'<ul class="resultados">{"".join(itens)}</ul>'
    else:
        mensagem = "Busque por uma sigla, número ou tipo de documento." if not consulta and not esfera else (
            "Nenhum documento corresponde à busca. Experimente outra sigla ou ajuste o filtro."
        )
        lista = f'<p class="sem-resultados">{mensagem}</p>'
    links = "".join(
        f'<a href="{escape(link.url)}" target="_blank" rel="noopener noreferrer">'
        f'{escape(link.acervo if len(links_externos) > 1 else "Pesquisar")} no {escape(link.fonte)}</a>'
        for link in links_externos
    )
    if links:
        links = f'<nav class="links-externos" aria-label="Pesquisas externas">{links}</nav>'
    url_acesso, rotulo_acesso = acesso
    historico = f'''
      <nav class="historico" aria-labelledby="titulo-historico" data-url="{url_acesso}"
           data-rotulo="{escape(rotulo_acesso)}" hidden>
        <h2 id="titulo-historico">Histórico de acessos</h2>
        <p>Nenhuma consulta anterior.</p>
        <ol></ol>
      </nav>'''
    return (f'<aside class="painel painel-resultados" aria-label="Resultados da busca">'
            f'{cabecalho}{links}{lista}{paginas}{historico}</aside>')


def _leitura(doc: Documento, commit: str, ancora: str) -> str:
    try:
        campos, corpo = _carregar(doc.caminho, commit)
    except (httpx.HTTPError, ErroDownload, UnicodeError):
        return _aviso("Texto indisponível", "Não foi possível carregar o documento do GitHub. Recarregue a página para tentar novamente.")

    arquivo_acervo = url(doc.caminho, commit)
    origem = arquivo_acervo
    versao = campos.get("versao_texto", "")
    parcial = versao.casefold() == "republicação/retificação"
    fonte_preferida = fonte_integral(doc.caminho) if parcial else None
    integral = None
    if fonte_preferida:
        try:
            integral = texto_integral(doc.caminho)
        except (httpx.HTTPError, ValueError):
            pass
        if integral:
            origem, corpo = integral
            versao = "Texto compilado do Planalto"
    md = renderizador(origem)
    titulo = campos.get("titulo") or doc.titulo
    trechos = estruturar(corpo)
    if trechos and trechos[0].tipo == "secao" and trechos[0].markdown.startswith("# "):
        primeiro = trechos.pop(0)
        titulo = primeiro.rotulo
        _, _, restante = primeiro.markdown.partition("\n")
        if restante.strip():
            primeiro.tipo, primeiro.ancora, primeiro.markdown = "texto", "", restante
            trechos.insert(0, primeiro)

    tipo = TIPOS.get(doc.tipo, ("Documento",))[0]
    situacao = "Marcado como revogado no acervo" if campos.get("revogada") == "true" else campos.get("situacao")
    metadados = " · ".join(filter(None, (tipo, campos.get("data") or str(doc.ano or ""))))
    informacoes = "".join(f'<span>{escape(valor)}</span>' for valor in (versao, situacao) if valor)
    fonte = _fonte(fonte_preferida or campos.get("fonte", ""))
    rotulo_fonte = "Texto oficial no Planalto" if fonte_preferida else "Fonte indicada"
    fontes = f'<a href="{fonte}" rel="noreferrer">{rotulo_fonte}</a>' if fonte else ""
    rotulo_acervo = "Republicação/retificação no acervo" if integral else "Markdown do acervo"
    fontes += f'<a href="{escape(arquivo_acervo)}" rel="noreferrer">{rotulo_acervo}</a>'
    dispositivos = any(t.tipo in _TIPOS_ESTRUTURA for t in trechos)
    sumario = []
    corpo_html = []
    for trecho in trechos:
        id_html = f' id="{trecho.ancora}" tabindex="-1"' if trecho.ancora else ""
        rotulo = f' data-rotulo="{escape(trecho.rotulo)}"' if trecho.ancora else ""
        corpo_html.append(
            f'<div class="trecho {trecho.tipo}"{id_html}{rotulo}>{md.render(trecho.markdown)}</div>'
        )
        if trecho.tipo == "artigo" or (not dispositivos and trecho.tipo == "secao"):
            sumario.append(f'<li><a href="#{trecho.ancora}">{escape(trecho.rotulo)}</a></li>')

    avisos = []
    if parcial and not integral:
        avisos.append("O arquivo do acervo é uma republicação ou retificação e pode trazer apenas parte da norma. Consulte a fonte indicada para conferir o texto integral.")
    if ancora and not any(t.ancora == ancora for t in trechos):
        avisos.append("O dispositivo solicitado não foi identificado nesta versão do documento.")
    aviso = "".join(f'<p class="nota">{texto}</p>' for texto in avisos)
    navegacao = '<details class="sumario"><summary>Sumário</summary><ul>' + "".join(sumario) + "</ul></details>" if sumario else ""
    return f"""
      <header class="documento-topo">
        <p class="metadados">{escape(metadados)}</p>
        <h2>{escape(titulo)}</h2>
        <div class="versoes">{informacoes}</div>
        <div class="fontes">{fontes}</div>
      </header>
      <div class="ferramentas">
        <div class="busca-texto" hidden>
          <label for="no-documento">Buscar no documento</label>
          <input id="no-documento" type="search" autocomplete="off" placeholder="Art. 5º ou proteção de dados" aria-controls="ocorrencias">
          <div class="ocorrencias" id="ocorrencias" hidden>
            <p role="status"></p><ul aria-label="Ocorrências no documento"></ul>
          </div>
        </div>
        {navegacao}
      </div>
      {aviso}
      <div id="texto" class="texto">{"".join(corpo_html)}</div>"""


def pagina(params: dict[str, list[str]]) -> str:
    consulta = params.get("q", ["LGPD"])[0].strip()
    esfera = params.get("esfera", [""])[0]
    esfera = esfera if esfera in _ESFERAS else ""
    caminho = params.get("doc", [""])[0]
    numero_pagina = params.get("pagina", ["1"])[0]
    numero_pagina = int(numero_pagina) if numero_pagina.isascii() and numero_pagina.isdecimal() and len(numero_pagina) <= 5 else 1
    numero_pagina = max(1, numero_pagina)
    docs, total, erro = [], 0, ""
    selecionado, commit, ancora = None, "", ""
    links_externos = []
    try:
        consulta_documento, ancora = separar_referencia(consulta)
        filtros = interpretar(consulta_documento)
        if esfera:
            filtros.esfera = esfera
        links_externos = links_busca(consulta, filtros)
        with closing(Indice.abrir().con) as con:
            indice = Indice(con)
            if not filtros.vazia():
                docs, total = indice.buscar(filtros, _LIMITE, deslocamento=(numero_pagina - 1) * _LIMITE)
                if total and not docs:
                    numero_pagina = 1
                    docs, total = indice.buscar(filtros, _LIMITE)
            selecionado = indice.obter(caminho) if caminho else (docs[0] if total == 1 else None)
            if selecionado:
                commit = indice.commit
    except ErroIndice:
        erro = _aviso("Prepare o índice local", "Execute <code>coleg atualizar</code> no terminal e recarregue esta página.")
    except sqlite3.Error:
        erro = _aviso("Índice indisponível", "Execute <code>coleg atualizar</code> para recriar o índice local.")
    except (ValueError, OverflowError):
        erro = _aviso("Revise a consulta", "Informe um número e um ano válidos. Exemplo: Lei 14.133/2021.")

    sugestoes = "".join(
        f'<option value="{escape(a.sigla)}">{escape(a.nome)}</option>'
        f'<option value="{escape(a.nome)}">{escape(a.sigla)}</option>' for a in APELIDOS
    )
    atalhos = "".join(f'<a href="{_href(q)}">{escape(rotulo)}</a>' for rotulo, q in _ATALHOS)
    opcoes = "".join(
        f'<option value="{valor}"{" selected" if esfera == valor else ""}>{rotulo}</option>'
        for valor, rotulo in _ESFERAS.items()
    )
    acesso = ("", "")
    if ("q" in params or esfera or caminho) and (consulta or esfera or selecionado):
        doc_aberto = selecionado if caminho else None
        rotulo = " · ".join(filter(None, (consulta, _ESFERAS.get(esfera), doc_aberto.titulo if doc_aberto else None)))
        acesso = (_href(consulta, esfera, doc_aberto.caminho if doc_aberto else "",
                        numero_pagina if doc_aberto else 1, ancora), rotulo)
    resultados = _resultados(docs, total, consulta, esfera, selecionado.caminho if selecionado else "",
                             numero_pagina, ancora, links_externos, acesso)
    if erro:
        leitura = erro
    elif selecionado:
        leitura = _leitura(selecionado, commit, ancora)
    elif caminho:
        leitura = _aviso("Documento fora do índice", "Faça uma busca para selecionar um documento do acervo.")
    elif docs:
        leitura = _aviso("Selecione um documento", "Abra um resultado para consultar o texto e navegar pelos dispositivos.")
    elif ancora:
        leitura = _aviso("Informe a norma", "Inclua a sigla ou o número na busca. Exemplo: LGPD, art. 5º.")
    else:
        leitura = _aviso("Consulta legislativa", "Use a busca para localizar uma norma, uma súmula ou um tratado.")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="requested-device" content="{escape(ancora)}">
  <title>Coleg — Consulta legislativa</title>
  <link rel="stylesheet" href="/web.css">
  <script src="/web.js" defer></script>
</head>
<body>
  <a class="pular" href="#leitura">Pular para a leitura</a>
  <header class="topo"><div class="largura">
    <a class="marca" href="/"><span class="livro" aria-hidden="true">§</span>Coleg</a>
    <span class="topo-descricao">Acervo legislativo</span>
  </div></header>
  <main class="largura">
    <section class="busca" aria-labelledby="titulo">
      <h1 id="titulo">Consulta legislativa</h1>
      <form role="search" action="/">
        <div class="campo"><label for="consulta">Norma ou referência</label>
          <input id="consulta" name="q" type="search" maxlength="200" list="apelidos" value="{escape(consulta)}" placeholder="Ex.: LGPD, art. 5º">
          <datalist id="apelidos">{sugestoes}</datalist>
        </div>
        <div class="campo acervo"><label for="esfera">Acervo</label>
          <select id="esfera" name="esfera"><option value="">Todo o acervo</option>{opcoes}</select>
        </div>
        <button type="submit">Buscar</button>
      </form>
      <nav class="atalhos" aria-label="Normas frequentes"><span>Acesso rápido</span>{atalhos}</nav>
    </section>
    <section class="workspace" aria-label="Resultados e leitor">
      {resultados}
      <article class="painel leitor" id="leitura" tabindex="-1" aria-label="Leitor do documento">{leitura}</article>
    </section>
  </main>
</body>
</html>"""


def _resposta(caminho: str, consulta: str) -> tuple[HTTPStatus, str, bytes]:
    if caminho == "/":
        try:
            params = parse_qs(consulta, keep_blank_values=True, max_num_fields=20)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, "text/plain", b"Bad Request"
        return HTTPStatus.OK, "text/html", pagina(params).encode("utf-8")
    if caminho in {"/web.css", "/web.js"}:
        tipo = "text/css" if caminho == "/web.css" else "text/javascript"
        conteudo = files("coleg").joinpath("static", caminho[1:]).read_bytes()
        return HTTPStatus.OK, tipo, conteudo
    return HTTPStatus.NOT_FOUND, "text/plain", b"Not Found"


def _cabecalhos(tipo: str, tamanho: int) -> list[tuple[str, str]]:
    cabecalhos = [
        ("Content-Type", f"{tipo}; charset=utf-8"),
        ("Content-Length", str(tamanho)),
        ("X-Content-Type-Options", "nosniff"),
        ("Content-Security-Policy", "default-src 'self'; img-src 'self' https:; object-src 'none'; frame-ancestors 'none'"),
        ("Referrer-Policy", "no-referrer"),
    ]
    if tipo == "text/html":
        cabecalhos.append(("Cache-Control", "no-store"))
    return cabecalhos


def application(environ, start_response):
    """Entrada WSGI para servir a interface com um servidor de produção."""
    metodo = environ["REQUEST_METHOD"]
    if metodo in {"GET", "HEAD"}:
        status, tipo, conteudo = _resposta(environ["PATH_INFO"], environ.get("QUERY_STRING", ""))
    else:
        status, tipo, conteudo = HTTPStatus.METHOD_NOT_ALLOWED, "text/plain", b"Method Not Allowed"
    cabecalhos = _cabecalhos(tipo, len(conteudo))
    if status == HTTPStatus.METHOD_NOT_ALLOWED:
        cabecalhos.append(("Allow", "GET, HEAD"))
    start_response(f"{status.value} {status.phrase}", cabecalhos)
    return [b"" if metodo == "HEAD" else conteudo]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        destino = urlsplit(self.path)
        status, tipo, conteudo = _resposta(destino.path, destino.query)
        if status != HTTPStatus.OK:
            self.send_error(status)
            return
        self.send_response(status)
        for nome, valor in _cabecalhos(tipo, len(conteudo)):
            self.send_header(nome, valor)
        self.end_headers()
        self.wfile.write(conteudo)


class _Servidor(ThreadingHTTPServer):
    # No Windows, SO_REUSEADDR permite que outro processo ocupe a mesma porta.
    allow_reuse_address = not hasattr(socket, "SO_EXCLUSIVEADDRUSE")

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def servir(porta: int) -> None:
    with _Servidor(("127.0.0.1", porta), _Handler) as servidor:
        print(f"Coleg disponível em http://127.0.0.1:{porta}", flush=True)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
