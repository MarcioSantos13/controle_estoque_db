import sqlite3
import pandas as pd
import os

def verificar_dados():
    """Verifica os dados importados no banco SQLite"""
    db_path = "relatorios/controle_patrimonial.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Verificar estrutura da tabela
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(bens)")
        colunas = cursor.fetchall()
        
        print("=" * 60)
        print("📊 VERIFICAÇÃO DOS DADOS IMPORTADOS")
        print("=" * 60)
        
        print("\n🗂️  ESTRUTURA DA TABELA 'bens':")
        print("-" * 40)
        for coluna in colunas:
            print(f"  {coluna[1]:<25} ({coluna[2]:<10}) {'NOT NULL' if coluna[3] else 'NULLABLE'}")
        
        # Verificar total de registros
        print(f"\n📈 ESTATÍSTICAS:")
        print("-" * 40)
        total = pd.read_sql_query("SELECT COUNT(*) as total FROM bens", conn).iloc[0]['total']
        print(f"  Total de registros: {total}")
        
        # Contar por situação
        situacoes = pd.read_sql_query("SELECT situacao, COUNT(*) as quantidade FROM bens GROUP BY situacao", conn)
        print(f"\n  Situações dos bens:")
        for _, row in situacoes.iterrows():
            print(f"    {row['situacao']}: {row['quantidade']}")
        
        # Verificar novos campos
        print(f"\n🆕 NOVOS CAMPOS (IMPORTAÇÃO):")
        print("-" * 40)
        
        # Responsáveis
        responsaveis = pd.read_sql_query(
            "SELECT responsavel, COUNT(*) as quantidade FROM bens GROUP BY responsavel HAVING responsavel != '' LIMIT 10", 
            conn
        )
        print(f"  Responsáveis encontrados: {len(responsaveis)}")
        if not responsaveis.empty:
            for _, row in responsaveis.iterrows():
                print(f"    '{row['responsavel']}': {row['quantidade']} bens")
        
        # Auditores
        auditores = pd.read_sql_query(
            "SELECT auditor, COUNT(*) as quantidade FROM bens GROUP BY auditor HAVING auditor != '' LIMIT 10", 
            conn
        )
        print(f"  Auditores encontrados: {len(auditores)}")
        if not auditores.empty:
            for _, row in auditores.iterrows():
                print(f"    '{row['auditor']}': {row['quantidade']} bens")
        
        # Datas
        print(f"\n📅 DATAS DE VISTORIA:")
        print("-" * 40)
        datas_ultima = pd.read_sql_query(
            "SELECT MIN(data_ultima_vistoria) as primeira, MAX(data_ultima_vistoria) as ultima FROM bens", 
            conn
        ).iloc[0]
        print(f"  Última vistoria: de {datas_ultima['primeira']} a {datas_ultima['ultima']}")
        
        datas_atual = pd.read_sql_query(
            "SELECT MIN(data_vistoria_atual) as primeira, MAX(data_vistoria_atual) as ultima FROM bens", 
            conn
        ).iloc[0]
        print(f"  Vistoria atual:  de {datas_atual['primeira']} a {datas_atual['ultima']}")
        
        # Amostra de dados
        print(f"\n👀 AMOSTRA DE REGISTROS (5 primeiros):")
        print("-" * 40)
        amostra = pd.read_sql_query("""
            SELECT numero, nome, situacao, localizacao, responsavel, 
                   data_ultima_vistoria, data_vistoria_atual, auditor
            FROM bens 
            LIMIT 5
        """, conn)
        
        # Formatar a amostra para melhor visualização
        for idx, row in amostra.iterrows():
            print(f"\n  Registro {idx + 1}:")
            print(f"    Número: {row['numero']}")
            print(f"    Nome: {row['nome']}")
            print(f"    Situação: {row['situacao']}")
            print(f"    Localização: {row['localizacao']}")
            print(f"    Responsável: {row['responsavel']}")
            print(f"    Última vistoria: {row['data_ultima_vistoria']}")
            print(f"    Vistoria atual: {row['data_vistoria_atual']}")
            print(f"    Auditor: {row['auditor']}")
        
        # Verificar se há valores nulos nos novos campos
        print(f"\n🔍 VERIFICAÇÃO DE DADOS FALTANTES:")
        print("-" * 40)
        nulos_responsavel = pd.read_sql_query("SELECT COUNT(*) as total FROM bens WHERE responsavel IS NULL OR responsavel = ''", conn).iloc[0]['total']
        nulos_auditor = pd.read_sql_query("SELECT COUNT(*) as total FROM bens WHERE auditor IS NULL OR auditor = ''", conn).iloc[0]['total']
        
        print(f"  Registros sem responsável: {nulos_responsavel} ({nulos_responsavel/total*100:.1f}%)")
        print(f"  Registros sem auditor: {nulos_auditor} ({nulos_auditor/total*100:.1f}%)")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ VERIFICAÇÃO CONCLUÍDA")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_dados()