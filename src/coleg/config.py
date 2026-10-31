"""Constantes e pastas locais."""

import os
import sys
from pathlib import Path

REPO_URL = "https://github.com/buenobs/leis-bbs.git"
RAW_URL = "https://raw.githubusercontent.com/buenobs/leis-bbs/{ref}/{caminho}"
BRANCH = "main"

# Pastas do repositório cobertas pelo índice (fase 1).
ESCOPO = ("federal/", "jurisprudencia/", "tratados/")
CONSTITUICAO = "constituicao.md"


def pasta_dados() -> Path:
    """Pasta de cache: COLEG_HOME, ou %LOCALAPPDATA%\\coleg, ou ~/.cache/coleg."""
    if env := os.environ.get("COLEG_HOME"):
        base = Path(env)
    elif sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "coleg"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "coleg"
    base.mkdir(parents=True, exist_ok=True)
    return base


def pasta_repo() -> Path:
    return pasta_dados() / "repo"


def arquivo_indice() -> Path:
    return pasta_dados() / "indice.sqlite"


def arquivo_ultima_busca() -> Path:
    return pasta_dados() / "ultima_busca.json"
