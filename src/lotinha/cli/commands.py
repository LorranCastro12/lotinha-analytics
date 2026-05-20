"""CLI commands para Lotinha Analytics."""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from lotinha.config import Settings
from lotinha.extraction.api_client import ApiClient
from lotinha.extraction.orchestrator import ExtractionOrchestrator
from lotinha.reporting.report import ReportConfig, generate_report
from lotinha.storage.export_import import (
    export_to_json,
    export_to_parquet,
    import_from_json,
    import_from_parquet,
)
from lotinha.storage.gap_detector import GapDetector
from lotinha.storage.repository import SorteioRepository

console = Console()
err_console = Console(stderr=True)


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError as exc:
        raise click.BadParameter(f"Data inválida: {s!r}. Use o formato YYYY-MM-DD.") from exc


def _get_repo(ctx: click.Context) -> tuple[SorteioRepository, Settings, Path]:
    """Cria repositório a partir do contexto CLI."""
    from lotinha.storage.migrations import create_all_tables, create_engine_from_path

    settings = Settings()
    db_path: Path = ctx.obj.get("db_path") or settings.db_path
    engine = create_engine_from_path(db_path)
    create_all_tables(engine)
    return SorteioRepository(engine), settings, db_path


# ── Grupo principal ────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    envvar="LOTINHA_DB_PATH",
    help="Caminho do banco SQLite (padrão: data/lotinha.db).",
)
@click.pass_context
def cli(ctx: click.Context, db_path: Path | None) -> None:
    """Lotinha Analytics — extração, análise e predição."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


# ── extract ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--inicio", required=True, help="Data inicial YYYY-MM-DD.")
@click.option("--fim", required=True, help="Data final YYYY-MM-DD.")
@click.option(
    "--skip-existing/--no-skip-existing",
    default=True,
    show_default=True,
    help="Pular datas já presentes no banco.",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    show_default=True,
    help="Criar backup antes de extrair.",
)
@click.pass_context
def extract(
    ctx: click.Context,
    inicio: str,
    fim: str,
    skip_existing: bool,
    backup: bool,
) -> None:
    """Extrai sorteios de um intervalo de datas da API."""
    try:
        d_inicio = _parse_date(inicio)
        d_fim = _parse_date(fim)
    except click.BadParameter as exc:
        err_console.print(f"[red]{exc}[/red]")
        sys.exit(1)

    if d_inicio > d_fim:
        err_console.print("[red]--inicio deve ser anterior ou igual a --fim.[/red]")
        sys.exit(1)

    repo, settings, db_path = _get_repo(ctx)

    api = ApiClient(
        base_url=str(settings.api_base_url),
        rate_limit=float(settings.api_rate_limit),
    )
    orchestrator = ExtractionOrchestrator(api_client=api, repo=repo, db_path=db_path)

    console.print(f"Extraindo [cyan]{d_inicio}[/cyan] → [cyan]{d_fim}[/cyan]...")

    total_ref: list[int] = [0]

    def progress_cb(atual: int, total: int, data_atual: date) -> None:
        total_ref[0] = total
        console.print(f"  [{atual}/{total}] {data_atual}", end="\r")

    report = orchestrator.extract_range(
        inicio=d_inicio,
        fim=d_fim,
        skip_existing=skip_existing,
        backup_before=backup,
        progress_callback=progress_cb,
    )

    if total_ref[0]:
        console.print()

    color = "green" if report.sucesso else "yellow"
    console.print(
        f"[{color}]Concluído:[/{color}] "
        f"extraídos={report.extraidos} "
        f"já_presentes={report.ja_presentes} "
        f"vazios={report.vazios} "
        f"falhas={report.falhas}"
    )

    if report.backup_path:
        console.print(f"Backup: {report.backup_path}")

    if report.erros:
        err_console.print(f"[yellow]{len(report.erros)} falha(s):[/yellow]")
        for d, msg in report.erros:
            err_console.print(f"  {d}: {msg}")

    sys.exit(0 if report.sucesso else 1)


# ── status ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Exibe estatísticas do banco de dados."""
    repo, _, _ = _get_repo(ctx)

    total = repo.count_total()
    latest = repo.latest_date()
    bancas = repo.list_bancas()
    horarios = repo.list_horarios()
    dates = repo.dates_with_data()

    table = Table(title="Status do banco de dados", show_header=False, box=None)
    table.add_column("Campo", style="bold cyan", min_width=20)
    table.add_column("Valor")

    table.add_row("Total de sorteios", str(total))
    table.add_row("Data mais antiga", str(min(dates)) if dates else "—")
    table.add_row("Data mais recente", str(latest) if latest else "—")
    table.add_row("Dias com dados", str(len(dates)))
    table.add_row("Bancas", ", ".join(sorted(bancas)) if bancas else "—")
    table.add_row(
        "Horários",
        ", ".join(f"{h}h" for h in sorted(horarios)) if horarios else "—",
    )

    console.print(table)


# ── gaps ───────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--inicio", default=None, help="Data inicial YYYY-MM-DD.")
@click.option("--fim", default=None, help="Data final YYYY-MM-DD.")
@click.pass_context
def gaps(ctx: click.Context, inicio: str | None, fim: str | None) -> None:
    """Lista datas sem dados no banco."""
    repo, _, _ = _get_repo(ctx)
    detector = GapDetector(repo)

    d_inicio: date | None = _parse_date(inicio) if inicio else None
    d_fim: date | None = _parse_date(fim) if fim else None

    found: list[date] = (
        detector.find_gaps(d_inicio, d_fim) if d_inicio and d_fim else detector.find_all_gaps()
    )

    if not found:
        console.print("[green]Nenhuma lacuna encontrada.[/green]")
        return

    console.print(f"[yellow]{len(found)} lacuna(s) encontrada(s):[/yellow]")
    for g in found:
        console.print(f"  {g}")


# ── recover-gaps ───────────────────────────────────────────────────────────────

@cli.command("recover-gaps")
@click.option("--inicio", default=None, help="Data inicial YYYY-MM-DD.")
@click.option("--fim", default=None, help="Data final YYYY-MM-DD.")
@click.pass_context
def recover_gaps(ctx: click.Context, inicio: str | None, fim: str | None) -> None:
    """Reextrai datas faltantes entre o primeiro registro e hoje."""
    repo, settings, db_path = _get_repo(ctx)

    api = ApiClient(
        base_url=str(settings.api_base_url),
        rate_limit=float(settings.api_rate_limit),
    )
    orchestrator = ExtractionOrchestrator(api_client=api, repo=repo, db_path=db_path)

    d_inicio: date | None = _parse_date(inicio) if inicio else None
    d_fim: date | None = _parse_date(fim) if fim else None

    console.print("Buscando lacunas e recuperando...")

    report = orchestrator.recover_gaps(inicio=d_inicio, fim=d_fim)

    if report.total_dias == 0:
        console.print("[green]Nenhuma lacuna para recuperar.[/green]")
        return

    color = "green" if report.sucesso else "yellow"
    console.print(
        f"[{color}]Concluído:[/{color}] "
        f"extraídos={report.extraidos} "
        f"vazios={report.vazios} "
        f"falhas={report.falhas}"
    )

    if not report.sucesso:
        sys.exit(1)


# ── export ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Caminho do arquivo de saída.",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["json", "parquet"]),
    default="json",
    show_default=True,
    help="Formato de exportação.",
)
@click.pass_context
def export(ctx: click.Context, output: Path, fmt: str) -> None:
    """Exporta todos os sorteios para JSON ou Parquet."""
    repo, _, _ = _get_repo(ctx)

    console.print(f"Exportando para [cyan]{output}[/cyan] ({fmt})...")
    count = export_to_parquet(repo, output) if fmt == "parquet" else export_to_json(repo, output)
    console.print(f"[green]{count} sorteios exportados.[/green]")


# ── import ─────────────────────────────────────────────────────────────────────

@cli.command("import")
@click.option(
    "--input", "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Caminho do arquivo de entrada.",
)
@click.option(
    "--format", "fmt",
    type=click.Choice(["json", "parquet"]),
    default="json",
    show_default=True,
    help="Formato de importação.",
)
@click.pass_context
def import_cmd(ctx: click.Context, input_path: Path, fmt: str) -> None:
    """Importa sorteios de JSON ou Parquet para o banco."""
    repo, _, _ = _get_repo(ctx)

    console.print(f"Importando de [cyan]{input_path}[/cyan] ({fmt})...")
    count = (
        import_from_parquet(repo, input_path)
        if fmt == "parquet"
        else import_from_json(repo, input_path)
    )
    console.print(f"[green]{count} sorteios importados.[/green]")


# ── report ────────────────────────────────────────────────────────────────────

@cli.command()
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Caminho do arquivo PDF de saída.",
)
@click.option("--banca", default=None, help="Filtrar por banca.")
@click.option("--horario", type=int, default=None, help="Filtrar por horário (ex: 14).")
@click.pass_context
def report(ctx: click.Context, output: Path, banca: str | None, horario: int | None) -> None:
    """Gera relatório PDF com análise estatística dos sorteios."""
    repo, _, _ = _get_repo(ctx)
    cfg = ReportConfig(banca=banca, hora=horario)
    console.print(f"Gerando relatório [cyan]{output}[/cyan]...")
    result = generate_report(repo, output, config=cfg)
    console.print(f"[green]Relatório gerado:[/green] {result}")


# ── gui ────────────────────────────────────────────────────────────────────────

@cli.command()
@click.pass_context
def gui(ctx: click.Context) -> None:
    """Abre a interface gráfica."""
    try:
        from lotinha.gui import run as gui_run
    except ImportError as exc:
        err_console.print(f"[red]Erro ao importar GUI: {exc}[/red]")
        sys.exit(1)
    gui_run()
