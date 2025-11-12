#!/usr/bin/env python3
"""
Verificar configuração AJAX no app.py do servidor
"""
import os
import re

def verificar_app_py_servidor():
    print("🔍 VERIFICANDO app.py DO SERVIDOR")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    
    if not os.path.exists(app_path):
        print("❌ app.py não encontrado!")
        return
    
    with open(app_path, 'r') as f:
        conteudo = f.read()
    
    print("📋 CONFIGURAÇÕES ENCONTRADAS:")
    
    # Verificar elementos críticos
    verificacoes = {
        'Rota POST para /': '@app.route' in conteudo and 'POST' in conteudo and '"/"' in conteudo,
        'Suporte a AJAX': 'request.is_xhr' in conteudo or 'XMLHttpRequest' in conteudo or 'request.headers.get' in conteudo,
        'Retorno JSON': 'jsonify' in conteudo,
        'Tabela bem_patrimonial': 'bem_patrimonial' in conteudo,
        'Tabela usuario': 'usuario' in conteudo,
    }
    
    for config, encontrado in verificacoes.items():
        status = "✅" if encontrado else "❌"
        print(f"   {status} {config}")
    
    # Encontrar a função index
    print(f"\n🔍 FUNÇÃO INDEX:")
    linhas = conteudo.split('\n')
    for i, linha in enumerate(linhas):
        if 'def index()' in linha or 'def index():' in linha:
            print(f"   📍 Encontrada na linha {i+1}")
            
            # Mostrar próxima linha com POST
            if i > 0 and 'POST' in linhas[i-1]:
                print(f"   📨 Método: {linhas[i-1].strip()}")
            
            # Mostrar algumas linhas da função
            for j in range(i, min(i+15, len(linhas))):
                if 'return ' in linhas[j]:
                    print(f"   📄 Retorno: {linhas[j].strip()}")
                    break
    
    # Verificar se está usando as tabelas corretas
    print(f"\n🗄️  USO DAS TABELAS:")
    tabelas_verificar = ['bem_patrimonial', 'usuario', 'bens', 'usuarios']
    for tabela in tabelas_verificar:
        count = conteudo.count(tabela)
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {tabela}: {count} ocorrências")
    
    print(f"\n💡 RECOMENDAÇÃO:")
    if all([verificacoes['Rota POST para /'], verificacoes['Retorno JSON'], verificacoes['Tabela bem_patrimonial']]):
        print("   ✅ App parece configurado corretamente")
    else:
        print("   ⚠️  App pode precisar de ajustes para AJAX")

if __name__ == '__main__':
    verificar_app_py_servidor()