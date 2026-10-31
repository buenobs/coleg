# coleg — proposta de projeto

CLI para localizar e baixar normas, jurisprudência e demais documentos do repositório
[buenobs/leis-bbs](https://github.com/buenobs/leis-bbs).

## 1. O que foi levantado no repositório

| Item | Valor |
| --- | --- |
| Tamanho | ~7,5 GB, ~1,49 milhão de arquivos (~1,26 milhão `.md`) |
| Branch | `main` |
| Índice pronto | **não existe** (`_indice/` fica fora do versionamento) |
| Formato | Markdown com cabeçalho YAML (`titulo`, `tipo`, `numero`, `data`, `ementa`, `situacao`, `fonte`…) |

Distribuição dos `.md`:

| Pasta | Arquivos | Estrutura |
| --- | ---: | --- |
| `estaduais/` | 728.250 | `UF/<tipo>/…` |
| `reguladores/` | 273.456 | `<orgao>/<tipo>/…` (anvisa, bcb, cade, contran, rfb…) |
| `federal/` | 207.283 | `<tipo>/AAAA/lei-10406-2002-01-10.md` |
| `municipais/` | 39.122 | `UF/<municipio>/…` |
| `jurisprudencia/` | 11.700 | `stf/{sumulas,sumulas-vinculantes,repercussao-geral,controle-concentrado}`, `stj/{sumulas,repetitivos}`, `tst`, `tnu`, `trf4`… |
| `tratados/` | 161 | `bitributacao`, `direitos-humanos`, `oit` |
| `constituicao.md` | 1 | CF/88 |

Conclusão: navegar pela API do GitHub não serve (60 req/h sem token, árvore truncada).
Testei um **clone parcial sem conteúdo** (`git clone --filter=blob:none --no-checkout --depth=1`):
**5 s e 45 MB** trazem a lista completa dos 1,49 milhão de caminhos. Essa é a base do índice.

## 2. Arquitetura

```
coleg atualizar ──► clone parcial (só árvore) ──► git ls-tree ──► SQLite (FTS5) local
coleg buscar    ──► consulta no SQLite (instantâneo, offline)
coleg baixar    ──► raw.githubusercontent.com/buenobs/leis-bbs/main/<caminho> ──► disco
```

- **Índice local**: cada caminho é decomposto em campos — esfera, UF, município, órgão,
  tribunal, tipo, número, ano, data — a partir do padrão de nomes das pastas e arquivos.
- **Download**: arquivo a arquivo via URL *raw* (sem limite de API, sem token).
- **Ementa/cabeçalho**: lidos sob demanda (`info`), baixando só o arquivo escolhido.
- Cache em `%LOCALAPPDATA%\coleg` (Windows) / `~/.cache/coleg`.

## 3. Comandos propostos

```bash
coleg atualizar                       # cria/atualiza o índice (~5 s)

coleg buscar lei 8666                 # texto livre, com apelidos
coleg buscar lc 101                   # lei complementar
coleg buscar decreto-lei 2848
coleg buscar sv 13                    # súmula vinculante STF
coleg buscar sumula 7 stj
coleg buscar adi 4277
coleg buscar tema 1046 stf
coleg buscar lei 1234 --uf SP         # estadual
coleg buscar --orgao anvisa --tipo rdc --ano 2022
coleg buscar --municipio vitoria --uf ES lei 5000

coleg info 3                          # cabeçalho/ementa do 3º resultado da última busca
coleg baixar 3                        # baixa o 3º resultado
coleg baixar lei 8666                 # busca + baixa direto se o resultado for único
coleg baixar federal/leis-ordinarias/1993/lei-8666-1993-06-21.md
coleg baixar cf                       # Constituição Federal
coleg baixar 1 2 5 -o .\normas        # vários de uma vez, pasta de destino
coleg listar jurisprudencia/stf       # navegar pastas
```

Opções gerais: `-o/--destino`, `--formato md|txt` (txt = remove o YAML), `--limite N`,
`--json` (saída para scripts).

Apelidos iniciais: `lei`, `lc`, `dl`/`decreto-lei`, `ec`, `decreto`, `sv`, `sumula`,
`tema`, `adi`/`adc`/`adpf`/`ado`, `rdc`, `in`, `resolucao`, `portaria`, `cf`.

## 4. Tecnologia

- Python 3.11+ (já disponível na máquina), instalação com `pipx install .`
- `typer` (CLI), `rich` (tabelas coloridas), `httpx` (download), `sqlite3` da biblioteca padrão
- Requer `git` no PATH (só para `atualizar`)

```
coleg/
  pyproject.toml
  README.md
  src/coleg/
    cli.py        # comandos
    indice.py     # clone parcial + ls-tree + SQLite
    parser.py     # caminho -> campos; texto livre -> filtros (apelidos)
    baixar.py     # download raw
    config.py     # pastas de cache
  tests/
```

## 5. Fases

1. **MVP**: `atualizar`, `buscar`, `info`, `baixar`, `listar` para federal, CF, jurisprudência e tratados.
2. Estaduais, municipais e reguladores (mesmo mecanismo, mais regras de parsing por pasta).
3. Extras opcionais: busca por palavras da ementa (indexar cabeçalhos sob demanda),
   anexos PDF, modo interativo.

## 6. Pontos para confirmar

1. Nome do comando: `coleg`?
2. Python + pipx está ok, ou prefere outra linguagem / executável único?
3. Começar pelo MVP da fase 1, ou já cobrir todas as esferas?
