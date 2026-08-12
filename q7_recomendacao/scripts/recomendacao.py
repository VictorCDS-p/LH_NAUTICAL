import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"

load_dotenv(ENV_FILE)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

REFERENCE_PRODUCT = "Motor de Popa 1949"
TOP_N = 5


# ============================================================
# EXTRAÇÃO
# ============================================================

def load_interactions(connection):

    query = """
        SELECT DISTINCT
            o.customer_id AS id_cliente,
            p.id AS id_produto
        FROM orders AS o

        INNER JOIN order_items AS oi
            ON oi.order_id = o.id

        INNER JOIN product_variants AS pv
            ON pv.id = oi.product_variant_id

        INNER JOIN products AS p
            ON p.id = pv.product_id

        WHERE o.customer_id IS NOT NULL
        ORDER BY o.customer_id, p.id;
    """

    return pd.read_sql_query(
        query,
        connection
    )


def load_products(connection):

    query = """
        SELECT
            id,
            name
        FROM products
        ORDER BY id;
    """

    return pd.read_sql_query(
        query,
        connection
    )


# ============================================================
# MATRIZ USUÁRIO × PRODUTO
# ============================================================

def build_matrix(interactions):

    matrix = pd.crosstab(
        interactions["id_cliente"],
        interactions["id_produto"]
    )

    # Presença/ausência.
    matrix = (
        matrix
        .clip(upper=1)
        .astype(int)
    )

    return matrix


# ============================================================
# SIMILARIDADE DE COSSENO
# ============================================================

def cosine_similarity(matrix):

    # Cada coluna representa um produto.
    # Portanto, calculamos a similaridade entre as colunas.

    product_matrix = matrix.T.to_numpy(
        dtype=float
    )

    norms = np.linalg.norm(
        product_matrix,
        axis=1
    )

    similarity = (
        product_matrix @ product_matrix.T
    )

    denominator = np.outer(
        norms,
        norms
    )

    similarity = np.divide(
        similarity,
        denominator,
        out=np.zeros_like(similarity),
        where=denominator != 0
    )

    return similarity


# ============================================================
# RANKING
# ============================================================

def generate_ranking(
    matrix,
    similarity,
    products
):

    product_ids = matrix.columns.tolist()

    reference = products[
        products["name"] == REFERENCE_PRODUCT
    ]

    if reference.empty:
        raise ValueError(
            f'Produto "{REFERENCE_PRODUCT}" não encontrado.'
        )

    reference_id = int(
        reference.iloc[0]["id"]
    )

    if reference_id not in product_ids:
        raise ValueError(
            f'Produto "{REFERENCE_PRODUCT}" não possui interações.'
        )

    reference_index = product_ids.index(
        reference_id
    )

    scores = similarity[
        reference_index
    ]

    ranking = pd.DataFrame({
        "id_produto": product_ids,
        "similaridade": scores
    })

    # Remove o próprio produto.
    ranking = ranking[
        ranking["id_produto"] != reference_id
    ]

    ranking = ranking.merge(
        products,
        left_on="id_produto",
        right_on="id",
        how="left"
    )

    ranking = (
        ranking
        .sort_values(
            "similaridade",
            ascending=False
        )
        .head(TOP_N)
    )

    return ranking[
        [
            "id_produto",
            "name",
            "similaridade"
        ]
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - SISTEMA DE RECOMENDAÇÃO")
    print("=" * 60)

    print(
        f"\nProduto de referência: "
        f"{REFERENCE_PRODUCT}"
    )

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    try:

        print(
            "\nConexão realizada com sucesso."
        )

        # ----------------------------------------------------
        # Interações
        # ----------------------------------------------------

        interactions = load_interactions(
            connection
        )

        print(
            f"Interações únicas: "
            f"{len(interactions):,}".replace(",", ".")
        )

        # ----------------------------------------------------
        # Produtos
        # ----------------------------------------------------

        products = load_products(
            connection
        )

        print(
            f"Produtos: {len(products)}"
        )

        # ----------------------------------------------------
        # Matriz
        # ----------------------------------------------------

        matrix = build_matrix(
            interactions
        )

        print(
            f"Matriz usuário × produto: "
            f"{matrix.shape[0]} clientes × "
            f"{matrix.shape[1]} produtos"
        )

        # ----------------------------------------------------
        # Similaridade
        # ----------------------------------------------------

        similarity = cosine_similarity(
            matrix
        )

        # ----------------------------------------------------
        # Ranking
        # ----------------------------------------------------

        ranking = generate_ranking(
            matrix,
            similarity,
            products
        )

        print("\n" + "=" * 60)
        print("TOP 5 PRODUTOS MAIS SIMILARES")
        print("=" * 60)

        for position, (_, row) in enumerate(
            ranking.iterrows(),
            start=1
        ):

            print(
                f"{position}. "
                f"{row['name']} | "
                f"Similaridade: "
                f"{row['similaridade']:.4f}"
            )

        # ----------------------------------------------------
        # Maior similaridade
        # ----------------------------------------------------

        first = ranking.iloc[0]

        print(
            f"\nMaior similaridade: "
            f"{first['name']}"
        )

        print(
            f"Score: "
            f"{first['similaridade']:.4f}"
        )

    finally:

        connection.close()

        print(
            "\nConexão com PostgreSQL encerrada."
        )


if __name__ == "__main__":
    main()