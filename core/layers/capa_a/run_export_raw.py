from __future__ import annotations

import argparse
from datetime import date

from core.layers.capa_a.extractor import export_capa_a_raw


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - CLI validation
        raise argparse.ArgumentTypeError(
            f"Fecha inválida '{value}'. Usa el formato YYYY-MM-DD."
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta CSV RAW por cuadrilla")
    parser.add_argument(
        "--start",
        type=_parse_date,
        help="Fecha inicial (YYYY-MM-DD). Default: hoy",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        help="Fecha final (YYYY-MM-DD). Default: fecha inicial",
    )
    args = parser.parse_args()

    groups = [
        "Retiro de equipos Gpon Riosactelcom",
        "Cañar / Riosactelcom",
        "Cuenca / Riosactelcom",
        "GYE,Centro Riosactelcom",
        "Machala / Riosactelcom",
        "Riosactelcom / Loja",
    ]

    start = args.start or date.today()
    end = args.end or start
    if end < start:
        parser.error("La fecha final no puede ser anterior a la inicial.")

    export_capa_a_raw(groups, start_date=start, end_date=end)


if __name__ == "__main__":
    main()

