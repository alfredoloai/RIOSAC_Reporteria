from __future__ import annotations

from core.layers.capa_a.extractor import export_capa_a_raw


def main() -> None:
    groups = [
        "Retiro de equipos Gpon Riosactelcom",
        "Cañar / Riosactelcom",
        "Cuenca / Riosactelcom",
        "GYE,Centro Riosactelcom",
        "Machala / Riosactelcom",
        "Riosactelcom / Loja",
    ]

    export_capa_a_raw(groups)


if __name__ == "__main__":
    main()

