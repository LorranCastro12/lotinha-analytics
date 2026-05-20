"""Orquestrador de extração: decide quais datas buscar e coordena todo o pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from lotinha.core.domain import ExtractionLogEntry
from lotinha.core.exceptions import (
    ApiServerError,
    BackupError,
    DateNotFoundError,
    RateLimitExceededError,
)
from lotinha.storage.backup import create_backup
from lotinha.storage.gap_detector import GapDetector

if TYPE_CHECKING:
    from lotinha.extraction.api_client import ApiClient
    from lotinha.storage.repository import SorteioRepository


@dataclass
class ExtractionReport:
    """Relatório de resultado de uma operação de extração.

    Attributes:
        inicio: Data inicial do intervalo tentado.
        fim: Data final do intervalo tentado.
        total_dias: Número total de dias processados.
        extraidos: Dias com ao menos um sorteio novo salvo.
        ja_presentes: Dias pulados por já terem dados no banco.
        falhas: Dias com erro de API (5xx, 429 esgotado, rede).
        vazios: Dias sem dados na API (404 ou resposta vazia).
        erros: Lista de (data, mensagem) para cada falha.
        started_at: Momento de início da operação.
        finished_at: Momento de término (None enquanto em andamento).
        backup_path: Caminho do backup criado, se houver.
    """

    inicio: date
    fim: date
    total_dias: int
    extraidos: int
    ja_presentes: int
    falhas: int
    vazios: int
    erros: list[tuple[date, str]]
    started_at: datetime
    finished_at: datetime | None = None
    backup_path: Path | None = None

    @property
    def sucesso(self) -> bool:
        """True se nenhum dia terminou com erro de API."""
        return self.falhas == 0


class ExtractionOrchestrator:
    """Coordena a extração de sorteios para um intervalo de datas.

    Responsabilidades:
    - Decidir quais datas extrair (todas vs. apenas lacunas)
    - Criar backup antes de extração massiva
    - Registrar tentativas no log de auditoria
    - Reportar progresso via callback
    - Não duplicar registros (idempotência garantida pelo upsert)

    Args:
        api_client: Cliente HTTP para a API.
        repo: Repositório de persistência.
        backup_dir: Diretório para backups automáticos.
        db_path: Caminho do arquivo SQLite (necessário para backup).
        max_backups: Máximo de backups a manter.
    """

    def __init__(
        self,
        api_client: ApiClient,
        repo: SorteioRepository,
        backup_dir: Path | None = None,
        db_path: Path | None = None,
        max_backups: int = 5,
    ) -> None:
        self._api = api_client
        self._repo = repo
        self._backup_dir = backup_dir or Path("data/backups")
        self._db_path = db_path
        self._max_backups = max_backups
        self._gap_detector = GapDetector(repo)

    # ── API pública ────────────────────────────────────────────────────────────

    def extract_range(
        self,
        inicio: date,
        fim: date,
        skip_existing: bool = True,
        backup_before: bool = True,
        progress_callback: Callable[[int, int, date], None] | None = None,
    ) -> ExtractionReport:
        """Extrai sorteios para um intervalo de datas.

        Args:
            inicio: Data inicial (inclusiva).
            fim: Data final (inclusiva).
            skip_existing: Se True, pula datas que já têm dados no banco.
            backup_before: Se True, cria backup do banco antes de começar.
            progress_callback: Chamado a cada dia processado com (atual, total, data).

        Returns:
            Relatório detalhado da operação.
        """
        if inicio > fim:
            return ExtractionReport(
                inicio=inicio, fim=fim, total_dias=0,
                extraidos=0, ja_presentes=0, falhas=0, vazios=0,
                erros=[], started_at=datetime.now(), finished_at=datetime.now(),
            )

        report = ExtractionReport(
            inicio=inicio, fim=fim, total_dias=0,
            extraidos=0, ja_presentes=0, falhas=0, vazios=0,
            erros=[], started_at=datetime.now(),
        )

        # Backup antes da extração
        if backup_before:
            report.backup_path = self._try_backup()

        # Determinar quais datas processar
        all_days = self._date_range(inicio, fim)
        existing = self._repo.dates_with_data() if skip_existing else set()
        days_to_fetch = [d for d in all_days if d not in existing]
        skipped = len(all_days) - len(days_to_fetch)
        report.ja_presentes = skipped
        report.total_dias = len(days_to_fetch)

        total = len(days_to_fetch)
        for idx, current in enumerate(days_to_fetch, start=1):
            self._process_day(current, report)
            if progress_callback:
                progress_callback(idx, total, current)

        report.finished_at = datetime.now()
        self._log_report(report)
        return report

    def recover_gaps(
        self,
        inicio: date | None = None,
        fim: date | None = None,
        progress_callback: Callable[[int, int, date], None] | None = None,
    ) -> ExtractionReport:
        """Reextrai todas as datas faltantes entre o primeiro registro e hoje (ou fim).

        Args:
            inicio: Início do intervalo (padrão: data mais antiga no banco).
            fim: Fim do intervalo (padrão: hoje).
            progress_callback: Chamado a cada dia processado.

        Returns:
            Relatório da operação. `total_dias=0` se não houver lacunas.
        """
        dates_with_data = self._repo.dates_with_data()
        if not dates_with_data:
            return ExtractionReport(
                inicio=date.today(), fim=date.today(), total_dias=0,
                extraidos=0, ja_presentes=0, falhas=0, vazios=0,
                erros=[], started_at=datetime.now(), finished_at=datetime.now(),
            )

        _inicio = inicio or min(dates_with_data)
        _fim = fim or date.today()
        gaps = self._gap_detector.find_gaps(_inicio, _fim)

        if not gaps:
            return ExtractionReport(
                inicio=_inicio, fim=_fim, total_dias=0,
                extraidos=0, ja_presentes=0, falhas=0, vazios=0,
                erros=[], started_at=datetime.now(), finished_at=datetime.now(),
            )

        report = ExtractionReport(
            inicio=gaps[0], fim=gaps[-1], total_dias=len(gaps),
            extraidos=0, ja_presentes=0, falhas=0, vazios=0,
            erros=[], started_at=datetime.now(),
        )
        total = len(gaps)
        for idx, gap_date in enumerate(gaps, start=1):
            self._process_day(gap_date, report)
            if progress_callback:
                progress_callback(idx, total, gap_date)

        report.finished_at = datetime.now()
        self._log_report(report)
        return report

    # ── Internals ──────────────────────────────────────────────────────────────

    def _process_day(self, current: date, report: ExtractionReport) -> None:
        """Busca e persiste sorteios de um dia, atualizando o relatório."""
        try:
            sorteios = self._api.fetch_day(current)
        except DateNotFoundError:
            logger.info(f"Sem dados na API para {current}")
            report.vazios += 1
            self._repo.log_extraction(ExtractionLogEntry(
                data=current, status="empty", timestamp=datetime.now(),
            ))
            return
        except (ApiServerError, RateLimitExceededError) as exc:
            logger.error(f"Falha ao extrair {current}: {exc}")
            report.falhas += 1
            report.erros.append((current, str(exc)))
            self._repo.log_extraction(ExtractionLogEntry(
                data=current, status="error",
                error_message=str(exc), timestamp=datetime.now(),
            ))
            return

        if not sorteios:
            logger.debug(f"API retornou lista vazia para {current}")
            report.vazios += 1
            self._repo.log_extraction(ExtractionLogEntry(
                data=current, status="empty", timestamp=datetime.now(),
            ))
            return

        self._repo.upsert_batch(sorteios)
        report.extraidos += 1
        self._repo.log_extraction(ExtractionLogEntry(
            data=current, status="success", timestamp=datetime.now(),
        ))
        logger.info(f"Extraídos {len(sorteios)} sorteios para {current}")

    def _try_backup(self) -> Path | None:
        """Tenta criar backup; retorna caminho ou None se não for possível."""
        if self._db_path is None or not self._db_path.exists():
            logger.debug("Backup ignorado: db_path não configurado ou arquivo inexistente")
            return None
        try:
            backup_path = create_backup(self._db_path, self._backup_dir, self._max_backups)
            logger.info(f"Backup criado: {backup_path}")
            return backup_path
        except BackupError as exc:
            logger.warning(f"Falha ao criar backup (operação continua): {exc}")
            return None

    def _log_report(self, report: ExtractionReport) -> None:
        duration = (
            (report.finished_at - report.started_at).total_seconds()
            if report.finished_at else 0.0
        )
        logger.info(
            f"Extração concluída em {duration:.1f}s — "
            f"extraídos={report.extraidos} "
            f"já_presentes={report.ja_presentes} "
            f"vazios={report.vazios} "
            f"falhas={report.falhas}"
        )

    @staticmethod
    def _date_range(inicio: date, fim: date) -> list[date]:
        days = []
        current = inicio
        while current <= fim:
            days.append(current)
            current += timedelta(days=1)
        return days
