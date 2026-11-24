"""Modelos de domínio POO alinhados ao diagrama UML oficial da DIO."""

from src.models.cliente import Cliente, PessoaFisica
from src.models.conta import Conta, ContaCorrente
from src.models.historico import Historico
from src.models.transacao import Deposito, Saque, Transacao

__all__ = [
    "Transacao",
    "Deposito",
    "Saque",
    "Historico",
    "Cliente",
    "PessoaFisica",
    "Conta",
    "ContaCorrente",
]
