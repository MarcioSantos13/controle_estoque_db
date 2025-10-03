# investigar_banco.py
import sqlite3
import os
import sys

def encontrar_bancos_sqlite():
    """Encontra todos os arquivos .db no projeto"""
    print("🔍 PROCURANDO TODOS OS BANCOS SQLITE NO PROJETO...")
    
    bancos_encontrados = []
    for root, dirs, files in os.walk('..'):
        for file in files:
            if file.endswith(('.db', '.sqlite', '.sqlite3')):
                caminho_completo = os.path.join(root, file)
                bancos_encontrados.append(caminho_completo)
                print(f"📁 {caminho_completo}")
    
    return bancos_encontrados

def verificar_tabela_em_todos_bancos():
    """Verifica a tabela usuarios em todos os bancos encontrados"""
    bancos = encontrar_bancos_sqlite()
    
    print("\n" + "="*60)
    print("📊 VERIFICANDO TABELA 'usuarios' EM TODOS OS BANCOS")
    print("="*60)
    
    for banco_path in bancos:
        print(f"\n🔎 Analisando: {banco_path}")
        
        try:
            conn = sqlite3.connect(banco_path)
            cursor = conn.cursor()
            
            # Verificar se tabela existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
            tabela_existe = cursor.fetchone()
            
            if tabela_existe:
                print("   ✅ Tabela 'usuarios' EXISTE")
                
                # Verificar estrutura
                cursor.execute("PRAGMA table_info(usuarios)")
                colunas = cursor.fetchall()
                print("   📋 Estrutura:")
                for coluna in colunas:
                    print(f"      {coluna[1]} ({coluna[2]})")
                
                # Verificar se tem a coluna departamento
                colunas_nomes = [col[1] for col in colunas]
                if 'departamento' in colunas_nomes:
                    print("   🎯 ✅ COLUNA 'departamento' ENCONTRADA!")
                else:
                    print("   ❌ COLUNA 'departamento' NÃO ENCONTRADA!")
                
                # Contar usuários
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                print(f"   👥 Total de usuários: {count}")
                
            else:
                print("   ❌ Tabela 'usuarios' NÃO EXISTE")
            
            conn.close()
            
        except Exception as e:
            print(f"   💥 Erro ao acessar: {e}")

def verificar_configuracao_flask():
    """Tenta encontrar a configuração do banco no Flask"""
    print("\n" + "="*60)
    print("🔧 VERIFICANDO CONFIGURAÇÃO DO FLASK")
    print("="*60)
    
    # Procurar por arquivos de configuração
    config_files = []
    for root, dirs, files in os.walk('..'):
        for file in files:
            if file in ['app.py', 'config.py', '__init__.py', 'models.py']:
                caminho = os.path.join(root, file)
                config_files.append(caminho)
    
    for config_file in config_files:
        print(f"\n📄 Analisando: {config_file}")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                if 'sqlite' in conteudo.lower() or 'database' in conteudo.lower():
                    print("   ⚠️  Possível configuração de banco encontrada")
                    # Mostrar linhas relevantes
                    linhas = conteudo.split('\n')
                    for i, linha in enumerate(linhas):
                        if 'sqlite' in linha.lower() or 'database' in linha.lower():
                            print(f"      Linha {i+1}: {linha.strip()}")
        except Exception as e:
            print(f"   Erro ao ler arquivo: {e}")

if __name__ == "__main__":
    print("🕵️ INVESTIGAÇÃO DO BANCO DE DADOS")
    print("="*60)
    
    verificar_tabela_em_todos_bancos()
    verificar_configuracao_flask()
    
    print("\n" + "="*60)
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. Execute este script para encontrar TODOS os bancos")
    print("2. Compare com o caminho que seu Flask está usando")
    print("3. Verifique se há múltiplos bancos no projeto")