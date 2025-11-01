import sqlite3
import os

DB_PATH = "relatorios/controle_patrimonial.db"

print("🔧 CRIANDO TABELA BENS FORÇADAMENTE...")

try:
    # Conectar ao banco
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Remover tabela se existir
    cursor.execute("DROP TABLE IF EXISTS bens")
    print("✅ Tabela antiga removida")
    
    # 2. Criar nova tabela
    cursor.execute('''
        CREATE TABLE bens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            situacao TEXT DEFAULT 'Pendente',
            localizacao TEXT,
            responsavel TEXT,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Nova tabela criada")
    
    # 3. Criar índice
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
    print("✅ Índice criado")
    
    # 4. Inserir alguns dados de teste
    cursor.execute("INSERT OR IGNORE INTO bens (numero, nome) VALUES (?, ?)", ('TESTE001', 'Item de Teste 1'))
    cursor.execute("INSERT OR IGNORE INTO bens (numero, nome) VALUES (?, ?)", ('TESTE002', 'Item de Teste 2'))
    print("✅ Dados de teste inseridos")
    
    # Commit
    conn.commit()
    
    # 5. Verificar
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
    resultado = cursor.fetchone()
    print(f"✅ TABELA CRIADA: {resultado}")
    
    cursor.execute("SELECT COUNT(*) FROM bens")
    count = cursor.fetchone()[0]
    print(f"✅ REGISTROS: {count}")
    
    conn.close()
    print("🎉 TABELA BENS CRIADA COM SUCESSO!")
    
except Exception as e:
    print(f"❌ ERRO: {e}")