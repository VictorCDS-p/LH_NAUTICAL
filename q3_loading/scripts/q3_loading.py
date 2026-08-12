from pathlib import Path
import csv
import os

import psycopg2
from dotenv import load_dotenv


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent

CSV_DIR = ROOT / "data" / "raw"
ENV_FILE = ROOT / ".env"


# ============================================================
# CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE
# ============================================================

load_dotenv(ENV_FILE)


# ============================================================
# CONFIGURAÇÃO DO POSTGRESQL
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}


# ============================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ============================================================

def validate_config():
    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing:
        raise EnvironmentError(
            "Variáveis de ambiente não configuradas: "
            + ", ".join(missing)
        )


# ============================================================
# LEITURA DO CABEÇALHO DO CSV
# ============================================================

def get_columns(csv_file):

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        columns = next(reader)

    return columns


# ============================================================
# CONTAGEM DE LINHAS
# ============================================================

def count_csv_rows(csv_file):

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        # Ignora o cabeçalho
        next(reader, None)

        return sum(1 for _ in reader)


# ============================================================
# CARREGAMENTO DE UMA TABELA
# ============================================================

def load_table(connection, csv_file):

    table_name = csv_file.stem

    columns = get_columns(csv_file)

    columns_sql = ", ".join(
        f'"{column}"'
        for column in columns
    )

    copy_sql = f"""
        COPY "{table_name}" ({columns_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            ENCODING 'UTF8'
        )
    """

    with connection.cursor() as cursor:

        with open(
            csv_file,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            cursor.copy_expert(
                copy_sql,
                file
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - CARREGAMENTO DOS CSVs")
    print("=" * 60)

    validate_config()

    print("\nDiretório dos CSVs:")
    print(CSV_DIR)

    csv_files = sorted(
        CSV_DIR.glob("*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em: {CSV_DIR}"
        )

    print(
        f"\nCSV encontrados: {len(csv_files)}"
    )

    print("\nConectando ao PostgreSQL...")

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    connection.set_client_encoding("UTF8")

    print("Conexão realizada com sucesso.\n")

    total_carregado = 0

    try:

        for index, csv_file in enumerate(
            csv_files,
            start=1
        ):

            table_name = csv_file.stem

            print(
                f"[{index}/{len(csv_files)}] "
                f"Carregando: {table_name}.csv"
            )

            linhas = count_csv_rows(
                csv_file
            )

            print(
                f"    Linhas no CSV: "
                f"{linhas:,}".replace(",", ".")
            )

            load_table(
                connection,
                csv_file
            )

            # Confirma a tabela imediatamente
            connection.commit()

            total_carregado += linhas

            print(
                f"    OK - {table_name} carregada"
            )

            print()

        print("=" * 60)
        print("CARREGAMENTO CONCLUÍDO")
        print("=" * 60)

        print(
            f"Tabelas carregadas: "
            f"{len(csv_files)}"
        )

        print(
            f"Linhas carregadas: "
            f"{total_carregado:,}".replace(",", ".")
        )

    except Exception:

        connection.rollback()

        print("\nERRO DURANTE O CARREGAMENTO.")
        print(
            "A transação da tabela com erro "
            "foi revertida."
        )

        raise

    finally:

        connection.close()

        print(
            "\nConexão com PostgreSQL encerrada."
        )


if __name__ == "__main__":
    main()