# API Schema — pontodobicho.com

> Capturado em: 2026-05-19  
> Endpoint real chamado uma vez; todos os testes usam este fixture mockado.

## Endpoint

```
GET https://api.pontodobicho.com/numeric-games/results/list
    ?date=<YYYY-MM-DD>
    &gameType=lotinha
```

### Headers de resposta relevantes

| Header | Valor observado | Significado |
|--------|----------------|-------------|
| `x-ratelimit-limit` | `30` | Máximo de requests na janela (provavelmente 1 minuto) |
| `x-ratelimit-remaining` | decremental | Requests restantes na janela atual |
| `content-type` | `application/json; charset=utf-8` | |
| `Retry-After` | inteiro (segundos) | Presente em respostas 429 |

**Rate limit efetivo:** 30 requests/minuto → mínimo **2 segundos** entre requests.  
O padrão configurável do sistema é **2.5s** para margem de segurança.

---

## Corpo da resposta (200 OK)

```json
{
  "type": "success",
  "message": "Resultados listados com sucesso",
  "data": [ <array de SorteioRaw> ]
}
```

### Objeto `SorteioRaw`

```json
{
  "id": "01JVCYK6ZEE1XS4ARSVAQ6T4P8",
  "numericGameCatalogId": "01JVBEWQQ5GS3S9WCWD2ZVE9XE",
  "resultStatus": "ADDED",
  "processingStatus": "COMPLETED",
  "drawnNumbers": [1, 2, 3, 5, 6, 7, 10, 11, 12, 13, 15, 17, 20, 21, 22],
  "gameDate": "2025-05-16",
  "totalBets": 24,
  "winningBets": 0,
  "totalAmount": "52.00",
  "totalPayout": "0.00",
  "drawDate": "2025-05-16T07:00:00.000-03:00",
  "processingStartedAt": "2025-05-16T13:24:47.861-03:00",
  "processingFinishedAt": "2025-05-16T13:24:47.975-03:00",
  "createdAt": "16/05/2025 13:24:47",
  "updatedAt": "16/05/2025 13:24:47",
  "catalog": {
    "name": "LOTINHA PONTO 07h"
  },
  "game": {
    "id": "01JVBEWQQ5GS3S9WCWD2ZVE9XE",
    "name": "LOTINHA PONTO 07h",
    "gameType": "LOTINHA",
    "gameVariant": "PONTO"
  }
}
```

### Campos relevantes para o parser

| Campo | Tipo | Uso |
|-------|------|-----|
| `drawnNumbers` | `list[int]` | 15 números sorteados (1–25) |
| `gameDate` | `"YYYY-MM-DD"` | Data do sorteio |
| `drawDate` | ISO 8601 com fuso `-03:00` | Hora extraída do `catalog.name` (mais confiável) |
| `catalog.name` | `"LOTINHA PONTO 07h"` | Fonte de banca e hora |
| `game.gameVariant` | `"PONTO"` \| `"FEDERAL"` | Identificador alternativo da banca |

### Parsing de `catalog.name`

Padrão: `"<BANCA> <HH>h"` (regex: `^(.+?)\s+(\d{1,2})h$`)

| `catalog.name` | `banca` | `hora` |
|----------------|---------|--------|
| `"LOTINHA PONTO 07h"` | `"LOTINHA PONTO"` | `7` |
| `"LOTINHA FEDERAL 19h"` | `"LOTINHA FEDERAL"` | `19` |

---

## Bancas observadas (2025-05-16)

| Banca | Horários | `gameVariant` |
|-------|----------|---------------|
| `LOTINHA PONTO` | 07h – 23h (17 sorteios) | `PONTO` |
| `LOTINHA FEDERAL` | 19h (1 sorteio) | `FEDERAL` |

**Total no dia:** 18 sorteios. Pode variar com novas bancas — o sistema **não hardcoda** bancas.

---

## Respostas de erro

| Status | Cenário | Comportamento do sistema |
|--------|---------|--------------------------|
| `200` | Sucesso | Parseia e salva |
| `429` | Rate limit | Lê `Retry-After`, espera, retenta (até 5x total) |
| `5xx` | Erro do servidor | Backoff exponencial 2/4/8/16/32s ±20% jitter, retenta |
| `404` | Data sem dados | `DateNotFoundError`, **não retenta** |
| `4xx ≠ 429` | Requisição inválida | `DateNotFoundError`, **não retenta** |

---

## Cache em disco

Payloads brutos são cacheados em `data/cache/<YYYY-MM-DD>.json`.  
Reprocessar o histórico não exige novas chamadas à API.
