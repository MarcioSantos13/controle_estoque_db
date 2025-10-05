import sqlite3

DB_PATH = '../relatorios/controle_patrimonial.db'

def migrar_coluna_data_atualizacao():
    """Adiciona coluna data_atualizacao ao banco principal"""
    conn = None
    try:
        print(f"🔧 Migrando: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = [coluna[1] for coluna in cursor.fetchall()]
        
        print("📋 Colunas atuais:", colunas)
        
        if 'data_atualizacao' not in colunas:
            print("🔄 Adicionando coluna data_atualizacao...")
            
            # ETAPA 1: Adicionar coluna sem default
            cursor.execute('''
                ALTER TABLE usuarios 
                ADD COLUMN data_atualizacao TIMESTAMP
            ''')
            
            # ETAPA 2: Preencher com data_criacao para registros existentes
            cursor.execute('''
                UPDATE usuarios 
                SET data_atualizacao = data_criacao 
                WHERE data_atualizacao IS NULL
            ''')
            
            conn.commit()
            print("✅ COLUNA data_atualizacao ADICIONADA COM SUCESSO!")
            
            # Verificar resultado
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas_finais = [coluna[1] for coluna in cursor.fetchall()]
            print("📋 Novas colunas:", colunas_finais)
            
        else:
            print("✅ Coluna data_atualizacao JÁ EXISTE!")
            
        # Verificar dados
        cursor.execute("SELECT COUNT(*) FROM bens")
        bens_count = cursor.fetchone()[0]
        print(f"📦 Itens de patrimônio: {bens_count}")
        
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        users_count = cursor.fetchone()[0] 
        print(f"👥 Usuários: {users_count}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrar_coluna_data_atualizacao()