"""Repositório em memória (BankRepository) para titulares PF e contas correntes."""

from __future__ import annotations

from decimal import Decimal

from src.exceptions import (
    CPFInvalidoOuDuplicadoError,
    ContaNaoEncontradaError,
    TitularNaoEncontradoError,
    ValorInvalidoError,
)
from src.formatters import mask_cpf_lgpd, sanitize_cpf
from src.models.cliente import PessoaFisica
from src.models.conta import ContaCorrente


class BankRepository:
    """Gerencia agregados de titulares (`PessoaFisica`) e contas (`ContaCorrente`) em memória.

    Garante unicidade de CPF sanitizado, vinculação consistente cliente-conta e
    numeração sequencial automática a partir da conta `0001`.
    """

    def __init__(self) -> None:
        self._clientes: list[PessoaFisica] = []
        self._clientes_por_cpf: dict[str, PessoaFisica] = {}
        self._contas: list[ContaCorrente] = []
        self._contas_por_numero: dict[int, ContaCorrente] = {}

    @property
    def clientes(self) -> tuple[PessoaFisica, ...]:
        """Visão imutável (tupla) de todos os titulares cadastrados."""
        return tuple(self._clientes)

    @property
    def contas(self) -> tuple[ContaCorrente, ...]:
        """Visão imutável (tupla) de todas as contas correntes abertas."""
        return tuple(self._contas)

    def buscar_cliente_por_cpf(self, cpf: str) -> PessoaFisica | None:
        """Localiza titular pelo CPF (com ou sem pontuação). Retorna `None` se não encontrado."""
        cpf_limpo = sanitize_cpf(cpf)
        return self._clientes_por_cpf.get(cpf_limpo)

    def obter_cliente_por_cpf(self, cpf: str) -> PessoaFisica:
        """Retorna titular pelo CPF ou lança `TitularNaoEncontradoError`."""
        cpf_limpo = sanitize_cpf(cpf)
        cliente = self._clientes_por_cpf.get(cpf_limpo)
        if cliente is None:
            raise TitularNaoEncontradoError(
                f"Nenhum titular cadastrado para o CPF {mask_cpf_lgpd(cpf_limpo)}."
            )
        return cliente

    def cadastrar_cliente(
        self,
        *,
        nome: str,
        data_nascimento: str,
        cpf: str,
        endereco: str,
    ) -> PessoaFisica:
        """Cadastra um novo titular Pessoa Física assegurando unicidade de CPF."""
        cpf_limpo = sanitize_cpf(cpf)
        if cpf_limpo in self._clientes_por_cpf:
            raise CPFInvalidoOuDuplicadoError(
                f"Já existe um titular cadastrado com o CPF {mask_cpf_lgpd(cpf_limpo)}."
            )

        cliente = PessoaFisica(
            nome=nome,
            data_nascimento=data_nascimento,
            cpf=cpf_limpo,
            endereco=endereco,
        )
        self._clientes.append(cliente)
        self._clientes_por_cpf[cpf_limpo] = cliente
        return cliente

    def criar_conta_corrente(
        self,
        cpf: str,
        *,
        limite: Decimal | int | float | str = ContaCorrente.LIMITE_PADRAO,
        limite_saques: int = ContaCorrente.LIMITE_SAQUES_PADRAO,
    ) -> ContaCorrente:
        """Abre nova conta corrente sequencial vinculada ao titular do CPF informado."""
        cliente = self.obter_cliente_por_cpf(cpf)
        numero_sequencial = len(self._contas) + 1

        conta = ContaCorrente.nova_conta(
            cliente=cliente,
            numero=numero_sequencial,
            limite=limite,
            limite_saques=limite_saques,
        )
        cliente.adicionar_conta(conta)
        self._contas.append(conta)
        self._contas_por_numero[numero_sequencial] = conta
        return conta

    def buscar_conta_por_numero(self, numero: int) -> ContaCorrente | None:
        """Localiza conta corrente pelo número sequencial."""
        if isinstance(numero, bool) or not isinstance(numero, int) or numero <= 0:
            raise ValorInvalidoError("O número da conta deve ser um inteiro positivo.")
        return self._contas_por_numero.get(numero)

    def obter_conta_por_numero(self, numero: int) -> ContaCorrente:
        """Retorna a conta corrente pelo número ou lança `ContaNaoEncontradaError`."""
        conta = self.buscar_conta_por_numero(numero)
        if conta is None:
            raise ContaNaoEncontradaError(f"Conta corrente nº {numero:04d} não encontrada.")
        return conta

    def obter_conta_do_cliente(
        self,
        cpf: str,
        numero_conta: int | None = None,
    ) -> ContaCorrente:
        """Resolve a conta corrente de um titular (seleção direta ou por número)."""
        cliente = self.obter_cliente_por_cpf(cpf)
        if not cliente.contas:
            raise ContaNaoEncontradaError(
                f"O titular {cliente.nome} ({cliente.cpf_mascarado}) não possui contas abertas."
            )

        if numero_conta is None:
            primeira = cliente.contas[0]
            assert isinstance(primeira, ContaCorrente)
            return primeira

        if isinstance(numero_conta, bool) or not isinstance(numero_conta, int) or numero_conta <= 0:
            raise ValorInvalidoError("Número da conta inválido.")

        for conta in cliente.contas:
            if conta.numero == numero_conta and isinstance(conta, ContaCorrente):
                return conta

        raise ContaNaoEncontradaError(
            f"A conta nº {numero_conta:04d} não pertence ao titular {cliente.cpf_mascarado}."
        )


__all__ = ["BankRepository"]
