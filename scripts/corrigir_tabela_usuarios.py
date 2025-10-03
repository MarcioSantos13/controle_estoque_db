# corrigir_tabela_usuarios.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = '../instance/patrimonio.db'

def corrigir_tabela_usuarios():
    """Corrige definitivamente a tabela usuarios"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=== CORRIGINDO TABELA USUARIOS ===")
        
        # 1. Primeiro, verificar a estrutura atual
        print("\n1. 📋 ESTRUTURA ATUAL:")
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_atuais = cursor.fetchall()
        
        for coluna in colunas_atuais:
            print(f"   {coluna[1]} ({coluna[2]})")
        
        # 2. Lista de TODAS as colunas que devem existir
        colunas_necessarias = [
            ('id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('email', 'TEXT UNIQUE NOT NULL'),
            ('nome', 'TEXT NOT NULL'),
            ('senha_hash', 'TEXT NOT NULL'),
            ('tipo', 'TEXT DEFAULT "usuario"'),
            ('departamento', 'TEXT'),
            ('telefone', 'TEXT'),
            ('ativo', 'INTEGER DEFAULT 1'),
            ('criado_por', 'INTEGER'),
            ('data_criacao', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('data_atualizacao', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]
        
        # 3. Fazer backup dos dados existentes
        print("\n2. 💾 FAZENDO BACKUP DOS DADOS...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios_backup'")
        if not cursor.fetchone():
            cursor.execute("CREATE TABLE usuarios_backup AS SELECT * FROM usuarios")
            print("   ✅ Backup criado: usuarios_backup")
        
        # Contar usuários no backup
        cursor.execute("SELECT COUNT(*) FROM usuarios_backup")
        count_backup = cursor.fetchone()[0]
        print(f"   📊 Usuários no backup: {count_backup}")
        
        # 4. Recriar a tabela com estrutura correta
        print("\n3. 🔨 RECRIANDO TABELA COM ESTRUTURA CORRETA...")
        
        # Dropar tabela atual
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        
        # Criar nova tabela com estrutura completa
        cursor.execute('''
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                tipo TEXT DEFAULT 'usuario',
                departamento TEXT,
                telefone TEXT,
                ativo INTEGER DEFAULT 1,
                criado_por INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 5. Recriar índices
        print("\n4. 📈 CRIANDO ÍNDICES...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)")
        
        # 6. Restaurar dados do backup (se houver)
        if count_backup > 0:
            print("\n5. 🔄 RESTAURANDO DADOS...")
            
            # Verificar quais colunas existem no backup
            cursor.execute("PRAGMA table_info(usuarios_backup)")
            colunas_backup = [col[1] for col in cursor.fetchall()]
            print(f"   Colunas no backup: {colunas_backup}")
            
            # Construir query dinâmica baseada nas colunas disponíveis
            colunas_comuns = []
            for coluna_nome, _ in colunas_necessarias:
                if coluna_nome in colunas_backup:
                    colunas_comuns.append(coluna_nome)
            
            if colunas_comuns:
                colunas_str = ', '.join(colunas_comuns)
                placeholders = ', '.join(['?' for _ in colunas_comuns])
                
                cursor.execute(f"SELECT {colunas_str} FROM usuarios_backup")
                usuarios_backup = cursor.fetchall()
                
                for usuario in usuarios_backup:
                    try:
                        cursor.execute(f"INSERT INTO usuarios ({colunas_str}) VALUES ({placeholders})", usuario)
                    except sqlite3.IntegrityError:
                        print(f"   ⚠️  Pulando usuário duplicado: {usuario[1]}")
                
                print(f"   ✅ {len(usuarios_backup)} usuários restaurados")
        
        conn.commit()
        
        # 7. Verificar estrutura final
        print("\n6. ✅ ESTRUTURA FINAL:")
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_finais = cursor.fetchall()
        
        for coluna in colunas_finais:
            print(f"   {coluna[1]} ({coluna[2]})")
        
        # Contar usuários na nova tabela
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count_final = cursor.fetchone()[0]
        print(f"\n📊 Total de usuários na nova tabela: {count_final}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO GRAVE: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def criar_admin_padrao():
    """Cria usuário administrador padrão"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n" + "="*50)
        print("👑 CRIANDO USUÁRIO ADMINISTRADOR PADRÃO")
        
        # Verificar se já existe admin
        cursor.execute("SELECT id FROM usuarios WHERE tipo = 'admin' LIMIT 1")
        if cursor.fetchone():
            print("   ⚠️  Já existe um administrador no sistema")
            return
        
        # Criar admin padrão
        admin_data = {
            'email': 'admin@empresa.com',
            'nome': 'Administrador do Sistema', 
            'senha': 'admin123',
            'tipo': 'admin',
            'departamento': 'TI',
            'ativo': 1
        }
        
        cursor.execute('''
            INSERT INTO usuarios (email, nome, senha_hash, tipo, departamento, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            admin_data['email'],
            admin_data['nome'],
            generate_password_hash(admin_data['senha']),
            admin_data['tipo'],
            admin_data['departamento'],
            admin_data['ativo']
        ))
        
        conn.commit()
        print("   ✅ ADMIN CRIADO COM SUCESSO!")
        print(f"   📧 E-mail: {admin_data['email']}")
        print(f"   🔑 Senha: {admin_data['senha']}")
        print("   🚨 ALERTA: Alterar a senha após o primeiro login!")
        
    except Exception as e:
        print(f"   ❌ Erro ao criar admin: {e}")
    finally:
        if conn:
            conn.close()

def testar_insercao():
    """Testa se a inserção funciona agora"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n" + "="*50)
        print("🧪 TESTANDO INSERÇÃO...")
        
        # Dados de teste
        teste_data = {
            'email': 'teste_correcao@empresa.com',
            'nome': 'Usuário Teste Correção',
            'senha': '123456',
            'tipo': 'usuario',
            'departamento': 'RH',
            'telefone': '(11) 99999-9999',
            'ativo': 1
        }
        
        cursor.execute('''
            INSERT INTO usuarios (email, nome, senha_hash, tipo, departamento, telefone, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            teste_data['email'],
            teste_data['nome'], 
            generate_password_hash(teste_data['senha']),
            teste_data['tipo'],
            teste_data['departamento'],
            teste_data['telefone'],
            teste_data['ativo']
        ))
        
        conn.commit()
        print("   ✅ INSERÇÃO TESTE FUNCIONOU!")
        print("   🎉 A TABELA ESTÁ CORRIGIDA!")
        
        # Mostrar o usuário inserido
        cursor.execute("SELECT id, email, nome, departamento FROM usuarios WHERE email = ?", 
                      (teste_data['email'],))
        usuario = cursor.fetchone()
        print(f"   👤 Usuário teste: ID {usuario[0]}, {usuario[1]}, Depto: {usuario[3]}")
        
    except Exception as e:
        print(f"   ❌ ERRO NA INSERÇÃO: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🛠️  INICIANDO CORREÇÃO DEFINITIVA DA TABELA USUARIOS")
    print("=" * 60)
    
    # Verificar se arquivo existe
    if not os.path.exists(DB_PATH):
        print(f"❌ Arquivo do banco não encontrado: {DB_PATH}")
        exit(1)
    
    # Executar correção
    if corrigir_tabela_usuarios():
        # Criar admin
        criar_admin_padrao()
        
        # Testar inserção
        testar_insercao()
        
        print("\n" + "=" * 60)
        print("🎉 CORREÇÃO CONCLUÍDA COM SUCESSO!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. ✅ Execute seu sistema Flask")
        print("2. ✅ Tente cadastrar um novo usuário")
        print("3. ✅ Use o admin criado para testes")
        
    else:
        print("\n❌ CORREÇÃO FALHOU!")
        print("Entre em contato com o suporte técnico.")