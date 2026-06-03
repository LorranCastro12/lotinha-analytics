# Relatório de Análise de Assertividade — Lotinha Analytics

**Período analisado:** 21/05/2026 a 27/05/2026  
**Gerado em:** 28/05/2026  
**Modelo de predição:** Cadeias de Markov  
**Ferramenta:** `analisar.py` — Análise de Cobertura de Predições

---

## 1. Visão Geral

O sistema gera, para cada data, **18 palpites** (um por horário, das 07h às 24h, exceto Lotinha Federal 19h) contendo **23 dezenas** cada — a partir de um universo de 25 possíveis. O resultado oficial de cada sorteio traz **15 dezenas**. A análise verifica se algum palpite cobriu integralmente essas 15 dezenas.

São avaliados dois critérios:

| Critério | Definição |
|----------|-----------|
| **Acerto mesmo horário** | O palpite do exato horário sorteado cobriu as 15 dezenas do resultado |
| **Cobertura cruzada** | Um palpite de outro horário cobriu as 15 dezenas do resultado |

---

## 2. Resultados por Data

### 21/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 17 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **4 (23,5%)** |
| 🔄 Cobertura cruzada adicional | 9 |
| ✅ Cobertos por ≥ 1 predição | **13 (76,5%)** |
| ❌ Sem cobertura alguma | **4 (23,5%)** |
| Sobreposição parcial média (erros) | 13,8/15 |
| Avaliação | 🔴 BAIXA |

**Acertos no mesmo horário:** 13h, 14h, 19h, 20h (todos Lotinha Ponto)

**Sem cobertura:**
- Lotinha Federal 19h — melhor sobreposição: 13/15
- Lotinha Ponto 10h — melhor sobreposição: 14/15
- Lotinha Ponto 17h — melhor sobreposição: 14/15
- Lotinha Ponto 21h — melhor sobreposição: 14/15

**Palpites mais eficientes:** 10h e 21h (4 sorteios cobertos cada)

---

### 22/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 17 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **3 (17,6%)** |
| 🔄 Cobertura cruzada adicional | 14 |
| ✅ Cobertos por ≥ 1 predição | **17 (100,0%)** |
| ❌ Sem cobertura alguma | **0 (0,0%)** |
| Avaliação | 🔴 BAIXA |

**Acertos no mesmo horário:** 09h, 11h, 15h (todos Lotinha Ponto)

**Sem cobertura:** nenhum — cobertura total de todos os sorteios do dia.

**Palpite mais eficiente:** 14h (6 sorteios cobertos)

---

### 23/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 17 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **5 (29,4%)** |
| 🔄 Cobertura cruzada adicional | 11 |
| ✅ Cobertos por ≥ 1 predição | **16 (94,1%)** |
| ❌ Sem cobertura alguma | **1 (5,9%)** |
| Sobreposição parcial média (erros) | 14,0/15 |
| Avaliação | 🔴 BAIXA |

**Acertos no mesmo horário:** 11h, 13h, 16h, 21h, 22h (todos Lotinha Ponto)

**Sem cobertura:**
- Lotinha Federal 19h — melhor sobreposição: 14/15

**Palpites mais eficientes:** 09h e 22h (5 sorteios cobertos cada)

---

### 24/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 17 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **6 (35,3%)** |
| 🔄 Cobertura cruzada adicional | 11 |
| ✅ Cobertos por ≥ 1 predição | **17 (100,0%)** |
| ❌ Sem cobertura alguma | **0 (0,0%)** |
| Avaliação | 🟡 MÉDIA |

**Acertos no mesmo horário:** 07h, 12h, 13h, 14h, 17h, 23h (todos Lotinha Ponto)

**Sem cobertura:** nenhum — melhor desempenho individual do período.

**Palpites mais eficientes:** 09h, 10h, 13h e 14h (5 sorteios cobertos cada)

> Este foi o **único dia** do período a atingir a faixa de avaliação **MÉDIA**.

---

### 25/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 16 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **2 (12,5%)** |
| 🔄 Cobertura cruzada adicional | 13 |
| ✅ Cobertos por ≥ 1 predição | **15 (93,8%)** |
| ❌ Sem cobertura alguma | **1 (6,2%)** |
| Sobreposição parcial média (erros) | 14,0/15 |
| Avaliação | 🔴 BAIXA |

**Acertos no mesmo horário:** 10h e 18h (Lotinha Ponto)

**Sem cobertura:**
- Lotinha Ponto 21h — melhor sobreposição: 14/15

**Palpite mais eficiente:** 07h (5 sorteios cobertos)

---

### 26/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 18 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **0 (0,0%)** |
| 🔄 Cobertura cruzada adicional | 15 |
| ✅ Cobertos por ≥ 1 predição | **15 (83,3%)** |
| ❌ Sem cobertura alguma | **3 (16,7%)** |
| Sobreposição parcial média (erros) | 14,0/15 |
| Avaliação | 🔴 BAIXA |

**Acertos no mesmo horário:** nenhum — **pior desempenho individual** do período.

**Sem cobertura:**
- Lotinha Federal 19h — melhor sobreposição: 14/15
- Lotinha Ponto 08h — melhor sobreposição: 14/15
- Lotinha Ponto 23h — melhor sobreposição: 14/15

**Palpites mais eficientes:** 12h e 18h (4 sorteios cobertos cada)

---

### 27/05/2026

| Métrica | Valor |
|---------|-------|
| Sorteios analisados | 18 |
| Predições disponíveis | 18 |
| ✅ Acerto mesmo horário | **1 (5,6%)** |
| 🔄 Cobertura cruzada adicional | 12 |
| ✅ Cobertos por ≥ 1 predição | **13 (72,2%)** |
| ❌ Sem cobertura alguma | **5 (27,8%)** |
| Sobreposição parcial média (erros) | 14,0/15 |
| Avaliação | 🔴 BAIXA |

**Acerto no mesmo horário:** 13h (Lotinha Ponto)

**Sem cobertura:**
- Lotinha Federal 19h — melhor sobreposição: 14/15
- Lotinha Ponto 08h — melhor sobreposição: 14/15
- Lotinha Ponto 14h — melhor sobreposição: 14/15
- Lotinha Ponto 15h — melhor sobreposição: 14/15
- Lotinha Ponto 23h — melhor sobreposição: 14/15

**Palpites mais eficientes:** 08h e 12h (4 sorteios cobertos cada)

---

## 3. Consolidado do Período

### 3.1 Métricas Agregadas

| Data | Sorteios | Acerto mesmo horário | Cobertura cruzada | Cobertos (qualquer) | Sem cobertura | Avaliação |
|------|:--------:|:--------------------:|:-----------------:|:-------------------:|:-------------:|:---------:|
| 21/05 | 17 | 4 (23,5%) | 9 | 13 (76,5%) | 4 (23,5%) | 🔴 |
| 22/05 | 17 | 3 (17,6%) | 14 | 17 (100,0%) | 0 (0,0%) | 🔴 |
| 23/05 | 17 | 5 (29,4%) | 11 | 16 (94,1%) | 1 (5,9%) | 🔴 |
| 24/05 | 17 | 6 (35,3%) | 11 | 17 (100,0%) | 0 (0,0%) | 🟡 |
| 25/05 | 16 | 2 (12,5%) | 13 | 15 (93,8%) | 1 (6,2%) | 🔴 |
| 26/05 | 18 | 0 (0,0%) | 15 | 15 (83,3%) | 3 (16,7%) | 🔴 |
| 27/05 | 18 | 1 (5,6%) | 12 | 13 (72,2%) | 5 (27,8%) | 🔴 |
| **Total** | **120** | **21 (17,5%)** | **85** | **106 (88,3%)** | **14 (11,7%)** | — |

### 3.2 Evolução da Taxa de Acerto (mesmo horário)

```
24/05  ██████████████  35,3%  ← pico do período
23/05  ████████████    29,4%
21/05  ██████████      23,5%
22/05  ████████        17,6%
25/05  █████           12,5%
27/05  ██              5,6%
26/05  ░               0,0%   ← pior dia
```

### 3.3 Tendência da Cobertura Total

```
22/05  ████████████████████  100,0%
24/05  ████████████████████  100,0%
23/05  ███████████████████░   94,1%
25/05  ███████████████████░   93,8%
26/05  █████████████████░░░   83,3%
21/05  ███████████████░░░░░   76,5%
27/05  ██████████████░░░░░░   72,2%
```

---

## 4. Padrões e Observações

### 4.1 Ponto cego recorrente: Lotinha Federal 19h

A **Lotinha Federal 19h** não foi coberta por nenhuma predição em **quatro dos sete dias** analisados (21/05, 23/05, 26/05 e 27/05). Nos dias em que houve cobertura, ela foi sempre cruzada. A sobreposição parcial média ficou em **13–14/15**, indicando que o modelo se aproxima do resultado, mas sistematicamente falha 1–2 dezenas nesse sorteio específico. Isso sugere que o comportamento histórico da Lotinha Federal 19h difere do padrão geral, possivelmente por distribuição de frequências diferente.

### 4.2 Cobertura cruzada como principal mecanismo de acerto

Em todos os dias, a cobertura cruzada (palpite de outro horário cobrindo o resultado) foi o principal mecanismo de cobertura, superando amplamente os acertos no mesmo horário. Isso indica que as predições por Markov capturam padrões gerais de distribuição de dezenas que se repetem ao longo do dia, mas têm dificuldade em mapear a variação específica por horário.

### 4.3 Distribuição irregular dos acertos no mesmo horário

Os acertos no mesmo horário concentraram-se em determinados palpites ao longo da semana:

| Horário | Dias com acerto direto |
|---------|----------------------|
| 13h | 21/05, 23/05, 24/05, 27/05 |
| 14h | 21/05, 24/05 |
| 11h | 23/05, 22/05 |
| 22h | 23/05 |
| 07h, 12h, 17h, 23h | 24/05 apenas |
| 09h, 15h | 22/05 apenas |
| 19h, 20h | 21/05 apenas |
| 10h, 18h | 25/05 apenas |

O horário **13h** foi o mais estável, acertando em 4 dos 7 dias.

### 4.4 Sobreposição parcial nos erros

Nos sorteios sem cobertura, a sobreposição média entre o melhor palpite e o resultado foi de **13,8–14,0/15 dezenas** — ou seja, o modelo errou apenas 1 ou 2 dezenas. Isso indica que as predições são próximas da resposta correta, sem erros grosseiros, sugerindo que ajustes finos no modelo (ex.: ampliar de 23 para 24 dezenas por palpite) poderiam eliminar grande parte das falhas residuais.

---

## 5. Métricas de Eficiência dos Palpites

Os palpites mais recorrentemente eficientes ao longo dos 7 dias foram:

| Palpite | Dias em destaque | Observação |
|---------|-----------------|------------|
| 07h | 25/05 (5 cob.), 27/05 (3 cob.) | Forte alcance cruzado |
| 09h | 23/05 (5 cob.), 24/05 (5 cob.) | Melhor performance em 2 dias consecutivos |
| 10h | 21/05 (4 cob.), 24/05 (5 cob.) | Constante |
| 12h | 26/05 (4 cob.), 27/05 (4 cob.) | Consistente nos dias mais difíceis |
| 13h | 24/05 (5 cob.) | Pico em 24/05 |
| 14h | 22/05 (6 cob.), 24/05 (5 cob.) | **Melhor performance absoluta** (6 em 22/05) |
| 18h | 26/05 (4 cob.) | Ativo no dia com 0% de acerto direto |
| 21h | 21/05 (4 cob.) | Eficiente em 21/05 |
| 22h | 23/05 (5 cob.) | Em destaque em 23/05 |
| 23h | 25/05 (4 cob.) | Forte em 25/05 |

O palpite **14h** registrou a **maior eficiência individual** do período: 6 sorteios cobertos em um único dia (22/05).

---

## 6. Avaliação Geral do Sistema

### 6.1 Desempenho por critério

| Critério | Taxa média (7 dias) | Classificação |
|----------|:-------------------:|:-------------:|
| Acerto mesmo horário | **17,5%** | 🔴 BAIXA |
| Cobertura por qualquer palpite | **88,3%** | 🟢 ALTA |
| Taxa de falha total | **11,7%** | — |

### 6.2 Interpretação

O sistema demonstra **alta capacidade de varredura** do espaço de resultados: em 88,3% dos sorteios analisados, ao menos um dos 18 palpites cobrindo 23 dezenas continha todas as 15 dezenas do resultado. Contudo, a **precisão temporal é baixa** — acertar o palpite correto para o horário exato ocorreu em apenas 17,5% dos casos.

Esse padrão é consistente com o comportamento esperado de cadeias de Markov aplicadas a dados de sorteio: o modelo aprende distribuições marginais de dezenas, mas não consegue capturar a dependência temporal intra-dia com suficiente especificidade.

### 6.3 Conclusão

> O sistema Markov, no período de 21 a 27/05/2026, alcançou **avaliação BAIXA** em 6 dos 7 dias e **MÉDIA** em apenas 1 dia (24/05). A cobertura global (≥ 1 palpite) foi sólida, ficando acima de 72% em todos os dias e atingindo 100% em dois deles. O principal ponto de melhoria identificado é a **precisão por horário**, especialmente para Lotinha Federal 19h, que apresentou falha sistemática em 57% dos dias analisados.

---

> ⚠️ **Aviso:** predições baseadas em frequência histórica não garantem acertos futuros. Este relatório destina-se exclusivamente a estudo e análise estatística.
