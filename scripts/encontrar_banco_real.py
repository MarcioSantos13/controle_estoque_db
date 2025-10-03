# encontrar_banco_real.py
import sqlite3
import os
import glob

def encontrar_todos_bancos():
    """Encontra TODOS os arquivos .db no projeto inteiro"""
    print("🔍 PROCURANDO TODOS OS ARQUIVOS .db NO PROJETO...")
    print("=" * 60)
    
    bancos_encontrados = []
    
    # Procurar em todo o projeto
    for root, dirs, files in os.walk('..'):
        for file in files:
            if file.endswith('.db'):
                caminho_completo = os.path.abspath(os.path.join(root, file))
                tamanho = os.path.getsize(caminho_completo)
                bancos_encontrados.append((caminho_completo, tamanho))
                print(f"📁 {caminho_completo}")
                print(f"   📊 Tamanho: {tamanho} bytes ({tamanho/1024:.1f} KB)")
    
    return bancos_encontrados

def verificar_db_path_no_app():
    """Procura a variável DB_PATH no app.py"""
    print("\n" + "=" * 60)
    print("🔧 PROCURANDO DB_PATH NO app.py")
    print("=" * 60)
    
    app_path = '../app.py'
    if os.path.exists(app_path):
        with open(app_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
            # Procurar por DB_PATH ou caminhos de banco
            linhas = conteudo.split('\n')
            for i, linha in enumerate(linhas):
                if 'DB_PATH' in linha or 'sqlite3.connect' in linha:
                    print(f"Linha {i+1}: {linha.strip()}")
                    
                    # Extrair o caminho se possível
                    if 'sqlite3.connect(' in linha:
                        inicio = linha.find('sqlite3.connect(') + len('sqlite3.connect(')
                        fim = linha.find(')', inicio)
                        if fim != -1:
                            caminho = linha[inicio:fim].strip('\"\'')
                            print(f"   🎯 CAMINHO ENCONTRADO: {caminho}")
    else:
        print("❌ app.py não encontrado!")

def testar_bancos_encontrados(bancos):
    """Testa cada banco encontrado para ver qual tem a tabela usuarios"""
    print("\n" + "=" * 60)
    print("🧪 TESTANDO BANCOS ENCONTRADOS")
    print("=" * 60)
    
    for caminho, tamanho in bancos:
        print(f"\n🔎 Testando: {os.path.basename(caminho)}")
        print(f"   📍 Caminho: {caminho}")
        
        try:
            conn = sqlite3.connect(caminho)
            cursor = conn.cursor()
            
            # Verificar se tem tabela usuarios
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
            if cursor.fetchone():
                print("   ✅ TEM tabela 'usuarios'")
                
                # Verificar estrutura
                cursor.execute("PRAGMA table_info(usuarios)")
                colunas = cursor.fetchall()
                colunas_nomes = [col[1] for col in colunas]
                
                print("   📋 Estrutura:")
                for coluna in colunas:
                    print(f"      {coluna[1]} ({coluna[2]})")
                
                # Verificar coluna departamento
                if 'departamento' in colunas_nomes:
                    print("   🎯 ✅ TEM coluna 'departamento'")
                else:
                    print("   ❌ NÃO TEM coluna 'departamento'")
                
                # Contar usuários
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                print(f"   👥 Usuários: {count}")
                
            else:
                print("   ❌ NÃO TEM tabela 'usuarios'")
            
            conn.close()
            
        except Exception as e:
            print(f"   💥 Erro: {e}")

def criar_banco_correto():
    """Cria o banco correto no local padrão"""
    print("\n" + "=" * 60)
    print("🛠️  CRIANDO BANCO CORRETO")
    print("=" * 60)
    
    # Locais padrão onde o Flask geralmente procura
    locais_padrao = [
        '../instance/patrimonio.db',
        './instance/patrimonio.db',
        '../patrimonio.db', 
        './patrimonio.db',
        '../database.db',
        './database.db'
    ]
    
    for local in locais_padrao:
        caminho_absoluto = os.path.abspath(local)
        print(f"\n📁 Tentando: {caminho_absoluto}")
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(caminho_absoluto), exist_ok=True)
        
        try:
            conn = sqlite3.connect(caminho_absoluto)
            cursor = conn.cursor()
            
            # Criar tabela usuarios com estrutura completa
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
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
            
            # Criar índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)")
            
            conn.commit()
            
            # Verificar se criou
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = [col[1] for col in cursor.fetchall()]
            
            if 'departamento' in colunas:
                print("   ✅ Banco criado com estrutura CORRETA!")
                print("   📋 Colunas:", ', '.join(colunas))
            else:
                print("   ⚠️  Banco criado mas sem coluna departamento")
            
            conn.close()
            
        except Exception as e:
            print(f"   💥 Erro ao criar: {e}")

if __name__ == "__main__":
    print("🎯 ENCONTRANDO O BANCO REAL DO FLASK")
    print("=" * 60)
    
    # 1. Verificar DB_PATH no app.py
    verificar_db_path_no_app()
    
    # 2. Encontrar todos os bancos
    bancos = encontrar_todos_bancos()
    
    if not bancos:
        print("\n❌ NENHUM BANCO .db ENCONTRADO!")
        print("Criando banco padrão...")
        criar_banco_correto()
    else:
        # 3. Testar bancos encontrados
        testar_bancos_encontrados(bancos)
    
    print("\n" + "=" * 60)
    print("🎯 SOLUÇÃO:")
    print("1. Execute: python encontrar_banco_real.py")
    print("2. Veja qual banco está sendo usado")
    print("3. Se necessário, execute a correção no banco correto")