# verificar_correcao.py
import sqlite3

DB_PATH_REAL = '../relatorios/controle_patrimonial.db'

def verificar_correcao():
    """Verifica se a correção do banco funcionou"""
    print("🔍 VERIFICANDO SE A CORREÇÃO DO BANCO FUNCIONOU")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_PATH_REAL)
        cursor = conn.cursor()
        
        # Verificar estrutura
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        print("📋 ESTRUTURA DA TABELA usuarios:")
        for coluna in colunas:
            print(f"   ✅ {coluna}")
        
        # Verificar colunas críticas
        colunas_criticas = ['departamento', 'telefone', 'criado_por']
        for coluna in colunas_criticas:
            if coluna in colunas:
                print(f"   🎯 {coluna}: ✅ PRESENTE")
            else:
                print(f"   🎯 {coluna}: ❌ AUSENTE")
        
        # Testar inserção
        print("\n🧪 TESTANDO INSERÇÃO:")
        try:
            cursor.execute('''
                INSERT INTO usuarios (email, nome, senha_hash, tipo, departamento, ativo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'verificacao@empresa.com',
                'Usuário Verificação',
                'hash_teste',
                'usuario',
                'TI',  # ← departamento
                1
            ))
            conn.commit()
            print("   ✅ INSERÇÃO COM DEPARTAMENTO FUNCIONOU!")
        except Exception as e:
            print(f"   ❌ Erro na inserção: {e}")
        
        conn.close()
        
        print("\n🎯 STATUS DO BANCO:")
        if all(coluna in colunas for coluna in colunas_criticas):
            print("✅ BANCO CORRIGIDO COM SUCESSO!")
            print("📝 O problema agora é apenas com os templates")
        else:
            print("❌ AINDA FALTAM COLUNAS NO BANCO")
            
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")

if __name__ == "__main__":
    verificar_correcao()