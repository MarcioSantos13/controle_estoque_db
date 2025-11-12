#!/usr/bin/env python3
"""
Script de diagnóstico melhorado para localizar o banco
"""
import os
import sys
import sqlite3
from pathlib import Path

def encontrar_banco_dados():
    print("🔍 PROCURANDO BANCO DE DADOS...")
    print("=" * 50)
    
    locais_comuns = [
        '/var/www',
        '/var/www/relatorios', 
        '/var/www/controle_estoque_db',
        '/var/www/html',
        os.getcwd(),
        os.path.dirname(os.getcwd()),
        os.path.join(os.getcwd(), '..', 'relatorios'),
        os.path.join(os.getcwd(), 'relatorios')
    ]
    
    bancos_encontrados = []
    
    for local in locais_comuns:
        if os.path.exists(local):
            print(f"\n📁 Verificando: {local}")
            for arquivo in os.listdir(local):
                if arquivo.endswith('.db'):
                    caminho_completo = os.path.join(local, arquivo)
                    tamanho = os.path.getsize(caminho_completo)
                    bancos_encontrados.append((caminho_completo, tamanho))
                    print(f"   ✅ {arquivo} ({tamanho} bytes)")
    
    # Buscar recursivamente
    print(f"\n🔄 Buscando recursivamente em {os.getcwd()}...")
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            if file.endswith('.db'):
                caminho_completo = os.path.join(root, file)
                tamanho = os.path.getsize(caminho_completo)
                bancos_encontrados.append((caminho_completo, tamanho))
                print(f"   ✅ {caminho_completo} ({tamanho} bytes)")
    
    return bancos_encontrados

def verificar_estrutura_banco(caminho_banco):
    """Verificar a estrutura do banco encontrado"""
    print(f"\n🔍 ANALISANDO BANCO: {caminho_banco}")
    
    try:
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()
        
        # Verificar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas = cursor.fetchall()
        
        print("📊 Tabelas encontradas:")
        for tabela in tabelas:
            nome_tabela = tabela[0]
            cursor.execute(f"SELECT COUNT(*) FROM {nome_tabela}")
            count = cursor.fetchone()[0]
            print(f"   • {nome_tabela}: {count} registros")
            
            # Mostrar colunas
            cursor.execute(f"PRAGMA table_info({nome_tabela})")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]
            print(f"     Colunas: {', '.join(colunas_nomes)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Erro ao analisar banco: {e}")
        return False

def verificar_configuracao_app():
    """Verificar como o app está configurado"""
    print(f"\n⚙️ CONFIGURAÇÃO DO APP:")
    
    # Tentar importar o app para ver a configuração
    try:
        sys.path.insert(0, os.getcwd())
        from app import app
        
        print(f"   Root Path: {app.root_path}")
        print(f"   Instance Path: {app.instance_path}")
        
        # Verificar configurações de database
        if 'DATABASE' in app.config:
            print(f"   DATABASE config: {app.config['DATABASE']}")
        
        return True
    except Exception as e:
        print(f"   ❌ Erro ao importar app: {e}")
        return False

def main():
    print("🔍 DIAGNÓSTICO AVANÇADO - LOCALIZAÇÃO DO BANCO")
    print("=" * 60)
    
    # Encontrar bancos
    bancos = encontrar_banco_dados()
    
    if not bancos:
        print("\n❌ NENHUM BANCO DE DADOS ENCONTRADO!")
        return
    
    print(f"\n🎯 TOTAL ENCONTRADO: {len(bancos)} banco(s) de dados")
    
    # Analisar cada banco encontrado
    for caminho, tamanho in bancos:
        verificar_estrutura_banco(caminho)
    
    # Verificar configuração
    verificar_configuracao_app()
    
    print("\n" + "=" * 60)
    print("💡 RECOMENDAÇÕES:")
    
    if bancos:
        print("1. Use o caminho completo do banco no app.py")
        print("2. Configure o DATABASE_URL corretamente")
        print("3. Verifique as permissões do arquivo do banco")
        
        # Sugerir comando para corrigir
        banco_principal = bancos[0][0]
        print(f"\n📝 Para usar o banco encontrado, adicione no app.py:")
        print(f'   app.config["DATABASE"] = "{banco_principal}"')

if __name__ == '__main__':
    main()