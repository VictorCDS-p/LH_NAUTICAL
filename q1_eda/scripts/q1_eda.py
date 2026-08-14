from pathlib import Path
import csv
from statistics import mean
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Caminho da raiz do projeto
ROOT = Path(__file__).resolve().parents[2]

# Caminho dos dados brutos
ORDERS_FILE = ROOT / "data" / "raw" / "orders.csv"


def main():

    # ========================================================
    # LEITURA DOS DADOS
    # ========================================================

    with open(
        ORDERS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as arquivo:

        reader = csv.DictReader(arquivo)
        rows = list(reader)

    # ========================================================
    # PARTE 1 — VISÃO GERAL DA TABELA
    # ========================================================

    # Quantidade total de linhas
    total_linhas = len(rows)

    # Quantidade total de colunas
    total_colunas = len(reader.fieldnames)

    # Datas de criação
    datas = [
        row["created_at"]
        for row in rows
        if row["created_at"]
    ]

    data_minima = min(datas)
    data_maxima = max(datas)

    # ========================================================
    # PARTE 2 — ANÁLISE DA COLUNA TOTAL
    # ========================================================

    totais = [
        float(row["total"])
        for row in rows
        if row["total"]
    ]

    valor_minimo = min(totais)
    valor_maximo = max(totais)
    valor_medio = mean(totais)

    # ========================================================
    # PARTE 3 — QUALIDADE DOS DADOS
    # ========================================================

    # Quantidade de valores nulos/vazios em created_at
    nulos_created_at = sum(
        1
        for row in rows
        if not row["created_at"]
    )

    # Quantidade de valores nulos/vazios em total
    nulos_total = sum(
        1
        for row in rows
        if not row["total"]
    )

    # ========================================================
    # VERIFICAÇÃO DE DATAS FUTURAS
    # ========================================================

    agora = datetime.now()

    datas_futuras = [
        row["created_at"]
        for row in rows
        if row["created_at"]
        and datetime.strptime(
            row["created_at"],
            "%Y-%m-%d %H:%M:%S"
        ) > agora
    ]

    quantidade_datas_futuras = len(datas_futuras)

    # ========================================================
    # RESULTADOS
    # ========================================================

    print("=" * 60)
    print("QUESTÃO 1 — EDA")
    print("=" * 60)

    print("\n[PARTE 1] VISÃO GERAL")
    print(f"Linhas: {total_linhas}")
    print(f"Colunas: {total_colunas}")
    print(f"created_at mínimo: {data_minima}")
    print(f"created_at máximo: {data_maxima}")

    print("\n[PARTE 2] ANÁLISE DE TOTAL")
    print(f"Valor mínimo: {valor_minimo:.2f}")
    print(f"Valor máximo: {valor_maximo:.2f}")
    print(f"Valor médio: {valor_medio:.2f}")

    print("\n[PARTE 3] QUALIDADE DOS DADOS")
    print(f"Nulos/vazios em created_at: {nulos_created_at}")
    print(f"Nulos/vazios em total: {nulos_total}")

    print("\n[VERIFICAÇÃO TEMPORAL]")
    print(
        f"Registros com created_at futuro: "
        f"{quantidade_datas_futuras}"
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
