# PLANO DE IMPLEMENTAÇÃO — Lotinha Analytics

> **Status:** Aguardando aprovação  
> **Criado em:** 2026-05-19  
> **Modelo executor:** Claude Sonnet 4.6

---

## Sumário Executivo

Sistema desktop em Python para extração, armazenamento, análise estatística e predição de resultados da Lotinha (sorteio de 15/25 números). A arquitetura segue TDD estrito, honestidade estatística obrigatória e GUI responsiva via threads.

---

## Fases de Implementação

### Fase 0 — Setup do Projeto _(~1-2h)_

**Objetivo:** Projeto instalável, ferramentas configuradas, CI local funcionando.

**Entregáveis:**
- `pyproject.toml` com todas as dependências declaradas
- `.gitignore`, `.env.example`
- `ruff.toml` + `mypy.ini` configurados
- Estrutura de pastas completa (`src/lotinha/`, `tests/`, `docs/`, `data/`, `logs/`)
- `src/lotinha/config.py` — configurações via `pydantic-settings` (lê `.env`)
- `src/lotinha/logging_setup.py` — `loguru` com rotação (console + arquivo)
- `tests/conftest.py` base
- `alembic.ini` + diretório `alembic/`
- `pytest` passando (0 testes, 0 falhas)

**Decisões desta fase:**
- Gerenciador de pacotes: `uv` (mais rápido que pip)
- Python target: 3.11+
- Todos os imports do projeto via `src/` layout (PEP 660)

---

### Fase 1 — Schema do Banco + Repository _(~2-3h)_

**Objetivo:** Camada de persistência completa e testada antes de qualquer extração real.

**Testes escritos primeiro (`tests/unit/test_storage.py`):**
- Criar tabelas em SQLite em memória
- Inserir sorteio, verificar constraint UNIQUE(data, hora, banca)
- Tentar reinserir mesmo sorteio → deve ignorar (upsert) sem erro
- `gap_detector`: dado sorteios de dias 1,2,4,5 → retorna dia 3 como lacuna
- Export/import de banco (round-trip fiel)
- Backup automático cria arquivo com timestamp correto

**Módulos implementados:**
- `storage/models.py` — SQLAlchemy 2.0 com `Mapped[...]`
  - Tabela `sorteios` (campos conforme spec)
  - Tabela `extraction_log`
  - Tabela `predictions`
- `storage/repository.py` — `SorteioRepository` com métodos:
  - `upsert(sorteio: Sorteio) -> None`
  - `get_resultados(banca, hora, desde, ate) -> pd.DataFrame`
  - `list_bancas() -> list[str]`
  - `list_horarios() -> list[int]`
  - `count_total() -> int`
  - `latest_date() -> date | None`
- `storage/gap_detector.py` — `GapDetector.find_gaps(inicio, fim) -> list[date]`
- `storage/migrations.py` — wrapper Alembic para criar/upgradar schema
- Primeira migration Alembic: `0001_initial_schema.py`

**Meta de cobertura desta fase:** ≥ 90%

---

### Fase 2 — ApiClient _(~2-3h)_

**Objetivo:** Cliente HTTP robusto com retry, rate-limit e cache em disco.

**Pré-passo (único request real):**
- Fazer 1 chamada real à API `https://api.pontodobicho.com/numeric-games/results/list?date=2025-05-16&gameType=lotinha`
- Salvar resposta em `tests/fixtures/api_response_2025-05-16.json`
- Documentar schema em `docs/api_schema.md` (todos os campos, tipos, valores de exemplo)
- A partir daí, **todos os testes mocham com esse fixture**

**Testes escritos primeiro (`tests/unit/test_api_client.py`):**
- Request bem-sucedido → retorna lista de `SorteioRaw`
- HTTP 429 com `Retry-After: 5` → espera e tenta de novo (mock com `respx`)
- HTTP 429 repetido 5x → levanta `RateLimitExceededError`
- HTTP 500 → backoff exponencial, 3 tentativas, levanta `ApiServerError`
- HTTP 404 → levanta `DateNotFoundError`, não retenta
- Cache hit: segundo request para mesma data não bate na rede
- Rate-limit interno: dois requests seguidos respeitam o intervalo configurado

**Módulos implementados:**
- `core/exceptions.py` — hierarquia de exceções do domínio
- `core/domain.py` — dataclasses: `SorteioRaw`, `Sorteio`, `PredictionResult`
- `extraction/api_client.py` — `ApiClient` com `httpx` + `tenacity`
  - Cache em disco: `data/cache/<YYYY-MM-DD>.json`
  - Headers realistas
  - Retry com jitter
- `extraction/parser.py` — `parse_response(raw: dict) -> list[Sorteio]`

**Meta de cobertura desta fase:** ≥ 88%

---

### Fase 3 — Orchestrator + Gap Detector _(~1-2h)_

**Objetivo:** Pipeline de extração idempotente com progresso reportável.

**Testes escritos primeiro (`tests/unit/test_orchestrator.py`):**
- `extract_range(d1, d2)` com banco vazio → tenta extrair todos os dias
- `extract_range(d1, d2)` com metade já no banco → extrai apenas lacunas
- `extract_range` com falha em 1 dia → loga erro, continua os outros dias
- Progresso: callback é chamado com (atual, total) a cada dia processado
- Backup automático é criado antes da extração em lote
- Reextrair mesmo dia não duplica no banco

**Módulos implementados:**
- `extraction/orchestrator.py` — `ExtractionOrchestrator`
  - `extract_range(inicio, fim, progress_callback)` 
  - `recover_gaps()` — reextrai todas as lacunas conhecidas
  - Backup automático via `storage/backup.py`
- `storage/backup.py` — cria backup, mantém últimos 5

**Meta de cobertura desta fase:** ≥ 88%

---

### Fase 4 — CLI Mínimo _(~1h)_

**Objetivo:** Validar pipeline completo antes de GUI. Teste de fumaça end-to-end.

**Comandos implementados (`python -m lotinha <cmd>`):**
```
python -m lotinha extract --from 2025-05-16 --to 2025-05-31
python -m lotinha status          # total de sorteios, lacunas
python -m lotinha gaps            # lista datas faltantes
python -m lotinha recover-gaps    # reextrai lacunas
python -m lotinha export --format parquet --out data/export.parquet
python -m lotinha import --file data/export.parquet
```

**Módulos implementados:**
- `__main__.py` com `argparse` (ou `click`)
- Saída colorida via `rich` (adicionar à stack se aprovado)

**Validação manual:** rodar extract real para 2025-05-16 a 2025-05-18 e checar banco.

---

### Fase 5 — Statistics Core _(~2-3h)_

**Objetivo:** Funções estatísticas puras, 100% testáveis sem banco ou API.

**Testes escritos primeiro (`tests/unit/test_statistics.py`):**
- `frequencia(historico, janela=None)` → dict[int, float], soma = 1.0
- `frequencia` com decay temporal → números recentes têm peso maior
- `atraso(historico, numero)` → int (concursos desde última aparição)
- `pares_coocorrencia(historico)` → matriz 25×25 normalizada
- `trincas_coocorrencia(historico)` → dict[(a,b,c), float]
- Todos testados com `tests/fixtures/synthetic.py` (100 sorteios fake)

**Módulos implementados:**
- `tests/fixtures/synthetic.py` — gerador determinístico de sorteios fake
  - `make_historico(n=100, seed=42, vies={7: 0.3}) -> pd.DataFrame`
- `core/statistics.py`
  - `calcular_frequencias(df, half_life_dias=None) -> dict[int, float]`
  - `calcular_atrasos(df) -> dict[int, int]`
  - `calcular_coocorrencias_pares(df) -> np.ndarray`  _(25×25)_
  - `calcular_valor_esperado(n_apostados, premios_por_faixa) -> float`
  - `probabilidade_acertos(n_apostados, n_sorteados=15, universo=25) -> dict[int, float]`

**Destaque:** `calcular_valor_esperado` calcula matematicamente o EV da aposta.

**Meta de cobertura:** 95%+ (lógica pura, fácil de testar)

---

### Fase 6 — Estratégias de Predição _(~3-4h)_

**Objetivo:** 4 estratégias + ensemble, todas herdando `BaseStrategy`.

**Testes escritos primeiro (`tests/unit/test_strategies.py`):**
- Cada estratégia: `fit(df)` não levanta exceção
- `predict(22)` retorna exatamente 22 números únicos no range [1,25]
- `FrequencyStrategy` com viés injetado detecta números frequentes
- `DelayStrategy` favorece números ausentes há mais tempo
- `MarkovStrategy` com histórico trivial (A sempre segue B) aprende a transição
- `EnsembleStrategy` combina pesos e resultado é consistente

**Módulos implementados:**
- `analysis/strategies/base.py` — `BaseStrategy` (ABC), `PredictionResult`
- `analysis/strategies/frequency.py` — `FrequencyStrategy(half_life=30)`
- `analysis/strategies/delay.py` — `DelayStrategy`
- `analysis/strategies/markov.py` — `MarkovStrategy` (matriz de co-presença)
- `analysis/strategies/ml_lightgbm.py` — `MLStrategy` (25 classificadores binários)
  - Features: freq_5, freq_10, freq_20, freq_50, gap, dia_semana, hora, banca_enc, paridade
  - Treina apenas se houver ≥ 100 registros; caso contrário, delega para `FrequencyStrategy`
- `analysis/strategies/ensemble.py` — `EnsembleStrategy(pesos: dict[str, float])`
- `analysis/predictor.py` — `Predictor.predict(banca, horario, data_alvo, n=22) -> PredictionResult`
- `core/features.py` — funções de feature engineering (usadas por `MLStrategy`)

**Meta de cobertura:** ≥ 85%

---

### Fase 7 — Backtester _(~3-4h)_

**Objetivo:** Validação científica honesta das estratégias vs baseline aleatório.

**Testes escritos primeiro (`tests/unit/test_backtester.py`):**
- Walk-forward com 20 sorteios sintéticos → retorna tabela correta
- Baseline aleatório tem EV ≈ esperado (11 acertos em 22 de 25 com 15 sorteados: 22×15/25 = 13.2 esperado — verificar matematicamente)
- Estratégia com viés injetado (número 7 sai 60%) → detectada como superior ao aleatório
- Estratégia aleatória → p-value > 0.05 (não rejeitamos H0)
- `BacktestResult` serializa/desserializa corretamente para JSON

**Módulos implementados:**
- `analysis/backtester.py` — `Backtester`
  - `run(banca, horario, estrategia, inicio_teste, fim_teste) -> BacktestResult`
  - Walk-forward: treina em t<D, testa em D, avança
  - Métricas: acertos_medio, std, vs_random_delta, p_value (Wilcoxon), roi_acumulado
  - Gráfico ROI como `matplotlib.Figure` (para embutir na GUI e no PDF)
  - Baseline aleatório: 1000 simulações de Monte Carlo para distribuição de referência
- `BacktestResult`: dataclass com todos os campos + método `to_dict()`

**Regra de ouro implementada:** se `p_value > 0.05 ou edge <= 0`, seta `recomenda_aposta = False` e `aviso_usuario` com texto explicativo.

**Meta de cobertura:** ≥ 85%

---

### Fase 8 — GUI (customtkinter) _(~4-5h)_

**Objetivo:** Interface funcional com 5 abas, operações longas em threads.

**Arquitetura de threading:**
- Toda operação longa roda em `threading.Thread`
- Comunicação com GUI via `queue.Queue` + `root.after(50, poll_queue)`
- `GUIController` (testável) separa lógica dos widgets

**Implementação aba por aba:**

**Aba 1 — Dashboard:**
- Cards: total sorteios, data mais recente, Nº de lacunas, último backtest
- Botão "Atualizar até hoje" → inicia thread de extração
- Aviso vermelho se `recomenda_aposta = False` em todas as estratégias

**Aba 2 — Extração:**
- DatePicker ou campos texto (YYYY-MM-DD)
- Botão "Verificar Lacunas" → mostra lista de datas faltantes
- Botão "Extrair" → barra de progresso + log scrollable em tempo real
- Botão "Recuperar Lacunas"

**Aba 3 — Análise / Predição:**
- Dropdowns: banca, horário, data alvo, estratégia
- Botão "Gerar Predição" → grid 5×5 com 25 números (22 destacados em verde, 3 em cinza)
- Barra de confidence
- Botão "Gerar PDF do Dia" → abre diálogo de salvar

**Aba 4 — Backtesting:**
- Seletores: período de validação, banca, horário
- Tabela: estratégia | acertos_medio | edge | p_value | roi | recomendado?
- Gráfico ROI (matplotlib embutido via `FigureCanvasTkAgg`)
- Aviso proeminente se nenhuma estratégia tem p < 0.05

**Aba 5 — Configurações:**
- Caminho do banco SQLite (botão "Procurar...")
- Import/Export banco
- Rate-limit da API (slider 0.5s a 5.0s)
- Tema claro/escuro
- Botão "Testar Conexão API"

**Módulos implementados:**
- `gui/app.py` — janela principal, sistema de abas, `queue` polling
- `gui/views/dashboard.py`
- `gui/views/extraction_view.py`
- `gui/views/analysis_view.py`
- `gui/views/backtest_view.py`
- `gui/views/settings_view.py`
- `gui/widgets/number_grid.py` — grid 5×5 reutilizável
- `gui/widgets/progress_panel.py` — barra + log
- `gui/controller.py` — lógica dos botões (testável sem GUI)

---

### Fase 9 — Relatório PDF _(~2h)_

**Objetivo:** PDF profissional com palpites de todos os (banca × horário) do dia.

**Conteúdo por página:**
- Cabeçalho: logo/título, data alvo, timestamp de geração
- Para cada (banca, horário): seção com
  - Grid visual 5×5 (números recomendados destacados)
  - Estratégia usada + confidence
  - Aviso de edge (ou aviso de ausência de edge)
- Página final: tabela de backtesting resumida + rodapé estatístico

**Módulos implementados:**
- `reporting/pdf_generator.py` — `PDFGenerator.generate(data_alvo, output_path)`
- `reporting/templates/` — estilos ReportLab

---

### Fase 10 — Polish e Documentação Final _(~2h)_

**Objetivo:** Sistema pronto para uso e distribuição.

**Entregáveis:**
- `README.md` completo:
  - Instalação (`uv sync`)
  - Uso (CLI + GUI)
  - Seção **"Limitações e Premissas Estatísticas"** (obrigatória)
  - Screenshots da GUI
- `docs/decisions/` com ADRs:
  - `ADR-001-sqlite-vs-postgres.md`
  - `ADR-002-httpx-vs-requests.md`
  - `ADR-003-walk-forward-validation.md`
  - `ADR-004-honestidade-estatistica.md`
- Cobertura final: `pytest --cov` → relatório HTML em `htmlcov/`
- `mypy --strict src/lotinha/core` → 0 erros
- `ruff check .` → 0 erros
- PyInstaller (opcional, se solicitado): `build.spec`

---

## Grafo de Dependências entre Fases

```
Fase 0 (Setup)
    │
    ├─▶ Fase 1 (Banco + Repo)
    │       │
    │       ├─▶ Fase 3 (Orchestrator) ◀── Fase 2 (ApiClient)
    │       │       │
    │       │       └─▶ Fase 4 (CLI) ──── validação end-to-end
    │       │
    │       └─▶ Fase 5 (Statistics Core)
    │               │
    │               └─▶ Fase 6 (Estratégias)
    │                       │
    │                       └─▶ Fase 7 (Backtester)
    │                               │
    │                               └─▶ Fase 8 (GUI)
    │                                       │
    │                                       └─▶ Fase 9 (PDF)
    │                                               │
    │                                               └─▶ Fase 10 (Polish)
    │
    └─▶ Fase 2 (ApiClient) ──────────────────────────────────┘
```

---

## Stack Final (confirmada)

| Camada | Tecnologia | Versão mínima |
|--------|-----------|---------------|
| Python | CPython | 3.11 |
| HTTP | `httpx` | 0.27 |
| Retry | `tenacity` | 8.x |
| Validação | `pydantic` v2 | 2.7 |
| ORM | `sqlalchemy` | 2.0 |
| Migrations | `alembic` | 1.13 |
| Configuração | `pydantic-settings` | 2.x |
| Análise | `pandas`, `numpy`, `scipy` | latest stable |
| ML | `scikit-learn`, `lightgbm` | latest stable |
| GUI | `customtkinter` | 5.x |
| PDF | `reportlab` | 4.x |
| Logging | `loguru` | 0.7 |
| Mock HTTP | `respx` | 0.21 |
| Testes | `pytest`, `pytest-cov`, `pytest-mock` | latest |
| Lint | `ruff` | 0.4 |
| Tipos | `mypy` | 1.10 |
| CLI | `click` | 8.x |
| Tabelas CLI | `rich` | 13.x |

---

## Estimativa de Esforço

| Fase | Esforço estimado |
|------|-----------------|
| 0 — Setup | 1-2h |
| 1 — Banco | 2-3h |
| 2 — ApiClient | 2-3h |
| 3 — Orchestrator | 1-2h |
| 4 — CLI | 1h |
| 5 — Statistics | 2-3h |
| 6 — Estratégias | 3-4h |
| 7 — Backtester | 3-4h |
| 8 — GUI | 4-5h |
| 9 — PDF | 2h |
| 10 — Polish | 2h |
| **Total** | **~23-32h** |

---

## Perguntas Abertas (preciso de resposta antes de avançar nas fases indicadas)

| # | Pergunta | Necessária para | Minha suposição default |
|---|----------|-----------------|------------------------|
| Q1 | Quais são os valores reais de prêmio por faixa (11, 12, 13, 14, 15 acertos) e o custo de apostas com 17..23 números? | Fase 7 (backtester com ROI real), Fase 9 (PDF) | Parametrizar: usuário preenche na tela de Configurações |
| Q2 | Confirmar horários exatos dos sorteios (07h..23h = 17 sorteios, ou 07h..24h = 18?) | Fase 1 (constraint do banco) | Descobrir empiricamente na Fase 2, ao analisar fixture real |
| Q3 | Selenium fallback é prioridade ou pode ficar como stub? | Fase 2 | Implementar como stub `raise NotImplementedError` e marcar como `TODO` |
| Q4 | Empacotamento com PyInstaller é necessário nesta entrega? | Fase 10 | Opcional — só executar se solicitado |

---

## Critérios de Saída por Fase

Antes de avançar para a próxima fase, apresentarei:
1. Output de `pytest -v --cov` desta fase
2. 3-5 bullets do que foi implementado
3. Qualquer decisão técnica não-trivial tomada

**Aguardando aprovação deste plano para iniciar a Fase 0.**
