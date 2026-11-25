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

## 24 e 25/11/2026 — Interface web, pesquisa externa e preparação do deploy

Entrada escrita em 25/11/2026 a partir dos commits `33a85d7` (24/11) e `810a2a9` (25/11).

### Incluído em 24/11 (`33a85d7`)

a. **Interface web** (`src/coleg/web.py`, `src/coleg/static/`): comando `coleg web [--porta]`, em `127.0.0.1:8000` por padrão. Usa o mesmo índice da CLI e carrega o texto do GitHub ao abrir o documento. Tem filtro por acervo, paginação de 20 em 20, sumário, busca no documento e histórico dos 10 últimos acessos (guardado só no navegador).

b. **Leitor de dispositivos** (`src/coleg/leitor.py`): reconhece artigos, parágrafos, incisos, alíneas e itens no Markdown, com âncora para cada um. Aceita referências como `LGPD, art. 5º, § 1º` e `art. 5º da LGPD`. Dependência nova: `markdown-it-py`.

c. **Texto integral oficial** (`src/coleg/fontes.py`): quando o acervo só tem a republicação ou retificação, o leitor busca o texto compilado no Planalto e confere a sequência de artigos antes de usar. Por enquanto, só a Lei 14.133/2021 (194 artigos). Se a busca falhar, mostra o texto do acervo com aviso.

d. **Pesquisa externa** (`src/coleg/pesquisa_externa.py`): links para continuar a consulta no LegJur (legislação, súmulas e jurisprudência) e no TCU (jurisprudência), na web e no `buscar`. No `--json`, cada resultado ganhou `links_externos` e, quando houver, `url_legjur`.

e. **Paginação no índice** (`src/coleg/indice.py`): `Indice.buscar` ganhou o parâmetro `deslocamento`.

f. **Deploy** (`Dockerfile`, `.dockerignore`): imagem para coleg.artes.digital, com gunicorn na porta 8080, usuário sem privilégios e índice em `/var/lib/coleg`, criado na primeira subida. A entrada WSGI é `coleg.web:application`.

### Incluído em 25/11 (`810a2a9`)

a. **Modelo Inicial** (`src/coleg/pesquisa_externa.py`): links para os quatro acervos do portal (legislação, jurisprudências, artigos e modelos). Aparecem em toda busca, qualquer que seja o acervo. Sem termo de busca, abrem a página inicial de cada um.

### Git

a. Os dois commits foram feitos na branch `deploy/coleg-artes-digital`. Em 25/11 a `main` foi levada até `810a2a9` por fast-forward e enviada ao GitHub. A branch de deploy foi mantida.

### Testes

a. 13 testes novos: 12 em 24/11 e 1 em 25/11 (`tests/test_fontes.py` e `tests/test_legjur.py`).
b. Suíte completa: 72 testes passando.

### Pendências

1. Da avaliação de 20/11, os itens 1 a 7 continuam abertos. O item 8 foi atendido em parte: o `buscar` da CLI já tem testes, mas faltam testes próprios de `indice.py` e dos demais comandos.
2. Sem teste: a entrada WSGI (`application`), a paginação da web, `separar_referencia` e `static/web.js`.
3. Confirmar qual versão está no ar em coleg.artes.digital.
4. O índice do contêiner só é criado se não existir; falta definir como atualizá-lo depois.

### Próximo passo

Conferir a versão publicada e, depois, retomar a Fase 2 (estaduais, municipais e reguladores), começando pelo teste de contrato com uma amostra real de caminhos.
