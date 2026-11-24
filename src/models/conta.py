"""Entidades Conta e ContaCorrente seguindo estritamente o diagrama UML da DIO."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Self

from src.exceptions import (
    LimiteDiarioSaquesError,
    LimiteSaqueExcedidoError,
    SaldoInsuficienteError,
    ValorInvalidoError,
)
from src.formatters import format_brl, parse_monetary_value, quantize_brl
from src.models.cliente import Cliente, PessoaFisica
from src.models.historico import Historico
from src.models.transacao import Saque


class Conta:
    """Entidade base de conta bancária com saldo protegido, histórico e fábrica `nova_conta`."""

    AGENCIA_PADRAO: str = "0001"

    def __init__(
        self,
        numero: int,
        cliente: Cliente,
        agencia: str = AGENCIA_PADRAO,
    ) -> None:
        if isinstance(numero, bool) or not isinstance(numero, int) or numero <= 0:
            raise ValorInvalidoError("O número da conta deve ser um inteiro positivo.")
        if not isinstance(cliente, Cliente):
            raise TypeError("O titular da conta deve ser uma instância de Cliente.")
        if not isinstance(agencia, str) or not agencia.strip():
            raise ValorInvalidoError("O código da agência não pode estar vazio.")

        self._saldo: Decimal = Decimal("0.00")
        self._numero: int = numero
        self._agencia: str = agencia.strip()
        self._cliente: Cliente = cliente
        self._historico: Historico = Historico()

    @classmethod
    def nova_conta(cls, cliente: Cliente, numero: int, **kwargs: Any) -> Self:
        """Método fábrica oficial do diagrama UML para criação padronizada de contas."""
        return cls(numero=numero, cliente=cliente, **kwargs)

    @property
    def saldo(self) -> Decimal:
        """Saldo atual protegido em Decimal (somente leitura)."""
        return self._saldo

    @property
    def numero(self) -> int:
        """Número sequencial identificador da conta."""
        return self._numero

    @property
    def agencia(self) -> str:
        """Agência bancária da conta (padrão '0001')."""
        return self._agencia

    @property
    def cliente(self) -> Cliente:
        """Titular proprietário da conta."""
        return self._cliente

    @property
    def historico(self) -> Historico:
        """Instância dedicada de `Historico` contendo a trilha auditável da conta."""
        return self._historico

    def sacar(self, valor: Decimal | int | float | str) -> bool:
        """Debita `valor` do saldo caso positivo e coberto pelo saldo disponível."""
        quantia = parse_monetary_value(valor)
        if quantia <= Decimal("0.00"):
            raise ValorInvalidoError("O valor do saque deve ser maior que R$ 0,00.")
        if quantia > self._saldo:
            raise SaldoInsuficienteError(
                f"Saldo insuficiente: disponível {format_brl(self._saldo)}, "
                f"solicitado {format_brl(quantia)}."
            )

        self._saldo = quantize_brl(self._saldo - quantia)
        return True

    def depositar(self, valor: Decimal | int | float | str) -> bool:
        """Credita `valor` positivo ao saldo com precisão Decimal (`ROUND_HALF_UP`)."""
        quantia = parse_monetary_value(valor)
        if quantia <= Decimal("0.00"):
            raise ValorInvalidoError("O valor do depósito deve ser maior que R$ 0,00.")

        self._saldo = quantize_brl(self._saldo + quantia)
        return True

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(agencia='{self._agencia}', "
            f"numero={self._numero}, saldo=Decimal('{self._saldo}'))"
        )

    def __str__(self) -> str:
        titular = (
            f"{self._cliente.nome} ({self._cliente.cpf_mascarado})"
            if isinstance(self._cliente, PessoaFisica)
            else self._cliente.endereco
        )
        return (
            f"Agência:\t{self._agencia}\n"
            f"C/C:\t\t{self._numero:04d}\n"
            f"Titular:\t{titular}\n"
            f"Saldo:\t\t{format_brl(self._saldo)}"
        )


class ContaCorrente(Conta):
    """Especialização de Conta com teto polimórfico por saque e cota de saques via `Historico`."""

    LIMITE_PADRAO: Decimal = Decimal("500.00")
    LIMITE_SAQUES_PADRAO: int = 3

    def __init__(
        self,
        numero: int,
        cliente: Cliente,
        limite: Decimal | int | float | str = LIMITE_PADRAO,
        limite_saques: int = LIMITE_SAQUES_PADRAO,
        agencia: str = Conta.AGENCIA_PADRAO,
    ) -> None:
        super().__init__(numero=numero, cliente=cliente, agencia=agencia)

        limite_decimal = parse_monetary_value(limite)
        if limite_decimal <= Decimal("0.00"):
            raise ValorInvalidoError("O limite por saque deve ser maior que R$ 0,00.")
        if isinstance(limite_saques, bool) or not isinstance(limite_saques, int) or limite_saques <= 0:
            raise ValorInvalidoError("O limite de saques deve ser um inteiro positivo.")

        self._limite: Decimal = limite_decimal
        self._limite_saques: int = limite_saques

    @property
    def limite(self) -> Decimal:
        """Valor teto permitido por operação de saque (padrão R$ 500,00)."""
        return self._limite

    @property
    def limite_saques(self) -> int:
        """Quantidade máxima de saques permitidos (padrão 3)."""
        return self._limite_saques

    @property
    def saques_realizados(self) -> int:
        """Quantidade de saques já contabilizados diretamente na instância `Historico`."""
        return self.historico.contar_transacoes_por_tipo(Saque.__name__)

    def sacar(self, valor: Decimal | int | float | str) -> bool:
        """Sobrescrita polimórfica que aplica teto por saque e contagem no `Historico`."""
        quantia = parse_monetary_value(valor)
        if quantia <= Decimal("0.00"):
            raise ValorInvalidoError("O valor do saque deve ser maior que R$ 0,00.")

        numero_saques = self.saques_realizados
        if numero_saques >= self._limite_saques:
            raise LimiteDiarioSaquesError(
                f"Limite diário de saques atingido ({numero_saques}/{self._limite_saques})."
            )

        if quantia > self._limite:
            raise LimiteSaqueExcedidoError(
                f"Valor {format_brl(quantia)} excede o teto por saque de {format_brl(self._limite)}."
            )

        return super().sacar(quantia)

    def __str__(self) -> str:
        if isinstance(self._cliente, PessoaFisica):
            titular_linha = f"{self._cliente.nome}\nCPF (LGPD):\t{self._cliente.cpf_mascarado}"
        else:
            titular_linha = self._cliente.endereco

        return (
            f"Agência:\t{self._agencia}\n"
            f"C/C:\t\t{self._numero:04d}\n"
            f"Titular:\t{titular_linha}\n"
            f"Saldo:\t\t{format_brl(self._saldo)}\n"
            f"Limite/Saque:\t{format_brl(self._limite)} "
            f"({self.saques_realizados}/{self._limite_saques} saques)"
        )


__all__ = ["Conta", "ContaCorrente"]
