import sqlite3
import os
from utils.logger import logger

def corrigir_estrutura_banco():
    """Corrige a estrutura do banco adicionando colunas missing"""
    DB_PATH = "relatorios/controle_patrimonial.db"
    
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados não encontrado!")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("🔍 Verificando estrutura do banco...")
        
        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(bens)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        print(f"Colunas existentes: {colunas_existentes}")
        
        # Adicionar colunas missing (sem DEFAULT para evitar o erro)
        colunas_necessarias = {
            'data_localizacao': 'DATETIME',
            'data_criacao': 'DATETIME'  # Removido o DEFAULT
        }
        
        for coluna, tipo in colunas_necessarias.items():
            if coluna not in colunas_existentes:
                print(f"➕ Adicionando coluna {coluna}...")
                cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} {tipo}")
                print(f"✅ Coluna {coluna} adicionada com sucesso!")
        
        # Agora atualizar os valores das novas colunas
        if 'data_criacao' not in colunas_existentes:
            print("🔄 Atualizando data_criacao para registros existentes...")
            cursor.execute("UPDATE bens SET data_criacao = datetime('now') WHERE data_criacao IS NULL")
        
        if 'data_localizacao' not in colunas_existentes:
            print("🔄 Atualizando data_localizacao para bens já localizados...")
            cursor.execute("UPDATE bens SET data_localizacao = datetime('now') WHERE situacao = 'OK' AND data_localizacao IS NULL")
        
        conn.commit()
        
        # Verificar se a correção foi bem sucedida
        cursor.execute("PRAGMA table_info(bens)")
        colunas_finais = [col[1] for col in cursor.fetchall()]
        print(f"🎉 Estrutura final: {colunas_finais}")
        
        # Contar registros atualizados
        cursor.execute("SELECT COUNT(*) FROM bens WHERE data_criacao IS NOT NULL")
        com_data_criacao = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bens WHERE data_localizacao IS NOT NULL")
        com_data_localizacao = cursor.fetchone()[0]
        
        print(f"📊 Registros com data_criacao: {com_data_criacao}")
        print(f"📊 Registros com data_localizacao: {com_data_localizacao}")
        
        conn.close()
        
        print("🎉 Estrutura do banco corrigida com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir banco: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    corrigir_estrutura_banco()