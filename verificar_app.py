#!/usr/bin/env python3
"""
Verificar diferenças na configuração do app.py
"""
import os
import importlib.util

def verificar_app_py():
    print("🔍 ANALISANDO app.py DO SERVIDOR")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    
    if not os.path.exists(app_path):
        print("❌ app.py não encontrado!")
        return
    
    # Ler o app.py
    with open(app_path, 'r') as f:
        conteudo = f.read()
    
    # Verificar configurações importantes
    verificacoes = {
        'DEBUG': 'DEBUG' in conteudo and 'True' in conteudo,
        'AJAX': 'XMLHttpRequest' in conteudo,
        'JSONIFY': 'jsonify' in conteudo,
        'DATABASE': 'controle_patrimonial.db' in conteudo,
        'SECRET_KEY': 'SECRET_KEY' in conteudo,
    }
    
    print("📋 Configurações encontradas:")
    for config, encontrado in verificacoes.items():
        status = "✅" if encontrado else "❌"
        print(f"  {status} {config}: {'Encontrado' if encontrado else 'Não encontrado'}")
    
    # Verificar se há rota para AJAX
    if '@app.route' in conteudo and 'POST' in conteudo:
        print("✅ Rotas POST encontradas")
    else:
        print("❌ Nenhuma rota POST encontrada")
    
    print("\n📝 Trechos relevantes:")
    linhas = conteudo.split('\n')
    for i, linha in enumerate(linhas):
        if 'jsonify' in linha or 'request.json' in linha or 'XMLHttpRequest' in linha:
            print(f"  Linha {i+1}: {linha.strip()}")
    
    print("\n" + "=" * 50)

if __name__ == '__main__':
    verificar_app_py()