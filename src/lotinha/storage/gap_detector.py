"""Detecção de datas faltantes no banco."""

from __future__ import annotations

from datetime import date, timedelta

from lotinha.storage.repository import SorteioRepository


class GapDetector:
    """Identifica datas sem nenhum sorteio dentro de um intervalo.

    Args:
        repo: Repositório de sorteios para consulta.
    """

    def __init__(self, repo: SorteioRepository) -> None:
        self._repo = repo

    def find_gaps(self, inicio: date, fim: date) -> list[date]:
        """Retorna datas em [inicio, fim] sem nenhum sorteio no banco.

        Args:
            inicio: Data inicial do intervalo (inclusiva).
            fim: Data final do intervalo (inclusiva).

        Returns:
            Lista de datas sem dados, em ordem cronológica.
        """
        if inicio > fim:
            return []

        dates_with_data = self._repo.dates_with_data()

        gaps: list[date] = []
        current = inicio
        while current <= fim:
            if current not in dates_with_data:
                gaps.append(current)
            current += timedelta(days=1)
        return gaps

    def find_all_gaps(self) -> list[date]:
        """Retorna datas faltantes entre a data mais antiga e hoje.

        Returns:
            Lista de datas sem dados. Vazia se o banco estiver vazio.
        """
        dates_with_data = self._repo.dates_with_data()
        if not dates_with_data:
            return []

        inicio = min(dates_with_data)
        fim = date.today()
        return self.find_gaps(inicio, fim)

    def count_gaps(self, inicio: date, fim: date) -> int:
        """Conta datas sem dados em um intervalo."""
        return len(self.find_gaps(inicio, fim))
