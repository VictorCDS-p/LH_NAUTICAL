from pathlib import Path
import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"

PRODUCT_NAME = "Bússola de Bordo 702"

TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-03-31"


# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

if not ENV_FILE.exists():
    raise FileNotFoundError(
        f"Arquivo .env não encontrado: {ENV_FILE}"
    )

# override=True garante que o .env do projeto
# sobrescreva variáveis de ambiente do Windows.
load_dotenv(ENV_FILE, override=True)


DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}


def validate_config():

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
# EXTRAÇÃO DOS DADOS
# ============================================================

def load_sales_data(connection):

    query = """
        SELECT
            DATE_TRUNC('month', o.placed_at)::date AS mes,
            SUM(oi.quantity) AS unidades_vendidas

        FROM orders AS o

        INNER JOIN order_items AS oi
            ON oi.order_id = o.id

        INNER JOIN product_variants AS pv
            ON pv.id = oi.product_variant_id

        INNER JOIN products AS p
            ON p.id = pv.product_id

        WHERE p.name = %s

        GROUP BY 1
        ORDER BY 1;
    """

    df = pd.read_sql_query(
        query,
        connection,
        params=(PRODUCT_NAME,)
    )

    if df.empty:
        raise ValueError(
            f"Nenhuma venda encontrada para: {PRODUCT_NAME}"
        )

    df["mes"] = pd.to_datetime(df["mes"])

    df["unidades_vendidas"] = (
        df["unidades_vendidas"]
        .astype(int)
    )

    return df


# ============================================================
# PREPARAÇÃO DA SÉRIE TEMPORAL
# ============================================================

def prepare_dataset(df):

    meses = pd.date_range(
        start=df["mes"].min(),
        end=df["mes"].max(),
        freq="MS"
    )

    df = (
        df.set_index("mes")
        .reindex(meses, fill_value=0)
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
# PREVISÃO — MÉDIA MÓVEL DE 3 MESES
# ============================================================

def generate_forecasts(df):

    train_end = pd.Timestamp(TRAIN_END)
    test_start = pd.Timestamp(TEST_START)
    test_end = pd.Timestamp(TEST_END)

    train = df[
        df["mes"] <= train_end
    ].copy()

    test = df[
        (df["mes"] >= test_start)
        & (df["mes"] <= test_end)
    ].copy()

    if len(train) < 3:
        raise ValueError(
            "O período de treinamento possui menos de 3 meses."
        )

    if test.empty:
        raise ValueError(
            "Nenhum dado encontrado no período de teste."
        )

    history = train["unidades_vendidas"].tolist()

    forecasts = []

    for _, row in test.iterrows():

        previsao = sum(history[-3:]) / 3

        forecasts.append(previsao)

        # O valor real só entra no histórico
        # depois que a previsão foi realizada.
        history.append(
            row["unidades_vendidas"]
        )

    test["previsao"] = forecasts

    return test


# ============================================================
# AVALIAÇÃO
# ============================================================

def calculate_mae(test):

    return (
        test["unidades_vendidas"]
        - test["previsao"]
    ).abs().mean()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - PREVISÃO DE DEMANDA")
    print("=" * 60)

    print(f"\nProduto: {PRODUCT_NAME}")
    print("Modelo: Média móvel dos últimos 3 meses")
    print("Treino: até 31/12/2025")
    print("Teste: 1º trimestre de 2026")

    validate_config()

    print(f"\nArquivo .env:")
    print(ENV_FILE)

    print("\nConectando ao PostgreSQL...")

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    print("Conexão realizada com sucesso.")

    try:

        df = load_sales_data(
            connection
        )

        df = prepare_dataset(
            df
        )

        test = generate_forecasts(
            df
        )

        mae = calculate_mae(
            test
        )

        # ----------------------------------------------------
        # RESULTADOS
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("RESULTADOS")
        print("=" * 60)

        for _, row in test.iterrows():

            mes = row["mes"].strftime("%m/%Y")
            real = int(row["unidades_vendidas"])
            previsao = row["previsao"]
            arredondada = round(previsao)

            print(
                f"{mes} | "
                f"Real: {real:>3} | "
                f"Previsão: {previsao:>6.2f} | "
                f"Arredondada: {arredondada:>3}"
            )

        previsao_total = round(
            test["previsao"].sum()
        )

        vendas_reais = int(
            test["unidades_vendidas"].sum()
        )

        print(f"\nMAE: {mae:.2f} unidades")

        print(
            f"Previsão total do 1º trimestre: "
            f"{previsao_total} unidades"
        )

        print(
            f"Vendas reais no 1º trimestre: "
            f"{vendas_reais} unidades"
        )

        print(
            f"Diferença entre previsão e realizado: "
            f"{vendas_reais - previsao_total} unidades"
        )

    finally:

        connection.close()

        print(
            "\nConexão com PostgreSQL encerrada."
        )


if __name__ == "__main__":
    main()