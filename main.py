"""Ponto de entrada da aplicação Core Banking v3 // Object-Oriented Engine (UML).

Uso:
    python main.py          # Abre o terminal interativo bancário
    python main.py --demo   # Executa automaticamente o Modo Tour / Auto-Testes guiado
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from src.cli import run_cli, run_demo_tour


def _configure_utf8_console() -> None:
    """Garante renderização limpa de box-drawing Unicode no Windows PowerShell/CMD."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser de argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        prog="core-banking-v3",
        description=(
            "Core Banking v3 // Object-Oriented Engine (UML DIO) — "
            "Sistema Bancário 100% Orientado a Objetos em Python."
        ),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Executa automaticamente o Modo Tour / Auto-Testes interativos e encerra.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Executa a CLI interativa ou o Modo Tour (`--demo`)."""
    _configure_utf8_console()
    args = build_parser().parse_args(argv)
    if args.demo:
        run_demo_tour()
        return 0
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
