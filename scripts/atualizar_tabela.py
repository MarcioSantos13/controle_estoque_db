# atualizar_tabela.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = '../instance/patrimonio.db'

def verificar_estrutura_tabela():
    """Verifica a estrutura atual da tabela usuarios"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=== ESTRUTURA ATUAL DA TABELA usuarios ===")
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = cursor.fetchall()
        
        if not colunas:
            print("❌ Tabela 'usuarios' não existe!")
            return []
        
        print("Colunas encontradas:")
        for coluna in colunas:
            print(f"  {coluna[1]} ({coluna[2]})")
        
        return [coluna[1] for coluna in colunas]
        
    except Exception as e:
        print(f"Erro ao verificar estrutura: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_colunas_faltantes():
    """Adiciona colunas que estão faltando na tabela"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n=== ADICIONANDO COLUNAS FALTANTES ===")
        
        # Colunas que PRECISAM existir baseado no seu código
        colunas_necessarias = ['departamento', 'telefone', 'criado_por', 'data_atualizacao']
        colunas_existentes = verificar_estrutura_tabela()
        
        colunas_adicionadas = []
        for coluna in colunas_necessarias:
            if coluna not in colunas_existentes:
                print(f"➕ Adicionando coluna: {coluna}")
                
                if coluna == 'departamento':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN departamento TEXT")
                elif coluna == 'telefone':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN telefone TEXT")
                elif coluna == 'criado_por':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN criado_por INTEGER")
                elif coluna == 'data_atualizacao':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                
                colunas_adicionadas.append(coluna)
        
        conn.commit()
        
        if colunas_adicionadas:
            print(f"✅ Colunas adicionadas: {', '.join(colunas_adicionadas)}")
        else:
            print("✅ Todas as colunas já existem!")
        
        return colunas_adicionadas
        
    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def criar_usuario_administracao():
    """Cria um usuário administrador padrão"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n=== CRIANDO USUÁRIO ADMINISTRADOR ===")
        
        # Verificar se já existe algum administrador
        cursor.execute("SELECT id FROM usuarios WHERE tipo = 'admin' LIMIT 1")
        if cursor.fetchone():
            print("⚠️  Já existe um usuário administrador no sistema")
            return
        
        # Dados do administrador padrão
        email_admin = "admin@empresa.com"
        nome_admin = "Administrador do Sistema"
        senha_admin = "admin123"  # Senha padrão - deve ser alterada depois
        
        # Verificar se o email já existe
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email_admin,))
        if cursor.fetchone():
            print("⚠️  Usuário admin já existe")
            return
        
        # Inserir usuário administrador
        cursor.execute('''
            INSERT INTO usuarios (
                email, nome, senha_hash, tipo, departamento, ativo
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            email_admin,
            nome_admin,
            generate_password_hash(senha_admin),
            'admin',
            'TI',
            1
        ))
        
        conn.commit()
        print("✅ Usuário administrador criado com sucesso!")
        print(f"📧 E-mail: {email_admin}")
        print(f"🔑 Senha: {senha_admin}")
        print("⚠️  ALERTA: Alterar esta senha após o primeiro login!")
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário admin: {e}")
    finally:
        if conn:
            conn.close()

def mostrar_local_banco():
    """Mostra onde o banco está salvo"""
    print("\n=== LOCALIZAÇÃO DO BANCO DE DADOS ===")
    print(f"📁 Caminho absoluto: {os.path.abspath(DB_PATH)}")
    print(f"📁 Pasta: {os.path.dirname(os.path.abspath(DB_PATH))}")
    print(f"✅ Arquivo existe: {os.path.exists(DB_PATH)}")
    
    if os.path.exists(DB_PATH):
        tamanho = os.path.getsize(DB_PATH)
        print(f"📊 Tamanho do arquivo: {tamanho} bytes ({tamanho/1024:.2f} KB)")

def mostrar_todas_tabelas():
    """Mostra todas as tabelas do banco"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n=== TODAS AS TABELAS DO BANCO ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tabelas = cursor.fetchall()
        
        if tabelas:
            for tabela in tabelas:
                print(f"📊 {tabela[0]}")
                
                # Mostrar quantidade de registros
                cursor.execute(f"SELECT COUNT(*) FROM {tabela[0]}")
                count = cursor.fetchone()[0]
                print(f"   📈 Registros: {count}")
        else:
            print("❌ Nenhuma tabela encontrada!")
            
    except Exception as e:
        print(f"Erro ao listar tabelas: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 INICIANDO ATUALIZAÇÃO DO BANCO DE DADOS")
    print("=" * 50)
    
    # 1. Mostrar local do banco
    mostrar_local_banco()
    
    # 2. Mostrar tabelas existentes
    mostrar_todas_tabelas()
    
    # 3. Verificar e atualizar estrutura
    colunas_antes = verificar_estrutura_tabela()
    colunas_adicionadas = adicionar_colunas_faltantes()
    colunas_depois = verificar_estrutura_tabela()
    
    # 4. Criar usuário admin (apenas se solicitado)
    print("\n" + "=" * 50)
    criar_admin = input("Deseja criar um usuário administrador? (s/n): ").lower().strip()
    if criar_admin in ['s', 'sim', 'y', 'yes']:
        criar_usuario_administracao()
    
    # 5. Resumo final
    print("\n" + "=" * 50)
    print("🎉 ATUALIZAÇÃO CONCLUÍDA!")
    if colunas_adicionadas:
        print(f"✅ Colunas adicionadas: {', '.join(colunas_adicionadas)}")
    else:
        print("✅ Nenhuma alteração necessária na estrutura")
    
    print(f"📋 Total de colunas na tabela usuarios: {len(colunas_depois)}")