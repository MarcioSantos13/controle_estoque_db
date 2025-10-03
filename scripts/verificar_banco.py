# atualizar_tabela.py
import sqlite3
import os

DB_PATH = '../instance/patrimonio.db'

def atualizar_tabela_usuarios():
    """Adiciona colunas faltantes na tabela usuarios"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("=== VERIFICANDO COLUNAS FALTANTES ===")
        
        # Lista de colunas que devem existir
        colunas_necessarias = [
            'departamento',
            'telefone', 
            'criado_por',
            'data_atualizacao'
        ]
        
        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        print(f"Colunas existentes: {colunas_existentes}")
        
        # Adicionar colunas faltantes
        for coluna in colunas_necessarias:
            if coluna not in colunas_existentes:
                print(f"Adicionando coluna: {coluna}")
                
                if coluna == 'departamento':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN departamento TEXT")
                elif coluna == 'telefone':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN telefone TEXT")
                elif coluna == 'criado_por':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN criado_por INTEGER")
                elif coluna == 'data_atualizacao':
                    cursor.execute("ALTER TABLE usuarios ADD COLUMN data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        conn.commit()
        print("✅ Tabela atualizada com sucesso!")
        
        # Verificar estrutura final
        print("\n=== ESTRUTURA FINAL ===")
        cursor.execute("PRAGMA table_info(usuarios)")
        for coluna in cursor.fetchall():
            print(f"  {coluna[1]} ({coluna[2]})")
            
    except Exception as e:
        print(f"❌ Erro ao atualizar tabela: {e}")
    finally:
        if conn:
            conn.close()

def verificar_problemas_insercao():
    """Testa uma inserção para identificar problemas"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n=== TESTANDO INSERÇÃO SIMULADA ===")
        
        # Dados de teste
        dados_teste = {
            'email': 'teste2@empresa.com',
            'nome': 'Usuário Teste 2',
            'senha': '123456',
            'tipo': 'usuario',
            'departamento': 'TI',
            'telefone': '(11) 99999-9999',
            'ativo': 1
        }
        
        # Tentar inserção
        cursor.execute('''
            INSERT INTO usuarios (
                email, nome, senha_hash, tipo, departamento, 
                telefone, ativo, criado_por
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados_teste['email'],
            dados_teste['nome'],
            'hash_temporario',  # Hash simulado
            dados_teste['tipo'],
            dados_teste['departamento'],
            dados_teste['telefone'],
            dados_teste['ativo'],
            None  # criado_por
        ))
        
        conn.commit()
        print("✅ Inserção teste funcionou!")
        
    except Exception as e:
        print(f"❌ Erro na inserção: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    atualizar_tabela_usuarios()
    verificar_problemas_insercao()