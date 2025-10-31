# ==============================
# INÍCIO: excel_importer.py CORRIGIDO
# ==============================

import sqlite3
import pandas as pd
from openpyxl import load_workbook
import os
import shutil
import tempfile
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, date
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# ==============================
# CONSTANTES PARA ESTABILIDADE
# ==============================

# Timeouts para operações de banco
DB_TIMEOUT = 30  # segundos
MAX_CSV_SIZE = 100 * 1024 * 1024  # 100MB
SUPPORTED_ENCODINGS = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']

# ==============================
# FUNÇÃO VERIFICAR_ESTRUTURA_EXCEL - ADICIONADA PARA CORRIGIR ERRO
# ==============================

def verificar_estrutura_excel(caminho_arquivo: str, aba_nome: str = 'Estoque') -> Dict[str, Any]:
    """
    Verifica a estrutura do arquivo Excel e valida se está no formato esperado
    Retorna: Dict com informações sobre a estrutura do arquivo
    """
    try:
        logger.info(f"Verificando estrutura do arquivo: {caminho_arquivo}")
        
        # Verificar se arquivo existe
        if not os.path.exists(caminho_arquivo):
            return {
                'sucesso': False,
                'valido': False,
                'mensagem': f"Arquivo não encontrado: {caminho_arquivo}",
                'colunas': [],
                'total_linhas': 0
            }
        
        # Verificar extensão
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        if extensao not in ['.xlsx', '.xls', '.csv']:
            return {
                'sucesso': False,
                'valido': False,
                'mensagem': f"Formato de arquivo não suportado: {extensao}",
                'colunas': [],
                'total_linhas': 0
            }
        
        # Para arquivos CSV
        if extensao == '.csv':
            try:
                # Tentar detectar encoding
                encoding_detectado = None
                for encoding in SUPPORTED_ENCODINGS:
                    try:
                        with open(caminho_arquivo, 'r', encoding=encoding) as f:
                            primeira_linha = f.readline()
                        encoding_detectado = encoding
                        break
                    except UnicodeDecodeError:
                        continue
                
                if not encoding_detectado:
                    return {
                        'sucesso': False,
                        'valido': False,
                        'mensagem': "Não foi possível detectar encoding do CSV",
                        'colunas': [],
                        'total_linhas': 0
                    }
                
                # Ler CSV
                df = pd.read_csv(caminho_arquivo, encoding=encoding_detectado, nrows=5)  # Ler apenas as primeiras linhas
                colunas = df.columns.tolist()
                total_linhas = len(pd.read_csv(caminho_arquivo, encoding=encoding_detectado))
                
            except Exception as e:
                return {
                    'sucesso': False,
                    'valido': False,
                    'mensagem': f"Erro ao ler CSV: {str(e)}",
                    'colunas': [],
                    'total_linhas': 0
                }
        
        # Para arquivos Excel
        else:
            try:
                # Verificar se a aba existe
                planilha = pd.ExcelFile(caminho_arquivo)
                abas_disponiveis = planilha.sheet_names
                
                if aba_nome not in abas_disponiveis:
                    mensagem_abas = f"Aba '{aba_nome}' não encontrada. Abas disponíveis: {', '.join(abas_disponiveis)}"
                    return {
                        'sucesso': False,
                        'valido': False,
                        'mensagem': mensagem_abas,
                        'colunas': [],
                        'total_linhas': 0,
                        'abas_disponiveis': abas_disponiveis
                    }
                
                # Ler dados da aba
                df = pd.read_excel(caminho_arquivo, sheet_name=aba_nome, nrows=5)  # Ler apenas as primeiras linhas
                colunas = df.columns.tolist()
                
                # Contar total de linhas (sem cabeçalho)
                df_completo = pd.read_excel(caminho_arquivo, sheet_name=aba_nome)
                total_linhas = len(df_completo)
                
            except Exception as e:
                return {
                    'sucesso': False,
                    'valido': False,
                    'mensagem': f"Erro ao ler Excel: {str(e)}",
                    'colunas': [],
                    'total_linhas': 0
                }
        
        # Validar colunas obrigatórias
        colunas_obrigatorias_encontradas = []
        colunas_faltantes = []
        
        # Procurar por colunas que possam ser número e nome
        colunas_lower = [str(col).lower() for col in colunas]
        
        # Verificar coluna de número
        possiveis_numeros = ['numero', 'número', 'patrimonio', 'patrimônio', 'codigo', 'código', 'num', 'nº', 'id']
        encontrou_numero = any(any(palavra in col for palavra in possiveis_numeros) for col in colunas_lower)
        
        # Verificar coluna de nome
        possiveis_nomes = ['nome', 'descrição', 'descricao', 'item', 'equipamento', 'bem', 'denominação', 'denominacao']
        encontrou_nome = any(any(palavra in col for palavra in possiveis_nomes) for col in colunas_lower)
        
        # Coletar informações das colunas encontradas
        colunas_detectadas = detectar_colunas(df)
        
        valido = encontrou_numero and encontrou_nome
        
        mensagem = "✅ Estrutura do arquivo validada com sucesso!" if valido else "⚠️ Estrutura do arquivo pode precisar de ajustes"
        
        if not encontrou_numero:
            mensagem += "\n❌ Coluna de número/patrimônio não encontrada"
        if not encontrou_nome:
            mensagem += "\n❌ Coluna de nome/descrição não encontrada"
        
        return {
            'sucesso': True,
            'valido': valido,
            'mensagem': mensagem,
            'colunas': colunas,
            'total_linhas': total_linhas,
            'colunas_detectadas': colunas_detectadas,
            'encontrou_numero': encontrou_numero,
            'encontrou_nome': encontrou_nome,
            'extensao': extensao
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura do Excel: {str(e)}")
        return {
            'sucesso': False,
            'valido': False,
            'mensagem': f"Erro ao verificar estrutura: {str(e)}",
            'colunas': [],
            'total_linhas': 0
        }

# ==============================
# FUNÇÕES AUXILIARES CORRIGIDAS
# ==============================

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Conexão robusta com SQLite com timeout e tratamento de erro"""
    try:
        conn = sqlite3.connect(db_path, timeout=DB_TIMEOUT)
        conn.row_factory = sqlite3.Row
        # Configurar para melhor performance em escritas
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Erro de conexão com banco {db_path}: {str(e)}")
        raise

def criar_tabela_atualizada(db_path: str) -> None:
    """Cria/atualiza tabela com tratamento robusto de erro"""
    conn = None
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
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
        
        # Verificar e adicionar colunas faltantes de forma segura
        colunas_necessarias = [
            ('responsavel', 'TEXT'),
            ('data_ultima_vistoria', 'DATE'),
            ('data_vistoria_atual', 'DATE'), 
            ('auditor', 'TEXT'),
            ('ultima_atualizacao', 'DATETIME')
        ]
        
        cursor.execute("PRAGMA table_info(bens)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        
        for coluna, tipo in colunas_necessarias:
            if coluna not in colunas_existentes:
                try:
                    cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} {tipo}")
                    logger.info(f"Coluna {coluna} adicionada à tabela bens")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise
        
        # Criar índices para performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
        
        conn.commit()
        logger.info("Tabela bens criada/atualizada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao criar/atualizar tabela: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def processar_data_excel(valor: Any) -> Optional[date]:
    """Processa datas do Excel com múltiplos fallbacks"""
    try:
        if valor is None or pd.isna(valor) or valor == '':
            return None
        
        # Se já é objeto de data
        if isinstance(valor, (datetime, date)):
            return valor.date() if isinstance(valor, datetime) else valor
        
        # Se é string, tentar parsing
        if isinstance(valor, str):
            valor_limpo = valor.strip()
            if not valor_limpo:
                return None
            
            # Tentar diferentes formatos de data
            formatos = [
                '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', 
                '%d/%m/%y', '%Y/%m/%d', '%d.%m.%Y',
                '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S'
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(valor_limpo, formato).date()
                except ValueError:
                    continue
            
            # Tentar parser do pandas como último recurso
            try:
                data_pd = pd.to_datetime(valor_limpo, errors='coerce', dayfirst=True)
                if not pd.isna(data_pd):
                    return data_pd.date()
            except:
                pass
        
        # Tentar converter numérico do Excel
        try:
            if isinstance(valor, (int, float)):
                return datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(valor) - 2).date()
        except:
            pass
            
        return None
    except Exception as e:
        logger.debug(f"Erro ao processar data '{valor}': {str(e)}")
        return None

def normalizar_valor(valor: Any, max_length: int = 500) -> Optional[str]:
    """Normaliza valores com limite de tamanho para segurança"""
    if pd.isna(valor) or valor is None:
        return None
    
    try:
        if isinstance(valor, (int, float)):
            valor_str = str(int(valor)) if isinstance(valor, float) and valor.is_integer() else str(valor)
        else:
            valor_str = str(valor)
        
        valor_limpo = valor_str.strip()
        if not valor_limpo:
            return None
            
        # Limitar tamanho para prevenir problemas
        if len(valor_limpo) > max_length:
            valor_limpo = valor_limpo[:max_length] + "..."
            
        return valor_limpo
    except Exception as e:
        logger.debug(f"Erro ao normalizar valor '{valor}': {str(e)}")
        return None

# ==============================
# FUNÇÃO PARA APAGAR DADOS - CORRIGIDA
# ==============================

def apagar_todos_dados(db_path: str) -> Tuple[bool, str]:
    """Apaga TODOS os dados com verificação de segurança"""
    conn = None
    try:
        logger.warning(f"INICIANDO LIMPEZA COMPLETA DO BANCO: {db_path}")
        
        # Verificar se o banco existe
        if not os.path.exists(db_path):
            return True, "ℹ️ Banco não existe, nenhuma ação necessária."
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Contar registros antes
        cursor.execute("SELECT COUNT(*) FROM bens")
        total_antes = cursor.fetchone()[0]
        
        if total_antes == 0:
            return True, "ℹ️ O banco já estava vazio."
        
        # Backup da contagem para log
        cursor.execute("SELECT numero, nome FROM bens LIMIT 5")
        exemplos = cursor.fetchall()
        
        # Apagar todos os registros com transação
        cursor.execute("DELETE FROM bens")
        
        # Resetar sequência
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'bens'")
        
        # Vacuum para otimizar espaço
        cursor.execute("VACUUM")
        
        conn.commit()
        
        mensagem = f"✅ LIMPEZA CONCLUÍDA! {total_antes:,} registros removidos."
        logger.warning(mensagem)
        
        if exemplos:
            logger.info(f"Exemplos removidos: {[f'{e[0]} - {e[1]}' for e in exemplos]}")
        
        return True, mensagem
        
    except Exception as e:
        error_msg = f"❌ Erro ao apagar dados: {str(e)}"
        logger.error(error_msg)
        if conn:
            conn.rollback()
        return False, error_msg
    finally:
        if conn:
            conn.close()

# ==============================
# DETECÇÃO DE COLUNAS - CORRIGIDA
# ==============================

def detectar_colunas(df: pd.DataFrame) -> Dict[str, Any]:
    """Detecta colunas com mapeamento robusto e fallbacks"""
    # Normalizar nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]
    
    mapeamento_colunas = {
        'numero': None, 'nome': None, 'situacao': None, 'localizacao': None,
        'responsavel': None, 'data_ultima_vistoria': None, 
        'data_vistoria_atual': None, 'auditor': None
    }
    
    logger.info(f"Colunas encontradas: {df.columns.tolist()}")
    
    # Mapeamento direto priorizado
    mapeamento_direto = {
        'NOME': 'nome',
        'NUMERO DO BEM': 'numero', 
        'NÚMERO DO BEM': 'numero',
        'SITUAÇÃO': 'situacao',
        'SITUACAO': 'situacao', 
        'LOCALIZAÇÃO': 'localizacao',
        'LOCALIZACAO': 'localizacao',
        'Responsavel': 'responsavel',
        'Responsável': 'responsavel',
        'Data da ultima vistoria': 'data_ultima_vistoria',
        'Data da última vistoria': 'data_ultima_vistoria',
        'Data da vistoria atual': 'data_vistoria_atual',
        'Auditor': 'auditor'
    }
    
    # Primeira passagem: mapeamento direto exato
    for coluna_df in df.columns:
        coluna_normalizada = coluna_df.upper().strip()
        for coluna_excel, coluna_alvo in mapeamento_direto.items():
            if coluna_excel.upper() == coluna_normalizada:
                if not mapeamento_colunas[coluna_alvo]:  # Não sobrescrever se já encontrou
                    mapeamento_colunas[coluna_alvo] = coluna_df
                    logger.info(f"✅ Mapeamento direto: '{coluna_df}' -> '{coluna_alvo}'")
    
    # Segunda passagem: mapeamento por similaridade
    possiveis_nomes = {
        'numero': ['numero', 'número', 'patrimonio', 'patrimônio', 'codigo', 'código', 'num', 'nº', 'id'],
        'nome': ['nome', 'descrição', 'descricao', 'item', 'equipamento', 'bem', 'denominação', 'denominacao'],
        'situacao': ['situação', 'situacao', 'status', 'estado', 'condição', 'condicao'],
        'localizacao': ['localização', 'localizacao', 'local', 'setor', 'departamento', 'localidade'],
        'responsavel': ['responsavel', 'responsável', 'encarregado', 'curador'],
        'data_ultima_vistoria': ['ultima vistoria', 'última vistoria', 'data ultima'],
        'data_vistoria_atual': ['vistoria atual', 'data vistoria'],
        'auditor': ['auditor', 'inspetor', 'vistoriador']
    }
    
    colunas_df_lower = [str(col).strip().lower() for col in df.columns]
    
    for coluna_alvo, possibilidades in possiveis_nomes.items():
        if mapeamento_colunas[coluna_alvo]:  # Já foi mapeada
            continue
            
        for possibilidade in possibilidades:
            for idx, coluna_df in enumerate(colunas_df_lower):
                if possibilidade in coluna_df:
                    mapeamento_colunas[coluna_alvo] = df.columns[idx]
                    logger.info(f"✅ Mapeamento similar: '{df.columns[idx]}' -> '{coluna_alvo}'")
                    break
            if mapeamento_colunas[coluna_alvo]:
                break
    
    # Validar mapeamentos obrigatórios
    if not mapeamento_colunas['numero']:
        # Tentar encontrar qualquer coluna que possa ser número
        for col in df.columns:
            if any(palavra in str(col).lower() for palavra in ['numero', 'número', 'patrim', 'cod']):
                mapeamento_colunas['numero'] = col
                logger.warning(f"⚠️ Mapeamento inferido: '{col}' -> 'numero'")
                break
    
    if not mapeamento_colunas['nome']:
        for col in df.columns:
            if any(palavra in str(col).lower() for palavra in ['nome', 'descri', 'item']):
                mapeamento_colunas['nome'] = col
                logger.warning(f"⚠️ Mapeamento inferido: '{col}' -> 'nome'")
                break
    
    return mapeamento_colunas

# ==============================
# IMPORTAÇÃO CSV - CORRIGIDA
# ==============================

def importar_csv_para_sqlite(caminho_csv: str, db_path: str, delimiter: str = ',') -> Dict[str, Any]:
    """Importa CSV com tratamento robusto de encoding e tamanho"""
    conn = None
    temp_file = None
    
    try:
        logger.info(f"Iniciando importação CSV: {caminho_csv}")
        
        # Verificar se arquivo existe e tem tamanho razoável
        if not os.path.exists(caminho_csv):
            return criar_resposta_erro(f"Arquivo CSV não encontrado: {caminho_csv}")
        
        file_size = os.path.getsize(caminho_csv)
        if file_size > MAX_CSV_SIZE:
            return criar_resposta_erro(f"Arquivo CSV muito grande: {file_size/1024/1024:.1f}MB > {MAX_CSV_SIZE/1024/1024:.1f}MB")
        
        # Criar/atualizar tabela
        criar_tabela_atualizada(db_path)
        
        # Detectar encoding
        encoding_detectado = None
        for encoding in SUPPORTED_ENCODINGS:
            try:
                with open(caminho_csv, 'r', encoding=encoding) as f:
                    f.read(1024)  # Ler apenas um pouco para teste
                encoding_detectado = encoding
                logger.info(f"Encoding detectado: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if not encoding_detectado:
            return criar_resposta_erro("Não foi possível detectar encoding do CSV")
        
        # Ler CSV com pandas
        try:
            df = pd.read_csv(caminho_csv, delimiter=delimiter, encoding=encoding_detectado)
            logger.info(f"DataFrame CSV carregado: {len(df)} linhas, {len(df.columns)} colunas")
        except Exception as e:
            return criar_resposta_erro(f"Erro ao ler CSV: {str(e)}")
        
        if df.empty:
            return criar_resposta_erro("CSV está vazio")
        
        # Processar importação
        return processar_dataframe_importacao(df, db_path, 'CSV')
        
    except Exception as e:
        error_msg = f"Erro crítico na importação CSV: {str(e)}"
        logger.error(error_msg)
        return criar_resposta_erro(error_msg)
    finally:
        # Limpeza de arquivos temporários
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

# ==============================
# FUNÇÃO PRINCIPAL DE IMPORTAÇÃO - CORRIGIDA
# ==============================

def importar_excel_para_sqlite(
    caminho_excel: str, 
    db_path: str, 
    aba_nome: str = 'Estoque', 
    criar_backup: bool = True, 
    apagar_dados_antes: bool = False
) -> Dict[str, Any]:
    """Importa Excel/CSV para SQLite com tratamento robusto de erro"""
    
    conn = None
    temp_file = None
    
    try:
        logger.info(f"Iniciando importação: {caminho_excel}, Aba: {aba_nome}")
        
        # Verificar se arquivo existe
        if not os.path.exists(caminho_excel):
            return criar_resposta_erro(f"Arquivo não encontrado: {caminho_excel}")
        
        # Se for objeto de arquivo do Flask, salvar temporariamente
        if hasattr(caminho_excel, 'filename'):
            temp_file = salvar_arquivo_temporario(caminho_excel)
            caminho_processar = temp_file
        else:
            caminho_processar = caminho_excel
        
        # Verificar extensão
        extensao = os.path.splitext(caminho_processar)[1].lower()
        if extensao == '.csv':
            return importar_csv_para_sqlite(caminho_processar, db_path)
        
        # Limpeza de dados se solicitado
        if apagar_dados_antes:
            sucesso, mensagem = apagar_todos_dados(db_path)
            if not sucesso:
                return criar_resposta_erro(f"Falha ao apagar dados: {mensagem}")
        
        # Criar/atualizar tabela
        criar_tabela_atualizada(db_path)
        
        # Backup do banco
        backup_path = ""
        if criar_backup and os.path.exists(db_path) and not apagar_dados_antes:
            backup_path = criar_backup_banco(db_path)
        
        # Ler arquivo Excel
        try:
            df = pd.read_excel(caminho_processar, sheet_name=aba_nome)
            logger.info(f"DataFrame carregado: {len(df)} linhas, {len(df.columns)} colunas")
        except Exception as e:
            return criar_resposta_erro(f"Erro ao ler Excel: {str(e)}")
        
        if df.empty:
            return criar_resposta_erro("Arquivo Excel está vazio")
        
        # Processar importação
        return processar_dataframe_importacao(df, db_path, 'Excel', apagar_dados_antes, backup_path)
        
    except Exception as e:
        error_msg = f"Erro crítico na importação: {str(e)}"
        logger.error(error_msg)
        return criar_resposta_erro(error_msg)
    finally:
        # Limpeza sempre executada
        if conn:
            conn.close()
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Erro ao remover temp file {temp_file}: {e}")

# ==============================
# FUNÇÕES AUXILIARES NOVAS
# ==============================

def criar_resposta_erro(mensagem: str) -> Dict[str, Any]:
    """Cria resposta padronizada de erro"""
    logger.error(mensagem)
    return {
        'sucesso': False,
        'mensagem': f"❌ {mensagem}",
        'registros_processados': 0,
        'registros_inseridos': 0,
        'registros_atualizados': 0,
        'registros_erro': 0
    }

def salvar_arquivo_temporario(arquivo_flask) -> str:
    """Salva arquivo do Flask em local temporário"""
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{arquivo_flask.filename}")
        arquivo_flask.save(temp_path)
        logger.info(f"Arquivo salvo temporariamente: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo temporário: {e}")
        raise

def criar_backup_banco(db_path: str) -> str:
    """Cria backup do banco de dados"""
    try:
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"backup_controle_{timestamp}.db")
        shutil.copy2(db_path, backup_path)
        logger.info(f"Backup criado: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return ""

def processar_dataframe_importacao(
    df: pd.DataFrame, 
    db_path: str, 
    tipo_arquivo: str,
    apagar_dados_antes: bool = False,
    backup_path: str = ""
) -> Dict[str, Any]:
    """Processa DataFrame comum para importação"""
    
    conn = None
    try:
        # Detectar mapeamento de colunas
        mapeamento = detectar_colunas(df)
        
        # Validar colunas obrigatórias
        if not mapeamento['numero'] or not mapeamento['nome']:
            colunas_encontradas = ", ".join(df.columns.tolist())
            return criar_resposta_erro(
                f"Colunas obrigatórias não detectadas. Colunas encontradas: {colunas_encontradas}"
            )
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        registros_inseridos = 0
        registros_atualizados = 0
        registros_erro = 0
        
        logger.info("Iniciando processamento dos registros...")
        
        for index, row in df.iterrows():
            linha_arquivo = index + 2
            
            try:
                # Pular linhas vazias
                if row.isnull().all():
                    continue
                
                # Extrair e validar dados básicos
                numero = normalizar_valor(row[mapeamento['numero']])
                nome = normalizar_valor(row[mapeamento['nome']])
                
                if not numero or not nome:
                    registros_erro += 1
                    logger.warning(f"Linha {linha_arquivo}: Dados obrigatórios vazios")
                    continue
                
                # Extrair dados opcionais
                situacao = normalizar_valor(row.get(mapeamento.get('situacao'), 'Pendente')) or 'Pendente'
                localizacao = normalizar_valor(row.get(mapeamento.get('localizacao'))) or ''
                responsavel = normalizar_valor(row.get(mapeamento.get('responsavel'))) or ''
                auditor = normalizar_valor(row.get(mapeamento.get('auditor'))) or ''
                
                # Processar datas
                data_ultima_vistoria = processar_data_excel(row.get(mapeamento.get('data_ultima_vistoria')))
                data_vistoria_atual = processar_data_excel(row.get(mapeamento.get('data_vistoria_atual')))
                
                # Verificar se registro existe
                cursor.execute("SELECT id, localizacao FROM bens WHERE numero = ?", (numero,))
                registro_existente = cursor.fetchone()
                
                if registro_existente:
                    # Atualizar registro existente
                    localizacao_antiga = registro_existente['localizacao'] if registro_existente['localizacao'] else ''
                    atualizar_data_localizacao = localizacao and localizacao != localizacao_antiga
                    
                    cursor.execute('''
                        UPDATE bens SET 
                        nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                        data_ultima_vistoria = ?, data_vistoria_atual = ?, auditor = ?,
                        data_localizacao = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE data_localizacao END,
                        ultima_atualizacao = CURRENT_TIMESTAMP
                        WHERE numero = ?
                    ''', (
                        nome, situacao, localizacao, responsavel,
                        data_ultima_vistoria, data_vistoria_atual, auditor,
                        atualizar_data_localizacao, numero
                    ))
                    
                    registros_atualizados += 1
                    logger.debug(f"Linha {linha_arquivo}: ATUALIZADO - {numero}")
                        
                else:
                    # Inserir novo registro
                    cursor.execute('''
                        INSERT INTO bens 
                        (numero, nome, situacao, localizacao, responsavel, 
                         data_ultima_vistoria, data_vistoria_atual, auditor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        numero, nome, situacao, localizacao, responsavel,
                        data_ultima_vistoria, data_vistoria_atual, auditor
                    ))
                    registros_inseridos += 1
                    logger.debug(f"Linha {linha_arquivo}: NOVO - {numero}")
                
                # Commit periódico a cada 50 registros
                if (registros_inseridos + registros_atualizados) % 50 == 0:
                    conn.commit()
                
            except Exception as e:
                registros_erro += 1
                logger.error(f"Linha {linha_arquivo}: ERRO - {str(e)}")
                continue
        
        conn.commit()
        
        # Relatório final
        total_processados = registros_inseridos + registros_atualizados + registros_erro
        
        logger.info(f"IMPORTAÇÃO {tipo_arquivo} CONCLUÍDA: "
                   f"Novos: {registros_inseridos}, Atualizados: {registros_atualizados}, "
                   f"Erros: {registros_erro}, Total: {total_processados}")
        
        # Mensagem formatada para usuário
        mensagem_user = formatar_mensagem_importacao({
            'sucesso': True,
            'registros_processados': total_processados,
            'registros_inseridos': registros_inseridos,
            'registros_atualizados': registros_atualizados,
            'registros_erro': registros_erro
        }, apagar_dados_antes)
        
        return {
            'sucesso': True,
            'mensagem': mensagem_user,
            'registros_processados': total_processados,
            'registros_inseridos': registros_inseridos,
            'registros_atualizados': registros_atualizados,
            'registros_erro': registros_erro
        }
        
    except Exception as e:
        logger.error(f"Erro no processamento do DataFrame: {e}")
        if conn:
            conn.rollback()
        return criar_resposta_erro(f"Erro no processamento: {str(e)}")
    finally:
        if conn:
            conn.close()

def formatar_mensagem_importacao(resultado: Dict[str, Any], apagar_dados_antes: bool = False) -> str:
    """Formata mensagem de resultado da importação"""
    total = resultado['registros_processados']
    novos = resultado['registros_inseridos']
    atualizados = resultado['registros_atualizados']
    erros = resultado['registros_erro']
    
    if apagar_dados_antes:
        return f"✅ IMPORTACAO CONCLUÍDA! {novos:,} novos registros adicionados. Erros: {erros:,}"
    else:
        return f"✅ IMPORTACAO CONCLUÍDA! {novos:,} novos, {atualizados:,} atualizados, {erros:,} erros. Total: {total:,}"

# ==============================
# FIM: excel_importer.py CORRIGIDO  
# ==============================