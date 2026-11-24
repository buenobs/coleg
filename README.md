# coleg

CLI e interface web local para localizar e consultar normas federais, a Constituição, jurisprudência e tratados do
repositório [buenobs/leis-bbs](https://github.com/buenobs/leis-bbs).

O índice é montado a partir de um clone parcial do git que traz só a lista de arquivos
(~45 MB, poucos segundos). A busca roda local e offline, e cada arquivo é baixado pela URL
*raw* do GitHub, sem token e sem limite da API.

## Instalação

Requer Python 3.11+ e `git` no PATH.

```bash
python -m venv .venv
.venv\Scripts\pip install -e .
```

Ou, para ter o comando disponível em qualquer lugar: `pipx install .`

## Uso

```bash
coleg atualizar                     # cria/atualiza o índice (rode primeiro)
```

### Interface web

```bash
coleg web
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000) no navegador. Para escolher outra
porta, use `coleg web --porta 8080`. A interface usa o mesmo índice da CLI e
carrega o texto do GitHub ao abrir um documento.

Busque por sigla, número ou referência, como `LGPD, art. 5º` ou `CPC, art. 3º, § 2º`.
No leitor, use o sumário para ir a um artigo e a busca no documento para localizar
artigos e palavras. Parágrafos, incisos, alíneas e itens reconhecidos aparecem com
recuos e podem ser acessados pelos resultados da busca no documento.

### Buscar

```bash
coleg buscar lei 8666
coleg buscar "Lei nº 14.133/2021"
coleg buscar lc 101
coleg buscar decreto-lei 2848
coleg buscar mp 2200                # todas as reedições
coleg buscar sv 13                  # súmula vinculante
coleg buscar sumula 7 stj
coleg buscar tema 1046 stf          # ou: repercussao geral 1046
coleg buscar repetitivo 903         # tema repetitivo do STJ
coleg buscar adi 4277
coleg buscar oj sdi1 336
coleg buscar oit 29                 # tratados: palavras do nome do arquivo
coleg buscar --tipo lei --ano 2021 --limite 100
coleg buscar sumula 1 --json
```

Apelidos aceitos: `lei`, `lc`, `dl`/`decreto-lei`, `decreto`, `decreto legislativo`, `ec`,
`ecr`, `lei delegada`, `mp`, `resolucao`, `constituicao`, `regimento`, `regulamento`,
`sv`, `sumula`, `tema`, `adi`, `adc`, `ado`, `adpf`, `oj`, `puil`, `tratado`.
Tribunais: `stf`, `stj`, `tst`, `tnu`, `trf4`, `tcu`, `stm`.

### Normas conhecidas pela sigla

Um dicionário com ~100 normas usuais permite buscar pela sigla ou pelo nome — a consulta
inteira precisa ser só a sigla ou o nome:

```bash
coleg buscar CPC                    # = coleg buscar lei 13105/2015
coleg buscar "Código Penal"         # = decreto-lei 2848/1940
coleg baixar clt
coleg apelidos                      # lista o dicionário
coleg apelidos processo             # filtra por sigla ou nome
```

O dicionário fica em `src/coleg/apelidos.py`; para incluir uma norma, acrescente uma linha
em `_ENTRADAS`.

### Ver e baixar

```bash
coleg info 1                        # cabeçalho (ementa, situação, fonte) do 1º resultado
coleg info 1 --texto                # e o texto integral
coleg baixar 1                      # baixa o 1º resultado da última busca
coleg baixar 1 3 5 -o normas        # vários, para a pasta 'normas'
coleg baixar lei 8666               # busca e baixa direto quando o resultado é único
coleg baixar cf                     # Constituição Federal
coleg baixar sumula 7 --todos       # todos os resultados
coleg baixar 1 --formato txt        # sem o cabeçalho YAML
coleg baixar 1 --anexos             # inclui imagens/PDFs referenciados
coleg baixar 1 --manter-pastas      # reproduz federal/leis-ordinarias/AAAA/...
coleg baixar estaduais/SP/constituicao/constituicao-sp.md   # qualquer caminho do repositório
```

Sem `--manter-pastas`, a jurisprudência é gravada com o tribunal como prefixo
(`stj-sumula-7.md`), para súmulas de mesmo número não se sobrescreverem.

### Navegar

```bash
coleg listar
coleg listar jurisprudencia/stf
```

## Dados locais

Ficam em `%LOCALAPPDATA%\coleg` (Windows) ou `~/.cache/coleg`; defina `COLEG_HOME` para
mudar. Contêm o clone parcial (`repo/`), o índice (`indice.sqlite`) e a última busca.

## Testes

```bash
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

> Os textos do repositório têm caráter informativo e não substituem a publicação oficial.
> Confira a fonte indicada no cabeçalho de cada documento.
