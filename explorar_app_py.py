#!/usr/bin/env python3
"""
Explorar a estrutura atual do app.py
"""
import os

def explorar_app_py():
    print("🔍 EXPLORANDO ESTRUTURA DO app.py")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    
    with open(app_path, 'r') as f:
        linhas = f.readlines()
    
    print("📋 ESTRUTURA DO ARQUIVO:")
    
    # Encontrar todas as rotas e funções
    funcoes = []
    for i, linha in enumerate(linhas):
        if '@app.route' in linha:
            print(f"📍 Rota na linha {i+1}: {linha.strip()}")
            # Procurar a função associada
            for j in range(i+1, min(i+5, len(linhas))):
                if 'def ' in linhas[j]:
                    print(f"   🎯 Função: {linhas[j].strip()}")
                    funcoes.append((i+1, linhas[j].strip()))
                    break
    
    # Procurar especificamente por funções relacionadas à página principal
    print(f"\n🔍 PROCURANDO FUNÇÃO DA PÁGINA PRINCIPAL:")
    for i, linha in enumerate(linhas):
        if 'def ' in linha and ('index' in linha.lower() or 'home' in linha.lower() or 'main' in linha.lower()):
            print(f"   📍 Linha {i+1}: {linha.strip()}")
            # Mostrar a rota anterior
            for j in range(max(0, i-5), i):
                if '@app.route' in linhas[j]:
                    print(f"   🛣️  Rota: {linhas[j].strip()}")
    
    # Mostrar as primeiras 50 linhas para contexto
    print(f"\n📄 PRIMEIRAS 50 LINHAS:")
    for i in range(min(50, len(linhas))):
        print(f"{i+1:4d}: {linhas[i].rstrip()}")
    
    return linhas

if __name__ == '__main__':
    explorar_app_py()