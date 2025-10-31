import os
import sqlite3
from utils.logger import logger

# Verificar se o banco existe
DB_PATH = "relatorios/controle_patrimonial.db"
print(f"Caminho do banco: {DB_PATH}")
print(f"Banco existe: {os.path.exists(DB_PATH)}")

if os.path.exists(DB_PATH):
    try:
        # Conectar e verificar tabelas
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar total de registros
        cursor.execute("SELECT COUNT(*) FROM bens")
        count = cursor.fetchone()[0]
        print(f"Total de registros: {count}")
        
        # Verificar localizados vs não localizados
        cursor.execute("SELECT situacao, COUNT(*) as count FROM bens GROUP BY situacao")
        situacoes = cursor.fetchall()
        print("Situações:")
        for situacao in situacoes:
            print(f"  {situacao['situacao']}: {situacao['count']}")
        
        # Testar a função gerar_planilhas_localizacao
        from utils.db_handler import gerar_planilhas_localizacao
        localizados, nao_localizados = gerar_planilhas_localizacao(DB_PATH)
        print(f"Localizados: {len(localizados)}")
        print(f"Não Localizados: {len(nao_localizados)}")
        
        # Mostrar alguns localizados
        print("\nPrimeiros 3 localizados:")
        for i, item in enumerate(localizados[:3]):
            print(f"  {i+1}. {item}")
            
        conn.close()
        
    except Exception as e:
        print(f"Erro ao acessar banco: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Banco de dados não encontrado.")