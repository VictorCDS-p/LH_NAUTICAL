from pathlib import Path
import csv
import os

import psycopg2
from dotenv import load_dotenv


# ============================================================
# DESAFIO LIGHTHOUSE - DADOS E IA
# QUESTÃO 3 - CARREGAMENTO
# ============================================================
#
# Objetivo:
# Carregar todos os arquivos CSV da pasta de dados brutos
# nas respectivas tabelas do PostgreSQL, utilizando o schema
# criado na Questão 2.
#
# Premissas:
# - Todos os CSVs devem ser carregados;
# - O banco de destino é PostgreSQL;
# - O carregamento deve preservar os dados brutos;
# - Não são realizados tratamentos ou correções nos dados.
#
# Bibliotecas:
# - csv e os: biblioteca padrão do Python;
# - pathlib: manipulação de caminhos;
# - psycopg2: conexão e carregamento no PostgreSQL;
# - python-dotenv: leitura das variáveis de ambiente.
# ============================================================


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Raiz do projeto
ROOT = Path(__file__).resolve().parent.parent.parent

# Diretório contendo os arquivos CSV
CSV_DIR = ROOT / "data" / "raw"

# Arquivo contendo as credenciais do banco
ENV_FILE = ROOT / ".env"

# Schema PostgreSQL utilizado na Questão 2
DB_SCHEMA = "public"


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
    "password": os.getenv("DB_PASSWORD"),
}


# ============================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ============================================================

def validate_config():
    """
    Verifica se todas as variáveis necessárias para conexão
    com o PostgreSQL foram configuradas.
    """

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise EnvironmentError(
            "Variáveis de ambiente não configuradas: "
            + ", ".join(missing_variables)
        )


# ============================================================
# LEITURA DAS COLUNAS DO CSV
# ============================================================

def get_columns(csv_file):
    """
    Retorna os nomes das colunas presentes no cabeçalho
    do arquivo CSV.
    """

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.reader(file)
        columns = next(reader, None)

    if not columns:
        raise ValueError(
            f"O arquivo CSV não possui cabeçalho: "
            f"{csv_file.name}"
        )

    return columns


# ============================================================
# CONTAGEM DE LINHAS DO CSV
# ============================================================

def count_csv_rows(csv_file):
    """
    Conta a quantidade de registros do CSV, desconsiderando
    a linha de cabeçalho.
    """

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.reader(file)

        # Ignora o cabeçalho.
        next(reader, None)

        return sum(
            1
            for _ in reader
        )


# ============================================================
# VALIDAÇÃO DA TABELA NO POSTGRESQL
# ============================================================

def table_exists(connection, table_name):
    """
    Verifica se a tabela correspondente ao CSV existe
    no schema PostgreSQL definido.
    """

    query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
        );
    """

    with connection.cursor() as cursor:

        cursor.execute(
            query,
            (
                DB_SCHEMA,
                table_name,
            ),
        )

        return cursor.fetchone()[0]


# ============================================================
# INFORMAÇÕES DA CONEXÃO
# ============================================================

def show_database_info(connection):
    """
    Exibe informações básicas da conexão estabelecida.
    """

    query = """
        SELECT
            current_database(),
            current_user,
            current_schema();
    """

    with connection.cursor() as cursor:

        cursor.execute(query)

        database, user, schema = cursor.fetchone()

    print("\nInformações da conexão:")
    print(f"    Banco:       {database}")
    print(f"    Usuário:     {user}")
    print(f"    Schema atual: {schema}")
    print()


# ============================================================
# CARREGAMENTO DE UMA TABELA
# ============================================================

def load_table(connection, csv_file):
    """
    Carrega um arquivo CSV na tabela PostgreSQL correspondente.

    O nome da tabela é obtido a partir do nome do arquivo.
    O carregamento é realizado por COPY, preservando os dados
    sem limpeza ou transformação.
    """

    table_name = csv_file.stem

    # --------------------------------------------------------
    # Verificação da existência da tabela
    # --------------------------------------------------------

    if not table_exists(
        connection,
        table_name,
    ):
        raise RuntimeError(
            f'A tabela "{DB_SCHEMA}"."{table_name}" '
            f'não existe no banco de dados.'
        )

    # --------------------------------------------------------
    # Identificação das colunas
    # --------------------------------------------------------

    columns = get_columns(csv_file)

    columns_sql = ", ".join(
        f'"{column}"'
        for column in columns
    )

    # --------------------------------------------------------
    # Identificação da tabela de destino
    # --------------------------------------------------------

    table_sql = (
        f'"{DB_SCHEMA}"."{table_name}"'
    )

    # --------------------------------------------------------
    # Comando COPY
    # --------------------------------------------------------

    copy_sql = f"""
        COPY {table_sql} ({columns_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            ENCODING 'UTF8'
        )
    """

    # --------------------------------------------------------
    # Execução do carregamento
    # --------------------------------------------------------

    with connection.cursor() as cursor:

        with open(
            csv_file,
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            cursor.copy_expert(
                copy_sql,
                file,
            )


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - CARREGAMENTO DOS CSVs")
    print("=" * 60)

    # --------------------------------------------------------
    # Validação da configuração
    # --------------------------------------------------------

    validate_config()

    print("\nDiretório dos CSVs:")
    print(CSV_DIR)

    print("\nArquivo de configuração:")
    print(ENV_FILE)

    print("\nSchema PostgreSQL:")
    print(DB_SCHEMA)

    # --------------------------------------------------------
    # Localização dos arquivos CSV
    # --------------------------------------------------------

    csv_files = sorted(
        CSV_DIR.glob("*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum arquivo CSV encontrado em: "
            f"{CSV_DIR}"
        )

    print(
        f"\nArquivos CSV encontrados: "
        f"{len(csv_files)}"
    )

    # --------------------------------------------------------
    # Conexão com PostgreSQL
    # --------------------------------------------------------

    print("\nConectando ao PostgreSQL...")

    connection = psycopg2.connect(
        **DB_CONFIG
    )

    connection.set_client_encoding(
        "UTF8"
    )

    print(
        "Conexão realizada com sucesso."
    )

    show_database_info(connection)

    # --------------------------------------------------------
    # Carregamento dos arquivos
    # --------------------------------------------------------

    total_linhas_carregadas = 0

    try:

        for index, csv_file in enumerate(
            csv_files,
            start=1,
        ):

            table_name = csv_file.stem

            print(
                f"[{index}/{len(csv_files)}] "
                f"Carregando: {table_name}.csv"
            )

            # --------------------------------------------
            # Contagem dos registros de origem
            # --------------------------------------------

            quantidade_linhas = count_csv_rows(
                csv_file
            )

            print(
                f"    Linhas no CSV: "
                f"{quantidade_linhas:,}".replace(
                    ",",
                    ".",
                )
            )

            try:

                # ----------------------------------------
                # Carregamento da tabela
                # ----------------------------------------

                load_table(
                    connection,
                    csv_file,
                )

                # ----------------------------------------
                # Confirmação da transação
                # ----------------------------------------

                connection.commit()

                total_linhas_carregadas += (
                    quantidade_linhas
                )

                print(
                    f"    OK - tabela "
                    f"'{table_name}' carregada"
                )

            except Exception:

                # Desfaz somente a operação da tabela
                # que apresentou erro.
                connection.rollback()

                print(
                    f"    ERRO - falha ao carregar "
                    f"'{table_name}'"
                )

                raise

            print()

        # ----------------------------------------------------
        # Resumo final
        # ----------------------------------------------------

        print("=" * 60)
        print("CARREGAMENTO CONCLUÍDO")
        print("=" * 60)

        print(
            f"Tabelas carregadas: "
            f"{len(csv_files)}"
        )

        print(
            f"Linhas carregadas: "
            f"{total_linhas_carregadas:,}".replace(
                ",",
                ".",
            )
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