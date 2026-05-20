# ADR-003 — Walk-Forward Backtesting com teste de Wilcoxon

**Status:** Aceito  
**Data:** 2026-05-19

## Contexto

Para avaliar estratégias de predição precisávamos de um método que:
1. Não introduzisse data leakage (usar dados futuros para treinar).
2. Produzisse uma comparação estatisticamente honesta com um baseline aleatório.
3. Comunicasse claramente ao usuário quando a estratégia **não** supera o acaso.

## Decisão

**Walk-forward (expanding window):** para cada sorteio `t` a partir de `train_size`, a estratégia treina com `df.iloc[:t]` e prediz o sorteio `t`. O conjunto de treino cresce a cada iteração — sem lookahead.

**Baseline aleatório com mesma semente:** para cada `t`, um baseline sorteia N números aleatoriamente (mesma semente `seed=42`). Isso garante que a comparação estratégia vs aleatório seja pareada — requisito do teste de Wilcoxon.

**Teste de Wilcoxon signed-rank** (`alternative="greater"`, `zero_method="zsplit"`): testa se a distribuição de acertos da estratégia é estocasticamente superior ao baseline. Mínimo de 10 observações; retorna `None` se insuficiente. Um `p_value < 0.05` indica evidência estatística de superioridade — não garante lucratividade.

**Aviso obrigatório:** quando a estratégia não supera o baseline com p < 0.05, a GUI exibe uma mensagem de alerta vermelha explícita. Nunca é silenciado.

## Consequências

**Positivas:**
- Sem data leakage: cada predição usa apenas histórico passado.
- Comparação pareada: o mesmo sorteio é avaliado por estratégia e baseline simultaneamente.
- Honestidade: o usuário sempre sabe se a estratégia supera ou não o acaso.

**Negativas:**
- Walk-forward com `train_size=60` requer pelo menos 60 sorteios históricos antes do primeiro teste — limita o uso com históricos curtos.
- O teste de Wilcoxon assume independência entre observações — em séries temporais isso pode não ser totalmente válido.
- `p < 0.05` é condição necessária mas não suficiente para estratégia lucrativa (ver ADR-004).
