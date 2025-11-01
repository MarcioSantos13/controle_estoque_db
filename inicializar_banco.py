#!/usr/bin/env python3
"""
SCRIPT DE INICIALIZAÇÃO FORÇADA DO BANCO
Execute este script para criar o banco e a tabela bens manualmente
"""

import sqlite3
import os
import sys

def criar_banco_forcado():
    """Cria o banco e a tabela bens manualmente"""
    
    # Caminho do banco
    DB_PATH = "D:\\controle_estoque_db\\relatorios\\controle_patrimonial.db"
    
    print("🚀 INICIALIZAÇÃO FORÇADA DO BANCO DE DADOS")
    print(f"📁 Caminho do banco: {DB_PATH}")
    
    try:
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        print("✅ Diretório criado/verificado")
        
        # Conectar ao banco
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Criar tabela bens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                situacao TEXT DEFAULT 'Pendente',
                localizacao TEXT,
                responsavel TEXT,
                data_ultima_vistoria DATE,
                data_vistoria_atual DATE,
                auditor TEXT,
                observacoes TEXT,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_localizacao DATETIME,
                ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Criar índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_localizacao ON bens(localizacao)")
        
        # Verificar se a tabela foi criada
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
        resultado = cursor.fetchone()
        
        if resultado:
            print("✅ TABELA 'bens' CRIADA COM SUCESSO!")
            
            # Inserir um registro de teste
            cursor.execute('''
                INSERT OR IGNORE INTO bens (numero, nome, situacao) 
                VALUES (?, ?, ?)
            ''', ("TESTE001", "Item de Teste", "Pendente"))
            
            # Contar registros
            cursor.execute("SELECT COUNT(*) FROM bens")
            count = cursor.fetchone()[0]
            print(f"✅ REGISTROS NA TABELA: {count}")
            
        else:
            print("❌ FALHA AO CRIAR TABELA 'bens'")
            return False
        
        conn.commit()
        conn.close()
        
        print("🎉 BANCO INICIALIZADO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        return False

if __name__ == "__main__":
    success = criar_banco_forcado()
    if success:
        print("\n💡 Agora reinicie o servidor Flask: python app.py")
        sys.exit(0)
    else:
        print("\n💥 Falha na inicialização do banco")
        sys.exit(1)