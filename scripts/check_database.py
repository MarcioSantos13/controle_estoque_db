# scripts/check_database.py
import os
import sqlite3
import sys

def caminho_relativo(pasta: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, pasta)
    return os.path.join(os.path.abspath("."), pasta)

DB_PATH = os.path.join(caminho_relativo("relatorios"), "controle_patrimonial.db")

def verificar_estrutura():
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados não encontrado")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ver estrutura da tabela
        cursor.execute("PRAGMA table_info(bens)")
        colunas = cursor.fetchall()
        
        print("📋 Estrutura da tabela 'bens':")
        for coluna in colunas:
            print(f"   {coluna[1]} ({coluna[2]})")
        
        # Ver quantidade de registros
        cursor.execute("SELECT COUNT(*) FROM bens")
        total = cursor.fetchone()[0]
        print(f"📊 Total de registros: {total}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {str(e)}")

if __name__ == "__main__":
    verificar_estrutura()