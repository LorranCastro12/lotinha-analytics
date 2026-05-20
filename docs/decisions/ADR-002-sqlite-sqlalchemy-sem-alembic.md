# ADR-002 — SQLite + SQLAlchemy Core sem Alembic em produção

**Status:** Aceito  
**Data:** 2026-05-19

## Contexto

O sistema precisa persistir sorteios localmente. É uma aplicação desktop single-user, sem concorrência entre processos e sem necessidade de servidor de banco de dados.

## Decisão

- **SQLite**: banco embutido, zero configuração, arquivo único copiável como backup.
- **SQLAlchemy Core** (sem ORM declarativo pesado): queries explícitas via `select()`, `insert()`, `update()`. Mais verboso, mas sem "mágica" e fácil de auditar.
- **Sem Alembic em produção**: as tabelas são criadas com `create_all_tables(engine)` chamado a cada inicialização (idempotente via `IF NOT EXISTS`). Alembic está disponível no projeto mas não é executado automaticamente.
- **Backup antes de extrações**: `SorteioRepository` não persiste backups — o `ExtractionOrchestrator` coordena o backup via `BackupManager` antes de qualquer escrita.

## Consequências

**Positivas:**
- Zero configuração para o usuário final.
- Backup trivial: copiar o arquivo `.db`.
- Schema evolui sem migrações para o escopo atual (aplicação pessoal, schema estável).

**Negativas:**
- SQLite não suporta múltiplas escritas simultâneas — aceitável para uso single-user.
- Sem Alembic automático: mudanças de schema futuras exigem script manual de migração.
- Se o schema mudar, usuários com banco antigo precisarão de instrução explícita.
