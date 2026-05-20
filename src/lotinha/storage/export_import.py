"""Exportação e importação do banco para formatos portáveis."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from lotinha.core.domain import Sorteio
from lotinha.core.exceptions import ExportError
from lotinha.core.exceptions import ImportError as LotinhaImportError
from lotinha.storage.repository import SorteioRepository


def export_to_json(repo: SorteioRepository, output_path: Path) -> int:
    """Exporta todos os sorteios para um arquivo JSON.

    Args:
        repo: Repositório de origem.
        output_path: Caminho do arquivo JSON de saída.

    Returns:
        Número de registros exportados.

    Raises:
        ExportError: Em caso de falha ao gravar o arquivo.
    """
    records = repo.get_all_as_dicts()
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"Falha ao gravar {output_path}: {exc}") from exc
    return len(records)


def import_from_json(repo: SorteioRepository, input_path: Path) -> int:
    """Importa sorteios de um arquivo JSON para o repositório.

    Args:
        repo: Repositório de destino.
        input_path: Caminho do arquivo JSON de origem.

    Returns:
        Número de registros importados.

    Raises:
        LotinhaImportError: Em caso de falha ao ler ou processar o arquivo.
    """
    try:
        records = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LotinhaImportError(f"Falha ao ler {input_path}: {exc}") from exc

    sorteios = [_dict_to_sorteio(r) for r in records]
    return repo.upsert_batch(sorteios)


def export_to_parquet(repo: SorteioRepository, output_path: Path) -> int:
    """Exporta todos os sorteios para um arquivo Parquet.

    Args:
        repo: Repositório de origem.
        output_path: Caminho do arquivo Parquet de saída.

    Returns:
        Número de registros exportados.

    Raises:
        ExportError: Em caso de falha ao gravar o arquivo.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ExportError("pandas é necessário para exportar em Parquet") from exc

    records = repo.get_all_as_dicts()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(
            columns=["data", "hora", "banca", "numeros", "extracted_at", "source", "raw_payload"]
        )

    # numeros precisa ser serializado como string no parquet (lista não é type-safe)
    df["numeros"] = df["numeros"].apply(json.dumps)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False)
    except Exception as exc:
        raise ExportError(f"Falha ao gravar parquet {output_path}: {exc}") from exc

    return len(records)


def import_from_parquet(repo: SorteioRepository, input_path: Path) -> int:
    """Importa sorteios de um arquivo Parquet para o repositório.

    Args:
        repo: Repositório de destino.
        input_path: Caminho do arquivo Parquet de origem.

    Returns:
        Número de registros importados.

    Raises:
        LotinhaImportError: Em caso de falha ao ler o arquivo.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise LotinhaImportError("pandas é necessário para importar Parquet") from exc

    try:
        df = pd.read_parquet(input_path)
    except Exception as exc:
        raise LotinhaImportError(f"Falha ao ler {input_path}: {exc}") from exc

    records: list[dict[str, Any]] = df.to_dict(orient="records")  # type: ignore[assignment]
    sorteios = [_dict_to_sorteio(r) for r in records]
    return repo.upsert_batch(sorteios)


def export_to_excel(repo: SorteioRepository, output_path: Path) -> int:
    """Exporta histórico para Excel com uma sheet por banca/horário.

    Cada sheet tem colunas: Data, N01..N15 (números individuais, ordenados).

    Returns:
        Total de linhas exportadas.

    Raises:
        ExportError: Em caso de falha ao gravar o arquivo.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ExportError("pandas é necessário para exportar em Excel") from exc

    bancas = sorted(repo.list_bancas())
    horarios = sorted(repo.list_horarios())
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for banca in bancas:
                for hora in horarios:
                    df = repo.get_resultados(banca=banca, hora=hora)
                    if df.empty:
                        continue

                    rows = []
                    for _, row in df.iterrows():
                        nums = sorted(row["numeros"])
                        entry: dict[str, object] = {"Data": row["data"]}
                        for i, n in enumerate(nums, start=1):
                            entry[f"N{i:02d}"] = n
                        rows.append(entry)

                    sheet_df = pd.DataFrame(rows).sort_values("Data")
                    banca_short = banca.replace("LOTINHA ", "")
                    sheet_name = f"{banca_short} {hora:02d}h"[:31]
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    total += len(sheet_df)
    except Exception as exc:
        raise ExportError(f"Falha ao gravar Excel {output_path}: {exc}") from exc

    return total


def _dict_to_sorteio(d: dict[str, Any]) -> Sorteio:
    """Converte dicionário (export format) em entidade Sorteio."""
    numeros = d["numeros"]
    if isinstance(numeros, str):
        numeros = json.loads(numeros)

    extracted_at = d["extracted_at"]
    if isinstance(extracted_at, str):
        extracted_at = datetime.fromisoformat(extracted_at)

    data = d["data"]
    if isinstance(data, str):
        data = date.fromisoformat(data)

    return Sorteio(
        data=data,
        hora=int(d["hora"]),
        banca=str(d["banca"]),
        numeros=list(numeros),
        extracted_at=extracted_at,
        source=str(d.get("source", "api")),
        raw_payload=d.get("raw_payload"),
    )
