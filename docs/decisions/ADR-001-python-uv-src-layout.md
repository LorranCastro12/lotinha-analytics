# ADR-001 — Python 3.11, uv e layout `src/`

**Status:** Aceito  
**Data:** 2026-05-19

## Contexto

O projeto é uma aplicação desktop Python para análise estatística. Precisávamos escolher versão de Python, gerenciador de pacotes e estrutura de diretórios.

## Decisão

- **Python 3.11**: versão estável com `tomllib` nativo, melhorias de performance e mensagens de erro melhores. Compatível com todas as dependências (customtkinter, lightgbm, scipy).
- **uv**: gerenciador de pacotes e ambientes virtuais. Resolução de dependências mais rápida que pip/poetry; `uv sync` é determinístico via `uv.lock`. Suporte nativo a `pyproject.toml`.
- **Layout `src/`**: pacote em `src/lotinha/` em vez de `lotinha/` na raiz. Evita que importações relativas funcionem sem instalação, forçando `uv sync` para desenvolvimento. Isola o pacote distribuível do código de teste.

## Consequências

**Positivas:**
- Ambiente reproduzível com `uv sync`.
- Testes importam o pacote instalado, não o diretório — detecta erros de instalação.
- Separação clara entre código de distribuição (`src/`) e testes (`tests/`).

**Negativas:**
- Curva de aprendizado leve para quem está acostumado com `setup.py` / `pip install -e .`.
- `uv` é relativamente novo — menos documentação comunitária que pip/poetry.
