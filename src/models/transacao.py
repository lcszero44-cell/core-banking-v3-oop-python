"""Contratos abstratos e implementações concretas de Transação (UML DIO)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from src.exceptions import ValorInvalidoError
from src.formatters import format_brl, generate_protocol, parse_monetary_value

if TYPE_CHECKING:
    from src.models.conta import Conta


class Transacao(ABC):
    """Interface abstrata que define o contrato polimórfico de qualquer transação bancária."""

    @property
    @abstractmethod
    def valor(self) -> Decimal:
        """Retorna o valor monetário quantizado da transação."""

    @abstractmethod
    def registrar(self, conta: Conta) -> bool:
        """Executa a operação na conta alvo e registra no histórico se aprovada."""


class _TransacaoMonetariaBase(Transacao):
    """Base interna compartilhada para validação Decimal (ROUND_HALF_UP) e protocolo UUID4."""

    def __init__(self, valor: Decimal | int | float | str) -> None:
        quantia = parse_monetary_value(valor)
        if quantia <= Decimal("0.00"):
            raise ValorInvalidoError(
                "O valor da transação deve ser estritamente maior que R$ 0,00."
            )
        self._valor: Decimal = quantia
        self._protocolo: str = generate_protocol()

    @property
    def valor(self) -> Decimal:
        """Valor monetário validado em Decimal com precisão de centavos (ROUND_HALF_UP)."""
        return self._valor

    @property
    def protocolo(self) -> str:
        """Protocolo único de rastreabilidade baseado em UUID4 (TX-XXXXXXXX)."""
        return self._protocolo

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(valor=Decimal('{self._valor}'), "
            f"protocolo='{self._protocolo}')"
        )

    def __str__(self) -> str:
        return f"{self.__class__.__name__} [{self._protocolo}] {format_brl(self._valor)}"


class Deposito(_TransacaoMonetariaBase):
    """Transação concreta de crédito em conta bancária."""

    def registrar(self, conta: Conta) -> bool:
        """Efetua depósito na conta e grava no histórico apenas se a operação for aprovada."""
        sucesso_transacao = conta.depositar(self.valor)
        if sucesso_transacao:
            conta.historico.adicionar_transacao(self, saldo_resultante=conta.saldo)
        return sucesso_transacao


class Saque(_TransacaoMonetariaBase):
    """Transação concreta de débito em conta bancária."""

    def registrar(self, conta: Conta) -> bool:
        """Efetua saque na conta e grava no histórico apenas se a operação for aprovada."""
        sucesso_transacao = conta.sacar(self.valor)
        if sucesso_transacao:
            conta.historico.adicionar_transacao(self, saldo_resultante=conta.saldo)
        return sucesso_transacao


__all__ = ["Transacao", "Deposito", "Saque"]
