"""Índice local: clone parcial do repositório (só a árvore) convertido em SQLite."""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import config
from .parser import ORDEM_TRIBUNAL, Consulta, Documento, classificar

ESQUEMA = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE docs (
    caminho TEXT PRIMARY KEY,
    esfera TEXT, colecao TEXT, tipo TEXT, tribunal TEXT,
    numero INTEGER, complemento TEXT, ano INTEGER, data TEXT,
    busca TEXT
);
CREATE INDEX docs_tipo_numero ON docs (tipo, numero);
CREATE INDEX docs_numero ON docs (numero);
"""


class ErroIndice(RuntimeError):
    pass


def _git(*args: str, cwd: Path | None = None) -> str:
    if shutil.which("git") is None:
        raise ErroIndice("git não encontrado no PATH; instale-o para usar 'coleg atualizar'.")
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise ErroIndice(f"git {' '.join(args)} falhou:\n{proc.stderr.strip()}")
    return proc.stdout


def sincronizar_repo() -> str:
    """Clona (ou atualiza) o repositório sem conteúdo de arquivos e devolve o commit."""
    repo = config.pasta_repo()
    if not (repo / ".git").exists():
        if repo.exists():
            shutil.rmtree(repo)
        _git("clone", "--filter=blob:none", "--no-checkout", "--depth=1",
             "--branch", config.BRANCH, config.REPO_URL, str(repo))
    else:
        _git("fetch", "--filter=blob:none", "--depth=1", "origin", config.BRANCH, cwd=repo)
        _git("update-ref", "HEAD", "FETCH_HEAD", cwd=repo)
    return _git("rev-parse", "HEAD", cwd=repo).strip()


def listar_arvore(ref: str, pasta: str = "") -> list[tuple[str, str]]:
    """Itens (tipo, nome) diretamente dentro de uma pasta: tipo é 'tree' ou 'blob'."""
    alvo = pasta.strip("/")
    saida = _git("ls-tree", "-z", ref, "--", f"{alvo}/" if alvo else ".", cwd=config.pasta_repo())
    itens = []
    for linha in filter(None, saida.split("\0")):
        cabeca, caminho = linha.split("\t", 1)
        itens.append((cabeca.split()[1], caminho))
    return itens


def _linha(d: Documento) -> tuple:
    return (d.caminho, d.esfera, d.colecao, d.tipo, d.tribunal, d.numero, d.complemento,
            d.ano, d.data, d.caminho.lower())


def atualizar() -> tuple[str, int]:
    """Recria o índice a partir do commit mais recente. Devolve (commit, nº de documentos)."""
    sha = sincronizar_repo()
    saida = _git("ls-tree", "-r", "-z", "--name-only", sha, cwd=config.pasta_repo())
    docs = [
        d for caminho in saida.split("\0")
        if (caminho == config.CONSTITUICAO or caminho.startswith(config.ESCOPO))
        and (d := classificar(caminho)) is not None
    ]
    destino = config.arquivo_indice()
    temp = destino.with_suffix(".tmp")
    temp.unlink(missing_ok=True)
    with sqlite3.connect(temp) as con:
        con.executescript(ESQUEMA)
        con.executemany("INSERT INTO docs VALUES (?,?,?,?,?,?,?,?,?,?)", map(_linha, docs))
        con.executemany("INSERT INTO meta VALUES (?, ?)", [("commit", sha)])
    con.close()
    os.replace(temp, destino)
    return sha, len(docs)


@dataclass
class Indice:
    con: sqlite3.Connection

    @classmethod
    def abrir(cls) -> "Indice":
        caminho = config.arquivo_indice()
        if not caminho.exists():
            raise ErroIndice("Índice não encontrado. Rode primeiro: coleg atualizar")
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        return cls(con)

    @property
    def commit(self) -> str:
        return self.con.execute("SELECT valor FROM meta WHERE chave='commit'").fetchone()[0]

    def total(self) -> int:
        return self.con.execute("SELECT count(*) FROM docs").fetchone()[0]

    def obter(self, caminho: str) -> Documento | None:
        r = self.con.execute("SELECT * FROM docs WHERE caminho = ?", (caminho,)).fetchone()
        return _doc(r) if r else None

    def buscar(self, c: Consulta, limite: int | None = 50) -> tuple[list[Documento], int]:
        """Devolve (documentos até o limite, total de correspondências)."""
        onde, params = [], []
        for coluna in ("tipo", "numero", "complemento", "ano", "tribunal", "esfera", "caminho"):
            valor = getattr(c, coluna)
            if valor is not None:
                onde.append(f"{coluna} = ?")
                params.append(valor)
        for p in c.palavras:
            onde.append("busca LIKE ?")
            params.append(f"%{p}%")
        where = " AND ".join(onde) or "1"
        total = self.con.execute(f"SELECT count(*) FROM docs WHERE {where}", params).fetchone()[0]
        casos = " ".join(f"WHEN '{t}' THEN {i}" for t, i in ORDEM_TRIBUNAL.items())
        sql = (
            f"SELECT * FROM docs WHERE {where} "
            f"ORDER BY CASE esfera WHEN 'federal' THEN 0 WHEN 'jurisprudencia' THEN 1 ELSE 2 END, "
            f"CASE tribunal {casos} ELSE 99 END, ano DESC, data DESC, numero, caminho"
        )
        if limite:
            sql += f" LIMIT {int(limite)}"
        return [_doc(r) for r in self.con.execute(sql, params)], total


def _doc(r: sqlite3.Row) -> Documento:
    return Documento(r["caminho"], r["esfera"], r["colecao"], r["tipo"], r["tribunal"],
                     r["numero"], r["complemento"], r["ano"], r["data"])
