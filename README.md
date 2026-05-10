# verbIndenter

Sistema que eu criei para me auxiliar nos meus estudos de ingles.

Ele me ajuda a pesquisar verbos, identificar se o verbo e regular ou irregular, e consultar suas formas principais usando APIs web.

Ele mostra:

- infinitivo
- passado simples
- participio
- tipo do verbo: regular ou irregular
- definicao quando a palavra e encontrada no dicionario online

## Como executar a interface grafica

No terminal, dentro da pasta do projeto:

```bash
python verb_gui.py
```

Digite parte de um verbo no campo de busca. O sistema atualiza as sugestoes enquanto voce escreve.

Exemplos:

- `w`
- `wo`
- `went`
- `calcu`

Ao selecionar uma palavra, clique em `Salvar` para gravar a consulta no historico.

## Historico

O historico fica no arquivo:

```text
history.txt
```

Esse arquivo e criado na mesma pasta da aplicacao. Se futuramente o projeto for empacotado como `.exe`, ele sera criado ao lado do executavel.

Se o arquivo for apagado, o sistema recria automaticamente ao abrir novamente ou ao salvar uma palavra.

## Como executar no terminal

Tambem existe uma versao simples de terminal:

```bash
python cli.py
```

## Organizacao do codigo

- `verb_indenter.py`: regra de negocio e consultas web.
- `verb_gui.py`: interface grafica feita com Tkinter.
- `cli.py`: interface de terminal.

## Consulta online

O sistema usa a web como fonte de verdade:

- `en.wiktionary.org`: valida se a palavra existe como verbo e busca formas verbais.
- `datamuse.com`: busca sugestoes de palavras por prefixo.

Nao existe mais lista local de verbos. Se a palavra nao existir como verbo na consulta web, o sistema nao inventa conjugacao.

## Ambiente virtual

Criar:

```bash
python -m venv .venv
```

Ativar no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Rodar a interface:

```bash
python verb_gui.py
```

Sair do ambiente:

```bash
deactivate
```

Por enquanto nao existem dependencias externas obrigatorias.

## Gerar .exe

Instale o PyInstaller dentro do ambiente virtual:

```powershell
pip install pyinstaller
```

Gere o executavel usando o arquivo `.spec`:

```powershell
pyinstaller .\verb_indenter.spec
```

O executavel sera criado em:

```text
dist\VerbIndenter.exe
```

O arquivo `history.txt` sera criado automaticamente ao lado do `.exe`.

Para limpar builds antigos antes de gerar de novo, apague as pastas:

```text
build
dist
```
