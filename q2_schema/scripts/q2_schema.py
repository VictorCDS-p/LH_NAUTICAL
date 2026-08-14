from pathlib import Path
import csv
from datetime import datetime


# ============================================================
# DESAFIO LIGHTHOUSE — DADOS E IA
# QUESTÃO 2 — SCHEMA
# ============================================================
#
# Objetivo:
# Ler todos os arquivos CSV de um diretório, identificar suas
# colunas e inferir seus tipos para PostgreSQL, gerando um
# único arquivo schema.sql com uma tabela para cada CSV.
#
# Bibliotecas utilizadas:
# - pathlib
# - csv
# - datetime
#
# Não são utilizadas bibliotecas externas.
# ============================================================


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# Raiz do projeto
ROOT = Path(__file__).resolve().parent.parent.parent

# Diretório contendo os arquivos CSV de origem
CSV_DIR = ROOT / "data" / "raw"

# Diretório e arquivo de saída
OUTPUT_DIR = ROOT / "q2_schema" / "output"
OUTPUT_FILE = OUTPUT_DIR / "schema.sql"


# ============================================================
# VALIDAÇÃO DE TIPOS
# ============================================================

def is_integer(value):
    """
    Verifica se o valor pode ser interpretado como inteiro.
    """
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_numeric(value):
    """
    Verifica se o valor pode ser interpretado como numérico.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_boolean(value):
    """
    Verifica se o valor representa um booleano.
    """
    return value.lower() in {
        "true",
        "false",
        "t",
        "f",
    }


def get_datetime_format(value):
    """
    Identifica o formato de data/hora de um valor.

    Retorna:
    - "TIMESTAMP" para valores com data e hora;
    - "DATE" para valores contendo somente a data;
    - None quando o valor não corresponde aos formatos esperados.
    """

    timestamp_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    date_formats = [
        "%Y-%m-%d",
    ]

    for date_format in timestamp_formats:
        try:
            datetime.strptime(value, date_format)
            return "TIMESTAMP"
        except ValueError:
            continue

    for date_format in date_formats:
        try:
            datetime.strptime(value, date_format)
            return "DATE"
        except ValueError:
            continue

    return None


# ============================================================
# INFERÊNCIA DE TIPOS
# ============================================================

def infer_column_type(column_name, values):
    """
    Infere o tipo PostgreSQL da coluna com base no nome da
    coluna e nos valores encontrados no CSV.

    A inferência segue a seguinte ordem:
    1. Identificadores que devem ser preservados como TEXT;
    2. Datas e timestamps;
    3. Booleanos;
    4. Inteiros;
    5. Valores numéricos;
    6. TEXT como tipo padrão.
    """

    # Remove valores vazios antes da inferência.
    values = [
        value.strip()
        for value in values
        if value is not None and value.strip() != ""
    ]

    # Se não houver valores disponíveis para inferência,
    # utiliza TEXT como tipo padrão.
    if not values:
        return "TEXT"

    column_lower = column_name.lower()

    # --------------------------------------------------------
    # IDENTIFICADORES
    # --------------------------------------------------------
    #
    # Alguns campos podem conter somente números, mas são
    # identificadores e não devem ser tratados como valores
    # numéricos.
    # --------------------------------------------------------

    identifier_keywords = [
        "cpf",
        "cnpj",
        "tax_id",
        "ean",
        "barcode",
        "access_key",
        "ncm_code",
        "postal_code",
        "phone",
    ]

    if any(
        keyword in column_lower
        for keyword in identifier_keywords
    ):
        return "TEXT"

    # --------------------------------------------------------
    # DATAS E TIMESTAMPS
    # --------------------------------------------------------

    date_keywords = [
        "_at",
        "_date",
    ]

    if any(
        column_lower.endswith(keyword)
        for keyword in date_keywords
    ):
        detected_types = {
            get_datetime_format(value)
            for value in values
        }

        if detected_types == {"TIMESTAMP"}:
            return "TIMESTAMP"

        if detected_types == {"DATE"}:
            return "DATE"

    # --------------------------------------------------------
    # BOOLEANOS
    # --------------------------------------------------------

    if all(is_boolean(value) for value in values):
        return "BOOLEAN"

    # --------------------------------------------------------
    # INTEIROS
    # --------------------------------------------------------

    if all(is_integer(value) for value in values):
        return "BIGINT"

    # --------------------------------------------------------
    # NUMÉRICOS
    # --------------------------------------------------------

    if all(is_numeric(value) for value in values):
        return "NUMERIC"

    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    return "TEXT"


# ============================================================
# LEITURA DOS ARQUIVOS CSV
# ============================================================

def read_csv_columns(csv_file):
    """
    Lê um arquivo CSV e retorna:
    - nome das colunas;
    - registros encontrados no arquivo.
    """

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames

        if not columns:
            raise ValueError(
                f"O arquivo não possui cabeçalho: {csv_file.name}"
            )

        rows = list(reader)

    return columns, rows


# ============================================================
# GERAÇÃO DO CREATE TABLE
# ============================================================

def generate_create_table(table_name, columns, rows):
    """
    Gera o comando CREATE TABLE correspondente a um arquivo CSV.
    """

    sql = [
        "-- ============================================================",
        f"-- TABELA: {table_name}",
        "-- ============================================================",
        f'CREATE TABLE "{table_name}" (',
    ]

    definitions = []

    for column in columns:

        # Coleta os valores da coluna para realizar a inferência.
        values = [
            row[column]
            for row in rows
        ]

        column_type = infer_column_type(
            column,
            values,
        )

        definitions.append(
            f'    "{column}" {column_type}'
        )

    sql.append(",\n".join(definitions))
    sql.append(");")
    sql.append("")

    return "\n".join(sql)


# ============================================================
# CABEÇALHO DO SCHEMA
# ============================================================

def create_schema_header():
    """
    Cria o cabeçalho do arquivo schema.sql.
    """

    return (
        "-- ============================================================\n"
        "-- LH NAUTICAL - SCHEMA\n"
        "-- Schema gerado automaticamente a partir dos arquivos CSV\n"
        "-- Banco de destino: PostgreSQL\n"
        "-- ============================================================\n\n"
    )


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL — GERAÇÃO DO SCHEMA")
    print("=" * 60)

    print("\nDiretório dos CSVs:")
    print(CSV_DIR)

    print("\nArquivo de saída:")
    print(OUTPUT_FILE)

    # --------------------------------------------------------
    # LOCALIZAÇÃO DOS CSVs
    # --------------------------------------------------------

    csv_files = sorted(
        CSV_DIR.glob("*.csv")
    )

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum arquivo CSV encontrado em: {CSV_DIR}"
        )

    print(
        f"\nArquivos CSV encontrados: {len(csv_files)}"
    )

    # --------------------------------------------------------
    # PREPARAÇÃO DO DIRETÓRIO DE SAÍDA
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # INICIALIZAÇÃO DO SCHEMA
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            create_schema_header()
        )

    # --------------------------------------------------------
    # PROCESSAMENTO DOS CSVs
    # --------------------------------------------------------

    for index, csv_file in enumerate(
        csv_files,
        start=1,
    ):

        table_name = csv_file.stem

        print(
            f"\n[{index}/{len(csv_files)}] "
            f"Processando: {table_name}.csv"
        )

        # Leitura do CSV
        columns, rows = read_csv_columns(
            csv_file
        )

        print(
            f"    Linhas lidas: "
            f"{len(rows):,}".replace(",", ".")
        )

        print(
            f"    Colunas identificadas: "
            f"{len(columns)}"
        )

        # Geração do CREATE TABLE
        create_table = generate_create_table(
            table_name,
            columns,
            rows,
        )

        # Adiciona a tabela ao schema.sql
        with open(
            OUTPUT_FILE,
            "a",
            encoding="utf-8",
        ) as file:

            file.write(create_table)
            file.write("\n")

        print(
            f"    Tabela '{table_name}' "
            f"adicionada ao schema.sql"
        )

    # --------------------------------------------------------
    # FINALIZAÇÃO
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SCHEMA GERADO COM SUCESSO")
    print("=" * 60)

    print(
        f"Tabelas processadas: {len(csv_files)}"
    )

    print(
        f"Arquivo gerado: {OUTPUT_FILE}"
    )

    print("\nProcessamento concluído.")
    print("=" * 60)


if __name__ == "__main__":
    main()

