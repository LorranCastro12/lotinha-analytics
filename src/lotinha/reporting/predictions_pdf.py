"""Geração de PDF com predições para todos os sorteios de uma data alvo."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from lotinha.analysis.strategies import (
    AtrasoStrategy,
    BaseStrategy,
    EnsembleStrategy,
    FrequenciaStrategy,
    MarkovStrategy,
)
from lotinha.core.exceptions import InsufficientDataError
from lotinha.storage.repository import SorteioRepository


def generate_predictions_pdf(
    repo: SorteioRepository,
    output: Path,
    data_alvo: date,
    estrategia_nome: str = "Ensemble",
    n_preditos: int = 22,
) -> tuple[Path, int]:
    """Gera PDF com predições para todas as bancas/horários de uma data.

    Usa apenas sorteios anteriores a data_alvo para fazer as predições.

    Returns:
        Tupla (caminho do PDF, número de predições geradas com sucesso).
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    strategy = _make_strategy(estrategia_nome)
    bancas = sorted(repo.list_bancas())
    horarios = sorted(repo.list_horarios())

    rows, n_ok = _build_prediction_rows(
        repo, bancas, horarios, strategy, n_preditos, data_alvo
    )

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(_build_story(rows, data_alvo, estrategia_nome, n_preditos))
    return output, n_ok


# ── Builders ────────────────────────────────────────────────────────────────


def _make_strategy(nome: str) -> BaseStrategy:
    ensemble = EnsembleStrategy([FrequenciaStrategy(), AtrasoStrategy(), MarkovStrategy()])
    strat_map: dict[str, BaseStrategy] = {
        "Frequência": FrequenciaStrategy(),
        "Atraso": AtrasoStrategy(),
        "Markov": MarkovStrategy(),
        "Ensemble": ensemble,
    }
    return strat_map.get(nome, ensemble)


def _cell_style() -> ParagraphStyle:
    return ParagraphStyle(
        "cell",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        wordWrap="CJK",
    )


def _header_style() -> ParagraphStyle:
    return ParagraphStyle(
        "header",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
    )


def _build_prediction_rows(
    repo: SorteioRepository,
    bancas: list[str],
    horarios: list[int],
    strategy: BaseStrategy,
    n_preditos: int,
    data_alvo: date,
) -> tuple[list[list[Any]], int]:
    cs = _cell_style()
    hs = _header_style()
    header: list[Any] = [
        Paragraph("Banca", hs),
        Paragraph("Hor.", hs),
        Paragraph(f"Números Preditos (top {n_preditos})", hs),
        Paragraph("Conf.", hs),
        Paragraph("Hist.", hs),
    ]
    rows: list[list[Any]] = [header]
    n_ok = 0

    for banca in bancas:
        for hora in horarios:
            df_full = repo.get_resultados(banca=banca, hora=hora)
            if df_full.empty:
                continue

            df = df_full[df_full["data"] < data_alvo].copy()

            if df.empty:
                rows.append([
                    Paragraph(banca, cs),
                    Paragraph(f"{hora:02d}h", cs),
                    Paragraph("Sem histórico anterior", cs),
                    Paragraph("—", cs),
                    Paragraph("0", cs),
                ])
                continue

            try:
                result = strategy.predict(df, n=n_preditos)
                nums_str = ", ".join(str(n) for n in sorted(result.numeros))
                conf_str = f"{result.confidence:.1%}"
                n_ok += 1
            except InsufficientDataError:
                nums_str = "Dados insuficientes"
                conf_str = "—"
            except Exception as exc:
                nums_str = f"Erro: {exc}"
                conf_str = "—"

            rows.append([
                Paragraph(banca, cs),
                Paragraph(f"{hora:02d}h", cs),
                Paragraph(nums_str, cs),
                Paragraph(conf_str, cs),
                Paragraph(str(len(df)), cs),
            ])

    return rows, n_ok


def _build_story(
    rows: list[list[Any]],
    data_alvo: date,
    estrategia_nome: str,
    n_preditos: int,
) -> list[Any]:
    styles = getSampleStyleSheet()

    story: list[Any] = []

    story.append(Paragraph("Lotinha Analytics", styles["Title"]))
    story.append(Paragraph(f"Predições — {data_alvo}", styles["Heading2"]))
    story.append(Paragraph(
        f"Estratégia: <b>{estrategia_nome}</b> &nbsp;&nbsp; "
        f"N preditos: <b>{n_preditos}</b> &nbsp;&nbsp; "
        f"Gerado em: <b>{date.today()}</b>",
        styles["BodyText"],
    ))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.darkgreen))
    story.append(Spacer(1, 0.4 * cm))

    # Widths sum to 17cm (A4 usable width with 2cm margins each side)
    col_widths = [4.5 * cm, 1.5 * cm, 7.5 * cm, 2.0 * cm, 1.5 * cm]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkgreen),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "CENTER"),
    ]))
    story.append(tbl)

    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Aviso estatístico</b>", styles["Heading3"]))
    story.append(Paragraph(
        "Predições baseadas em frequência histórica <b>não</b> têm valor preditivo "
        "comprovado em sorteios independentes (distribuição hipergeométrica). "
        "Use apenas para estudo e análise.",
        styles["BodyText"],
    ))

    return story
