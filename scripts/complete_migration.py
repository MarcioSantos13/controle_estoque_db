# scripts/complete_migration.py
import os
import sqlite3
import sys
import shutil
from datetime import datetime

def caminho_relativo(pasta: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, pasta)
    return os.path.join(os.path.abspath("."), pasta)

DB_PATH = os.path.join(caminho_relativo("relatorios"), "controle_patrimonial.db")
BACKUP_DIR = os.path.join(caminho_relativo("relatorios"), "backups")

def complete_migration():
    """Migração completa: cria novo banco e copia dados do antigo"""
    
    if not os.path.exists(DB_PATH):
        print("❌ Banco de dados original não encontrado.")
        return False
    
    # Criar backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_path = os.path.join(BACKUP_DIR, f"backup_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
    shutil.copy2(DB_PATH, backup_path)
    print(f"📦 Backup criado: {backup_path}")
    
    try:
        # Conectar ao banco antigo
        conn_old = sqlite3.connect(DB_PATH)
        conn_old.row_factory = sqlite3.Row
        cursor_old = conn_old.cursor()
        
        # Ler todos os dados do banco antigo
        cursor_old.execute("SELECT * FROM bens")
        dados_antigos = [dict(row) for row in cursor_old.fetchall()]
        
        print(f"📊 Dados lidos do banco antigo: {len(dados_antigos)} registros")
        
        # Fechar conexão antiga
        conn_old.close()
        
        # Renomear banco antigo
        old_db_path = DB_PATH + ".old"
        os.rename(DB_PATH, old_db_path)
        print(f"🔄 Banco antigo renomeado para: {old_db_path}")
        
        # Criar NOVO banco com estrutura completa
        conn_new = sqlite3.connect(DB_PATH)
        cursor_new = conn_new.cursor()
        
        # Criar tabela com estrutura COMPLETA
        cursor_new.execute("""
            CREATE TABLE bens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
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
        
        # Criar índices
        cursor_new.execute("CREATE INDEX idx_bens_numero ON bens(numero)")
        cursor_new.execute("CREATE INDEX idx_bens_situacao ON bens(situacao)")
        
        print("✅ Nova estrutura criada")
        
        # Inserir dados antigos na nova estrutura
        registros_inseridos = 0
        for registro in dados_antigos:
            try:
                cursor_new.execute("""
                    INSERT INTO bens (
                        numero, nome, situacao, localizacao, data_criacao, data_localizacao,
                        responsavel, detentor, lotacao_detentor, data_ultima_vistoria,
                        data_vistoria_atual, auditor, status, observacao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    registro.get('numero'),
                    registro.get('nome'),
                    registro.get('situacao', 'Pendente'),
                    registro.get('localizacao'),
                    registro.get('data_criacao'),
                    registro.get('data_localizacao'),
                    registro.get('responsavel', ''),  # Novas colunas com valores padrão
                    registro.get('detentor', ''),
                    registro.get('lotacao_detentor', ''),
                    registro.get('data_ultima_vistoria'),
                    registro.get('data_vistoria_atual'),
                    registro.get('auditor', ''),
                    registro.get('status', 'Ativo'),
                    registro.get('observacao', '')
                ))
                registros_inseridos += 1
            except Exception as e:
                print(f"⚠️  Erro ao inserir registro {registro.get('numero')}: {e}")
        
        conn_new.commit()
        conn_new.close()
        
        print(f"✅ Migração concluída: {registros_inseridos} registros transferidos")
        
        # Verificar estrutura final
        conn_final = sqlite3.connect(DB_PATH)
        cursor_final = conn_final.cursor()
        cursor_final.execute("PRAGMA table_info(bens)")
        colunas_finais = [col[1] for col in cursor_final.fetchall()]
        
        print("\n📋 ESTRUTURA FINAL:")
        for coluna in sorted(colunas_finais):
            print(f"   ✅ {coluna}")
        
        cursor_final.execute("SELECT COUNT(*) FROM bens")
        total_final = cursor_final.fetchone()[0]
        print(f"\n📊 Total no novo banco: {total_final} registros")
        
        conn_final.close()
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA MIGRAÇÃO: {str(e)}")
        # Restaurar backup em caso de erro
        if os.path.exists(old_db_path):
            os.rename(old_db_path, DB_PATH)
            print("🔄 Banco original restaurado")
        return False

if __name__ == "__main__":
    complete_migration()