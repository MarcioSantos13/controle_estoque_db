import sqlite3
import os

DB_PATH = "relatorios/controle_patrimonial.db"

if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar a estrutura da tabela bens
        cursor.execute("PRAGMA table_info(bens)")
        columns = cursor.fetchall()
        
        print("Estrutura da tabela 'bens':")
        print("ID | Nome | Tipo | Pode ser NULL | Valor Padrão | É PK")
        print("-" * 60)
        for col in columns:
            print(col)
            
        # Verificar alguns dados para ver os nomes reais das colunas
        print("\nPrimeiros 3 registros:")
        cursor.execute("SELECT * FROM bens LIMIT 3")
        sample_data = cursor.fetchall()
        for row in sample_data:
            print(row)
            
        conn.close()
        
    except Exception as e:
        print(f"Erro: {e}")
else:
    print("Banco não encontrado")