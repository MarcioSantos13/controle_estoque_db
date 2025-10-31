# scripts/migrate_excel_to_sqlite.py
import os
import sqlite3
import pandas as pd
from contextlib import closing

BASE_DIR = os.path.abspath(".")
RELATORIOS_DIR = os.path.join(BASE_DIR, "relatorios")
os.makedirs(RELATORIOS_DIR, exist_ok=True)

EXCEL_PATH = os.path.join(RELATORIOS_DIR, "controle_patrimonial.xlsx")   # arquivo de entrada
DB_PATH = os.path.join(RELATORIOS_DIR, "controle_patrimonial.db")        # banco de saída
TABELA = "bens"

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            nome TEXT,
            localizacao TEXT,
            situacao TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")

def recreate_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS bens")
    init_db(conn)

def main():
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"Excel não encontrado em: {EXCEL_PATH}")

    print(f"Lendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)  # Requer: pip install pandas openpyxl

    print("Colunas encontradas:", df.columns.tolist())

    # Valida colunas esperadas
    expected_cols = ["Nº DO BEM", "NOME DO BEM", "LOCALIZAÇÃO", "SITUAÇÃO"]
    missing = [col for col in expected_cols if col not in df.columns]
    if missing:
        raise RuntimeError(f"As colunas abaixo não foram encontradas no Excel: {missing}")

    # Mantém apenas as colunas que precisamos
    df = df[expected_cols]

    # Normalizações simples
    df["Nº DO BEM"] = df["Nº DO BEM"].astype(str).str.strip()
    df["NOME DO BEM"] = df["NOME DO BEM"].astype(str).str.strip()
    df["LOCALIZAÇÃO"] = df["LOCALIZAÇÃO"].astype(str).str.strip()
    df["SITUAÇÃO"] = df["SITUAÇÃO"].astype(str).str.strip()

    # Renomeia para o padrão do banco
    df = df.rename(columns={
        "Nº DO BEM": "numero",
        "NOME DO BEM": "nome",
        "LOCALIZAÇÃO": "localizacao",
        "SITUAÇÃO": "situacao"
    })

    with closing(sqlite3.connect(DB_PATH, timeout=60)) as conn, conn:
        print(f"Criando/Recriando tabela em: {DB_PATH}")
        recreate_table(conn)

        print("Inserindo registros...")
        df.to_sql(TABELA, conn, if_exists="append", index=False, chunksize=50_000)

    print("Migração concluída com sucesso.")

if __name__ == "__main__":
    main()
