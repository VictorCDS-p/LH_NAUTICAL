from pathlib import Path
import csv
from datetime import datetime


# ============================================================
# CONFIGURACAO
# ============================================================

ROOT = Path(__file__).resolve().parent.parent.parent

CSV_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "q2_schema" / "output"
OUTPUT_FILE = OUTPUT_DIR / "schema.sql"


# ============================================================
# FUNCOES AUXILIARES
# ============================================================

def is_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_numeric(value):
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_boolean(value):
    return value.lower() in {
        "true",
        "false",
        "t",
        "f"
    }


def is_timestamp(value):
    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d"
    ]

    for formato in formatos:
        try:
            datetime.strptime(value, formato)
            return True
        except ValueError:
            continue

    return False


def infer_column_type(column_name, values):
    """
    Infere o tipo PostgreSQL da coluna com base
    nos valores encontrados no CSV.
    """

    values = [
        value.strip()
        for value in values
        if value is not None and value.strip() != ""
    ]

    if not values:
        return "TEXT"

    column_lower = column_name.lower()

    # ========================================================
    # IDENTIFICADORES
    # ========================================================

    identifier_keywords = [
        "cpf",
        "cnpj",
        "tax_id",
        "ean",
        "barcode",
        "access_key",
        "ncm_code",
        "postal_code",
        "phone"
    ]

    if any(keyword in column_lower for keyword in identifier_keywords):
        return "TEXT"

    # ========================================================
    # DATAS
    # ========================================================

    date_keywords = [
        "_at",
        "_date"
    ]

    if any(column_lower.endswith(keyword) for keyword in date_keywords):

        if all(is_timestamp(value) for value in values):
            return "TIMESTAMP"

    # ========================================================
    # BOOLEANOS
    # ========================================================

    if all(is_boolean(value) for value in values):
        return "BOOLEAN"

    # ========================================================
    # INTEIROS
    # ========================================================

    if all(is_integer(value) for value in values):
        return "BIGINT"

    # ========================================================
    # NUMERICOS
    # ========================================================

    if all(is_numeric(value) for value in values):
        return "NUMERIC"

    # ========================================================
    # TEXTO
    # ========================================================

    return "TEXT"


def read_csv_columns(csv_file):

    with open(
        csv_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        columns = reader.fieldnames
        rows = list(reader)

    return columns, rows


def generate_create_table(table_name, columns, rows):

    sql = []

    sql.append("-- ============================================================")
    sql.append(f"-- TABELA: {table_name}")
    sql.append("-- ============================================================")

    sql.append(f'CREATE TABLE "{table_name}" (')

    definitions = []

    for column in columns:

        values = [
            row[column]
            for row in rows
        ]

        column_type = infer_column_type(
            column,
            values
        )

        definitions.append(
            f'    "{column}" {column_type}'
        )

    sql.append(",\n".join(definitions))

    sql.append(");")
    sql.append("")

    return "\n".join(sql)


# ============================================================
# CABECALHO
# ============================================================

def create_schema_header():

    return (
        "-- ============================================================\n"
        "-- LH NAUTICAL - SCHEMA\n"
        "-- Schema gerado automaticamente a partir dos arquivos CSV\n"
        "-- ============================================================\n\n"
    )


# ============================================================
# GERACAO DO SCHEMA
# ============================================================

def main():

    print("=" * 60)
    print("LH NAUTICAL - GERACAO DO SCHEMA")
    print("=" * 60)

    print("\nDiretorio dos CSVs:")
    print(CSV_DIR)

    print("\nArquivo de saida:")
    print(OUTPUT_FILE)

    # --------------------------------------------------------
    # Procura os CSVs
    # --------------------------------------------------------

    csv_files = sorted(CSV_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"Nenhum CSV encontrado em: {CSV_DIR}"
        )

    print(f"\nCSV encontrados: {len(csv_files)}")

    # --------------------------------------------------------
    # Cria pasta de saida
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Cria novo schema.sql
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(create_schema_header())

    # --------------------------------------------------------
    # Processa cada CSV
    # --------------------------------------------------------

    for index, csv_file in enumerate(csv_files, start=1):

        table_name = csv_file.stem

        print(
            f"\n[{index}/{len(csv_files)}] "
            f"Processando: {table_name}.csv"
        )

        # Leitura do CSV
        columns, rows = read_csv_columns(csv_file)

        print(
            f"    Linhas lidas: {len(rows):,}".replace(",", ".")
        )

        print(
            f"    Colunas: {len(columns)}"
        )

        # Gera CREATE TABLE
        create_table = generate_create_table(
            table_name,
            columns,
            rows
        )

        # ----------------------------------------------------
        # Salva imediatamente no schema.sql
        # ----------------------------------------------------

        with open(
            OUTPUT_FILE,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(create_table)
            file.write("\n")

        print(
            f"    Tabela {table_name} adicionada ao schema.sql"
        )

    # --------------------------------------------------------
    # Finalizacao
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SCHEMA GERADO COM SUCESSO")
    print("=" * 60)

    print(f"Tabelas processadas: {len(csv_files)}")
    print(f"Arquivo gerado: {OUTPUT_FILE}")

    print("\nProcessamento concluido.")
    print("=" * 60)


if __name__ == "__main__":
    main()