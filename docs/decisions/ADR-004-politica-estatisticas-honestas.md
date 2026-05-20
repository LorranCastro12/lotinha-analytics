# ADR-004 — Política de Estatísticas Honestas

**Status:** Aceito  
**Data:** 2026-05-19

## Contexto

Sistemas de análise de loterias frequentemente apresentam estatísticas de forma que sugere falsamente a existência de padrões previsíveis. Isso leva usuários a apostas com expectativa errônea de lucro. O projeto precisava de uma política explícita sobre como apresentar os resultados.

## Decisão

As seguintes regras são invioláveis no sistema:

1. **Sempre mostrar o baseline aleatório:** nenhuma métrica de estratégia é exibida sem a métrica correspondente de um baseline aleatório com mesma semente. O usuário sempre vê os dois lados.

2. **Sempre mostrar o p-value:** o resultado do teste de Wilcoxon é sempre exibido, mesmo quando favorável. Um p-value pequeno sem contexto é enganoso.

3. **Aviso obrigatório quando sem evidência:** quando `p_value >= 0.05` ou `p_value is None`, o sistema exibe um aviso explícito em destaque vermelho — nunca apenas omite ou esconde.

4. **Seção de limitações no README:** o README tem uma seção dedicada às limitações estatísticas (distribuição hipergeométrica, independência dos sorteios, overfitting temporal, valor esperado negativo). Não é um rodapé — é seção principal.

5. **Aviso no relatório PDF:** o relatório gerado pelo `report` sempre inclui um parágrafo de aviso estatístico, independentemente dos resultados.

6. **`valor_esperado()` disponível na API:** a função `analysis.valor_esperado()` calcula o valor esperado matemático de uma aposta, expondo explicitamente que é negativo para prêmios reais.

## Consequências

**Positivas:**
- O usuário jamais sai do sistema com uma falsa confiança em predições.
- O projeto pode ser usado como ferramenta educacional sobre probabilidade e viés de análise.
- Evita responsabilidade ética por perdas financeiras baseadas em interpretações erradas.

**Negativas:**
- Pode frustrar usuários que buscam um sistema que "indique os números certos".
- Avisos repetidos podem parecer excessivos para usuários já familiarizados com as limitações.
