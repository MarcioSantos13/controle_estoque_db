# utils/excel_importer.py - VERSÃO COMPLETA E CORRIGIDA
import sqlite3
import pandas as pd
import os
import shutil
import tempfile
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# Configurações
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'relatorios', 'controle_patrimonial.db')
DB_TIMEOUT = 30

# ==============================
# FUNÇÕES PRINCIPAIS
# ==============================

def importar_excel_para_sqlite(
    caminho_excel: str, 
    db_path: str = None, 
    aba_nome: str = 'Estoque', 
    criar_backup: bool = True, 
    apagar_dados_antes: bool = False
) -> Dict[str, Any]:
    """Função principal de importação"""
    
    if db_path is None:
        db_path = DB_PATH
        
    temp_file = None
    
    try:
        logger.info(f"📥 Iniciando importação: {caminho_excel}")
        
        # 1. Garantir que o banco existe
        if not garantir_banco_pronto(db_path):
            return criar_resposta_erro("Falha ao preparar banco de dados")
        
        # 2. Processar arquivo
        if hasattr(caminho_excel, 'save'):
            temp_file = salvar_arquivo_temporario(caminho_excel)
            caminho_processar = temp_file
            extensao = os.path.splitext(caminho_excel.filename)[1].lower()
        else:
            caminho_processar = caminho_excel
            extensao = os.path.splitext(caminho_excel)[1].lower()
        
        if not os.path.exists(caminho_processar):
            return criar_resposta_erro(f"Arquivo não encontrado: {caminho_processar}")
        
        # 3. Limpeza se solicitado
        if apagar_dados_antes:
            sucesso, mensagem = apagar_todos_dados(db_path)
            if not sucesso:
                return criar_resposta_erro(f"Falha ao apagar dados: {mensagem}")
        
        # 4. Ler arquivo
        if extensao == '.csv':
            df = ler_arquivo_csv(caminho_processar)
        else:
            df = ler_arquivo_excel(caminho_processar, aba_nome)
        
        if df is None or df.empty:
            return criar_resposta_erro("Arquivo está vazio ou inválido")
        
        # 5. Processar dados
        return processar_dataframe_importacao(df, db_path, apagar_dados_antes)
        
    except Exception as e:
        error_msg = f"Erro crítico na importação: {str(e)}"
        logger.error(error_msg)
        return criar_resposta_erro(error_msg)
    finally:
        if temp_file and os.path.exists(temp_file):
            remover_arquivo_seguro(temp_file)

def importar_csv_para_sqlite(caminho_csv: str, db_path: str = None, delimiter: str = ',') -> Dict[str, Any]:
    """Importa arquivo CSV para o banco SQLite"""
    if db_path is None:
        db_path = DB_PATH
        
    try:
        logger.info(f"📥 Iniciando importação CSV: {caminho_csv}")
        
        # Garantir que o banco existe
        if not garantir_banco_pronto(db_path):
            return criar_resposta_erro("Falha ao preparar banco de dados")
        
        if not os.path.exists(caminho_csv):
            return criar_resposta_erro(f"Arquivo CSV não encontrado: {caminho_csv}")
        
        # Verificar tamanho do arquivo
        file_size = os.path.getsize(caminho_csv)
        if file_size > 100 * 1024 * 1024:  # 100MB
            return criar_resposta_erro(f"Arquivo CSV muito grande: {file_size/1024/1024:.1f}MB")
        
        # Ler CSV
        df = ler_arquivo_csv(caminho_csv)
        if df is None or df.empty:
            return criar_resposta_erro("CSV está vazio ou inválido")
        
        logger.info(f"📊 CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")
        
        # Processar importação
        return processar_dataframe_importacao(df, db_path, False)
        
    except Exception as e:
        error_msg = f"Erro na importação CSV: {str(e)}"
        logger.error(error_msg)
        return criar_resposta_erro(error_msg)

def verificar_estrutura_excel(caminho_arquivo: str, aba_nome: str = 'Estoque') -> Dict[str, Any]:
    """Verifica estrutura do arquivo"""
    try:
        logger.info(f"🔍 Verificando estrutura: {caminho_arquivo}")
        
        if not os.path.exists(caminho_arquivo):
            return criar_resposta_estrutura(False, "Arquivo não encontrado")
        
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        if extensao not in ['.xlsx', '.xls', '.csv']:
            return criar_resposta_estrutura(False, "Formato não suportado")
        
        # Ler amostra do arquivo
        if extensao == '.csv':
            df = ler_arquivo_csv(caminho_arquivo, nrows=5)
        else:
            df = ler_arquivo_excel(caminho_arquivo, aba_nome, nrows=5)
        
        if df is None or df.empty:
            return criar_resposta_estrutura(False, "Arquivo vazio ou inválido")
        
        # Validar colunas
        colunas = df.columns.tolist()
        colunas_lower = [str(col).lower() for col in colunas]
        
        encontrou_numero = any(any(palavra in col for palavra in 
                                ['numero', 'número', 'patrimonio', 'patrimônio', 'codigo', 'código']) 
                              for col in colunas_lower)
        encontrou_nome = any(any(palavra in col for palavra in 
                               ['nome', 'descrição', 'descricao', 'item', 'equipamento']) 
                            for col in colunas_lower)
        
        valido = encontrou_numero and encontrou_nome
        mensagem = "✅ Estrutura válida" if valido else "⚠️ Estrutura pode precisar de ajustes"
        
        if not encontrou_numero:
            mensagem += "\n❌ Coluna de número não encontrada"
        if not encontrou_nome:
            mensagem += "\n❌ Coluna de nome não encontrada"
        
        return {
            'sucesso': True,
            'valido': valido,
            'mensagem': mensagem,
            'colunas': colunas,
            'total_linhas': len(df) if 'nrows' not in locals() else 'N/A',
            'encontrou_numero': encontrou_numero,
            'encontrou_nome': encontrou_nome,
            'extensao': extensao
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura: {str(e)}")
        return criar_resposta_estrutura(False, f"Erro: {str(e)}")

# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def garantir_banco_pronto(db_path: str) -> bool:
    """Garante que o banco está pronto para uso"""
    try:
        from .database_init import inicializar_banco_completo
        return inicializar_banco_completo(db_path)
    except Exception as e:
        logger.error(f"Erro ao preparar banco: {e}")
        return False

def get_db_connection(db_path: str = None):
    """Conexão com o banco"""
    if db_path is None:
        db_path = DB_PATH
    return sqlite3.connect(db_path, timeout=DB_TIMEOUT)

def ler_arquivo_csv(caminho: str, nrows: int = None):
    """Lê arquivo CSV"""
    try:
        # Detectar encoding
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                return pd.read_csv(caminho, encoding=encoding, nrows=nrows)
            except UnicodeDecodeError:
                continue
        return None
    except Exception as e:
        logger.error(f"Erro ao ler CSV: {e}")
        return None

def ler_arquivo_excel(caminho: str, aba_nome: str = 'Estoque', nrows: int = None):
    """Lê arquivo Excel"""
    try:
        return pd.read_excel(caminho, sheet_name=aba_nome, nrows=nrows)
    except Exception as e:
        logger.error(f"Erro ao ler Excel: {e}")
        return None

def criar_resposta_erro(mensagem: str) -> Dict[str, Any]:
    """Resposta de erro padronizada"""
    logger.error(mensagem)
    return {
        'sucesso': False,
        'mensagem': f"❌ {mensagem}",
        'registros_processados': 0,
        'registros_inseridos': 0,
        'registros_atualizados': 0,
        'registros_erro': 0
    }

def criar_resposta_estrutura(sucesso: bool, mensagem: str) -> Dict[str, Any]:
    """Resposta de estrutura padronizada"""
    return {
        'sucesso': sucesso,
        'valido': False,
        'mensagem': mensagem,
        'colunas': [],
        'total_linhas': 0,
        'encontrou_numero': False,
        'encontrou_nome': False,
        'extensao': ''
    }

def salvar_arquivo_temporario(arquivo_flask) -> str:
    """Salva arquivo temporário"""
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{arquivo_flask.filename}")
        arquivo_flask.save(temp_path)
        return temp_path
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo temporário: {e}")
        raise

def remover_arquivo_seguro(caminho_arquivo: str):
    """Remove arquivo com segurança"""
    try:
        for _ in range(3):
            try:
                if os.path.exists(caminho_arquivo):
                    os.remove(caminho_arquivo)
                    break
            except PermissionError:
                import time
                time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Não foi possível remover arquivo: {e}")

# ==============================
# FUNÇÕES DE PROCESSAMENTO
# ==============================

def apagar_todos_dados(db_path: str = None) -> Tuple[bool, str]:
    """Apaga todos os dados da tabela bens"""
    if db_path is None:
        db_path = DB_PATH
        
    conn = None
    try:
        logger.warning(f"🗑️ Apagando todos os dados de: {db_path}")
        
        if not os.path.exists(db_path):
            return True, "Banco não existe"
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Contar antes
        cursor.execute("SELECT COUNT(*) FROM bens")
        total_antes = cursor.fetchone()[0]
        
        if total_antes == 0:
            return True, "Banco já estava vazio"
        
        # Apagar
        cursor.execute("DELETE FROM bens")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='bens'")
        conn.commit()
        conn.close()
        
        # Vacuum
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        return True, f"✅ {total_antes} registros removidos"
        
    except Exception as e:
        error_msg = f"❌ Erro ao apagar: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    finally:
        if conn:
            conn.close()

def processar_dataframe_importacao(df: pd.DataFrame, db_path: str, apagar_dados_antes: bool = False) -> Dict[str, Any]:
    """Processa o DataFrame para importação"""
    
    conn = None
    try:
        # Detectar colunas
        mapeamento = detectar_colunas(df)
        
        if not mapeamento['numero'] or not mapeamento['nome']:
            return criar_resposta_erro("Colunas obrigatórias (número e nome) não encontradas")
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        inseridos = 0
        atualizados = 0
        erros = 0
        
        for index, row in df.iterrows():
            try:
                # Extrair valores básicos
                numero = str(row[mapeamento['numero']]).strip() if pd.notna(row[mapeamento['numero']]) else None
                nome = str(row[mapeamento['nome']]).strip() if pd.notna(row[mapeamento['nome']]) else None
                
                if not numero or not nome:
                    erros += 1
                    continue
                
                # Valores opcionais
                situacao = str(row.get(mapeamento.get('situacao'), 'Pendente')).strip() if pd.notna(row.get(mapeamento.get('situacao'))) else 'Pendente'
                localizacao = str(row.get(mapeamento.get('localizacao'))).strip() if pd.notna(row.get(mapeamento.get('localizacao'))) else ''
                
                # Verificar se existe
                cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
                existe = cursor.fetchone()
                
                if existe:
                    cursor.execute('''
                        UPDATE bens SET nome=?, situacao=?, localizacao=?, ultima_atualizacao=CURRENT_TIMESTAMP 
                        WHERE numero=?
                    ''', (nome, situacao, localizacao, numero))
                    atualizados += 1
                else:
                    cursor.execute('''
                        INSERT INTO bens (numero, nome, situacao, localizacao, responsavel, auditor, observacao) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (numero, nome, situacao, localizacao))
                    inseridos += 1
                
                # Commit periódico
                if (inseridos + atualizados) % 20 == 0:
                    conn.commit()
                    
            except Exception as e:
                erros += 1
                logger.debug(f"Erro na linha {index + 2}: {e}")
        
        conn.commit()
        
        total = inseridos + atualizados + erros
        mensagem = f"✅ Importação concluída! {inseridos} novos, {atualizados} atualizados, {erros} erros"
        
        return {
            'sucesso': True,
            'mensagem': mensagem,
            'registros_processados': total,
            'registros_inseridos': inseridos,
            'registros_atualizados': atualizados,
            'registros_erro': erros
        }
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        if conn:
            conn.rollback()
        return criar_resposta_erro(f"Erro no processamento: {str(e)}")
    finally:
        if conn:
            conn.close()

def detectar_colunas(df: pd.DataFrame) -> Dict[str, Any]:
    """Detecta automaticamente as colunas"""
    df.columns = [str(col).strip() for col in df.columns]
    
    mapeamento = {
        'numero': None, 'nome': None, 'situacao': None, 
        'localizacao': None, 'responsavel': None
    }
    
    colunas_lower = [col.lower() for col in df.columns]
    
    # Buscar por padrões
    for idx, col in enumerate(colunas_lower):
        if any(p in col for p in ['numero', 'número', 'patrim', 'cod', 'nº', 'id']):
            mapeamento['numero'] = df.columns[idx]
        elif any(p in col for p in ['nome', 'descri', 'item', 'equipamento', 'bem']):
            mapeamento['nome'] = df.columns[idx]
        elif any(p in col for p in ['situação', 'situacao', 'status', 'estado']):
            mapeamento['situacao'] = df.columns[idx]
        elif any(p in col for p in ['localização', 'localizacao', 'local', 'setor']):
            mapeamento['localizacao'] = df.columns[idx]
        elif any(p in col for p in ['responsavel', 'responsável', 'encarregado']):
            mapeamento['responsavel'] = df.columns[idx]
    
    return mapeamento