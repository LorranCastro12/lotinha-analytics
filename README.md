# Lotinha Analytics

Sistema desktop Python para extração, análise estatística e backtesting de estratégias de predição da **Lotinha** (sorteio de 15 números em um universo de 25, realizado várias vezes ao dia por diferentes bancas).

---

## Índice

1. [Instalação](#instalação)
2. [CLI — Referência de Comandos](#cli--referência-de-comandos)
3. [Interface Gráfica](#interface-gráfica)
4. [Arquitetura](#arquitetura)
5. [Estratégias de Predição](#estratégias-de-predição)
6. [Limitações Estatísticas](#limitações-estatísticas)
7. [Desenvolvimento e Testes](#desenvolvimento-e-testes)

---

## Instalação

Requer **Python 3.11+** e [`uv`](https://docs.astral.sh/uv/).

```bash
# Clonar e instalar dependências
uv sync

# Verificar instalação
uv run python -m lotinha --help
```

### Dependências principais

| Pacote | Uso |
|--------|-----|
| `customtkinter` | Interface gráfica |
| `pandas` / `numpy` | Processamento de dados |
| `scipy` | Teste de Wilcoxon |
| `lightgbm` | Estratégia LightGBM (opcional) |
| `matplotlib` | Gráficos na GUI e relatórios |
| `reportlab` | Geração de PDF |
| `sqlalchemy` | Persistência SQLite |
| `click` + `rich` | CLI |

---

## CLI — Referência de Comandos

Todos os comandos aceitam `--db-path PATH` para usar um banco alternativo.  
O banco padrão fica em `data/lotinha.db`.

### `extract` — Extração de dados

```bash
uv run python -m lotinha extract --inicio 2025-01-01 --fim 2025-05-19
```

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `--inicio` | obrigatório | Data inicial `YYYY-MM-DD` |
| `--fim` | obrigatório | Data final `YYYY-MM-DD` |
| `--skip-existing` | `true` | Pular datas já presentes no banco |
| `--backup / --no-backup` | `true` | Criar backup `.db.bak` antes de extrair |

### `status` — Estatísticas do banco

```bash
uv run python -m lotinha status
```

Exibe total de sorteios, período, bancas e horários disponíveis.

### `gaps` — Lacunas no histórico

```bash
uv run python -m lotinha gaps
uv run python -m lotinha gaps --inicio 2025-01-01 --fim 2025-03-31
```

Lista datas sem dados entre o primeiro registro e hoje (ou no intervalo informado).

### `recover-gaps` — Recuperar lacunas

```bash
uv run python -m lotinha recover-gaps
uv run python -m lotinha recover-gaps --inicio 2025-01-01 --fim 2025-03-31
```

Reextrai automaticamente as datas sem dados.

### `export` — Exportar dados

```bash
uv run python -m lotinha export --output sorteios.json
uv run python -m lotinha export --output sorteios.parquet --format parquet
```

### `import` — Importar dados

```bash
uv run python -m lotinha import --input sorteios.json
uv run python -m lotinha import --input sorteios.parquet --format parquet
```

### `report` — Relatório PDF

```bash
uv run python -m lotinha report --output relatorio.pdf
uv run python -m lotinha report --output relatorio.pdf --banca "LOTINHA PONTO" --horario 14
```

Gera um relatório PDF com gráficos de frequência, atraso, tabela top-N e aviso estatístico.

### `gui` — Interface gráfica

```bash
uv run python -m lotinha gui
```

---

## Interface Gráfica

A GUI (abre com `lotinha gui`) tem 5 abas:

| Aba | Descrição |
|-----|-----------|
| **Dashboard** | Estatísticas gerais do banco |
| **Extração** | Extração com barra de progresso em tempo real |
| **Análise** | Gráficos de frequência relativa e atraso por número |
| **Predição** | Geração de números preditos com grade visual |
| **Backtesting** | Walk-forward + teste de Wilcoxon com aviso honesto |

---

## Arquitetura

```
src/lotinha/
├── cli/            # Comandos Click
├── core/           # Domain objects (Sorteio) e exceções
├── extraction/     # ApiClient, parser, orchestrator
├── storage/        # SQLAlchemy models, repository, migrations, backup
├── analysis/       # Estatísticas, estratégias, backtester
├── reporting/      # Geração de PDF (reportlab)
├── gui/            # customtkinter — views, widgets
├── config.py       # Settings via pydantic-settings
└── __main__.py     # Entrypoint
```

**Banco de dados:** SQLite gerenciado via SQLAlchemy Core (sem Alembic em produção — as tabelas são criadas idempotentemente ao iniciar).

**Persistência de cache:** respostas brutas da API ficam em `data/cache/<YYYY-MM-DD>.json`, evitando requisições redundantes na re-extração.

---

## Estratégias de Predição

Todas implementam `BaseStrategy.predict(df, n) -> PredictionResult`.

| Estratégia | Lógica | Dados mínimos |
|------------|--------|---------------|
| `FrequenciaStrategy` | Top-N mais frequentes no histórico | 1 sorteio |
| `AtrasoStrategy` | Top-N com maior atraso (sorteios sem aparecer) | 1 sorteio |
| `MarkovStrategy` | Probabilidades de transição entre sorteios consecutivos | 2 sorteios |
| `EnsembleStrategy` | Média ponderada normalizada das estratégias acima | 2 sorteios |
| `LightGBMStrategy` | Classificador com features freq10/30/60, atraso, trend | 90 sorteios |

### Backtesting Walk-Forward

O `Backtester` avalia cada estratégia de forma honesta:

1. Para cada sorteio `t` (do `train_size` ao final), treina com `df.iloc[:t]` e prediz o sorteio `t`.
2. Conta acertos da estratégia **e de um baseline aleatório** com a mesma semente.
3. Aplica o **teste de Wilcoxon** (bicaudal: `alternative="greater"`) nos vetores de acertos.
4. Calcula ROI considerando prêmios por faixa de acertos e custo por aposta.

A estratégia só é considerada promissora se **p-value < 0.05** no teste de Wilcoxon. Caso contrário, o sistema exibe um aviso explícito.

---

## Limitações Estatísticas

> Esta seção é a mais importante do README. Leia antes de usar as predições.

### A Lotinha é um sorteio justo

A Lotinha sorteia 15 números de 25 sem reposição. A distribuição do número de acertos entre um conjunto de N números preditos e os 15 sorteados segue a **distribuição hipergeométrica**:

```
P(X = k) = C(15, k) × C(25-15, N-k) / C(25, N)
```

Em um sorteio **justo e independente**, a frequência histórica de cada número **não contém informação preditiva** sobre sorteios futuros. Cada realização é independente das anteriores.

### O que as estatísticas mostram (e o que não mostram)

| O que o sistema faz | O que isso NÃO implica |
|---------------------|------------------------|
| Mede frequência relativa histórica | Que números "quentes" continuarão saindo |
| Mede atraso (sorteios sem aparecer) | Que números "atrasados" têm maior probabilidade futura |
| Modela transições de Markov | Que há dependência temporal real entre sorteios |
| Calcula ROI histórico no backtest | Que o ROI futuro será igual ou positivo |

### Por que o backtest pode ser enganoso

Mesmo com walk-forward (sem data leakage), o backtest sobre dados históricos está sujeito a:

- **Overfitting temporal**: estratégias que parecem funcionar em um período podem ser ruído estatístico.
- **Múltiplas comparações**: testar 5 estratégias com 6 valores de N equivale a 30 testes. A probabilidade de ao menos um ter p < 0.05 por acaso é alta.
- **Não-estacionariedade**: se o comportamento dos sorteios muda ao longo do tempo, o passado não prevê o futuro.

### Valor esperado é negativo

Qualquer jogo de apostas com prêmios abaixo do valor matemático justo tem **valor esperado negativo**. O valor esperado de uma aposta de N números com custo `c` é:

```
E = Σ P(X=k) × prêmio(k) - c
```

Para os prêmios típicos da Lotinha, `E < 0` para qualquer N e qualquer estratégia.

### Conclusão

Este sistema é uma ferramenta de **análise estatística descritiva** e estudo de estratégias. **Não é um sistema de apostas lucrativas.** Use-o para entender padrões históricos, aprender sobre distribuições hipergeométricas e praticar backtesting honesto — não para decisões financeiras.

---

## Desenvolvimento e Testes

### Executar testes

```bash
uv run pytest                          # suite completa
uv run pytest tests/unit/test_report.py -v   # módulo específico
uv run pytest --co -q                  # listar todos os testes
```

Cobertura atual: **≥ 94%** (299 testes).

### Qualidade de código

```bash
uv run ruff check src/          # linting
uv run mypy src/lotinha/        # tipagem estática (--strict, exceto gui/)
```

### Estrutura de testes

```
tests/unit/
├── test_api_client.py      # ApiClient, rate limit, retry
├── test_backtester.py      # walk-forward, Wilcoxon, ROI
├── test_cli.py             # todos os comandos CLI
├── test_config.py          # Settings e validação
├── test_orchestrator.py    # ExtractionOrchestrator
├── test_parser.py          # parsing de respostas da API
├── test_report.py          # geração de PDF
├── test_statistics.py      # frequencia, atraso, co_ocorrencias, valor_esperado
├── test_storage.py         # repository, backup, export/import, gap_detector
└── test_strategies.py      # todas as estratégias de predição
```

### Convenções

- **TDD**: testes escritos antes da implementação.
- **mypy `--strict`** em todos os módulos exceto `gui/` (customtkinter não tem stubs completos).
- **ruff** com regras ANN (anotações obrigatórias) em toda a `src/`.
- GUI excluída do mypy mas incluída no ruff.
