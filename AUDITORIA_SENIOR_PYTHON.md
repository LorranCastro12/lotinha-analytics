cat <<'EOF' > AUDITORIA_SENIOR_PYTHON.md
Aja como um programador sênior especialista em Python, arquitetura de software, revisão de código, segurança, performance e qualidade de sistemas.

Analise todo o projeto Python presente neste diretório, incluindo subpastas, arquivos de configuração, dependências, scripts, testes, documentação e estrutura geral.

Sua missão é conferir cuidadosamente:

1. Erros de sintaxe, imports quebrados e problemas de execução.
2. Bugs lógicos prováveis.
3. Falhas de arquitetura ou organização do projeto.
4. Problemas de segurança, como uso inseguro de variáveis de ambiente, secrets, eval, exec, SQL injection, exposição de credenciais ou permissões indevidas.
5. Dependências ausentes, desatualizadas, conflitantes ou mal declaradas.
6. Problemas em requirements.txt, pyproject.toml, setup.py, Dockerfile, docker-compose.yml ou arquivos similares.
7. Falta de tratamento de exceções.
8. Código duplicado, morto, confuso ou difícil de manter.
9. Problemas de tipagem, lint, formatação e padrões PEP8.
10. Falhas em testes existentes ou ausência de testes importantes.
11. Possíveis gargalos de performance.
12. Problemas de compatibilidade entre versões do Python.
13. Erros em caminhos de arquivos, variáveis de ambiente, configuração de banco de dados, APIs externas e inicialização do sistema.

Execute uma revisão completa e produza um relatório objetivo contendo:

- Resumo geral do estado do projeto.
- Lista de erros críticos encontrados.
- Lista de problemas médios e baixos.
- Arquivos afetados.
- Explicação clara de cada problema.
- Sugestão de correção.
- Comandos recomendados para validar o projeto.
- Ordem de prioridade para correção.

Sempre que possível, proponha patches ou trechos de código corrigidos.

Não faça alterações destrutivas sem explicar antes.
Não remova arquivos sem autorização.
Não exponha secrets completos; oculte valores sensíveis.
EOF

python -m compileall .
python -m pip check
python -m pytest -q