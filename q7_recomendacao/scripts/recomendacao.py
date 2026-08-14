import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv


# ============================================================
# LH NAUTICAL - QUESTÃO 7
# SISTEMA DE RECOMENDAÇÃO
# ============================================================


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"

REFERENCE_PRODUCT = "Motor de Popa 1949"
TOP_N = 5


# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

load_dotenv(
    ENV_FILE,
    override=True
)

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
# EXTRAÇÃO DOS DADOS
# ============================================================

def load_interactions(connection):
    """
    Extrai as interações únicas entre clientes e produtos.

    Cadeia de relacionamento:

    orders
        ↓
    order_items
        ↓
    product_variants
        ↓
    products

    Cada combinação cliente-produto aparece apenas uma vez,
    independentemente da quantidade ou frequência da compra.
    """

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

        ORDER BY
            o.customer_id,
            p.id;
    """

    return pd.read_sql_query(
        query,
        connection
    )


def load_products(connection):
    """
    Carrega o identificador e o nome dos produtos para
    posteriormente traduzir o ranking de IDs para nomes.
    """

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
    """
    Constrói a matriz binária Usuário × Produto.

    Linhas:
        id_cliente

    Colunas:
        id_produto

    Valores:
        1 = cliente comprou o produto
        0 = cliente não comprou o produto

    A quantidade comprada é desconsiderada.
    """

    matrix = pd.crosstab(
        interactions["id_cliente"],
        interactions["id_produto"]
    )

    # Garante representação binária:
    # qualquer ocorrência de compra = 1.
    matrix = (
        matrix
        .clip(upper=1)
        .astype(int)
    )

    return matrix


# ============================================================
# SIMILARIDADE DE COSSENO
# ============================================================

def calculate_cosine_similarity(matrix):
    """
    Calcula a Similaridade de Cosseno entre os produtos.

    A matriz original possui:

        linhas  = clientes
        colunas = produtos

    Para comparar produtos, as colunas são transformadas
    em vetores, sendo cada vetor representado pelo conjunto
    de clientes que compraram aquele produto.
    """

    product_matrix = matrix.T.to_numpy(
        dtype=float
    )

    # Norma de cada vetor de produto.
    norms = np.linalg.norm(
        product_matrix,
        axis=1
    )

    # Produto escalar entre todos os pares de produtos.
    dot_product = (
        product_matrix
        @ product_matrix.T
    )

    # Produto das normas de cada par.
    denominator = np.outer(
        norms,
        norms
    )

    # Similaridade de cosseno:
    #
    # cos(A,B) =
    # (A . B) / (||A|| * ||B||)
    #
    # Produtos sem interações recebem similaridade 0.
    similarity = np.divide(
        dot_product,
        denominator,
        out=np.zeros_like(dot_product),
        where=denominator != 0
    )

    return similarity


# ============================================================
# RANKING DOS PRODUTOS
# ============================================================

def generate_ranking(
    matrix,
    similarity,
    products
):
    """
    Gera o ranking dos produtos mais similares ao produto
    de referência.
    """

    product_ids = matrix.columns.tolist()

    # --------------------------------------------------------
    # Identificação do produto de referência
    # --------------------------------------------------------

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
            f'Produto "{REFERENCE_PRODUCT}" '
            "não possui interações de compra."
        )

    # --------------------------------------------------------
    # Localização do produto na matriz de similaridade
    # --------------------------------------------------------

    reference_index = product_ids.index(
        reference_id
    )

    scores = similarity[
        reference_index
    ]

    # --------------------------------------------------------
    # Criação do ranking
    # --------------------------------------------------------

    ranking = pd.DataFrame({
        "id_produto": product_ids,
        "similaridade": scores
    })

    # Remove o próprio produto do ranking.
    ranking = ranking[
        ranking["id_produto"] != reference_id
    ]

    # Adiciona o nome dos produtos.
    ranking = ranking.merge(
        products,
        left_on="id_produto",
        right_on="id",
        how="left"
    )

    # Ordena pela maior similaridade.
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
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - QUESTÃO 7")
    print("SISTEMA DE RECOMENDAÇÃO")
    print("=" * 60)

    print(
        f"\nProduto de referência: "
        f"{REFERENCE_PRODUCT}"
    )

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    validate_config()

    # --------------------------------------------------------
    # Conexão
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
        # Extração das interações
        # ----------------------------------------------------

        interactions = load_interactions(
            connection
        )

        print(
            f"\nInterações únicas: "
            f"{len(interactions):,}".replace(",", ".")
        )

        # ----------------------------------------------------
        # Catálogo de produtos
        # ----------------------------------------------------

        products = load_products(
            connection
        )

        print(
            f"Produtos cadastrados: "
            f"{len(products)}"
        )

        # ----------------------------------------------------
        # Matriz Usuário × Produto
        # ----------------------------------------------------

        matrix = build_matrix(
            interactions
        )

        print(
            "\nMatriz Usuário × Produto:"
        )

        print(
            f"    Clientes: {matrix.shape[0]}"
        )

        print(
            f"    Produtos: {matrix.shape[1]}"
        )

        # ----------------------------------------------------
        # Similaridade
        # ----------------------------------------------------

        similarity = calculate_cosine_similarity(
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

        # ----------------------------------------------------
        # Resultado
        # ----------------------------------------------------

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


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()