"""Entidade Historico para trilha imutável de auditoria e métricas consolidadas."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from src.formatters import format_timestamp_brt, generate_protocol, now_brt, quantize_brl

if TYPE_CHECKING:
    from src.models.transacao import Transacao


class Historico:
    """Encapsula o registro cronológico e auditável de transações de uma conta.

    A propriedade `transacoes` retorna uma tupla imutável com cópias defensivas
    dos lançamentos, impedindo mutação externa direta da trilha de auditoria.
    """

    def __init__(self) -> None:
        self._transacoes: list[dict[str, Any]] = []

    @property
    def transacoes(self) -> tuple[dict[str, Any], ...]:
        """Retorna visão imutável (tupla) de todas as transações registradas."""
        return tuple(dict(registro) for registro in self._transacoes)

    def adicionar_transacao(
        self,
        transacao: Transacao,
        *,
        saldo_resultante: Decimal | None = None,
    ) -> dict[str, Any]:
        """Registra uma transação aprovada com timestamp em Brasília (UTC-3)."""
        momento_brt = now_brt()
        protocolo = getattr(transacao, "protocolo", None) or generate_protocol()
        saldo_formatado = (
            quantize_brl(saldo_resultante) if saldo_resultante is not None else None
        )

        registro: dict[str, Any] = {
            "protocolo": protocolo,
            "tipo": transacao.__class__.__name__,
            "valor": quantize_brl(transacao.valor),
            "data": format_timestamp_brt(momento_brt),
            "data_iso": momento_brt.isoformat(timespec="seconds"),
            "saldo_resultante": saldo_formatado,
        }
        self._transacoes.append(registro)
        return dict(registro)

    def contar_transacoes_por_tipo(self, tipo_transacao: str) -> int:
        """Conta quantas transações de determinado tipo estão registradas no histórico."""
        alvo = tipo_transacao.strip().lower()
        return sum(1 for item in self._transacoes if item["tipo"].lower() == alvo)

    def gerar_relatorio(self, tipo_transacao: str | None = None) -> dict[str, Any]:
        """Gera relatório consolidado e métricas financeiras com filtro opcional por tipo."""
        filtro_normalizado = tipo_transacao.strip().lower() if tipo_transacao else None

        filtradas: list[dict[str, Any]] = []
        total_depositos = Decimal("0.00")
        total_saques = Decimal("0.00")
        quantidade_depositos = 0
        quantidade_saques = 0

        for item in self._transacoes:
            if filtro_normalizado and item["tipo"].lower() != filtro_normalizado:
                continue

            copia = dict(item)
            filtradas.append(copia)

            tipo_lower = copia["tipo"].lower()
            if tipo_lower == "deposito":
                total_depositos = quantize_brl(total_depositos + copia["valor"])
                quantidade_depositos += 1
            elif tipo_lower == "saque":
                total_saques = quantize_brl(total_saques + copia["valor"])
                quantidade_saques += 1

        ultimo_saldo = filtradas[-1]["saldo_resultante"] if filtradas else None

        return {
            "filtro": tipo_transacao if tipo_transacao else "Todas",
            "transacoes": tuple(filtradas),
            "total_operacoes": len(filtradas),
            "total_depositos": total_depositos,
            "quantidade_depositos": quantidade_depositos,
            "total_saques": total_saques,
            "quantidade_saques": quantidade_saques,
            "saldo_liquido_periodo": quantize_brl(total_depositos - total_saques),
            "ultimo_saldo": ultimo_saldo,
        }

    def __len__(self) -> int:
        return len(self._transacoes)

    def __repr__(self) -> str:
        return f"Historico(total_transacoes={len(self._transacoes)})"


__all__ = ["Historico"]
