# scripts/force_update_database.py
import os
import sqlite3
import sys

def caminho_relativo(pasta: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, pasta)
    return os.path.join(os.path.abspath("."), pasta)

DB_PATH = os.path.join(caminho_relativo("relatorios"), "controle_patrimonial.db")

def force_update_database():
    """Atualiza FORÇADAMENTE a estrutura do banco de dados"""
    
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados não encontrado.")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("🔄 ATUALIZANDO FORÇADAMENTE a estrutura do banco...")
        
        # Lista de TODAS as colunas que devem existir
        todas_colunas = [
            'responsavel',
            'detentor', 
            'lotacao_detentor',
            'data_ultima_vistoria',
            'data_vistoria_atual',
            'auditor',
            'status',
            'observacao',
            'data_atualizacao'
        ]
        
        # Adicionar cada coluna individualmente com tratamento de erro
        for coluna in todas_colunas:
            try:
                if coluna in ['data_ultima_vistoria', 'data_vistoria_atual']:
                    cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} DATE")
                elif coluna == 'data_atualizacao':
                    cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} DATETIME")
                else:
                    cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} TEXT")
                print(f"✅ Coluna '{coluna}' adicionada com sucesso")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"⚠️  Coluna '{coluna}' já existe")
                else:
                    print(f"❌ Erro ao adicionar coluna '{coluna}': {e}")
        
        # Definir valores padrão
        try:
            cursor.execute("UPDATE bens SET status = 'Ativo' WHERE status IS NULL")
            print("✅ Valores padrão definidos para 'status'")
        except Exception as e:
            print(f"⚠️  Erro ao definir valores padrão: {e}")
        
        conn.commit()
        
        # Verificar estrutura final
        cursor.execute("PRAGMA table_info(bens)")
        colunas_finais = [col[1] for col in cursor.fetchall()]
        
        print("\n📋 ESTRUTURA FINAL DA TABELA:")
        for coluna in sorted(colunas_finais):
            print(f"   📍 {coluna}")
        
        print(f"\n✅ Atualização concluída! Total de colunas: {len(colunas_finais)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {str(e)}")
        return False

if __name__ == "__main__":
    force_update_database()
    