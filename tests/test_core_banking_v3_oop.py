"""Suíte completa de testes unitários do Core Banking v3 // Object-Oriented Engine (UML)."""

from __future__ import annotations

import inspect
import io
import re
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

import main as app_main
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

_PROTOCOL_REGEX = re.compile(r"^TX-[0-9A-F]{8}$")
_BRT_TIMESTAMP_REGEX = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2} BRT$")


class TestContratosAbstratosEHeranca(unittest.TestCase):
    """Valida contratos abstratos (ABC) e árvore oficial de herança do UML DIO."""

    def test_transacao_eh_abstrata_e_nao_pode_ser_instanciada(self) -> None:
        self.assertTrue(inspect.isabstract(Transacao))
        with self.assertRaises(TypeError):
            Transacao()  # type: ignore[abstract]

    def test_subclasse_incompleta_de_transacao_lanca_type_error(self) -> None:
        class TransacaoIncompleta(Transacao):
            @property
            def valor(self) -> Decimal:
                return Decimal("10.00")

        with self.assertRaises(TypeError):
            TransacaoIncompleta()  # type: ignore[abstract]

    def test_hierarquia_de_heranca_uml(self) -> None:
        self.assertTrue(issubclass(PessoaFisica, Cliente))
        self.assertTrue(issubclass(ContaCorrente, Conta))
        self.assertTrue(issubclass(Deposito, Transacao))
        self.assertTrue(issubclass(Saque, Transacao))

    def test_hierarquia_de_excecoes_de_dominio(self) -> None:
        subclasses = (
            CPFInvalidoOuDuplicadoError,
            TitularNaoEncontradoError,
            ContaNaoEncontradaError,
            ValorInvalidoError,
            SaldoInsuficienteError,
            LimiteSaqueExcedidoError,
            LimiteDiarioSaquesError,
        )
        for exc_cls in subclasses:
            with self.subTest(exception=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, BankingOOPError))
                inst = exc_cls("erro de teste")
                self.assertTrue(inst.code)


class TestEncapsulamentoProperty(unittest.TestCase):
    """Garante proteção estrita de estado interno via @property e coleções imutáveis."""

    def setUp(self) -> None:
        self.cliente = PessoaFisica(
            nome="Mariana Silva",
            data_nascimento="20/03/1992",
            cpf="321.654.987-00",
            endereco="Rua das Flores, 42 - Centro - Curitiba/PR",
        )
        self.conta = ContaCorrente.nova_conta(cliente=self.cliente, numero=1)
        self.cliente.adicionar_conta(self.conta)

    def test_propriedades_conta_nao_podem_ser_sobrescritas(self) -> None:
        atributos_protegidos = (
            ("saldo", Decimal("999999.00")),
            ("numero", 99),
            ("agencia", "9999"),
            ("cliente", self.cliente),
            ("historico", Historico()),
            ("limite", Decimal("9999.00")),
            ("limite_saques", 99),
        )
        for attr, valor in atributos_protegidos:
            with self.subTest(atributo=attr):
                with self.assertRaises(AttributeError):
                    setattr(self.conta, attr, valor)

    def test_propriedades_cliente_e_pessoa_fisica_nao_podem_ser_sobrescritas(self) -> None:
        for attr, valor in (
            ("endereco", "Outro endereço"),
            ("contas", []),
            ("cpf", "99988877766"),
            ("nome", "Outro Nome"),
            ("data_nascimento", "01/01/2000"),
        ):
            with self.subTest(atributo=attr):
                with self.assertRaises(AttributeError):
                    setattr(self.cliente, attr, valor)

        self.assertIsInstance(self.cliente.contas, tuple)

    def test_historico_transacoes_eh_tupla_imutavel_e_copia_defensiva(self) -> None:
        self.cliente.realizar_transacao(self.conta, Deposito("100.00"))

        with self.assertRaises(AttributeError):
            self.conta.historico.transacoes = []  # type: ignore[misc]

        snapshot = self.conta.historico.transacoes
        self.assertIsInstance(snapshot, tuple)
        self.assertEqual(len(snapshot), 1)

        # Mutar o dicionário retornado na cópia não pode corromper o estado interno
        snapshot[0]["valor"] = Decimal("999999.00")
        self.assertEqual(self.conta.historico.transacoes[0]["valor"], Decimal("100.00"))


class TestPolimorfismoERegrasDeDominio(unittest.TestCase):
    """Valida polimorfismo em ContaCorrente.sacar, Cliente.realizar_transacao e Historico."""

    def setUp(self) -> None:
        self.cliente = PessoaFisica(
            nome="Carlos Eduardo",
            data_nascimento="10/11/1988",
            cpf="456.789.123-45",
            endereco="Av. Brasil, 200 - Savassi - Belo Horizonte/MG",
        )
        self.conta = ContaCorrente.nova_conta(cliente=self.cliente, numero=1)
        self.cliente.adicionar_conta(self.conta)

    def test_deposito_e_saque_polimorficos_registram_protocolo_e_historico(self) -> None:
        deposito = Deposito("1.000,00")
        saque = Saque("300,00")

        self.assertRegex(deposito.protocolo, _PROTOCOL_REGEX)
        self.assertRegex(saque.protocolo, _PROTOCOL_REGEX)
        self.assertNotEqual(deposito.protocolo, saque.protocolo)

        self.assertTrue(self.cliente.realizar_transacao(self.conta, deposito))
        self.assertTrue(self.cliente.realizar_transacao(self.conta, saque))
        self.assertEqual(self.conta.saldo, Decimal("700.00"))

        registros = self.conta.historico.transacoes
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0]["tipo"], "Deposito")
        self.assertEqual(registros[0]["saldo_resultante"], Decimal("1000.00"))
        self.assertRegex(registros[0]["data"], _BRT_TIMESTAMP_REGEX)
        self.assertEqual(registros[1]["tipo"], "Saque")
        self.assertEqual(registros[1]["saldo_resultante"], Decimal("700.00"))

    def test_conta_corrente_bloqueia_saque_acima_do_teto_500(self) -> None:
        self.cliente.realizar_transacao(self.conta, Deposito("2000.00"))

        with self.assertRaises(LimiteSaqueExcedidoError):
            self.cliente.realizar_transacao(self.conta, Saque("500.01"))

        self.assertEqual(self.conta.saldo, Decimal("2000.00"))
        self.assertEqual(len(self.conta.historico), 1)

    def test_polimorfismo_conta_base_permite_saque_acima_de_500(self) -> None:
        conta_base = Conta.nova_conta(cliente=self.cliente, numero=99)
        self.cliente.adicionar_conta(conta_base)
        self.cliente.realizar_transacao(conta_base, Deposito("2000.00"))

        self.assertTrue(self.cliente.realizar_transacao(conta_base, Saque("1200.00")))
        self.assertEqual(conta_base.saldo, Decimal("800.00"))

    def test_conta_corrente_bloqueia_apos_3_saques_no_historico(self) -> None:
        self.cliente.realizar_transacao(self.conta, Deposito("1000.00"))

        for _ in range(3):
            self.cliente.realizar_transacao(self.conta, Saque("100.00"))

        self.assertEqual(self.conta.saques_realizados, 3)

        with self.assertRaises(LimiteDiarioSaquesError):
            self.cliente.realizar_transacao(self.conta, Saque("50.00"))

        self.assertEqual(self.conta.saldo, Decimal("700.00"))
        self.assertEqual(len(self.conta.historico), 4)

    def test_bloqueio_saldo_insuficiente_nao_grava_no_historico(self) -> None:
        self.cliente.realizar_transacao(self.conta, Deposito("100.00"))

        with self.assertRaises(SaldoInsuficienteError):
            self.cliente.realizar_transacao(self.conta, Saque("150.00"))

        self.assertEqual(self.conta.saldo, Decimal("100.00"))
        self.assertEqual(len(self.conta.historico), 1)

    def test_registrar_nao_grava_historico_quando_conta_retorna_false(self) -> None:
        class ContaRecusaTudo(Conta):
            def depositar(self, valor: Decimal | int | float | str) -> bool:
                return False

            def sacar(self, valor: Decimal | int | float | str) -> bool:
                return False

        conta_mock = ContaRecusaTudo.nova_conta(cliente=self.cliente, numero=55)
        self.cliente.adicionar_conta(conta_mock)

        self.assertFalse(self.cliente.realizar_transacao(conta_mock, Deposito("100.00")))
        self.assertFalse(self.cliente.realizar_transacao(conta_mock, Saque("50.00")))
        self.assertEqual(len(conta_mock.historico), 0)

    def test_cliente_nao_pode_operar_conta_de_terceiro_ou_objeto_invalido(self) -> None:
        outro = PessoaFisica(
            nome="Outro Titular",
            data_nascimento="02/02/1991",
            cpf="987.654.321-09",
            endereco="Rua B, 10 - Centro - Recife/PE",
        )
        conta_terceiro = ContaCorrente.nova_conta(cliente=outro, numero=2)
        outro.adicionar_conta(conta_terceiro)

        with self.assertRaises(ContaNaoEncontradaError):
            self.cliente.realizar_transacao(conta_terceiro, Deposito("50.00"))

        with self.assertRaises(TypeError):
            self.cliente.realizar_transacao(self.conta, "nao_eh_transacao")  # type: ignore[arg-type]

    def test_gerar_relatorio_com_filtros_e_metricas(self) -> None:
        self.cliente.realizar_transacao(self.conta, Deposito("500.00"))
        self.cliente.realizar_transacao(self.conta, Deposito("250.50"))
        self.cliente.realizar_transacao(self.conta, Saque("100.25"))

        rel_total = self.conta.historico.gerar_relatorio()
        self.assertEqual(rel_total["total_operacoes"], 3)
        self.assertEqual(rel_total["total_depositos"], Decimal("750.50"))
        self.assertEqual(rel_total["quantidade_depositos"], 2)
        self.assertEqual(rel_total["total_saques"], Decimal("100.25"))
        self.assertEqual(rel_total["quantidade_saques"], 1)
        self.assertEqual(rel_total["saldo_liquido_periodo"], Decimal("650.25"))
        self.assertEqual(rel_total["ultimo_saldo"], Decimal("650.25"))

        rel_saques = self.conta.historico.gerar_relatorio(tipo_transacao="saque")
        self.assertEqual(rel_saques["total_operacoes"], 1)
        self.assertEqual(rel_saques["total_saques"], Decimal("100.25"))
        self.assertEqual(rel_saques["total_depositos"], Decimal("0.00"))


class TestDecimalPrecisionELGPD(unittest.TestCase):
    """Valida precisão aritmética Decimal (ROUND_HALF_UP) e privacidade LGPD."""

    def test_precisao_decimal_elimina_erro_ieee754_e_aplica_round_half_up(self) -> None:
        self.assertEqual(
            parse_monetary_value("0.1") + parse_monetary_value("0.2"),
            Decimal("0.30"),
        )
        self.assertEqual(parse_monetary_value("10.005"), Decimal("10.01"))
        self.assertEqual(parse_monetary_value("10.015"), Decimal("10.02"))
        self.assertEqual(parse_monetary_value("R$ 1.250,50"), Decimal("1250.50"))
        self.assertEqual(format_brl(Decimal("1250.50")), "R$ 1.250,50")

        for invalido in ("0", "-10", "abc", "", None, True, float("nan"), float("inf")):
            with self.subTest(valor=invalido):
                with self.assertRaises(ValorInvalidoError):
                    Deposito(invalido)  # type: ignore[arg-type]

    def test_mascara_lgpd_nunca_expoe_cpf_completo(self) -> None:
        cpf_raw = "12345678901"
        self.assertEqual(sanitize_cpf("123.456.789-01"), cpf_raw)
        self.assertEqual(mask_cpf_lgpd(cpf_raw), "***.456.789-**")

        repo = BankRepository()
        cliente = repo.cadastrar_cliente(
            nome="Lucas Andrade",
            data_nascimento="05/09/1996",
            cpf="123.456.789-01",
            endereco="Av. Paulista, 100 - Bela Vista - São Paulo/SP",
        )
        conta = repo.criar_conta_corrente(cpf_raw)

        saidas = (
            str(cliente),
            repr(cliente),
            str(conta),
            format_accounts_table(repo.contas),
            format_statement(conta),
        )
        for texto in saidas:
            self.assertIn("***.456.789-**", texto)
            self.assertNotIn(cpf_raw, texto)
            self.assertNotIn("123.456.789-01", texto)

        with self.assertRaises(CPFInvalidoOuDuplicadoError) as ctx:
            repo.cadastrar_cliente(
                nome="Outro",
                data_nascimento="01/01/1990",
                cpf=cpf_raw,
                endereco="Rua X, 1 - Centro - SP/SP",
            )
        self.assertNotIn(cpf_raw, str(ctx.exception))
        self.assertIn("***.456.789-**", str(ctx.exception))


class TestRepositoryCLIEModeDemo(unittest.TestCase):
    """Valida BankRepository, CLI blindada e execução automatizada do Modo Tour (--demo)."""

    def test_repository_sequencial_e_multiplas_contas_por_cpf(self) -> None:
        repo = BankRepository()
        repo.cadastrar_cliente(
            nome="Beatriz Costa",
            data_nascimento="12/04/1995",
            cpf="555.666.777-88",
            endereco="Rua A, 10 - Botafogo - Rio de Janeiro/RJ",
        )
        c1 = repo.criar_conta_corrente("55566677788")
        c2 = repo.criar_conta_corrente("555.666.777-88")

        self.assertEqual(c1.numero, 1)
        self.assertEqual(c2.numero, 2)
        self.assertEqual(c1.agencia, "0001")
        self.assertEqual(len(repo.contas), 2)
        self.assertEqual(len(repo.obter_cliente_por_cpf("55566677788").contas), 2)

        with self.assertRaises(TitularNaoEncontradoError):
            repo.criar_conta_corrente("999.888.777-66")

    def test_fluxo_completo_cli_e_protecao_contra_eof(self) -> None:
        entradas = iter(
            [
                "nu",
                "111.222.333-44",
                "Rafael Souza",
                "18/07/1993",
                "Rua Central, 50 - Centro - Florianópolis/SC",
                "nc",
                "11122233344",
                "d",
                "11122233344",
                "600,00",
                "s",
                "11122233344",
                "200,00",
                "e",
                "11122233344",
                "",
                "lc",
                "comando_inexistente",
                "q",
            ]
        )
        saidas: list[str] = []
        repo = BankRepository()

        exit_code = run_cli(
            repository=repo,
            input_fn=lambda _prompt: next(entradas),
            output_fn=saidas.append,
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(repo.clientes), 1)
        self.assertEqual(len(repo.contas), 1)
        self.assertEqual(repo.contas[0].saldo, Decimal("400.00"))

        texto_completo = "\n".join(saidas)
        self.assertIn("***.222.333-**", texto_completo)
        self.assertNotIn("11122233344", texto_completo)
        self.assertIn("OPÇÃO INVÁLIDA", texto_completo)

    def test_cli_encerra_limpo_com_eof_e_keyboard_interrupt(self) -> None:
        for exc in (EOFError, KeyboardInterrupt):
            with self.subTest(interrupcao=exc.__name__):
                saidas: list[str] = []

                def _raise(_prompt: str, err: type[BaseException] = exc) -> str:
                    raise err()

                code = run_cli(input_fn=_raise, output_fn=saidas.append)
                self.assertEqual(code, 0)
                self.assertIn("SESSÃO ENCERRADA COM SEGURANÇA", "\n".join(saidas))

    def test_modo_demo_funcao_e_entrypoint_cli_flag(self) -> None:
        linhas: list[str] = []
        resumo = run_demo_tour(output_fn=linhas.append)
        self.assertEqual(len(resumo["verificacoes"]), 10)
        self.assertEqual(resumo["saldo_final_conta_1"], Decimal("1010.31"))
        self.assertEqual(resumo["total_operacoes_conta_1"], 7)
        self.assertEqual(resumo["total_contas"], 2)

        output_texto = "\n".join(linhas)
        self.assertIn("MODO TOUR INTERATIVO", output_texto)
        self.assertIn("TOUR CONCLUÍDO COM 100% DE INTEGRIDADE", output_texto)
        self.assertIn("***.456.789-**", output_texto)
        self.assertNotIn("12345678901", output_texto)

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = app_main.main(["--demo"])
        self.assertEqual(exit_code, 0)
        self.assertIn("EXTRATO BANCÁRIO AUDITADO", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
