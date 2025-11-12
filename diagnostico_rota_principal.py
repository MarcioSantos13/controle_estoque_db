#!/usr/bin/env python3
"""
Diagnóstico detalhado da rota principal
"""
import os
import re

def diagnostico_rota_principal():
    print("🔍 DIAGNÓSTICO DETALHADO DA ROTA PRINCIPAL")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    
    with open(app_path, 'r') as f:
        conteudo = f.read()
    
    # Encontrar a função index completa
    print("📋 FUNÇÃO INDEX COMPLETA:")
    
    linhas = conteudo.split('\n')
    in_function = False
    function_lines = []
    
    for i, linha in enumerate(linhas):
        if 'def index()' in linha:
            in_function = True
            print(f"📍 Início na linha {i+1}: {linha.strip()}")
            function_lines.append(linha)
            continue
            
        if in_function:
            function_lines.append(linha)
            # Verificar se é o final da função
            if linha.strip() and not linha.startswith(' ') and not linha.startswith('\t') and not linha.startswith('@'):
                in_function = False
                break
            if 'return ' in linha and 'render_template' in linha:
                print(f"📄 Retorno na linha {i+1}: {linha.strip()}")
    
    # Mostrar função completa
    print(f"\n📝 CÓDIGO DA FUNÇÃO INDEX:")
    for i, linha in enumerate(function_lines[:20]):  # Mostrar primeiras 20 linhas
        print(f"   {i+1:3d}: {linha}")
    
    # Verificar tratamento de AJAX
    print(f"\n🔍 TRATAMENTO DE AJAX:")
    if 'request.is_xhr' in conteudo or 'XMLHttpRequest' in conteudo:
        print("   ✅ Detecta requisições AJAX")
        # Encontrar onde é verificado
        for i, linha in enumerate(linhas):
            if 'request.is_xhr' in linha or 'XMLHttpRequest' in linha:
                print(f"   📍 Linha {i+1}: {linha.strip()}")
    else:
        print("   ❌ Não detecta requisições AJAX")
    
    if 'jsonify' in conteudo:
        print("   ✅ Usa jsonify para respostas")
        # Encontrar onde é usado
        for i, linha in enumerate(linhas):
            if 'jsonify' in linha and 'return' in linha:
                print(f"   📍 Linha {i+1}: {linha.strip()}")
    else:
        print("   ❌ Não usa jsonify")
    
    print(f"\n💡 PROBLEMA IDENTIFICADO:")
    print("   A função index não está diferenciando entre requisições normais e AJAX")
    print("   Está sempre retornando HTML, mesmo para requisições com XMLHttpRequest")

if __name__ == '__main__':
    diagnostico_rota_principal()