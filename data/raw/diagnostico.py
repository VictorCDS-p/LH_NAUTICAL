import csv
import os

PASTA = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("DIAGNÓSTICO DOS CSVs - LH NAUTICAL")
print("=" * 70)

arquivos = sorted(
    arquivo
    for arquivo in os.listdir(PASTA)
    if arquivo.lower().endswith(".csv")
)

print(f"\nQuantidade de arquivos CSV encontrados: {len(arquivos)}")

for arquivo in arquivos:
    caminho = os.path.join(PASTA, arquivo)

    print("\n" + "-" * 70)
    print(f"ARQUIVO: {arquivo}")

    try:
        with open(caminho, "r", encoding="utf-8-sig", newline="") as f:
            leitor = csv.reader(f)

            cabecalho = next(leitor)
            quantidade_linhas = sum(1 for _ in leitor)

        print(f"Quantidade de linhas: {quantidade_linhas}")
        print(f"Quantidade de colunas: {len(cabecalho)}")
        print("Colunas:")

        for coluna in cabecalho:
            print(f"  - {coluna}")

    except UnicodeDecodeError:
        print("Encoding UTF-8 falhou. Tentando latin-1...")

        with open(caminho, "r", encoding="latin-1", newline="") as f:
            leitor = csv.reader(f)

            cabecalho = next(leitor)
            quantidade_linhas = sum(1 for _ in leitor)

        print(f"Quantidade de linhas: {quantidade_linhas}")
        print(f"Quantidade de colunas: {len(cabecalho)}")
        print("Colunas:")

        for coluna in cabecalho:
            print(f"  - {coluna}")

    except Exception as erro:
        print(f"ERRO: {erro}")

print("\n" + "=" * 70)
print("FIM DO DIAGNÓSTICO")
print("=" * 70)