# corrigir_banco_real.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

# O BANCO REAL QUE SEU FLASK ESTÁ USANDO
DB_PATH_REAL = '../relatorios/controle_patrimonial.db'

def corrigir_banco_real():
    """Corrige o banco real que o Flask está usando"""
    print(f"🎯 CORRIGINDO O BANCO REAL: {DB_PATH_REAL}")
    print("=" * 60)
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH_REAL)
        cursor = conn.cursor()
        
        # 1. Verificar estrutura atual
        print("1. 📋 ESTRUTURA ATUAL:")
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_atuais = [col[1] for col in cursor.fetchall()]
        print("   Colunas:", ', '.join(colunas_atuais))
        
        # 2. Adicionar colunas faltantes
        print("\n2. 🔧 ADICIONANDO COLUNAS FALTANTES:")
        
        colunas_faltantes = []
        if 'departamento' not in colunas_atuais:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN departamento TEXT")
            colunas_faltantes.append('departamento')
            print("   ✅ Adicionada: departamento")
        
        if 'telefone' not in colunas_atuais:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN telefone TEXT")
            colunas_faltantes.append('telefone')
            print("   ✅ Adicionada: telefone")
        
        if 'criado_por' not in colunas_atuais:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN criado_por INTEGER")
            colunas_faltantes.append('criado_por')
            print("   ✅ Adicionada: criado_por")
        
        # 3. Verificar estrutura final
        print("\n3. ✅ ESTRUTURA FINAL:")
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_finais = [col[1] for col in cursor.fetchall()]
        print("   Colunas:", ', '.join(colunas_finais))
        
        # 4. Testar inserção
        print("\n4. 🧪 TESTANDO INSERÇÃO:")
        try:
            cursor.execute('''
                INSERT INTO usuarios (
                    email, nome, senha_hash, tipo, departamento, telefone, ativo
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'teste_corrigido@empresa.com',
                'Usuário Teste Corrigido',
                generate_password_hash('123456'),
                'usuario',
                'RH',  # ← AGORA TEM DEPARTAMENTO!
                '(11) 99999-9999',  # ← AGORA TEM TELEFONE!
                1
            ))
            
            conn.commit()
            print("   ✅ INSERÇÃO FUNCIONOU!")
            
            # Mostrar o usuário inserido
            cursor.execute("SELECT id, email, nome, departamento FROM usuarios WHERE email = ?", 
                          ('teste_corrigido@empresa.com',))
            usuario = cursor.fetchone()
            print(f"   👤 Usuário: ID {usuario[0]}, {usuario[1]}, Depto: {usuario[3]}")
            
        except Exception as e:
            print(f"   ❌ Erro na inserção: {e}")
            conn.rollback()
        
        # 5. Verificar usuários existentes
        print("\n5. 📊 USUÁRIOS EXISTENTES:")
        cursor.execute("SELECT id, email, nome, tipo FROM usuarios")
        usuarios = cursor.fetchall()
        
        for usuario in usuarios:
            print(f"   👤 ID {usuario[0]}: {usuario[1]} ({usuario[2]}) - {usuario[3]}")
        
        print(f"\n🎉 BANCO CORRIGIDO COM SUCESSO!")
        print(f"📍 Local: {DB_PATH_REAL}")
        
        if colunas_faltantes:
            print(f"✅ Colunas adicionadas: {', '.join(colunas_faltantes)}")
        else:
            print("✅ Todas as colunas já existiam")
            
        return True
        
    except Exception as e:
        print(f"❌ ERRO GRAVE: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def verificar_configuracao_app():
    """Verifica como o app.py está configurado"""
    print("\n" + "=" * 60)
    print("🔧 CONFIGURAÇÃO DO app.py")
    print("=" * 60)
    
    app_path = '../app.py'
    if os.path.exists(app_path):
        with open(app_path, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
            # Procurar DB_PATH
            if 'DB_PATH' in conteudo:
                print("✅ DB_PATH definido no app.py")
                # Extrair valor
                linhas = conteudo.split('\n')
                for linha in linhas:
                    if 'DB_PATH' in linha and '=' in linha:
                        print(f"   {linha.strip()}")
            else:
                print("❌ DB_PATH não encontrado no app.py")
                print("   O Flask deve estar usando caminho relativo")
                
    else:
        print("❌ app.py não encontrado!")

if __name__ == "__main__":
    print("🛠️  CORREÇÃO DO BANCO REAL DO FLASK")
    print("=" * 60)
    
    # Verificar se o banco existe
    if not os.path.exists(DB_PATH_REAL):
        print(f"❌ Banco não encontrado: {DB_PATH_REAL}")
        print("   Execute primeiro o script de criação de emergência")
        exit(1)
    
    # Verificar configuração
    verificar_configuracao_app()
    
    # Corrigir o banco
    if corrigir_banco_real():
        print("\n" + "=" * 60)
        print("🎯 PRÓXIMOS PASSOS:")
        print("1. ✅ REINICIE o servidor Flask (Ctrl+C e python app.py)")
        print("2. ✅ Teste o cadastro de usuários no sistema")
        print("3. ✅ O erro 'no column named departamento' deve sumir")
    else:
        print("\n❌ Correção falhou!")