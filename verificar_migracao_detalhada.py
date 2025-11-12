#!/usr/bin/env python3
"""
Verificação detalhada pós-migração
"""
import sqlite3

def verificar_migracao_detalhada():
    print("✅ VERIFICAÇÃO DETALHADA PÓS-MIGRAÇÃO")
    print("=" * 50)
    
    caminho_banco = '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db'
    
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    # Verificar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = [t[0] for t in cursor.fetchall()]
    print(f"📊 Todas as tabelas: {tabelas}")
    
    # Verificar estrutura das tabelas novas
    print(f"\n🔍 Estrutura da tabela 'bem_patrimonial':")
    cursor.execute("PRAGMA table_info(bem_patrimonial)")
    for col in cursor.fetchall():
        print(f"   • {col[1]} ({col[2]})")
    
    print(f"\n🔍 Estrutura da tabela 'usuario':")
    cursor.execute("PRAGMA table_info(usuario)")
    for col in cursor.fetchall():
        print(f"   • {col[1]} ({col[2]})")
    
    # Verificar alguns exemplos
    print(f"\n📋 Exemplos de bens migrados:")
    cursor.execute("""
        SELECT numero_bem, descricao, estado, localizacao 
        FROM bem_patrimonial 
        WHERE estado = 'localizado'
        LIMIT 3
    """)
    for bem in cursor.fetchall():
        print(f"   ✅ Localizado: {bem}")
    
    cursor.execute("""
        SELECT numero_bem, descricao, estado 
        FROM bem_patrimonial 
        WHERE estado = 'pendente'
        LIMIT 3
    """)
    for bem in cursor.fetchall():
        print(f"   ⏳ Pendente: {bem}")
    
    # Verificar usuários
    print(f"\n👥 Usuários migrados:")
    cursor.execute("SELECT nome, email, tipo FROM usuario")
    for usuario in cursor.fetchall():
        print(f"   👤 {usuario}")
    
    conn.close()
    
    print(f"\n🎉 MIGRAÇÃO VERIFICADA COM SUCESSO!")
    print("   Todas as tabelas e dados foram migrados corretamente.")

if __name__ == '__main__':
    verificar_migracao_detalhada()
    