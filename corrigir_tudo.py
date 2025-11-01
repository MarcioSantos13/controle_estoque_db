import sqlite3
import os

DB_PATH = "relatorios/controle_patrimonial.db"

print("🔧 CORREÇÃO RÁPIDA DO SISTEMA")

# 1. Criar tabela bens se não existir
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Criar tabela bens SIMPLES
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        nome TEXT NOT NULL,
        situacao TEXT DEFAULT 'Pendente',
        localizacao TEXT,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()

# Verificar
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("✅ Tabelas criadas:", [t[0] for t in tables])

cursor.execute("SELECT COUNT(*) FROM bens")
count = cursor.fetchone()[0]
print(f"✅ Registros na tabela bens: {count}")

conn.close()
print("🎉 Sistema corrigido! Agora execute: python app.py")