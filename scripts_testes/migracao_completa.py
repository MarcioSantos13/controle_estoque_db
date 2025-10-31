import sqlite3
import os
from datetime import datetime

def migracao_completa():
    """Migração completa e criação da estrutura correta"""
    DB_PATH = "relatorios/controle_patrimonial.db"
    
    # Backup do banco antigo se existir
    if os.path.exists(DB_PATH):
        backup_path = f"relatorios/backup_controle_patrimonial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.rename(DB_PATH, backup_path)
        print(f"📦 Backup criado: {backup_path}")
    
    try:
        # Criar novo banco com estrutura correta
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Criar tabela com estrutura completa
        cursor.execute("""
            CREATE TABLE bens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL,
                nome TEXT NOT NULL,
                localizacao TEXT NOT NULL DEFAULT '',
                situacao TEXT NOT NULL DEFAULT 'Pendente',
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_localizacao DATETIME,
                UNIQUE(numero)
            )
        """)
        
        # Inserir dados de exemplo ou migrar do backup
        dados_exemplo = [
            ('367248', 'MESA REDONDA', 'Sala da Direção', 'OK', datetime.now(), datetime.now()),
            ('404500', 'MESA', 'Sala da Direção', 'OK', datetime.now(), datetime.now()),
            ('404612', 'MESA', 'Sala da Direção', 'OK', datetime.now(), datetime.now()),
            ('469704', 'COMPUTADOR', '', 'Pendente', datetime.now(), None),
        ]
        
        cursor.executemany("""
            INSERT INTO bens (numero, nome, localizacao, situacao, data_criacao, data_localizacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, dados_exemplo)
        
        conn.commit()
        conn.close()
        
        print("✅ Banco criado com estrutura correta!")
        print("✅ Dados de exemplo inseridos!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na migração completa: {e}")
        return False

if __name__ == "__main__":
    migracao_completa()