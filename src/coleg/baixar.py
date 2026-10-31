"""Download de arquivos pelo endereço raw do GitHub."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import httpx

from . import __version__, config

_RE_LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)(\))")


class ErroDownload(RuntimeError):
    pass


def cliente() -> httpx.Client:
    return httpx.Client(
        timeout=60, follow_redirects=True,
        headers={"User-Agent": f"coleg/{__version__}"},
        transport=httpx.HTTPTransport(retries=3),
    )


def url(caminho: str, ref: str) -> str:
    return config.RAW_URL.format(ref=ref, caminho=quote(caminho))


def obter(cli: httpx.Client, caminho: str, ref: str) -> bytes:
    resp = cli.get(url(caminho, ref))
    if resp.status_code == 404:
        raise ErroDownload(f"Arquivo não encontrado no repositório: {caminho} "
                           "(se for uma pasta, use 'coleg listar')")
    resp.raise_for_status()
    return resp.content


def separar_cabecalho(texto: str) -> tuple[dict[str, str], str]:
    """Separa o cabeçalho YAML (chave: valor, uma por linha) do corpo."""
    if not texto.startswith("---"):
        return {}, texto
    fim = texto.find("\n---", 3)
    if fim < 0:
        return {}, texto
    campos = {}
    for linha in texto[3:fim].strip().splitlines():
        chave, sep, valor = linha.partition(":")
        if sep and not linha.startswith((" ", "\t", "-")):
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] == '"':
                valor = valor[1:-1].replace('\\"', '"')
            campos[chave.strip()] = valor
    return campos, texto[fim + 4:].lstrip("\n")


def links_relativos(texto: str) -> list[str]:
    alvos = (m[2] for m in _RE_LINK.finditer(texto))
    return [a for a in alvos if not re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", a, re.I)]


def nome_local(caminho: str) -> str:
    """Nome do arquivo gravado sem estrutura de pastas; súmulas de tribunais diferentes
    teriam o mesmo nome, então a jurisprudência ganha o tribunal como prefixo."""
    origem = PurePosixPath(caminho)
    partes = origem.parts
    if partes[0] == "jurisprudencia" and len(partes) >= 3:
        tribunal = partes[2] if partes[1] == "outros-tribunais" else partes[1]
        return f"{tribunal}-{origem.stem}"
    return origem.stem


def baixar(
    cli: httpx.Client, caminho: str, ref: str, destino: Path,
    *, manter_pastas: bool = False, formato: str = "md", anexos: bool = False,
) -> list[Path]:
    """Baixa um documento (e, se pedido, os arquivos que ele referencia). Devolve o que gravou."""
    texto = obter(cli, caminho, ref).decode("utf-8")
    origem = PurePosixPath(caminho)
    base = destino / origem.parent if manter_pastas else destino
    stem = origem.stem if manter_pastas else nome_local(caminho)
    gravados: list[Path] = []

    if anexos:
        pasta_anexos = f"{stem}_anexos"
        for alvo in dict.fromkeys(links_relativos(texto)):
            no_repo = posixpath.normpath(posixpath.join(str(origem.parent), alvo))
            if manter_pastas:
                local = destino / no_repo
            else:
                local = base / pasta_anexos / PurePosixPath(no_repo).name
                texto = texto.replace(f"]({alvo})", f"]({pasta_anexos}/{local.name})")
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(obter(cli, no_repo, ref))
            gravados.append(local)

    if formato == "txt":
        _, texto = separar_cabecalho(texto)
    arquivo = base / (stem + (".txt" if formato == "txt" else origem.suffix))
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")
    return [arquivo, *gravados]
