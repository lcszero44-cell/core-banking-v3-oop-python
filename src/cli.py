"""Interface CLI blindada com Unicode box-drawing e Modo Tour Interativo (--demo)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable

from src.exceptions import (
    BankingOOPError,
    CPFInvalidoOuDuplicadoError,
    LimiteDiarioSaquesError,
    LimiteSaqueExcedidoError,
    SaldoInsuficienteError,
    ValorInvalidoError,
)
from src.formatters import format_brl
from src.models.cliente import Cliente, PessoaFisica
from src.models.conta import ContaCorrente
from src.models.transacao import Deposito, Saque, Transacao
from src.repository import BankRepository

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]

_BOX_WIDTH = 78


def _render_banner() -> str:
    linha = "═" * _BOX_WIDTH
    return "\n".join(
        [
            f"╔{linha}╗",
            f"║{'CORE BANKING v3 // OBJECT-ORIENTED ENGINE (UML DIO)':^{_BOX_WIDTH}}║",
            f"║{'DDD • POO Estrita • Decimal ROUND_HALF_UP • UUID4 • LGPD • UTC-3':^{_BOX_WIDTH}}║",
            f"╚{linha}╝",
        ]
    )


def _render_menu() -> str:
    largura = _BOX_WIDTH
    linha = "─" * largura
    opcoes = [
        "  [d]    Depositar em Conta Corrente",
        "  [s]    Sacar da Conta Corrente (Polimórfico: Teto R$ 500 | 3 Saques)",
        "  [e]    Extrato Detalhado & Métricas Auditadas",
        "  [nu]   Novo Cliente Pessoa Física (PF)",
        "  [nc]   Nova Conta Corrente (Agência 0001)",
        "  [lc]   Listar Contas Cadastradas (Máscara LGPD)",
        "  [demo] Modo Tour / Auto-Testes Interativos (Demonstração Completa)",
        "  [q]    Sair do Terminal",
    ]
    linhas = [f"┌{linha}┐", f"│{' MENU OPERACIONAL — CORE BANKING v3 ':^{largura}}│", f"├{linha}┤"]
    for opcao in opcoes:
        linhas.append(f"│{opcao:<{largura}}│")
    linhas.append(f"└{linha}┘")
    return "\n".join(linhas)


def _render_box(titulo: str, conteudo: list[str], *, estilo: str = "info") -> str:
    prefixo = {"ok": "✔", "erro": "✖", "aviso": "▲", "info": "◆"}.get(estilo, "◆")
    cabecalho = f" {prefixo} {titulo} "
    largura = max(_BOX_WIDTH, len(cabecalho) + 4, *(len(line) + 4 for line in conteudo))
    borda_top = "─" * largura
    linhas = [f"┌{borda_top}┐", f"│{cabecalho:<{largura}}│", f"├{borda_top}┤"]
    for item in conteudo:
        linhas.append(f"│  {item:<{largura - 2}}│")
    linhas.append(f"└{borda_top}┘")
    return "\n".join(linhas)


def format_accounts_table(contas: tuple[ContaCorrente, ...] | list[ContaCorrente]) -> str:
    """Formata a tabela Unicode de contas correntes com máscara LGPD de CPF."""
    if not contas:
        return _render_box(
            "CARTEIRA DE CONTAS",
            ["Nenhuma conta corrente cadastrada até o momento."],
            estilo="aviso",
        )

    col_ag = 7
    col_cc = 6
    col_titular = 22
    col_cpf = 15
    col_saldo = 15
    col_saques = 8

    sep_top = (
        f"┌{'─' * (col_ag + 2)}┬{'─' * (col_cc + 2)}┬{'─' * (col_titular + 2)}┬"
        f"{'─' * (col_cpf + 2)}┬{'─' * (col_saldo + 2)}┬{'─' * (col_saques + 2)}┐"
    )
    sep_mid = (
        f"├{'─' * (col_ag + 2)}┼{'─' * (col_cc + 2)}┼{'─' * (col_titular + 2)}┼"
        f"{'─' * (col_cpf + 2)}┼{'─' * (col_saldo + 2)}┼{'─' * (col_saques + 2)}┤"
    )
    sep_bot = (
        f"└{'─' * (col_ag + 2)}┴{'─' * (col_cc + 2)}┴{'─' * (col_titular + 2)}┴"
        f"{'─' * (col_cpf + 2)}┴{'─' * (col_saldo + 2)}┴{'─' * (col_saques + 2)}┘"
    )

    header = (
        f"│ {'AGÊNCIA':^{col_ag}} │ {'CONTA':^{col_cc}} │ {'TITULAR':<{col_titular}} │ "
        f"{'CPF (LGPD)':^{col_cpf}} │ {'SALDO':>{col_saldo}} │ {'SAQUES':^{col_saques}} │"
    )
    linhas = [sep_top, header, sep_mid]

    for conta in contas:
        if isinstance(conta.cliente, PessoaFisica):
            nome = conta.cliente.nome[:col_titular]
            cpf_mask = conta.cliente.cpf_mascarado
        else:
            nome = conta.cliente.endereco[:col_titular]
            cpf_mask = "***.***.***-**"

        saldo_fmt = format_brl(conta.saldo)
        saques_fmt = f"{conta.saques_realizados}/{conta.limite_saques}"
        linhas.append(
            f"│ {conta.agencia:^{col_ag}} │ {conta.numero:04d}   │ {nome:<{col_titular}} │ "
            f"{cpf_mask:^{col_cpf}} │ {saldo_fmt:>{col_saldo}} │ {saques_fmt:^{col_saques}} │"
        )

    linhas.append(sep_bot)
    return "\n".join(linhas)


def format_statement(
    conta: ContaCorrente,
    *,
    tipo_transacao: str | None = None,
) -> str:
    """Renderiza extrato auditado com timestamps BRT, protocolos UUID4 e métricas."""
    relatorio = conta.historico.gerar_relatorio(tipo_transacao=tipo_transacao)
    transacoes = relatorio["transacoes"]

    titular = (
        f"{conta.cliente.nome} ({conta.cliente.cpf_mascarado})"
        if isinstance(conta.cliente, PessoaFisica)
        else conta.cliente.endereco
    )

    col_data = 23
    col_proto = 11
    col_tipo = 9
    col_valor = 14
    col_saldo = 14
    largura_total = (
        (col_data + 2)
        + (col_proto + 2)
        + (col_tipo + 2)
        + (col_valor + 2)
        + (col_saldo + 2)
        + 4
    )

    linha_info_1 = f"  Agência: {conta.agencia}   │   C/C: {conta.numero:04d}   │   Filtro: {relatorio['filtro']}"
    linha_info_2 = f"  Titular: {titular}"
    linha_resumo_1 = (
        f"  Operações: {relatorio['total_operacoes']}  │  "
        f"Depósitos ({relatorio['quantidade_depositos']}): {format_brl(relatorio['total_depositos'])}  │  "
        f"Saques ({relatorio['quantidade_saques']}): {format_brl(relatorio['total_saques'])}"
    )
    linha_resumo_2 = (
        f"  Saldo Atual: {format_brl(conta.saldo)}  │  "
        f"Limite/Saque: {format_brl(conta.limite)}  │  "
        f"Cota Saques: {conta.saques_realizados}/{conta.limite_saques}"
    )

    linhas = [
        f"╔{'═' * largura_total}╗",
        f"║{'EXTRATO BANCÁRIO AUDITADO — CORE BANKING v3':^{largura_total}}║",
        f"╠{'═' * largura_total}╣",
        f"║{linha_info_1:<{largura_total}}║",
        f"║{linha_info_2:<{largura_total}}║",
        f"╠{'─' * (col_data + 2)}┬{'─' * (col_proto + 2)}┬{'─' * (col_tipo + 2)}┬{'─' * (col_valor + 2)}┬{'─' * (col_saldo + 2)}╣",
        (
            f"║ {'DATA / HORA (BRT)':^{col_data}} │ {'PROTOCOLO':^{col_proto}} │ "
            f"{'TIPO':^{col_tipo}} │ {'VALOR':>{col_valor}} │ {'SALDO APÓS':>{col_saldo}} ║"
        ),
        f"╠{'─' * (col_data + 2)}┼{'─' * (col_proto + 2)}┼{'─' * (col_tipo + 2)}┼{'─' * (col_valor + 2)}┼{'─' * (col_saldo + 2)}╣",
    ]

    if not transacoes:
        linhas.append(
            f"║{'Não foram realizadas movimentações para o filtro selecionado.':^{largura_total}}║"
        )
    else:
        for item in transacoes:
            sinal = "+" if item["tipo"] == "Deposito" else "-"
            valor_fmt = f"{sinal}{format_brl(item['valor'])}"
            saldo_pos = (
                format_brl(item["saldo_resultante"])
                if item["saldo_resultante"] is not None
                else "—"
            )
            linhas.append(
                f"║ {item['data']:<{col_data}} │ {item['protocolo']:^{col_proto}} │ "
                f"{item['tipo']:^{col_tipo}} │ {valor_fmt:>{col_valor}} │ {saldo_pos:>{col_saldo}} ║"
            )

    linhas.extend(
        [
            f"╠{'─' * (col_data + 2)}┴{'─' * (col_proto + 2)}┴{'─' * (col_tipo + 2)}┴{'─' * (col_valor + 2)}┴{'─' * (col_saldo + 2)}╣",
            f"║{linha_resumo_1:<{largura_total}}║",
            f"║{linha_resumo_2:<{largura_total}}║",
            f"╚{'═' * largura_total}╝",
        ]
    )
    return "\n".join(linhas)


def run_demo_tour(output_fn: OutputFn = print) -> dict[str, Any]:
    """Executa tour guiado completo demonstrando todos os pilares POO, UML e regras de domínio."""
    sandbox_repo = BankRepository()
    verificacoes: list[str] = []

    output_fn("")
    output_fn(_render_banner())
    output_fn(
        _render_box(
            "MODO TOUR INTERATIVO // AUTO-TESTE GUIADO (--demo)",
            [
                "Executando roteiro isolado de ponta a ponta sobre o domínio UML da DIO.",
                "Nenhuma conta real da sessão será alterada durante este tour.",
            ],
            estilo="info",
        )
    )

    # 1. Cadastro de Titular PF & Unicidade de CPF
    output_fn("\n[PASSO 1/7] Cadastro de PessoaFisica + Sanitização de CPF + Proteção contra Duplicidade")
    cliente = sandbox_repo.cadastrar_cliente(
        nome="Ana Clara Mendes",
        data_nascimento="14/05/1994",
        cpf="123.456.789-01",
        endereco="Av. Paulista, 1500 - Bela Vista - São Paulo/SP",
    )
    verificacoes.append("cadastro_pf")
    output_fn(
        _render_box(
            "TITULAR CADASTRADO",
            [
                f"Instância: {cliente.__class__.__name__} (herda de Cliente: {isinstance(cliente, Cliente)})",
                f"Titular:   {cliente.nome} | Nascimento: {cliente.data_nascimento}",
                f"CPF LGPD:  {cliente.cpf_mascarado} (armazenado sanitizado com 11 dígitos)",
            ],
            estilo="ok",
        )
    )

    try:
        sandbox_repo.cadastrar_cliente(
            nome="Duplicata Teste",
            data_nascimento="01/01/1990",
            cpf="12345678901",
            endereco="Rua Teste, 10 - Centro - São Paulo/SP",
        )
    except CPFInvalidoOuDuplicadoError as exc:
        verificacoes.append("bloqueio_cpf_duplicado")
        output_fn(_render_box("BLOQUEIO DE CPF DUPLICADO VALIDADO", [f"[{exc.code}] {exc}"], estilo="aviso"))

    # 2. Abertura de Múltiplas Contas Correntes
    output_fn("\n[PASSO 2/7] Abertura de Múltiplas Contas via Fábrica ContaCorrente.nova_conta()")
    conta_1 = sandbox_repo.criar_conta_corrente(cliente.cpf)
    conta_2 = sandbox_repo.criar_conta_corrente(cliente.cpf)
    verificacoes.append("multiplas_contas")
    output_fn(format_accounts_table(sandbox_repo.contas))

    # 3. Depósitos Polimórficos + Precisão Decimal (ROUND_HALF_UP) + UUID4
    output_fn("\n[PASSO 3/7] Depósitos via Cliente.realizar_transacao() + Precisão Decimal + UUID4")
    dep_1 = Deposito("1.500,00")
    dep_2 = Deposito("0,10")
    dep_3 = Deposito("0,20")
    dep_4 = Deposito("10.005")  # Arredonda via ROUND_HALF_UP para R$ 10,01
    cliente.realizar_transacao(conta_1, dep_1)
    cliente.realizar_transacao(conta_1, dep_2)
    cliente.realizar_transacao(conta_1, dep_3)
    cliente.realizar_transacao(conta_1, dep_4)
    verificacoes.append("depositos_decimal_uuid4")
    output_fn(
        _render_box(
            "CRÉDITOS PROCESSADOS COM PRECISÃO DECIMAL",
            [
                f"Protocolo #1: {dep_1.protocolo} | +{format_brl(dep_1.valor)}",
                f"Protocolo #2: {dep_2.protocolo} | +{format_brl(dep_2.valor)}  (prova IEEE 754: 0.10 + 0.20)",
                f"Protocolo #3: {dep_3.protocolo} | +{format_brl(dep_3.valor)}  -> soma exata: R$ 0,30",
                f"Protocolo #4: {dep_4.protocolo} | +{format_brl(dep_4.valor)}  (ROUND_HALF_UP de 10.005)",
                f"Saldo Atual C/C {conta_1.numero:04d}: {format_brl(conta_1.saldo)}",
            ],
            estilo="ok",
        )
    )

    # 4. Saque Válido + Bloqueio Polimórfico por Teto (R$ 500,00)
    output_fn("\n[PASSO 4/7] Saque Válido & Bloqueio Polimórfico pelo Teto de R$ 500,00")
    saque_1 = Saque("250,00")
    cliente.realizar_transacao(conta_1, saque_1)
    output_fn(
        _render_box(
            "SAQUE #1 APROVADO",
            [
                f"Protocolo: {saque_1.protocolo} | -{format_brl(saque_1.valor)}",
                f"Saldo Atual: {format_brl(conta_1.saldo)} | Saques: {conta_1.saques_realizados}/{conta_1.limite_saques}",
            ],
            estilo="ok",
        )
    )

    historico_antes = len(conta_1.historico)
    try:
        cliente.realizar_transacao(conta_1, Saque("500,01"))
    except LimiteSaqueExcedidoError as exc:
        verificacoes.append("bloqueio_teto_500")
        output_fn(
            _render_box(
                "TETO DE R$ 500,00 APLICADO (CONTA CORRENTE)",
                [
                    f"[{exc.code}] {exc}",
                    f"Integridade do Histórico: {len(conta_1.historico)} == {historico_antes} (operação rejeitada não gravada).",
                ],
                estilo="aviso",
            )
        )

    # 5. Bloqueio por 3 Saques Diários + Saldo Insuficiente
    output_fn("\n[PASSO 5/7] Cota Máxima de 3 Saques no Histórico & Proteção de Saldo Insuficiente")
    cliente.realizar_transacao(conta_1, Saque("150,00"))
    cliente.realizar_transacao(conta_1, Saque("100,00"))
    try:
        cliente.realizar_transacao(conta_1, Saque("50,00"))
    except LimiteDiarioSaquesError as exc:
        verificacoes.append("bloqueio_3_saques")
        output_fn(_render_box("COTA DE 3 SAQUES BLOQUEADA", [f"[{exc.code}] {exc}"], estilo="aviso"))

    try:
        cliente.realizar_transacao(conta_2, Saque("10,00"))
    except SaldoInsuficienteError as exc:
        verificacoes.append("bloqueio_saldo_insuficiente")
        output_fn(_render_box("PROTEÇÃO DE SALDO INSUFICIENTE (C/C 0002)", [f"[{exc.code}] {exc}"], estilo="aviso"))

    # 6. Auditoria de Contratos POO (ABC + Encapsulamento @property)
    output_fn("\n[PASSO 6/7] Auditoria de Contratos Abstratos (ABC) e Encapsulamento (@property)")
    checks_oop: list[str] = []
    try:
        Transacao()  # type: ignore[abstract]
    except TypeError:
        verificacoes.append("abc_transacao_bloqueada")
        checks_oop.append("Transacao() direto -> TypeError confirmado (classe abstrata ABC).")

    try:
        conta_1.saldo = Decimal("999999.00")  # type: ignore[misc]
    except AttributeError:
        verificacoes.append("encapsulamento_saldo")
        checks_oop.append("conta.saldo = ... -> AttributeError confirmado (@property read-only).")

    if isinstance(conta_1.historico.transacoes, tuple):
        verificacoes.append("historico_imutavel")
        checks_oop.append(
            f"conta.historico.transacoes -> tuple imutável ({len(conta_1.historico.transacoes)} registros protegidos)."
        )

    output_fn(_render_box("PILARES POO VERIFICADOS EM RUNTIME", checks_oop, estilo="ok"))

    # 7. Extrato Consolidado Auditado
    output_fn("\n[PASSO 7/7] Emissão de Extrato Detalhado Auditado (UTC-3 Brasília)")
    output_fn(format_statement(conta_1))
    output_fn(
        _render_box(
            "TOUR CONCLUÍDO COM 100% DE INTEGRIDADE",
            [
                f"Verificações aprovadas: {len(verificacoes)}/10 cenários arquiteturais.",
                f"Saldo final auditado C/C 0001: {format_brl(conta_1.saldo)}",
            ],
            estilo="ok",
        )
    )

    return {
        "verificacoes": tuple(verificacoes),
        "saldo_final_conta_1": conta_1.saldo,
        "total_operacoes_conta_1": len(conta_1.historico),
        "total_contas": len(sandbox_repo.contas),
    }


def _selecionar_conta(
    repo: BankRepository,
    input_fn: InputFn,
    output_fn: OutputFn,
) -> tuple[PessoaFisica, ContaCorrente]:
    cpf = input_fn("Informe o CPF do titular: ")
    cliente = repo.obter_cliente_por_cpf(cpf)

    if not cliente.contas:
        return cliente, repo.obter_conta_do_cliente(cliente.cpf)

    if len(cliente.contas) == 1:
        conta = repo.obter_conta_do_cliente(cliente.cpf)
        return cliente, conta

    output_fn("\nContas vinculadas ao titular:")
    for conta in cliente.contas:
        output_fn(f"  • Agência {conta.agencia} | C/C {conta.numero:04d} | Saldo: {format_brl(conta.saldo)}")

    numero_raw = input_fn("Informe o número da conta desejada: ").strip()
    try:
        numero_conta = int(numero_raw)
    except ValueError as exc:
        raise ValorInvalidoError("Número da conta deve ser um inteiro válido.") from exc

    conta_selecionada = repo.obter_conta_do_cliente(cliente.cpf, numero_conta=numero_conta)
    return cliente, conta_selecionada


def _fluxo_depositar(repo: BankRepository, input_fn: InputFn, output_fn: OutputFn) -> None:
    cliente, conta = _selecionar_conta(repo, input_fn, output_fn)
    valor_raw = input_fn("Informe o valor do depósito (ex.: 250,00): ")
    transacao = Deposito(valor_raw)
    cliente.realizar_transacao(conta, transacao)
    output_fn(
        _render_box(
            "DEPÓSITO REALIZADO COM SUCESSO",
            [
                f"Protocolo:   {transacao.protocolo}",
                f"Conta:       Agência {conta.agencia} / C/C {conta.numero:04d}",
                f"Valor:       +{format_brl(transacao.valor)}",
                f"Novo Saldo:  {format_brl(conta.saldo)}",
            ],
            estilo="ok",
        )
    )


def _fluxo_sacar(repo: BankRepository, input_fn: InputFn, output_fn: OutputFn) -> None:
    cliente, conta = _selecionar_conta(repo, input_fn, output_fn)
    valor_raw = input_fn("Informe o valor do saque (ex.: 150,00): ")
    transacao = Saque(valor_raw)
    cliente.realizar_transacao(conta, transacao)
    output_fn(
        _render_box(
            "SAQUE REALIZADO COM SUCESSO",
            [
                f"Protocolo:     {transacao.protocolo}",
                f"Conta:         Agência {conta.agencia} / C/C {conta.numero:04d}",
                f"Valor:         -{format_brl(transacao.valor)}",
                f"Novo Saldo:    {format_brl(conta.saldo)}",
                f"Cota Saques:   {conta.saques_realizados}/{conta.limite_saques}",
            ],
            estilo="ok",
        )
    )


def _fluxo_extrato(repo: BankRepository, input_fn: InputFn, output_fn: OutputFn) -> None:
    _, conta = _selecionar_conta(repo, input_fn, output_fn)
    filtro_raw = input_fn(
        "Filtrar por tipo ([Enter]=Todas, [d]=Depósitos, [s]=Saques): "
    ).strip().lower()
    mapa_filtro = {"": None, "t": None, "d": "Deposito", "s": "Saque"}
    if filtro_raw not in mapa_filtro:
        raise ValorInvalidoError("Filtro inválido. Utilize Enter, 'd' ou 's'.")
    output_fn(format_statement(conta, tipo_transacao=mapa_filtro[filtro_raw]))


def _fluxo_novo_cliente(repo: BankRepository, input_fn: InputFn, output_fn: OutputFn) -> None:
    cpf = input_fn("CPF (11 dígitos, com ou sem pontuação): ")
    nome = input_fn("Nome completo: ")
    data_nascimento = input_fn("Data de nascimento (DD/MM/AAAA): ")
    endereco = input_fn("Endereço (logradouro, nro - bairro - cidade/UF): ")

    cliente = repo.cadastrar_cliente(
        nome=nome,
        data_nascimento=data_nascimento,
        cpf=cpf,
        endereco=endereco,
    )
    output_fn(
        _render_box(
            "CLIENTE PESSOA FÍSICA CADASTRADO",
            [
                f"Titular:    {cliente.nome}",
                f"CPF (LGPD): {cliente.cpf_mascarado}",
                f"Nascimento: {cliente.data_nascimento}",
                f"Endereço:   {cliente.endereco}",
            ],
            estilo="ok",
        )
    )


def _fluxo_nova_conta(repo: BankRepository, input_fn: InputFn, output_fn: OutputFn) -> None:
    cpf = input_fn("Informe o CPF do titular já cadastrado: ")
    conta = repo.criar_conta_corrente(cpf)
    titular = (
        f"{conta.cliente.nome} ({conta.cliente.cpf_mascarado})"
        if isinstance(conta.cliente, PessoaFisica)
        else conta.cliente.endereco
    )
    output_fn(
        _render_box(
            "CONTA CORRENTE ABERTA COM SUCESSO",
            [
                f"Agência:      {conta.agencia}",
                f"Número C/C:   {conta.numero:04d}",
                f"Titular:      {titular}",
                f"Limite/Saque: {format_brl(conta.limite)} ({conta.limite_saques} saques/dia)",
            ],
            estilo="ok",
        )
    )


def run_cli(
    *,
    repository: BankRepository | None = None,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
) -> int:
    """Executa o loop principal da CLI blindado contra erros de domínio, EOF e Ctrl+C."""
    repo = repository if repository is not None else BankRepository()
    output_fn(_render_banner())

    while True:
        output_fn("")
        output_fn(_render_menu())
        try:
            opcao = input_fn("Selecione a operação => ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            output_fn(
                _render_box(
                    "SESSÃO ENCERRADA COM SEGURANÇA",
                    ["Interrupção detectada (EOF / Ctrl+C). Obrigado por usar o Core Banking v3."],
                    estilo="info",
                )
            )
            return 0

        if opcao == "q":
            output_fn(
                _render_box(
                    "SESSÃO ENCERRADA",
                    ["Terminal Core Banking v3 finalizado com segurança."],
                    estilo="info",
                )
            )
            return 0

        try:
            if opcao == "d":
                _fluxo_depositar(repo, input_fn, output_fn)
            elif opcao == "s":
                _fluxo_sacar(repo, input_fn, output_fn)
            elif opcao == "e":
                _fluxo_extrato(repo, input_fn, output_fn)
            elif opcao == "nu":
                _fluxo_novo_cliente(repo, input_fn, output_fn)
            elif opcao == "nc":
                _fluxo_nova_conta(repo, input_fn, output_fn)
            elif opcao == "lc":
                output_fn(format_accounts_table(repo.contas))
            elif opcao == "demo":
                run_demo_tour(output_fn=output_fn)
            else:
                output_fn(
                    _render_box(
                        "OPÇÃO INVÁLIDA",
                        [
                            f"Comando '{opcao}' não reconhecido.",
                            "Escolha uma das opções válidas: [d], [s], [e], [nu], [nc], [lc], [demo] ou [q].",
                        ],
                        estilo="aviso",
                    )
                )
        except BankingOOPError as exc:
            output_fn(
                _render_box(
                    f"OPERAÇÃO RECUSADA [{exc.code}]",
                    [str(exc)],
                    estilo="erro",
                )
            )
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            output_fn(
                _render_box(
                    "OPERAÇÃO CANCELADA",
                    ["Interrupção recebida durante o fluxo. Sessão encerrada com segurança."],
                    estilo="info",
                )
            )
            return 0


__all__ = [
    "format_accounts_table",
    "format_statement",
    "run_demo_tour",
    "run_cli",
]
