#!/usr/bin/env python3
"""
Migração forçada para o servidor
"""
import sqlite3
import os
from datetime import datetime

def migracao_forcada():
    print("🔧 MIGRAÇÃO FORÇADA - SERVIDOR")
    print("=" * 50)
    
    caminho_banco = '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db'
    
    if not os.path.exists(caminho_banco):
        print("❌ Banco não encontrado!")
        return False
    
    # Backup
    backup_path = f'/var/www/controle_estoque_db/relatorios/backup_migracao_forcada_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.system(f'cp "{caminho_banco}" "{backup_path}"')
    print(f"✅ Backup criado: {backup_path}")
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    try:
        print("🔄 INICIANDO MIGRAÇÃO FORÇADA...")
        
        # 1. Criar tabelas novas se não existirem
        print("📦 Criando tabela bem_patrimonial...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bem_patrimonial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_bem TEXT UNIQUE NOT NULL,
            descricao TEXT,
            localizacao TEXT,
            estado TEXT DEFAULT 'pendente',
            data_localizacao TIMESTAMP,
            localizador TEXT,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        print("👥 Criando tabela usuario...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'user',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 2. Migrar dados da tabela bens para bem_patrimonial
        print("🔄 Migrando dados de 'bens' para 'bem_patrimonial'...")
        
        # Primeiro verificar a estrutura exata da tabela bens
        cursor.execute("PRAGMA table_info(bens)")
        colunas_bens = [col[1] for col in cursor.fetchall()]
        print(f"📋 Colunas em 'bens': {colunas_bens}")
        
        # Query de migração adaptativa
        colunas_para_migrar = []
        if 'numero' in colunas_bens:
            colunas_para_migrar.append('numero as numero_bem')
        if 'nome' in colunas_bens:
            colunas_para_migrar.append('nome as descricao')
        if 'localizacao' in colunas_bens:
            colunas_para_migrar.append('localizacao')
        if 'situacao' in colunas_bens:
            colunas_para_migrar.append('''
                CASE 
                    WHEN situacao LIKE '%localiz%' OR situacao = 'localizado' THEN 'localizado'
                    ELSE 'pendente' 
                END as estado
            ''')
        if 'data_localizacao' in colunas_bens:
            colunas_para_migrar.append('data_localizacao')
        if 'observacao' in colunas_bens:
            colunas_para_migrar.append('observacao as observacoes')
        if 'data_criacao' in colunas_bens:
            colunas_para_migrar.append('data_criacao')
        
        if colunas_para_migrar:
            query_migracao = f'''
            INSERT OR IGNORE INTO bem_patrimonial 
            (numero_bem, descricao, localizacao, estado, data_localizacao, observacoes, data_criacao)
            SELECT {', '.join(colunas_para_migrar)}
            FROM bens
            '''
            
            print(f"📝 Executando query: {query_migracao}")
            cursor.execute(query_migracao)
            print(f"✅ Migrados {cursor.rowcount} registros de 'bens' para 'bem_patrimonial'")
        else:
            print("❌ Nenhuma coluna compatível para migração")
        
        # 3. Migrar dados da tabela usuarios para usuario
        print("🔄 Migrando dados de 'usuarios' para 'usuario'...")
        
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_usuarios = [col[1] for col in cursor.fetchall()]
        print(f"📋 Colunas em 'usuarios': {colunas_usuarios}")
        
        colunas_para_migrar = []
        if 'nome' in colunas_usuarios:
            colunas_para_migrar.append('nome')
        if 'email' in colunas_usuarios:
            colunas_para_migrar.append('email')
        if 'senha_hash' in colunas_usuarios:
            colunas_para_migrar.append('senha_hash as senha')
        if 'tipo' in colunas_usuarios:
            colunas_para_migrar.append('tipo')
        if 'data_criacao' in colunas_usuarios:
            colunas_para_migrar.append('data_criacao')
        
        if colunas_para_migrar:
            query_migracao = f'''
            INSERT OR IGNORE INTO usuario 
            (nome, email, senha, tipo, data_criacao)
            SELECT {', '.join(colunas_para_migrar)}
            FROM usuarios
            WHERE ativo = 1 OR 1=1  -- Incluir todos ou apenas ativos
            '''
            
            print(f"📝 Executando query: {query_migracao}")
            cursor.execute(query_migracao)
            print(f"✅ Migrados {cursor.rowcount} registros de 'usuarios' para 'usuario'")
        else:
            print("❌ Nenhuma coluna compatível para migração")
        
        # 4. Criar tabela de logs
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_alteracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tabela TEXT NOT NULL,
            registro_id INTEGER,
            acao TEXT NOT NULL,
            dados_antigos TEXT,
            dados_novos TEXT,
            usuario TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 5. Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM bem_patrimonial")
        total_bens = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM usuario")
        total_usuarios = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bem_patrimonial WHERE estado = 'localizado'")
        localizados = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bem_patrimonial WHERE estado = 'pendente'")
        pendentes = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        print("\n🎉 MIGRAÇÃO FORÇADA CONCLUÍDA!")
        print("📊 Estatísticas:")
        print(f"   • Bens patrimoniais: {total_bens}")
        print(f"   • Localizados: {localizados}")
        print(f"   • Pendentes: {pendentes}")
        print(f"   • Usuários: {total_usuarios}")
        print(f"   • Backup: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO na migração: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    migracao_forcada()