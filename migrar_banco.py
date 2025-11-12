#!/usr/bin/env python3
"""
Script de migração universal - funciona em servidor e desenvolvimento
"""
import sqlite3
import os
import sys
from datetime import datetime

def encontrar_banco_dados():
    """Encontrar automaticamente o banco de dados"""
    locais_comuns = [
        # Servidor
        '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db',
        '/var/www/relatorios/controle_patrimonial.db',
        
        # Desenvolvimento
        'database.db',
        'relatorios/controle_patrimonial.db',
        '../relatorios/controle_patrimonial.db',
        os.path.join(os.path.dirname(__file__), 'database.db'),
        os.path.join(os.path.dirname(__file__), 'relatorios', 'controle_patrimonial.db'),
    ]
    
    for caminho in locais_comuns:
        if os.path.exists(caminho):
            print(f"✅ Banco encontrado: {caminho}")
            return caminho
    
    print("❌ Nenhum banco de dados encontrado nos locais comuns")
    return None

def verificar_estrutura_atual(caminho_banco):
    """Verificar qual estrutura o banco atual possui"""
    print(f"\n🔍 ANALISANDO ESTRUTURA DO BANCO: {caminho_banco}")
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Verificar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = [t[0] for t in cursor.fetchall()]
    print(f"📊 Tabelas encontradas: {tabelas}")
    
    estrutura = {
        'tem_bens': 'bens' in tabelas,
        'tem_usuarios': 'usuarios' in tabelas,
        'tem_bem_patrimonial': 'bem_patrimonial' in tabelas,
        'tem_usuario': 'usuario' in tabelas,
        'tabelas': tabelas
    }
    
    # Verificar estrutura das tabelas existentes
    for tabela in tabelas:
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = [col[1] for col in cursor.fetchall()]
        print(f"   • {tabela}: {colunas}")
    
    conn.close()
    return estrutura

def migrar_para_nova_estrutura(caminho_banco, estrutura):
    """Migrar da estrutura antiga para a nova"""
    print("\n🔄 INICIANDO MIGRAÇÃO PARA NOVA ESTRUTURA")
    
    # Backup
    backup_path = f'backup_pre_migracao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    os.system(f'cp "{caminho_banco}" "{backup_path}"')
    print(f"✅ Backup criado: {backup_path}")
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    try:
        # 1. Migrar bens → bem_patrimonial (se necessário)
        if estrutura['tem_bens'] and not estrutura['tem_bem_patrimonial']:
            print("📦 Migrando tabela 'bens' para 'bem_patrimonial'...")
            
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
            
            # Verificar colunas disponíveis na tabela bens
            cursor.execute("PRAGMA table_info(bens)")
            colunas_bens = [col[1] for col in cursor.fetchall()]
            
            # Construir query de migração baseada nas colunas disponíveis
            colunas_origem = []
            mapeamento = {
                'numero': 'numero',
                'nome': 'nome', 
                'localizacao': 'localizacao',
                'situacao': 'situacao',
                'data_localizacao': 'data_localizacao',
                'observacao': 'observacao',
                'data_criacao': 'data_criacao'
            }
            
            for col_origem, col_alias in mapeamento.items():
                if col_origem in colunas_bens:
                    colunas_origem.append(col_origem)
            
            if colunas_origem:
                colunas_sql = ', '.join(colunas_origem)
                cursor.execute(f'''
                INSERT OR IGNORE INTO bem_patrimonial 
                (numero_bem, descricao, localizacao, estado, data_localizacao, observacoes, data_criacao)
                SELECT 
                    {', '.join(colunas_origem)}
                FROM bens
                ''')
                print(f"✅ Migrados {cursor.rowcount} registros de 'bens' para 'bem_patrimonial'")
            else:
                print("❌ Nenhuma coluna compatível encontrada na tabela 'bens'")
        
        # 2. Migrar usuarios → usuario (se necessário)
        if estrutura['tem_usuarios'] and not estrutura['tem_usuario']:
            print("👥 Migrando tabela 'usuarios' para 'usuario'...")
            
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
            
            # Verificar colunas disponíveis na tabela usuarios
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas_usuarios = [col[1] for col in cursor.fetchall()]
            
            colunas_origem = []
            mapeamento = {
                'nome': 'nome',
                'email': 'email',
                'senha_hash': 'senha_hash',
                'tipo': 'tipo',
                'data_criacao': 'data_criacao'
            }
            
            for col_origem, col_alias in mapeamento.items():
                if col_origem in colunas_usuarios:
                    colunas_origem.append(col_origem)
            
            if colunas_origem:
                colunas_sql = ', '.join(colunas_origem)
                cursor.execute(f'''
                INSERT OR IGNORE INTO usuario 
                (nome, email, senha, tipo, data_criacao)
                SELECT 
                    {', '.join(colunas_origem)}
                FROM usuarios
                ''')
                print(f"✅ Migrados {cursor.rowcount} registros de 'usuarios' para 'usuario'")
            else:
                print("❌ Nenhuma coluna compatível encontrada na tabela 'usuarios'")
        
        # 3. Criar tabelas da nova aplicação se não existirem
        print("⚙️ Criando tabelas da nova aplicação...")
        
        # Tabela de logs
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
        
        # 4. Verificar resultado final
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
        
        print("\n🎉 MIGRAÇÃO CONCLUÍDA!")
        print("📊 Estatísticas finais:")
        print(f"   • Bens patrimoniais: {total_bens}")
        print(f"   • Localizados: {localizados}")
        print(f"   • Pendentes: {pendentes}")
        print(f"   • Usuários: {total_usuarios}")
        print(f"   • Backup: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO durante migração: {e}")
        conn.rollback()
        conn.close()
        return False

def criar_estrutura_inicial(caminho_banco):
    """Criar estrutura inicial se o banco estiver vazio"""
    print("\n📦 CRIANDO ESTRUTURA INICIAL DO BANCO")
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    try:
        # Tabela de bens patrimoniais
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
        
        # Tabela de usuários
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
        
        # Tabela de logs
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
        
        # Inserir usuário admin padrão
        cursor.execute('''
        INSERT OR IGNORE INTO usuario (nome, email, senha, tipo)
        VALUES (?, ?, ?, ?)
        ''', ('Administrador', 'admin@cead.com', 'admin123', 'admin'))
        
        # Inserir alguns bens de exemplo
        bens_exemplo = [
            ('CEAD-001', 'Computador Desktop i5', 'Laboratório A', 'pendente'),
            ('CEAD-002', 'Projetor Epson', 'Sala 101', 'pendente'),
            ('CEAD-003', 'Mesa Executiva', 'Diretoria', 'pendente'),
        ]
        
        cursor.executemany('''
        INSERT OR IGNORE INTO bem_patrimonial (numero_bem, descricao, localizacao, estado)
        VALUES (?, ?, ?, ?)
        ''', bens_exemplo)
        
        conn.commit()
        conn.close()
        
        print("✅ Estrutura inicial criada com sucesso!")
        print("🔑 Credenciais padrão:")
        print("   Email: admin@cead.com")
        print("   Senha: admin123")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar estrutura: {e}")
        conn.rollback()
        conn.close()
        return False

def main():
    print("=" * 60)
    print("🔄 MIGRADOR UNIVERSAL - SISTEMA PATRIMONIAL")
    print("=" * 60)
    
    # Encontrar banco
    caminho_banco = encontrar_banco_dados()
    if not caminho_banco:
        print("\n💡 Dica: Crie um banco manualmente ou especifique o caminho")
        return
    
    # Analisar estrutura atual
    estrutura = verificar_estrutura_atual(caminho_banco)
    
    # Decidir ação baseada na estrutura
    if estrutura['tem_bem_patrimonial'] and estrutura['tem_usuario']:
        print("\n✅ O banco já está na estrutura nova!")
        print("📝 Nenhuma migração necessária.")
        
    elif estrutura['tem_bens'] or estrutura['tem_usuarios']:
        print("\n🔄 Estrutura antiga detectada. Migração necessária.")
        resposta = input("🔧 Prosseguir com migração? (s/n): ")
        if resposta.lower() == 's':
            migrar_para_nova_estrutura(caminho_banco, estrutura)
        else:
            print("⏹️ Migração cancelada.")
    
    else:
        print("\n📦 Banco vazio ou estrutura desconhecida.")
        resposta = input("🔧 Criar estrutura inicial? (s/n): ")
        if resposta.lower() == 's':
            criar_estrutura_inicial(caminho_banco)
        else:
            print("⏹️ Ação cancelada.")

if __name__ == '__main__':
    main()