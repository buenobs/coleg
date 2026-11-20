import httpx

from coleg.baixar import baixar

DOC = "federal/decretos/1944/dec-1-1944-01-01.md"
TEXTO = (
    "---\ntitulo: x\n---\n"
    "![a](../../anexos/decretos/1944/ok.png)\n"
    "![b](../../anexos/decretos/1944/quebrado.png)\n"
    "![c](../../../../../../fora.png)\n"
)


def _cliente(texto=TEXTO):
    def responder(req: httpx.Request) -> httpx.Response:
        caminho = req.url.path
        if caminho.endswith(".md"):
            return httpx.Response(200, content=texto.encode())
        if caminho.endswith("ok.png"):
            return httpx.Response(200, content=b"PNG")
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(responder))


def test_documento_gravado_mesmo_com_anexo_quebrado(tmp_path):
    gravados, avisos = baixar(_cliente(), DOC, "abc", tmp_path, anexos=True)
    doc = tmp_path / "dec-1-1944-01-01.md"
    assert gravados[0] == doc and doc.exists()
    assert (tmp_path / "dec-1-1944-01-01_anexos" / "ok.png").read_bytes() == b"PNG"
    texto = doc.read_text(encoding="utf-8")
    assert "](dec-1-1944-01-01_anexos/ok.png)" in texto
    assert "](../../anexos/decretos/1944/quebrado.png)" in texto  # link de anexo que falhou fica intacto
    assert any("quebrado.png" in a for a in avisos)


def test_anexo_fora_do_destino_e_ignorado(tmp_path):
    destino = tmp_path / "saida"
    gravados, avisos = baixar(_cliente(), DOC, "abc", destino, anexos=True, manter_pastas=True)
    assert not (tmp_path / "fora.png").exists()
    assert all(p.resolve().is_relative_to(destino.resolve()) for p in gravados)
    assert any("fora.png" in a and "ignorado" in a for a in avisos)
    assert (destino / "federal/anexos/decretos/1944/ok.png").exists()
