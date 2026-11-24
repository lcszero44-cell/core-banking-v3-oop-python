"""Entidades Cliente e PessoaFisica seguindo rigorosamente o diagrama UML da DIO."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.exceptions import ContaNaoEncontradaError
from src.formatters import (
    mask_cpf_lgpd,
    sanitize_cpf,
    validate_birth_date,
    validate_non_empty_text,
)
from src.models.transacao import Transacao

if TYPE_CHECKING:
    from src.models.conta import Conta


class Cliente:
    """Entidade base de titular bancário, responsável por gerenciar suas contas e acionar transações."""

    def __init__(self, endereco: str) -> None:
        self._endereco: str = validate_non_empty_text(endereco, "endereco")
        self._contas: list[Conta] = []

    @property
    def endereco(self) -> str:
        """Endereço residencial/comercial validado do cliente."""
        return self._endereco

    @property
    def contas(self) -> tuple[Conta, ...]:
        """Tupla imutável das contas vinculadas ao cliente."""
        return tuple(self._contas)

    def realizar_transacao(self, conta: Conta, transacao: Transacao) -> bool:
        """Executa polimorficamente uma `Transacao` sobre uma conta pertencente ao cliente."""
        if not isinstance(transacao, Transacao):
            raise TypeError(
                "A operação deve implementar a interface abstrata Transacao."
            )
        if conta not in self._contas:
            raise ContaNaoEncontradaError(
                f"A conta {getattr(conta, 'numero', '?')} não está vinculada a este titular."
            )
        return transacao.registrar(conta)

    def adicionar_conta(self, conta: Conta) -> None:
        """Vincula uma conta ao cliente, impedindo duplicidades ou contas de terceiros."""
        if getattr(conta, "cliente", None) is not self:
            raise ContaNaoEncontradaError(
                "Não é possível vincular uma conta pertencente a outro cliente."
            )
        if conta not in self._contas:
            self._contas.append(conta)

    def __repr__(self) -> str:
        return f"Cliente(endereco='{self._endereco}', contas={len(self._contas)})"


class PessoaFisica(Cliente):
    """Especialização de Cliente para titulares Pessoa Física com validação e máscara LGPD de CPF."""

    def __init__(
        self,
        nome: str,
        data_nascimento: str,
        cpf: str,
        endereco: str,
    ) -> None:
        super().__init__(endereco=endereco)
        self._cpf: str = sanitize_cpf(cpf)
        self._nome: str = validate_non_empty_text(nome, "nome")
        self._data_nascimento: str = validate_birth_date(data_nascimento)

    @property
    def cpf(self) -> str:
        """CPF sanitizado contendo exclusivamente 11 dígitos numéricos."""
        return self._cpf

    @property
    def cpf_mascarado(self) -> str:
        """CPF mascarado conforme diretrizes LGPD ('***.XXX.XXX-**')."""
        return mask_cpf_lgpd(self._cpf)

    @property
    def nome(self) -> str:
        """Nome completo do titular."""
        return self._nome

    @property
    def data_nascimento(self) -> str:
        """Data de nascimento validada no formato DD/MM/AAAA."""
        return self._data_nascimento

    def __repr__(self) -> str:
        return (
            f"PessoaFisica(nome='{self._nome}', cpf='{self.cpf_mascarado}', "
            f"data_nascimento='{self._data_nascimento}')"
        )

    def __str__(self) -> str:
        return f"{self._nome} (CPF: {self.cpf_mascarado})"


__all__ = ["Cliente", "PessoaFisica"]
