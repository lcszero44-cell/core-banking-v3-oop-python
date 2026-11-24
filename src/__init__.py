"""API pública consolidada do Core Banking v3 // Object-Oriented Engine (UML)."""

from src.cli import format_accounts_table, format_statement, run_cli, run_demo_tour
from src.exceptions import (
    BankingOOPError,
    CPFInvalidoOuDuplicadoError,
    ContaNaoEncontradaError,
    LimiteDiarioSaquesError,
    LimiteSaqueExcedidoError,
    SaldoInsuficienteError,
    TitularNaoEncontradoError,
    ValorInvalidoError,
)
from src.formatters import format_brl, mask_cpf_lgpd, parse_monetary_value, sanitize_cpf
from src.models import (
    Cliente,
    Conta,
    ContaCorrente,
    Deposito,
    Historico,
    PessoaFisica,
    Saque,
    Transacao,
)
from src.repository import BankRepository

__all__ = [
    # Modelos UML
    "Transacao",
    "Deposito",
    "Saque",
    "Historico",
    "Cliente",
    "PessoaFisica",
    "Conta",
    "ContaCorrente",
    # Repositório
    "BankRepository",
    # Exceções
    "BankingOOPError",
    "CPFInvalidoOuDuplicadoError",
    "TitularNaoEncontradoError",
    "ContaNaoEncontradaError",
    "ValorInvalidoError",
    "SaldoInsuficienteError",
    "LimiteSaqueExcedidoError",
    "LimiteDiarioSaquesError",
    # Utilitários e CLI
    "format_brl",
    "mask_cpf_lgpd",
    "parse_monetary_value",
    "sanitize_cpf",
    "format_accounts_table",
    "format_statement",
    "run_demo_tour",
    "run_cli",
]
