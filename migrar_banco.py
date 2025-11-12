#!/usr/bin/env python3
"""
Script para migrar a estrutura do banco para o formato da nova aplicação
"""
import sqlite3
import os
from datetime import datetime

def migrar_banco_dados():
    print("🔄 INICIANDO MIGRAÇÃO DO BANCO DE DADOS")
    
    caminho_banco = '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db'
    
    if not os.path.exists(caminho_banco):
        print("❌ Banco de dados não encontrado!")
        return False
    
    # Backup do banco atual
    backup_path = f'/var/www/controle_estoque_db/relatorios/backups/backup_pre_migracao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.system(f'cp "{caminho_banco}" "{backup_path}"')
    print(f"✅ Backup criado: {backup_path}")
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    try:
        print("📊 Analisando estrutura atual...")
        
        # Verificar tabelas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = [t[0] for t in cursor.fetchall()]
        print(f"Tabelas existentes: {tabelas}")
        
        # 1. Migrar tabela 'bens' para 'bem_patrimonial'
        if 'bens' in tabelas and 'bem_patrimonial' not in tabelas:
            print("🔄 Migrando tabela 'bens' para 'bem_patrimonial'...")
            
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
            
            # Migrar dados da tabela bens para bem_patrimonial
            cursor.execute('''
            INSERT OR IGNORE INTO bem_patrimonial 
            (numero_bem, descricao, localizacao, estado, data_localizacao, observacoes, data_criacao)
            SELECT 
                numero, 
                nome,
                localizacao,
                CASE 
                    WHEN situacao LIKE '%localiz%' OR situacao = 'localizado' THEN 'localizado'
                    ELSE 'pendente' 
                END,
                data_localizacao,
                observacao,
                data_criacao
            FROM bens
            ''')
            
            print(f"✅ Migrados {cursor.rowcount} registros de 'bens' para 'bem_patrimonial'")
        
        # 2. Migrar tabela 'usuarios' para 'usuario' (se necessário)
        if 'usuarios' in tabelas and 'usuario' not in tabelas:
            print("🔄 Migrando tabela 'usuarios' para 'usuario'...")
            
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
            
            # Migrar dados de usuarios para usuario
            cursor.execute('''
            INSERT OR IGNORE INTO usuario 
            (nome, email, senha, tipo, data_criacao)
            SELECT 
                nome,
                email,
                senha_hash,
                CASE 
                    WHEN tipo = 'admin' THEN 'admin'
                    ELSE 'user'
                END,
                data_criacao
            FROM usuarios
            WHERE ativo = 1
            ''')
            
            print(f"✅ Migrados {cursor.rowcount} registros de 'usuarios' para 'usuario'")
        
        # 3. Criar tabela de logs se não existir
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
        
        # 4. Verificar dados migrados
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
        
        print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("📊 Estatísticas finais:")
        print(f"   • Bens patrimoniais: {total_bens}")
        print(f"   • Localizados: {localizados}")
        print(f"   • Pendentes: {pendentes}")
        print(f"   • Usuários: {total_usuarios}")
        print(f"   • Backup: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO durante a migração: {e}")
        conn.rollback()
        conn.close()
        return False

def verificar_compatibilidade():
    """Verificar se as tabelas existentes são compatíveis"""
    print("\n🔍 VERIFICANDO COMPATIBILIDADE...")
    
    caminho_banco = '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db'
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Verificar estrutura da tabela bens
    cursor.execute("PRAGMA table_info(bens)")
    colunas_bens = [col[1] for col in cursor.fetchall()]
    print(f"Colunas da tabela 'bens': {colunas_bens}")
    
    # Verificar estrutura da tabela usuarios
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas_usuarios = [col[1] for col in cursor.fetchall()]
    print(f"Colunas da tabela 'usuarios': {colunas_usuarios}")
    
    # Verificar alguns dados de exemplo
    cursor.execute("SELECT numero, nome, localizacao, situacao FROM bens LIMIT 5")
    exemplos_bens = cursor.fetchall()
    print("\n📋 Exemplos de bens:")
    for bem in exemplos_bens:
        print(f"   {bem}")
    
    conn.close()
    
    # Verificar compatibilidade
    colunas_necessarias_bens = ['numero', 'nome', 'localizacao', 'situacao']
    colunas_necessarias_usuarios = ['email', 'nome', 'senha_hash', 'tipo']
    
    compativel_bens = all(col in colunas_bens for col in colunas_necessarias_bens)
    compativel_usuarios = all(col in colunas_usuarios for col in colunas_necessarias_usuarios)
    
    print(f"\n✅ Compatibilidade 'bens': {'SIM' if compativel_bens else 'NÃO'}")
    print(f"✅ Compatibilidade 'usuarios': {'SIM' if compativel_usuarios else 'NÃO'}")
    
    return compativel_bens and compativel_usuarios

if __name__ == '__main__':
    print("=" * 60)
    print("🔄 MIGRADOR DE BANCO DE DADOS - SISTEMA PATRIMONIAL")
    print("=" * 60)
    
    # Primeiro verificar compatibilidade
    if verificar_compatibilidade():
        resposta = input("\n🔧 Deseja prosseguir com a migração? (s/n): ")
        if resposta.lower() == 's':
            if migrar_banco_dados():
                print("\n🎊 Migração concluída! A aplicação deve funcionar agora.")
                print("📝 Reinicie o servidor web se necessário.")
            else:
                print("\n❌ Migração falhou. Verifique o backup criado.")
        else:
            print("⏹️ Migração cancelada.")
    else:
        print("\n❌ Estrutura do banco não é compatível para migração automática.")
        print("💡 Entre em contato com o suporte para migração manual.")