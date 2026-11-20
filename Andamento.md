# Andamento do projeto coleg

## 20/11/2026 — Avaliação cruzada (Kimi K3 × Gemini web) e correções

### Avaliação

1. O Kimi K3 (pela ponte ask.py, sessão `avaliacao-coleg`, somente leitura) deu nota 7,5. O Gemini web (conversa `avaliacao-coleg`, com o projeto anexado num único arquivo numerado) deu nota 7,2.
2. O Claude conferiu no código cada problema apontado:
   a. Kimi: 10 de 11 confirmados.
   b. Gemini: 6 de 12 confirmados. Não se sustentaram: "substituição global corrompe o documento" (o replace só troca links com o mesmo destino), "documentação promete opções inexistentes" (estão em "Comandos propostos", para a Fase 2), "injeção de SQL" (o trecho interpolado vem só de constantes) e "só há testes do parser".
3. As duas avaliações concordam no plano da Fase 2:
   a. colunas `uf`, `municipio` e `orgao` no índice;
   b. opções `--uf`, `--municipio` e `--orgao` no `buscar`;
   c. troca do `LIKE` por FTS5.
4. Sugestões só do Kimi:
   a. teste de contrato com uma amostra real de caminhos antes de ligar a Fase 2;
   b. prefixo de UF, município ou órgão no nome do arquivo baixado, para evitar colisões.

### Corrigido nesta data

a. **Reedição de MP e complemento com hífen** (`src/coleg/parser.py`, em `interpretar`): `mp 2200-2` e `dpl 44-a` deixaram de ser quebrados no hífen e passaram a virar número + complemento. Antes, `mp 2200-2` buscava o número 2200 e a palavra "2", misturando as reedições. Conferido no índice real: um único resultado, `mpv-2200-2-2001-08-24.md`.

b. **Anexo quebrado não impede mais gravar o documento** (`src/coleg/baixar.py`, em `baixar`): os anexos passaram a ser opcionais. Um anexo que falhe vira aviso, e o link para ele fica como estava no texto. O documento principal é gravado sempre. `baixar` passou a devolver `(gravados, avisos)`, e a CLI mostra os avisos (`src/coleg/cli.py`).

c. **Anexo fora da pasta de destino** (`src/coleg/baixar.py`): um link que, depois de normalizado, sai da raiz do repositório (`../`) ou cuja gravação cairia fora da pasta de destino (caso de `--manter-pastas`) é ignorado com aviso.

### Testes

a. 7 testes novos: 5 em `tests/test_parser.py` (casos de `interpretar`) e 2 em `tests/test_baixar.py` (download simulado com `httpx.MockTransport`).
b. Suíte completa: 59 testes passando.

### Pendências apontadas na avaliação (não corrigidas)

1. Validar `--tribunal` e `--esfera` (hoje um erro de digitação dá "Nada encontrado") — `src/coleg/cli.py`.
2. `--limite 0` devolve todos os resultados — `src/coleg/indice.py`, em `buscar`.
3. `Indice.commit` dá traceback se a tabela `meta` estiver vazia — `src/coleg/indice.py`.
4. git sem timeout e sem `GIT_TERMINAL_PROMPT=0` — `src/coleg/indice.py`, em `_git`.
5. `regimento-xxx` grava como tribunal um nome não validado — `src/coleg/parser.py`.
6. `coleg baixar 13105` é lido como índice da última busca, e não como número de lei — `src/coleg/cli.py`, em `_resolver`.
7. O `PROJETO.md` cita FTS5, mas o código usa `LIKE`.
8. Faltam testes de `indice.py` e `cli.py`.

### Próximo passo

Fase 2: incluir estaduais, municipais e reguladores na busca, começando pelo teste de contrato com uma amostra real de caminhos.
