#!/usr/bin/env python3
"""
Verificar rápida se o AJAX foi adicionado
"""
import os

def verificar_rapido():
    app_path = '/var/www/controle_estoque_db/app.py'
    
    with open(app_path, 'r') as f:
        conteudo = f.read()
    
    if 'X-Requested-With' in conteudo and 'XMLHttpRequest' in conteudo:
        print("✅ Correção AJAX aplicada com sucesso!")
        print("📝 A função index agora detecta requisições AJAX")
        return True
    else:
        print("❌ Correção AJAX não foi aplicada")
        return False

if __name__ == '__main__':
    verificar_rapido()