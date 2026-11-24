"""Hierarquia de exceções de domínio do Core Banking v3 (POO / UML)."""

from __future__ import annotations


class BankingOOPError(Exception):
    """Exceção base para violações de regras de negócio no domínio bancário."""

    default_code: str = "BANKING_OOP_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.code: str = code or self.default_code
        super().__init__(message)


class CPFInvalidoOuDuplicadoError(BankingOOPError):
    """Lançada quando o CPF é malformado ou já existe na base de titulares."""

    default_code = "CPF_INVALIDO_OU_DUPLICADO"


class TitularNaoEncontradoError(BankingOOPError):
    """Lançada quando nenhum titular (PessoaFisica) corresponde ao CPF informado."""

    default_code = "TITULAR_NAO_ENCONTRADO"


class ContaNaoEncontradaError(BankingOOPError):
    """Lançada quando a conta solicitada não existe ou não pertence ao titular."""

    default_code = "CONTA_NAO_ENCONTRADA"


class ValorInvalidoError(BankingOOPError):
    """Lançada quando um valor monetário ou dado cadastral é inválido."""

    default_code = "VALOR_INVALIDO"


class SaldoInsuficienteError(BankingOOPError):
    """Lançada quando o saldo disponível não cobre o valor do saque."""

    default_code = "SALDO_INSUFICIENTE"


class LimiteSaqueExcedidoError(BankingOOPError):
    """Lançada quando o valor do saque ultrapassa o teto permitido por operação."""

    default_code = "LIMITE_SAQUE_EXCEDIDO"


class LimiteDiarioSaquesError(BankingOOPError):
    """Lançada quando a conta atinge a cota máxima de saques permitidos."""

    default_code = "LIMITE_DIARIO_SAQUES"


__all__ = [
    "BankingOOPError",
    "CPFInvalidoOuDuplicadoError",
    "TitularNaoEncontradoError",
    "ContaNaoEncontradaError",
    "ValorInvalidoError",
    "SaldoInsuficienteError",
    "LimiteSaqueExcedidoError",
    "LimiteDiarioSaquesError",
]
