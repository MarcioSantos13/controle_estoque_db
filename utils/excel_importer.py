# utils/excel_importer.py - VERSÃO CORRIGIDA PARA SUA PLANILHA
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
                                ['numero', 'número', 'patrimonio', 'patrimônio', 'codigo', 'código', 'nº', 'num']) 
                              for col in colunas_lower)
        encontrou_nome = any(any(palavra in col for palavra in 
                               ['nome', 'descrição', 'descricao', 'item', 'equipamento', 'denominação']) 
                            for col in colunas_lower)
        
        valido = encontrou_numero and encontrou_nome
        mensagem = "✅ Estrutura válida" if valido else "⚠️ Estrutura pode precisar de ajustes"
        
        if not encontrou_numero:
            mensagem += "\n❌ Coluna de número não encontrada"
        if not encontrou_nome:
            mensagem += "\n❌ Coluna de nome não encontrada"
        
        # Verificar colunas específicas da sua planilha
        encontrou_responsavel = any('responsavel' in col.lower() for col in colunas_lower)
        encontrou_auditor = any('auditor' in col.lower() for col in colunas_lower)
        
        if encontrou_responsavel:
            mensagem += "\n✅ Coluna 'Responsavel' encontrada"
        else:
            mensagem += "\n❌ Coluna 'Responsavel' NÃO encontrada"
            
        if encontrou_auditor:
            mensagem += "\n✅ Coluna 'Auditor' encontrada"
        else:
            mensagem += "\n❌ Coluna 'Auditor' NÃO encontrada"
        
        return {
            'sucesso': True,
            'valido': valido,
            'mensagem': mensagem,
            'colunas': colunas,
            'total_linhas': len(df) if 'nrows' not in locals() else 'N/A',
            'encontrou_numero': encontrou_numero,
            'encontrou_nome': encontrou_nome,
            'encontrou_responsavel': encontrou_responsavel,
            'encontrou_auditor': encontrou_auditor,
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
    """Processa o DataFrame para importação - VERSÃO CORRIGIDA PARA SUA PLANILHA"""
    
    conn = None
    try:
        # Detectar colunas - COM DEBUG DETALHADO
        mapeamento = detectar_colunas_com_debug(df)
        
        if not mapeamento['numero'] or not mapeamento['nome']:
            return criar_resposta_erro("Colunas obrigatórias (número e nome) não encontradas")
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        inseridos = 0
        atualizados = 0
        erros = 0
        
        # DEBUG DETALHADO: Mostrar primeiras linhas para verificar dados
        logger.info("🔍 AMOSTRA DOS DADOS (primeiras 3 linhas):")
        for i in range(min(3, len(df))):
            linha_info = []
            for campo, coluna in mapeamento.items():
                if coluna and coluna in df.columns:
                    valor = df.iloc[i][coluna]
                    linha_info.append(f"{campo}: {valor}")
            logger.info(f"  Linha {i+1}: {', '.join(linha_info)}")
        
        for index, row in df.iterrows():
            try:
                # Extrair valores básicos
                numero_valor = row[mapeamento['numero']]
                nome_valor = row[mapeamento['nome']]
                
                numero = str(numero_valor).strip() if pd.notna(numero_valor) else None
                nome = str(nome_valor).strip() if pd.notna(nome_valor) else None
                
                if not numero or not nome:
                    logger.debug(f"Linha {index + 2}: Número ou nome vazio - Número: {numero}, Nome: {nome}")
                    erros += 1
                    continue
                
                # Valores opcionais - CORRIGIDO: Incluindo responsavel
                situacao_valor = row.get(mapeamento.get('situacao'))
                situacao = str(situacao_valor).strip() if pd.notna(situacao_valor) else 'Pendente'
                
                localizacao_valor = row.get(mapeamento.get('localizacao'))
                localizacao = str(localizacao_valor).strip() if pd.notna(localizacao_valor) else ''
                
                # ✅ CORREÇÃO: Extrair responsavel do Excel - COM DEBUG
                responsavel = ''
                if mapeamento.get('responsavel'):
                    responsavel_valor = row.get(mapeamento.get('responsavel'))
                    if pd.notna(responsavel_valor):
                        responsavel = str(responsavel_valor).strip()
                        logger.debug(f"Linha {index + 2}: Responsavel extraído = '{responsavel}'")
                    else:
                        logger.debug(f"Linha {index + 2}: Responsavel está vazio/NaN")
                else:
                    logger.warning(f"Linha {index + 2}: Coluna responsavel não mapeada")
                
                # ✅ CORREÇÃO: Extrair auditor do Excel
                auditor = ''
                if mapeamento.get('auditor'):
                    auditor_valor = row.get(mapeamento.get('auditor'))
                    auditor = str(auditor_valor).strip() if pd.notna(auditor_valor) else ''
                
                # ✅ CORREÇÃO: Extrair observacao do Excel
                observacao = ''
                if mapeamento.get('observacao'):
                    observacao_valor = row.get(mapeamento.get('observacao'))
                    observacao = str(observacao_valor).strip() if pd.notna(observacao_valor) else ''
                
                # Verificar se existe
                cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
                existe = cursor.fetchone()
                
                if existe:
                    # ✅ CORREÇÃO: UPDATE incluindo responsavel, auditor e observacao
                    cursor.execute('''
                        UPDATE bens SET 
                            nome=?, situacao=?, localizacao=?, responsavel=?, auditor=?, observacao=?, 
                            ultima_atualizacao=CURRENT_TIMESTAMP 
                        WHERE numero=?
                    ''', (nome, situacao, localizacao, responsavel, auditor, observacao, numero))
                    atualizados += 1
                    logger.debug(f"Linha {index + 2}: ATUALIZADO - Número: {numero}, Responsavel: '{responsavel}'")
                else:
                    # ✅ CORREÇÃO: INSERT incluindo responsavel, auditor e observacao
                    cursor.execute('''
                        INSERT INTO bens (numero, nome, situacao, localizacao, responsavel, auditor, observacao) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (numero, nome, situacao, localizacao, responsavel, auditor, observacao))
                    inseridos += 1
                    logger.debug(f"Linha {index + 2}: INSERIDO - Número: {numero}, Responsavel: '{responsavel}'")
                
                # Commit periódico
                if (inseridos + atualizados) % 20 == 0:
                    conn.commit()
                    
            except Exception as e:
                erros += 1
                logger.error(f"Erro na linha {index + 2}: {e}")
                logger.error(f"Dados da linha problemática: Número: {numero}, Nome: {nome}")
        
        conn.commit()
        
        total = inseridos + atualizados + erros
        mensagem = f"✅ Importação concluída! {inseridos} novos, {atualizados} atualizados, {erros} erros"
        
        logger.info(f"📊 RESUMO DA IMPORTAÇÃO:")
        logger.info(f"  Inseridos: {inseridos}")
        logger.info(f"  Atualizados: {atualizados}")
        logger.info(f"  Erros: {erros}")
        logger.info(f"  Mapeamento usado: {mapeamento}")
        
        return {
            'sucesso': True,
            'mensagem': mensagem,
            'registros_processados': total,
            'registros_inseridos': inseridos,
            'registros_atualizados': atualizados,
            'registros_erro': erros,
            'mapeamento': mapeamento  # ✅ Adicionado para debug
        }
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        if conn:
            conn.rollback()
        return criar_resposta_erro(f"Erro no processamento: {str(e)}")
    finally:
        if conn:
            conn.close()

def detectar_colunas_com_debug(df: pd.DataFrame) -> Dict[str, Any]:
    """Detecta automaticamente as colunas - VERSÃO COM DEBUG DETALHADO"""
    df.columns = [str(col).strip() for col in df.columns]
    
    mapeamento = {
        'numero': None, 
        'nome': None, 
        'situacao': None, 
        'localizacao': None, 
        'responsavel': None,
        'auditor': None,
        'observacao': None
    }
    
    colunas_originais = df.columns.tolist()
    colunas_lower = [col.lower() for col in colunas_originais]
    
    logger.info("🎯 DETECÇÃO DE COLUNAS - COLUNAS ORIGINAIS:")
    for i, col in enumerate(colunas_originais):
        logger.info(f"  Coluna {i}: '{col}' (lower: '{col.lower()}')")
    
    # Buscar por padrões ESPECÍFICOS para sua planilha
    for idx, col in enumerate(colunas_originais):
        col_lower = col.lower()
        
        # NÚMERO - Busca exata para sua planilha
        if any(p in col_lower for p in ['numero', 'número', 'nº', 'num', 'código', 'codigo', 'patrim']):
            if 'bem' in col_lower or any(p in col_lower for p in ['numero', 'nº']):
                mapeamento['numero'] = col
                logger.info(f"  ✅ NÚMERO: '{col}' → mapeado")
        
        # NOME - Busca exata
        elif 'nome' in col_lower:
            mapeamento['nome'] = col
            logger.info(f"  ✅ NOME: '{col}' → mapeado")
        
        # SITUAÇÃO - Busca exata  
        elif any(p in col_lower for p in ['situação', 'situacao', 'status']):
            mapeamento['situacao'] = col
            logger.info(f"  ✅ SITUAÇÃO: '{col}' → mapeado")
        
        # LOCALIZAÇÃO - Busca exata
        elif any(p in col_lower for p in ['localização', 'localizacao', 'local']):
            mapeamento['localizacao'] = col
            logger.info(f"  ✅ LOCALIZAÇÃO: '{col}' → mapeado")
        
        # RESPONSAVEL - BUSCA EXATA (SEM ACENTO - COMO ESTÁ NA SUA PLANILHA)
        elif 'responsavel' in col_lower:
            mapeamento['responsavel'] = col
            logger.info(f"  ✅ RESPONSAVEL: '{col}' → mapeado")
        
        # AUDITOR - Busca exata
        elif 'auditor' in col_lower:
            mapeamento['auditor'] = col
            logger.info(f"  ✅ AUDITOR: '{col}' → mapeado")
    
    # Se não encontrou por busca exata, tentar busca mais ampla
    if not mapeamento['numero']:
        for idx, col in enumerate(colunas_originais):
            if any(p in col.lower() for p in ['numero', 'nº', 'num', 'código']):
                mapeamento['numero'] = col
                logger.info(f"  ✅ NÚMERO (fallback): '{col}' → mapeado")
                break
    
    # DEBUG FINAL
    logger.info("🎯 MAPEAMENTO FINAL DETECTADO:")
    for campo, coluna in mapeamento.items():
        status = f"✅ '{coluna}'" if coluna else "❌ Não encontrada"
        logger.info(f"  {campo.upper():12}: {status}")
    
    # Verificar se as colunas realmente existem no DataFrame
    for campo, coluna in mapeamento.items():
        if coluna and coluna not in df.columns:
            logger.error(f"❌ ERRO: Coluna '{coluna}' não existe no DataFrame!")
            mapeamento[campo] = None
    
    return mapeamento

def detectar_colunas(df: pd.DataFrame) -> Dict[str, Any]:
    """Wrapper para manter compatibilidade"""
    return detectar_colunas_com_debug(df)

# ==============================
# FUNÇÕES ADICIONAIS PARA DEBUG
# ==============================

def verificar_mapeamento_detalhado(caminho_arquivo: str, aba_nome: str = 'Estoque') -> Dict[str, Any]:
    """Função especial para debug detalhado do mapeamento"""
    try:
        logger.info(f"🔍 VERIFICAÇÃO DETALHADA: {caminho_arquivo}")
        
        if not os.path.exists(caminho_arquivo):
            return {'sucesso': False, 'erro': 'Arquivo não encontrado'}
        
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        
        # Ler arquivo
        if extensao == '.csv':
            df = ler_arquivo_csv(caminho_arquivo, nrows=10)
        else:
            df = ler_arquivo_excel(caminho_arquivo, aba_nome, nrows=10)
        
        if df is None or df.empty:
            return {'sucesso': False, 'erro': 'Arquivo vazio'}
        
        # Detectar colunas
        mapeamento = detectar_colunas_com_debug(df)
        
        # Amostra de dados DETALHADA
        amostra = {}
        for campo, coluna in mapeamento.items():
            if coluna and coluna in df.columns:
                valores = []
                for i in range(min(5, len(df))):
                    valor = df.iloc[i][coluna]
                    valores.append({
                        'linha': i + 2,
                        'valor': str(valor) if pd.notna(valor) else 'VAZIO',
                        'tipo': type(valor).__name__
                    })
                amostra[campo] = {
                    'coluna': coluna,
                    'valores_detalhados': valores,
                    'total_vazios': df[coluna].isna().sum(),
                    'total_preenchidos': df[coluna].notna().sum()
                }
        
        return {
            'sucesso': True,
            'mapeamento': mapeamento,
            'amostra': amostra,
            'colunas_originais': df.columns.tolist(),
            'total_linhas': len(df),
            'colunas_detectadas': [col for col in mapeamento.values() if col]
        }
        
    except Exception as e:
        logger.error(f"Erro na verificação detalhada: {e}")
        return {'sucesso': False, 'erro': str(e)}

def testar_importacao_com_debug(caminho_arquivo: str, db_path: str = None) -> Dict[str, Any]:
    """Função de teste com debug completo"""
    try:
        logger.info(f"🧪 TESTE DE IMPORTAÇÃO COM DEBUG: {caminho_arquivo}")
        
        # 1. Verificação detalhada
        verificacao = verificar_mapeamento_detalhado(caminho_arquivo)
        if not verificacao['sucesso']:
            return verificacao
        
        # 2. Importação real
        resultado = importar_excel_para_sqlite(
            caminho_arquivo, 
            db_path, 
            apagar_dados_antes=True
        )
        
        # 3. Combinar resultados
        resultado['verificacao'] = verificacao
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro no teste de importação: {e}")
        return {'sucesso': False, 'erro': str(e)}

def verificar_dados_importados(db_path: str = None, limite: int = 10) -> Dict[str, Any]:
    """Verifica os dados que foram importados para o banco"""
    if db_path is None:
        db_path = DB_PATH
        
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Verificar totais
        cursor.execute("SELECT COUNT(*) as total FROM bens")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as com_responsavel FROM bens WHERE responsavel IS NOT NULL AND responsavel != ''")
        com_responsavel = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as sem_responsavel FROM bens WHERE responsavel IS NULL OR responsavel = ''")
        sem_responsavel = cursor.fetchone()[0]
        
        # Amostra de dados
        cursor.execute('''
            SELECT numero, nome, situacao, localizacao, responsavel, auditor, observacao 
            FROM bens 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limite,))
        
        amostra = []
        for row in cursor.fetchall():
            amostra.append({
                'numero': row[0],
                'nome': row[1],
                'situacao': row[2],
                'localizacao': row[3],
                'responsavel': row[4] or 'VAZIO',
                'auditor': row[5] or 'VAZIO',
                'observacao': row[6] or 'VAZIO'
            })
        
        return {
            'sucesso': True,
            'total_registros': total,
            'com_responsavel': com_responsavel,
            'sem_responsavel': sem_responsavel,
            'percentual_com_responsavel': (com_responsavel / total * 100) if total > 0 else 0,
            'amostra': amostra
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar dados importados: {e}")
        return {'sucesso': False, 'erro': str(e)}
    finally:
        if conn:
            conn.close()