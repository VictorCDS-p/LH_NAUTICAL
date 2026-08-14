from pathlib import Path
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv


# ============================================================
# LH NAUTICAL - QUESTÃO 6
# PREVISÃO DE DEMANDA
# ============================================================

# ------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"

PRODUCT_NAME = "Bússola de Bordo 702"

TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-03-31"

WINDOW_SIZE = 3


# ------------------------------------------------------------
# CONFIGURAÇÃO DO AMBIENTE
# ------------------------------------------------------------

if not ENV_FILE.exists():
    raise FileNotFoundError(
        f"Arquivo .env não encontrado: {ENV_FILE}"
    )

load_dotenv(
    ENV_FILE,
    override=True
)


# ------------------------------------------------------------
# CONFIGURAÇÃO DO POSTGRESQL
# ------------------------------------------------------------

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}


# ============================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ============================================================

def validate_config():
    """
    Verifica se todas as variáveis necessárias para conexão
    com o PostgreSQL estão configuradas.
    """

    missing = [
        key
        for key, value in DB_CONFIG.items()
        if not value
    ]

    if missing:
        raise EnvironmentError(
            "Variáveis ausentes no .env: "
            + ", ".join(missing)
        )


# ============================================================
# EXTRAÇÃO E UNIFICAÇÃO DOS DADOS
# ============================================================

def load_sales_data(connection):
    """
    Extrai e unifica os dados necessários para a previsão.

    Relacionamentos utilizados:

    products
        ↓
    product_variants
        ↓
    order_items
        ↓
    orders

    O resultado contém a quantidade total de unidades
    vendidas por mês para o produto analisado.
    """

    query = """
        SELECT
            DATE_TRUNC(
                'month',
                o.placed_at
            )::date AS mes,

            SUM(
                oi.quantity
            ) AS unidades_vendidas

        FROM orders AS o

        INNER JOIN order_items AS oi
            ON oi.order_id = o.id

        INNER JOIN product_variants AS pv
            ON pv.id = oi.product_variant_id

        INNER JOIN products AS p
            ON p.id = pv.product_id

        WHERE p.name = %s

        GROUP BY
            DATE_TRUNC(
                'month',
                o.placed_at
            )::date

        ORDER BY
            mes;
    """

    df = pd.read_sql_query(
        query,
        connection,
        params=(PRODUCT_NAME,)
    )

    if df.empty:
        raise ValueError(
            f"Nenhuma venda encontrada para o produto: "
            f"{PRODUCT_NAME}"
        )

    df["mes"] = pd.to_datetime(
        df["mes"]
    )

    df["unidades_vendidas"] = (
        df["unidades_vendidas"]
        .astype(int)
    )

    return df


# ============================================================
# PREPARAÇÃO DA SÉRIE TEMPORAL
# ============================================================

def prepare_dataset(df):
    """
    Garante que todos os meses existentes entre o primeiro
    e o último registro estejam presentes na série.

    Meses sem vendas são considerados como zero.
    """

    meses = pd.date_range(
        start=df["mes"].min(),
        end=df["mes"].max(),
        freq="MS"
    )

    df = (
        df
        .set_index("mes")
        .reindex(
            meses,
            fill_value=0
        )
        .rename_axis("mes")
        .reset_index()
    )

    df["unidades_vendidas"] = (
        df["unidades_vendidas"]
        .fillna(0)
        .astype(int)
    )

    return df


# ============================================================
# PREVISÃO - MÉDIA MÓVEL DE 3 MESES
# ============================================================

def generate_forecasts(df):
    """
    Gera previsões mensais utilizando a média das vendas
    dos três meses anteriores à previsão.

    O valor real do mês previsto somente é adicionado ao
    histórico depois que sua previsão foi calculada.
    Dessa forma, o valor do próprio mês não influencia
    sua previsão.
    """

    train_end = pd.Timestamp(
        TRAIN_END
    )

    test_start = pd.Timestamp(
        TEST_START
    )

    test_end = pd.Timestamp(
        TEST_END
    )

    # --------------------------------------------------------
    # Separação entre treino e teste
    # --------------------------------------------------------

    train = df[
        df["mes"] <= train_end
    ].copy()

    test = df[
        (df["mes"] >= test_start)
        & (df["mes"] <= test_end)
    ].copy()

    if len(train) < WINDOW_SIZE:
        raise ValueError(
            "O período de treinamento possui menos de "
            f"{WINDOW_SIZE} meses."
        )

    if test.empty:
        raise ValueError(
            "Nenhum dado encontrado no período de teste."
        )

    # --------------------------------------------------------
    # Histórico inicial
    # --------------------------------------------------------

    history = (
        train["unidades_vendidas"]
        .tolist()
    )

    forecasts = []

    # --------------------------------------------------------
    # Previsão mês a mês
    # --------------------------------------------------------

    for _, row in test.iterrows():

        # Média dos três últimos meses disponíveis.
        previsao = (
            sum(history[-WINDOW_SIZE:])
            / WINDOW_SIZE
        )

        forecasts.append(
            previsao
        )

        # O valor real só é incorporado ao histórico
        # depois que a previsão do mês foi realizada.
        history.append(
            row["unidades_vendidas"]
        )

    test["previsao"] = forecasts

    return test


# ============================================================
# MÉTRICA DE AVALIAÇÃO
# ============================================================

def calculate_mae(test):
    """
    Calcula o Mean Absolute Error (MAE).

    MAE = média do erro absoluto entre o valor real
    e o valor previsto.
    """

    return (
        test["unidades_vendidas"]
        - test["previsao"]
    ).abs().mean()


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - QUESTÃO 6")
    print("PREVISÃO DE DEMANDA")
    print("=" * 60)

    print(f"\nProduto: {PRODUCT_NAME}")
    print(
        "Modelo: Média móvel dos últimos "
        f"{WINDOW_SIZE} meses"
    )
    print(f"Treino: até {TRAIN_END}")
    print(
        f"Teste: {TEST_START} a {TEST_END}"
    )

    # --------------------------------------------------------
    # Validação da configuração
    # --------------------------------------------------------

    validate_config()

    # --------------------------------------------------------
    # Conexão com PostgreSQL
    # --------------------------------------------------------

    print("\nConectando ao PostgreSQL...")

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    print(
        "Conexão realizada com sucesso."
    )

    try:

        # ----------------------------------------------------
        # Extração dos dados
        # ----------------------------------------------------

        df = load_sales_data(
            connection
        )

        print(
            f"\nRegistros mensais extraídos: "
            f"{len(df)}"
        )

        # ----------------------------------------------------
        # Preparação da série temporal
        # ----------------------------------------------------

        df = prepare_dataset(
            df
        )

        # ----------------------------------------------------
        # Geração das previsões
        # ----------------------------------------------------

        test = generate_forecasts(
            df
        )

        # ----------------------------------------------------
        # Avaliação do modelo
        # ----------------------------------------------------

        mae = calculate_mae(
            test
        )

        # ----------------------------------------------------
        # RESULTADOS
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("RESULTADOS")
        print("=" * 60)

        print(
            f"\n{'Mês':<10}"
            f"{'Real':>10}"
            f"{'Previsão':>15}"
            f"{'Arredondada':>15}"
        )

        print("-" * 50)

        for _, row in test.iterrows():

            mes = row["mes"].strftime(
                "%m/%Y"
            )

            real = int(
                row["unidades_vendidas"]
            )

            previsao = row["previsao"]

            arredondada = round(
                previsao
            )

            print(
                f"{mes:<10}"
                f"{real:>10}"
                f"{previsao:>15.2f}"
                f"{arredondada:>15}"
            )

        # ----------------------------------------------------
        # Totais
        # ----------------------------------------------------

        previsao_total = round(
            test["previsao"].sum()
        )

        vendas_reais = int(
            test["unidades_vendidas"].sum()
        )

        diferenca = (
            vendas_reais
            - previsao_total
        )

        print("\n" + "-" * 50)

        print(
            f"MAE: "
            f"{mae:.2f} unidades"
        )

        print(
            "Previsão total do 1º trimestre: "
            f"{previsao_total} unidades"
        )

        print(
            "Vendas reais no 1º trimestre: "
            f"{vendas_reais} unidades"
        )

        print(
            "Diferença entre previsão e realizado: "
            f"{diferenca} unidades"
        )

    finally:

        connection.close()

        print(
            "\nConexão com PostgreSQL encerrada."
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()