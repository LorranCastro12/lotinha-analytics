"""Geração de relatório PDF com estatísticas de sorteios."""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lotinha.analysis.statistics import atraso, frequencia
from lotinha.storage.repository import SorteioRepository


@dataclass
class ReportConfig:
    """Configurações de filtragem do relatório."""

    banca: str | None = None
    hora: int | None = None
    n_top: int = 5


def generate_report(
    repo: SorteioRepository,
    output: Path,
    config: ReportConfig | None = None,
) -> Path:
    """Gera relatório PDF com análise estatística dos sorteios.

    Returns:
        Caminho do arquivo PDF gerado.
    """
    cfg = config or ReportConfig()
    output.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    story = _build_story(repo, cfg)
    doc.build(story)
    return output


# ── Builders ────────────────────────────────────────────────────────────────


def _build_story(repo: SorteioRepository, cfg: ReportConfig) -> list[Any]:
    styles = getSampleStyleSheet()
    style_title = styles["Title"]
    style_h2 = styles["Heading2"]
    style_body = styles["BodyText"]

    story: list[Any] = []

    # ── Cabeçalho ──────────────────────────────────────────────────────────
    story.append(Paragraph("Lotinha Analytics", style_title))
    story.append(Paragraph("Relatório de Análise Estatística", style_h2))
    story.append(Paragraph(f"Gerado em: {date.today()}", style_body))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.darkgreen))
    story.append(Spacer(1, 0.4 * cm))

    # ── Filtros aplicados ──────────────────────────────────────────────────
    banca_str = cfg.banca or "Todas"
    hora_str = f"{cfg.hora}h" if cfg.hora is not None else "Todos"
    filtros = f"<b>Banca:</b> {banca_str} &nbsp;&nbsp; <b>Horário:</b> {hora_str}"
    story.append(Paragraph(filtros, style_body))
    story.append(Spacer(1, 0.4 * cm))

    # ── Resumo do banco ────────────────────────────────────────────────────
    story.append(Paragraph("Resumo do Banco de Dados", style_h2))
    story.extend(_build_summary_table(repo))
    story.append(Spacer(1, 0.5 * cm))

    # ── Dados e gráficos ───────────────────────────────────────────────────
    df = repo.get_resultados(banca=cfg.banca, hora=cfg.hora)

    if df.empty:
        story.append(Paragraph(
            "Sem dados para os filtros selecionados.", style_body))
    else:
        story.extend(_build_freq_section(df))
        story.extend(_build_atraso_section(df))
        story.extend(_build_top_table(df, cfg.n_top))

    # ── Aviso estatístico ──────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Aviso estatístico</b>", style_h2))
    story.append(Paragraph(
        "Este relatório apresenta estatísticas descritivas históricas. "
        "Frequências e atrasos passados <b>não</b> implicam probabilidades "
        "futuras superiores ao acaso em um sorteio justo (Lotinha = hipergeométrica). "
        "Qualquer estratégia deve ser validada com walk-forward backtesting e "
        "teste de Wilcoxon antes de uso prático.",
        style_body,
    ))

    return story


def _build_summary_table(repo: SorteioRepository) -> list[Any]:
    total = repo.count_total()
    latest = repo.latest_date()
    bancas = repo.list_bancas()
    horarios = repo.list_horarios()
    dates = repo.dates_with_data()

    oldest = str(min(dates)) if dates else "—"
    newest = str(latest) if latest else "—"
    bancas_str = ", ".join(sorted(bancas)) if bancas else "—"
    hora_str = ", ".join(f"{h}h" for h in sorted(horarios)) if horarios else "—"

    data = [
        ["Campo", "Valor"],
        ["Total de sorteios", str(total)],
        ["Data mais antiga", oldest],
        ["Data mais recente", newest],
        ["Dias com dados", str(len(dates))],
        ["Bancas", bancas_str],
        ["Horários", hora_str],
    ]

    tbl = Table(data, colWidths=[7 * cm, 10 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [tbl]


def _build_freq_section(df: pd.DataFrame) -> list[Any]:
    s = getSampleStyleSheet()
    freq = frequencia(df)
    img = _chart_to_image(
        x=list(freq.index),
        y=list(freq.values),
        title="Frequência Relativa por Número",
        ylabel="Frequência",
        color="#2CC985",
        hline=15 / 25,
        hline_label="Esperado (15/25)",
    )
    return [
        Paragraph("Análise de Frequência", s["Heading2"]),
        Spacer(1, 0.3 * cm),
        img,
        Spacer(1, 0.3 * cm),
    ]


def _build_atraso_section(df: pd.DataFrame) -> list[Any]:
    s = getSampleStyleSheet()
    at = atraso(df).astype(float)
    img = _chart_to_image(
        x=list(at.index),
        y=list(at.values),
        title="Atraso por Número (sorteios sem aparecer)",
        ylabel="Atraso (sorteios)",
        color="#F4A000",
    )
    return [
        Paragraph("Análise de Atraso", s["Heading2"]),
        Spacer(1, 0.3 * cm),
        img,
        Spacer(1, 0.3 * cm),
    ]


def _build_top_table(df: pd.DataFrame, n_top: int) -> list[Any]:
    s = getSampleStyleSheet()

    freq = frequencia(df)
    at = atraso(df)
    n = n_top

    top_freq = freq.nlargest(n)
    top_atraso = at.nlargest(n)

    data: list[list[str]] = [
        ["Rank", f"Top {n} Mais Frequentes", "Freq.", f"Top {n} Maior Atraso", "Atraso"]
    ]
    for rank in range(1, n + 1):
        f_num = int(top_freq.index[rank - 1])
        f_val = f"{top_freq.iloc[rank - 1]:.3f}"
        a_num = int(top_atraso.index[rank - 1])
        a_val = str(int(top_atraso.iloc[rank - 1]))
        data.append([str(rank), str(f_num), f_val, str(a_num), a_val])

    tbl = Table(data, colWidths=[1.5 * cm, 4 * cm, 3 * cm, 4 * cm, 3 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return [
        Paragraph(f"Top {n} por Frequência e Atraso", s["Heading2"]),
        Spacer(1, 0.3 * cm),
        tbl,
    ]


# ── Chart helper ────────────────────────────────────────────────────────────


def _chart_to_image(
    x: list[int],
    y: list[float],
    title: str,
    ylabel: str,
    color: str,
    hline: float | None = None,
    hline_label: str | None = None,
    width_cm: float = 15.0,
    height_cm: float = 5.5,
) -> Image:
    dpi = 96
    fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=dpi)
    ax.bar(x, y, color=color, edgecolor="none")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("Número", fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xticks(range(1, 26))
    ax.tick_params(labelsize=7)
    if hline is not None:
        ax.axhline(hline, color="red", linestyle="--", linewidth=1,
                   label=hline_label or "")
        ax.legend(fontsize=7)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)
