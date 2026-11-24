"""Utilitários financeiros (Decimal BRL), compliance LGPD, relógio BRT e formatação CLI."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from src.exceptions import CPFInvalidoOuDuplicadoError, ValorInvalidoError

BRT_TIMEZONE = timezone(timedelta(hours=-3), name="BRT")
TWO_PLACES = Decimal("0.01")
_NON_DIGITS_RE = re.compile(r"\D+")


def quantize_brl(valor: Decimal) -> Decimal:
    """Quantiza um Decimal para duas casas decimais com arredondamento bancário ROUND_HALF_UP."""
    if not isinstance(valor, Decimal) or not valor.is_finite():
        raise ValorInvalidoError("Valor monetário deve ser um número finito válido.")
    return valor.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_monetary_value(valor: Any) -> Decimal:
    """Converte entrada monetária (Decimal, int, float ou str BR/EN) para Decimal(0.01).

    Aceita formatos como `1500`, `1500.5`, `"1.500,50"`, `"R$ 250,75"` ou `Decimal("10.005")`.
    Rejeita booleanos, NaN, infinito e strings malformadas.
    """
    if isinstance(valor, bool) or valor is None:
        raise ValorInvalidoError("Valor monetário inválido. Informe um valor numérico positivo.")

    if isinstance(valor, Decimal):
        if not valor.is_finite():
            raise ValorInvalidoError("Valor monetário não pode ser NaN ou infinito.")
        return quantize_brl(valor)

    if isinstance(valor, int):
        return quantize_brl(Decimal(valor))

    if isinstance(valor, float):
        try:
            dec = Decimal(str(valor))
        except InvalidOperation as exc:
            raise ValorInvalidoError("Valor monetário inválido.") from exc
        if not dec.is_finite():
            raise ValorInvalidoError("Valor monetário não pode ser NaN ou infinito.")
        return quantize_brl(dec)

    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            raise ValorInvalidoError("Valor monetário não pode estar vazio.")
        texto = texto.replace("R$", "").replace("r$", "").replace(" ", "")

        if "," in texto and "." in texto:
            # Determina qual separador é decimal pela última ocorrência
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")
        elif "," in texto:
            texto = texto.replace(",", ".")

        try:
            dec = Decimal(texto)
        except InvalidOperation as exc:
            raise ValorInvalidoError(
                f"Não foi possível interpretar '{valor}' como valor monetário."
            ) from exc

        if not dec.is_finite():
            raise ValorInvalidoError("Valor monetário não pode ser NaN ou infinito.")
        return quantize_brl(dec)

    raise ValorInvalidoError(
        f"Tipo '{type(valor).__name__}' não suportado para valor monetário."
    )


def format_brl(valor: Decimal | int | float | str) -> str:
    """Formata um valor monetário no padrão brasileiro (ex.: 'R$ 1.250,00')."""
    quantia = parse_monetary_value(valor)
    negativo = quantia < Decimal("0.00")
    absoluto = abs(quantia)
    bruto = f"{absoluto:,.2f}"
    formatado = bruto.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"-R$ {formatado}" if negativo else f"R$ {formatado}"


def sanitize_cpf(cpf: str) -> str:
    """Remove pontuação do CPF e valida exatamente 11 dígitos numéricos não repetitivos."""
    if not isinstance(cpf, str):
        raise CPFInvalidoOuDuplicadoError("CPF deve ser fornecido como texto.")

    digitos = _NON_DIGITS_RE.sub("", cpf)
    if len(digitos) != 11:
        raise CPFInvalidoOuDuplicadoError(
            "CPF inválido: informe exatamente 11 dígitos numéricos."
        )
    if digitos == digitos[0] * 11:
        raise CPFInvalidoOuDuplicadoError(
            "CPF inválido: sequências de dígitos idênticos não são permitidas."
        )
    return digitos


def mask_cpf_lgpd(cpf: str) -> str:
    """Aplica máscara de privacidade LGPD ao CPF no formato '***.XXX.XXX-**'."""
    digitos = _NON_DIGITS_RE.sub("", str(cpf))
    if len(digitos) != 11:
        return "***.***.***-**"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


def validate_birth_date(data_nascimento: str) -> str:
    """Valida a data de nascimento no formato DD/MM/AAAA."""
    if not isinstance(data_nascimento, str) or not data_nascimento.strip():
        raise ValorInvalidoError("Data de nascimento obrigatória no formato DD/MM/AAAA.")

    texto = data_nascimento.strip()
    try:
        parsed = datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValorInvalidoError(
            "Data de nascimento inválida. Utilize o formato DD/MM/AAAA (ex.: 15/08/1995)."
        ) from exc

    hoje = now_brt().date()
    if parsed > hoje or parsed < date(1900, 1, 1):
        raise ValorInvalidoError("Data de nascimento fora do intervalo válido.")
    return parsed.strftime("%d/%m/%Y")


def validate_non_empty_text(texto: str, campo: str) -> str:
    """Valida que um campo textual obrigatório não está vazio."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValorInvalidoError(f"O campo '{campo}' é obrigatório e não pode estar vazio.")
    return " ".join(texto.strip().split())


def generate_protocol() -> str:
    """Gera protocolo curto único baseado em UUID4 no padrão 'TX-XXXXXXXX'."""
    return f"TX-{uuid.uuid4().hex[:8].upper()}"


def now_brt() -> datetime:
    """Retorna o timestamp atual no fuso oficial de Brasília (UTC-3)."""
    return datetime.now(BRT_TIMEZONE)


def format_timestamp_brt(momento: datetime | None = None) -> str:
    """Formata timestamp no fuso de Brasília (ex.: '24/11/2026 09:55:10 BRT')."""
    dt = (momento or now_brt()).astimezone(BRT_TIMEZONE)
    return dt.strftime("%d/%m/%Y %H:%M:%S BRT")


__all__ = [
    "BRT_TIMEZONE",
    "TWO_PLACES",
    "quantize_brl",
    "parse_monetary_value",
    "format_brl",
    "sanitize_cpf",
    "mask_cpf_lgpd",
    "validate_birth_date",
    "validate_non_empty_text",
    "generate_protocol",
    "now_brt",
    "format_timestamp_brt",
]
