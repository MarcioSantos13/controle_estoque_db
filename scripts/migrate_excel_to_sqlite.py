# scripts/migrate_excel_to_sqlite.py
import os
import sqlite3
import pandas as pd
from contextlib import closing
from datetime import datetime

BASE_DIR = os.path.abspath(".")
RELATORIOS_DIR = os.path.join(BASE_DIR, "relatorios")
os.makedirs(RELATORIOS_DIR, exist_ok=True)

EXCEL_PATH = os.path.join(RELATORIOS_DIR, "controle_patrimonial.xlsx")
DB_PATH = os.path.join(RELATORIOS_DIR, "controle_patrimonial.db")
TABELA = "bens"

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            nome TEXT,
            situacao TEXT DEFAULT 'Pendente',
            localizacao TEXT,
            responsavel TEXT,
            detentor TEXT,
            lotacao_detentor TEXT,
            data_ultima_vistoria DATE,
            data_vistoria_atual DATE,
            auditor TEXT,
            status TEXT DEFAULT 'Ativo',
            observacao TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_localizacao DATETIME,
            data_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Índices para melhor performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_status ON bens(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bens_detentor ON bens(detentor)")

def recreate_table(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS bens")
    init_db(conn)

def parse_date(date_str):
    """Tenta converter string para data"""
    if pd.isna(date_str) or not date_str:
        return None
    try:
        return pd.to_datetime(date_str).strftime('%Y-%m-%d')
    except:
        return None

def main():
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"Excel não encontrado em: {EXCEL_PATH}")

    print(f"Lendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)

    print("Colunas encontradas:", df.columns.tolist())

    # Mapeamento das novas colunas
    column_mapping = {
        "numero": "NUMERO DO BEM",
        "nome": "NOME DO BEM", 
        "situacao": "Situacao",
        "localizacao": "Localizacao",
        "responsavel": "Responsavel",
        "detentor": "Detentor",
        "lotacao_detentor": "Lotacao Detentor",
        "data_ultima_vistoria": "Data da ultima vistoria",
        "data_vistoria_atual": "Data da vistoria atual",
        "auditor": "Auditor",
        "status": "Status",
        "observacao": "Observacao"
    }

    # Verificar colunas obrigatórias
    missing_required = []
    for excel_col in column_mapping.values():
        if excel_col not in df.columns:
            missing_required.append(excel_col)
    
    if missing_required:
        print(f"Aviso: Colunas não encontradas: {missing_required}")
        print("Colunas disponíveis:", df.columns.tolist())

    # Renomear colunas e manter apenas as que existem
    df_renamed = pd.DataFrame()
    for db_col, excel_col in column_mapping.items():
        if excel_col in df.columns:
            df_renamed[db_col] = df[excel_col]
        else:
            df_renamed[db_col] = None  # Ou valor padrão

    # Processar datas
    if 'data_ultima_vistoria' in df_renamed.columns:
        df_renamed['data_ultima_vistoria'] = df_renamed['data_ultima_vistoria'].apply(parse_date)
    
    if 'data_vistoria_atual' in df_renamed.columns:
        df_renamed['data_vistoria_atual'] = df_renamed['data_vistoria_atual'].apply(parse_date)

    # Limpeza de dados
    df_renamed["numero"] = df_renamed["numero"].astype(str).str.strip()
    df_renamed["nome"] = df_renamed["nome"].astype(str).str.strip()
    
    # Preencher valores padrão
    df_renamed["situacao"] = df_renamed["situacao"].fillna("Pendente")
    df_renamed["status"] = df_renamed["status"].fillna("Ativo")

    with closing(sqlite3.connect(DB_PATH, timeout=60)) as conn, conn:
        print(f"Criando/Recriando tabela em: {DB_PATH}")
        recreate_table(conn)

        print("Inserindo registros...")
        df_renamed.to_sql(TABELA, conn, if_exists="append", index=False, chunksize=50_000)

        # Verificar inserção
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM bens")
        count = cur.fetchone()[0]
        print(f"Total de registros inseridos: {count}")

    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    main()