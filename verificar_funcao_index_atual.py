#!/usr/bin/env python3
"""
Verificar o código atual da função index
"""
import os

def verificar_funcao_index_atual():
    print("🔍 VERIFICANDO FUNÇÃO INDEX ATUAL")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    
    with open(app_path, 'r') as f:
        linhas = f.readlines()
    
    # Encontrar a função index
    inicio = -1
    for i, linha in enumerate(linhas):
        if 'def index():' in linha and 'POST' in linhas[i-1] if i > 0 else False:
            inicio = i
            break
    
    if inicio == -1:
        print("❌ Função index não encontrada")
        return
    
    print(f"📍 Função index encontrada na linha {inicio + 1}")
    
    # Mostrar as primeiras 30 linhas da função
    print(f"\n📝 PRIMEIRAS 30 LINHAS DA FUNÇÃO INDEX:")
    for i in range(inicio, min(inicio + 30, len(linhas))):
        print(f"{i+1:4d}: {linhas[i].rstrip()}")
    
    # Verificar especificamente a lógica AJAX
    print(f"\n🔍 PROCURANDO POR LÓGICA AJAX:")
    encontrou_ajax = False
    for i, linha in enumerate(linhas[inicio:inicio+50], start=inicio):
        if 'X-Requested-With' in linha or 'XMLHttpRequest' in linha:
            print(f"✅ Linha {i+1}: {linha.strip()}")
            encontrou_ajax = True
            
            # Mostrar contexto
            for j in range(max(inicio, i-2), min(len(linhas), i+3)):
                if j != i:
                    print(f"   {j+1:4d}: {linhas[j].rstrip()}")
    
    if not encontrou_ajax:
        print("❌ Lógica AJAX não encontrada na função index")

if __name__ == '__main__':
    verificar_funcao_index_atual()