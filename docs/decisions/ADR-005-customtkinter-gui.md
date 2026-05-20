# ADR-005 — customtkinter para a Interface Gráfica

**Status:** Aceito  
**Data:** 2026-05-19

## Contexto

O projeto precisa de uma GUI desktop nativa para Windows/Linux/macOS. As alternativas consideradas foram:

| Opção | Prós | Contras |
|-------|------|---------|
| tkinter puro | Stdlib, zero deps | Visual datado, difícil de estilizar |
| **customtkinter** | Moderno, dark mode, stdlib-based | Relativamente novo, sem stubs mypy completos |
| PyQt6 / PySide6 | Profissional, bem documentado | Licença LGPL/GPL, dependência pesada |
| Dear PyGui | GPU-accelerated | Curva de aprendizado alta, menos widgets |
| Electron/Tauri | Visual moderno | Python → JS bridge complexo |
| Streamlit / Gradio | Fácil de usar | Requer browser, não é desktop nativo |

## Decisão

**customtkinter 5.2.2**: wrapper sobre tkinter que adiciona temas modernos (dark/light), widgets estilizados (`CTkButton`, `CTkTabview`, etc.) e suporte a DPI scaling. Mantém a distribuição simples (sem Qt, sem Electron) e funciona com `uv sync`.

Padrão de threading: operações longas (extração, backtesting) executam em `threading.Thread` com `queue.Queue` + polling via `.after(200, self._poll)` — evita bloquear o event loop do tkinter.

GUI excluída do mypy `--strict` (customtkinter não tem stubs completos) mas incluída no ruff.

## Consequências

**Positivas:**
- Instalação trivial com `uv sync` — sem Qt, sem dependências nativas pesadas.
- Dark mode e tema verde configurable com 2 linhas.
- Padrão de threading seguro e testado para UIs Python.
- Facilmente extensível com novos CTkFrame para novas abas.

**Negativas:**
- Sem stubs mypy — as views não passam por verificação estática de tipos.
- customtkinter é mantido por um único desenvolvedor (TomSchimansky) — risco de abandono.
- Widgets menos ricos que Qt — sem tree view, data table nativa, etc.
- Testes automatizados de UI são impraticáveis com tkinter (sem headless mode fácil).
