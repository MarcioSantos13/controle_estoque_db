# utils/excel_importer.py - VERSÃO CORRIGIDA PARA SERVIDOR
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
    """Função principal de importação - VERSÃO ROBUSTA"""
    
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
        
        logger.info(f"📊 Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
        
        # 5. Processar dados
        return processar_dataframe_importacao_robusta(df, db_path, apagar_dados_antes)
        
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
        return processar_dataframe_importacao_robusta(df, db_path, False)
        
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
            df = ler_arquivo_csv(caminho_arquivo, nrows=10)
        else:
            df = ler_arquivo_excel(caminho_arquivo, aba_nome, nrows=10)
        
        if df is None or df.empty:
            return criar_resposta_estrutura(False, "Arquivo vazio ou inválido")
        
        # Validar colunas
        colunas = df.columns.tolist()
        colunas_lower = [str(col).lower().strip() for col in colunas]
        
        # DEBUG: Mostrar todas as colunas detectadas
        logger.info("🎯 COLUNAS DETECTADAS NO ARQUIVO:")
        for i, col in enumerate(colunas):
            logger.info(f"  {i+1}. '{col}' (lower: '{col.lower()}')")
        
        encontrou_numero = any(any(palavra in col for palavra in 
                                ['numero', 'número', 'patrimonio', 'patrimônio', 'codigo', 'código', 'nº', 'num', 'bem']) 
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
        
        # Verificar colunas específicas
        encontrou_responsavel = any('responsavel' in col for col in colunas_lower)
        encontrou_auditor = any('auditor' in col for col in colunas_lower)
        encontrou_situacao = any(any(p in col for p in ['situação', 'situacao', 'status']) for col in colunas_lower)
        encontrou_localizacao = any(any(p in col for p in ['localização', 'localizacao', 'local']) for col in colunas_lower)
        
        mensagem += f"\n📊 Detalhes:"
        mensagem += f"\n  • Número: {'✅' if encontrou_numero else '❌'}"
        mensagem += f"\n  • Nome: {'✅' if encontrou_nome else '❌'}"
        mensagem += f"\n  • Situação: {'✅' if encontrou_situacao else '❌'}"
        mensagem += f"\n  • Localização: {'✅' if encontrou_localizacao else '❌'}"
        mensagem += f"\n  • Responsável: {'✅' if encontrou_responsavel else '❌'}"
        mensagem += f"\n  • Auditor: {'✅' if encontrou_auditor else '❌'}"
        
        return {
            'sucesso': True,
            'valido': valido,
            'mensagem': mensagem,
            'colunas': colunas,
            'colunas_lower': colunas_lower,
            'total_linhas': len(df),
            'encontrou_numero': encontrou_numero,
            'encontrou_nome': encontrou_nome,
            'encontrou_responsavel': encontrou_responsavel,
            'encontrou_auditor': encontrou_auditor,
            'encontrou_situacao': encontrou_situacao,
            'encontrou_localizacao': encontrou_localizacao,
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
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        for encoding in encodings:
            try:
                df = pd.read_csv(caminho, encoding=encoding, nrows=nrows, delimiter=',', skipinitialspace=True)
                logger.info(f"✅ CSV lido com encoding: {encoding}")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError) as e:
                logger.debug(f"Encoding {encoding} falhou: {e}")
                continue
        logger.error("❌ Nenhum encoding funcionou para o CSV")
        return None
    except Exception as e:
        logger.error(f"Erro ao ler CSV: {e}")
        return None

def ler_arquivo_excel(caminho: str, aba_nome: str = 'Estoque', nrows: int = None):
    """Lê arquivo Excel"""
    try:
        # Tentar ler com engine automática
        try:
            df = pd.read_excel(caminho, sheet_name=aba_nome, nrows=nrows, engine=None)
            logger.info("✅ Excel lido com engine automática")
            return df
        except Exception as e:
            logger.warning(f"Engine automática falhou, tentando openpyxl: {e}")
            try:
                df = pd.read_excel(caminho, sheet_name=aba_nome, nrows=nrows, engine='openpyxl')
                logger.info("✅ Excel lido com openpyxl")
                return df
            except Exception as e2:
                logger.warning(f"Openpyxl falhou, tentando xlrd: {e2}")
                df = pd.read_excel(caminho, sheet_name=aba_nome, nrows=nrows, engine='xlrd')
                logger.info("✅ Excel lido com xlrd")
                return df
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
        logger.info(f"✅ Arquivo temporário salvo: {temp_path}")
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
                    logger.info(f"✅ Arquivo temporário removido: {caminho_arquivo}")
                    break
            except PermissionError:
                import time
                time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Não foi possível remover arquivo: {e}")

# ==============================
# FUNÇÕES DE PROCESSAMENTO - VERSÃO ROBUSTA
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

def processar_dataframe_importacao_robusta(df: pd.DataFrame, db_path: str, apagar_dados_antes: bool = False) -> Dict[str, Any]:
    """Processa o DataFrame para importação - VERSÃO ROBUSTA PARA SERVIDOR"""
    
    conn = None
    try:
        # Detectar colunas - COM FALLBACKS ROBUSTOS
        mapeamento = detectar_colunas_robusto(df)
        
        if not mapeamento['numero'] or not mapeamento['nome']:
            return criar_resposta_erro("Colunas obrigatórias (número e nome) não encontradas")
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        inseridos = 0
        atualizados = 0
        erros = 0
        linhas_processadas = 0
        
        # DEBUG: Mostrar primeiras linhas para verificar dados
        logger.info("🔍 AMOSTRA DOS DADOS (primeiras 5 linhas):")
        for i in range(min(5, len(df))):
            linha_info = []
            for campo, coluna in mapeamento.items():
                if coluna and coluna in df.columns:
                    valor = df.iloc[i][coluna]
                    linha_info.append(f"{campo}: '{valor}'")
                else:
                    linha_info.append(f"{campo}: NÃO MAPEADO")
            logger.info(f"  Linha {i+2}: {', '.join(linha_info)}")
        
        # PROCESSAMENTO PRINCIPAL
        for index, row in df.iterrows():
            linhas_processadas += 1
            try:
                # EXTRAÇÃO ROBUSTA DE VALORES
                numero = extrair_valor_seguro(row, mapeamento['numero'])
                nome = extrair_valor_seguro(row, mapeamento['nome'])
                
                # VALIDAÇÃO CRÍTICA
                if not numero or numero == 'nan' or numero == 'None' or str(numero).strip() == '':
                    logger.debug(f"Linha {index + 2}: Número inválido - '{numero}'")
                    erros += 1
                    continue
                    
                if not nome or nome == 'nan' or nome == 'None' or str(nome).strip() == '':
                    logger.debug(f"Linha {index + 2}: Nome inválido - '{nome}'")
                    erros += 1
                    continue
                
                # Limpar valores
                numero = str(numero).strip()
                nome = str(nome).strip()
                
                # VALORES OPCIONAIS
                situacao = extrair_valor_seguro(row, mapeamento.get('situacao'), 'Pendente')
                localizacao = extrair_valor_seguro(row, mapeamento.get('localizacao'), '')
                responsavel = extrair_valor_seguro(row, mapeamento.get('responsavel'), '')
                auditor = extrair_valor_seguro(row, mapeamento.get('auditor'), '')
                observacao = extrair_valor_seguro(row, mapeamento.get('observacao'), '')
                
                # Verificar se existe
                cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
                existe = cursor.fetchone()
                
                if existe:
                    # UPDATE
                    cursor.execute('''
                        UPDATE bens SET 
                            nome=?, situacao=?, localizacao=?, responsavel=?, auditor=?, observacao=?, 
                            ultima_atualizacao=CURRENT_TIMESTAMP 
                        WHERE numero=?
                    ''', (nome, situacao, localizacao, responsavel, auditor, observacao, numero))
                    atualizados += 1
                    
                    if atualizados <= 5:  # Log apenas os primeiros para debug
                        logger.info(f"📝 ATUALIZADO #{atualizados}: {numero} - '{nome}' | Responsável: '{responsavel}'")
                else:
                    # INSERT
                    cursor.execute('''
                        INSERT INTO bens (numero, nome, situacao, localizacao, responsavel, auditor, observacao) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (numero, nome, situacao, localizacao, responsavel, auditor, observacao))
                    inseridos += 1
                    
                    if inseridos <= 5:  # Log apenas os primeiros para debug
                        logger.info(f"🆕 INSERIDO #{inseridos}: {numero} - '{nome}' | Responsável: '{responsavel}'")
                
                # Commit periódico
                if (inseridos + atualizados) % 50 == 0:
                    conn.commit()
                    logger.info(f"💾 Commit intermediário: {inseridos + atualizados} registros")
                    
            except Exception as e:
                erros += 1
                logger.error(f"❌ ERRO na linha {index + 2}: {str(e)}")
                # Log dos valores problemáticos
                try:
                    numero_debug = extrair_valor_seguro(row, mapeamento['numero'], 'ERRO')
                    nome_debug = extrair_valor_seguro(row, mapeamento['nome'], 'ERRO')
                    logger.error(f"   Dados da linha: Número='{numero_debug}', Nome='{nome_debug}'")
                except:
                    logger.error("   Não foi possível extrair dados para debug")
        
        # COMMIT FINAL
        conn.commit()
        logger.info(f"💾 Commit final realizado")
        
        total = inseridos + atualizados + erros
        mensagem = f"✅ Importação concluída! {inseridos} novos, {atualizados} atualizados, {erros} erros"
        
        if erros == total:
            mensagem = f"❌ FALHA CRÍTICA: Todos os {total} registros falharam!"
        
        logger.info(f"📊 RESUMO FINAL:")
        logger.info(f"  Linhas processadas: {linhas_processadas}")
        logger.info(f"  Inseridos: {inseridos}")
        logger.info(f"  Atualizados: {atualizados}")
        logger.info(f"  Erros: {erros}")
        logger.info(f"  Taxa de sucesso: {(inseridos + atualizados) / total * 100:.1f}%")
        
        return {
            'sucesso': True if (inseridos + atualizados) > 0 else False,
            'mensagem': mensagem,
            'registros_processados': total,
            'registros_inseridos': inseridos,
            'registros_atualizados': atualizados,
            'registros_erro': erros,
            'mapeamento': mapeamento
        }
        
    except Exception as e:
        logger.error(f"💥 ERRO CRÍTICO no processamento: {e}")
        if conn:
            conn.rollback()
            logger.info("🔙 Rollback realizado")
        return criar_resposta_erro(f"Erro no processamento: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.info("🔒 Conexão com banco fechada")

def extrair_valor_seguro(row, coluna, valor_default=''):
    """Extrai valor de forma segura, tratando NaN e None"""
    if not coluna or coluna not in row:
        return valor_default
    
    valor = row[coluna]
    
    # Tratar pandas NaN, None e strings vazias
    if pd.isna(valor) or valor is None:
        return valor_default
    
    valor_str = str(valor).strip()
    
    # Tratar strings que representam NaN
    if valor_str.lower() in ['nan', 'none', 'null', '']:
        return valor_default
    
    return valor_str

def detectar_colunas_robusto(df: pd.DataFrame) -> Dict[str, Any]:
    """Detecta automaticamente as colunas - VERSÃO ROBUSTA"""
    
    # Garantir que as colunas são strings
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
    
    logger.info("🎯 DETECÇÃO DE COLUNAS - MODO ROBUSTO")
    logger.info(f"Colunas disponíveis ({len(colunas_originais)}): {colunas_originais}")
    
    # MAPEAMENTO DIRETO - busca exata primeiro
    mapeamento_direto = {
        'numero': ['numero do bem', 'nº do bem', 'número do bem', 'patrimonio', 'código'],
        'nome': ['nome'],
        'situacao': ['situação', 'situacao', 'status'],
        'localizacao': ['localização', 'localizacao', 'local'],
        'responsavel': ['responsavel', 'responsável'],
        'auditor': ['auditor'],
        'observacao': ['observação', 'observacao', 'obs']
    }
    
    for campo, padroes in mapeamento_direto.items():
        for padrao in padroes:
            if padrao in colunas_lower:
                idx = colunas_lower.index(padrao)
                mapeamento[campo] = colunas_originais[idx]
                logger.info(f"  ✅ {campo.upper():12} → '{colunas_originais[idx]}' (padrão: '{padrao}')")
                break
    
    # FALLBACKS INTELIGENTES para campos obrigatórios
    if not mapeamento['numero']:
        for idx, col in enumerate(colunas_originais):
            col_lower = col.lower()
            if any(p in col_lower for p in ['numero', 'nº', 'num', 'código', 'codigo', 'patrim']):
                mapeamento['numero'] = col
                logger.info(f"  ✅ NÚMERO (fallback) → '{col}'")
                break
    
    if not mapeamento['nome']:
        for idx, col in enumerate(colunas_originais):
            col_lower = col.lower()
            if any(p in col_lower for p in ['nome', 'descrição', 'descricao', 'item']):
                mapeamento['nome'] = col
                logger.info(f"  ✅ NOME (fallback) → '{col}'")
                break
    
    # FALLBACK ULTIMO RECURSO - usar primeira e segunda coluna
    if not mapeamento['numero'] and len(colunas_originais) >= 1:
        mapeamento['numero'] = colunas_originais[0]
        logger.warning(f"  ⚠️ NÚMERO (emergência) → primeira coluna: '{colunas_originais[0]}'")
    
    if not mapeamento['nome'] and len(colunas_originais) >= 2:
        mapeamento['nome'] = colunas_originais[1]
        logger.warning(f"  ⚠️ NOME (emergência) → segunda coluna: '{colunas_originais[1]}'")
    
    # VERIFICAÇÃO FINAL
    logger.info("🎯 MAPEAMENTO FINAL:")
    for campo, coluna in mapeamento.items():
        status = f"✅ '{coluna}'" if coluna else "❌ Não encontrada"
        logger.info(f"  {campo.upper():12}: {status}")
    
    return mapeamento

# ==============================
# FUNÇÕES DE DEBUG E DIAGNÓSTICO
# ==============================

def diagnosticar_problema_importacao(caminho_arquivo: str, aba_nome: str = 'Estoque') -> Dict[str, Any]:
    """Diagnóstico completo do problema de importação"""
    try:
        logger.info(f"🔧 DIAGNÓSTICO COMPLETO: {caminho_arquivo}")
        
        if not os.path.exists(caminho_arquivo):
            return {'sucesso': False, 'erro': 'Arquivo não encontrado'}
        
        # 1. Verificar estrutura
        estrutura = verificar_estrutura_excel(caminho_arquivo, aba_nome)
        
        # 2. Ler dados completos
        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        if extensao == '.csv':
            df = ler_arquivo_csv(caminho_arquivo)
        else:
            df = ler_arquivo_excel(caminho_arquivo, aba_nome)
        
        if df is None:
            return {'sucesso': False, 'erro': 'Não foi possível ler o arquivo'}
        
        # 3. Análise detalhada dos dados
        analise_dados = {
            'total_linhas': len(df),
            'total_colunas': len(df.columns),
            'colunas': df.columns.tolist(),
            'primeiras_linhas': []
        }
        
        # Amostra das primeiras 5 linhas
        for i in range(min(5, len(df))):
            linha = {}
            for coluna in df.columns:
                valor = df.iloc[i][coluna]
                linha[coluna] = {
                    'valor': str(valor) if pd.notna(valor) else 'NaN',
                    'tipo': type(valor).__name__,
                    'vazio': pd.isna(valor)
                }
            analise_dados['primeiras_linhas'].append(linha)
        
        # 4. Verificar valores das colunas críticas
        mapeamento = detectar_colunas_robusto(df)
        problemas = []
        
        for campo in ['numero', 'nome']:
            if mapeamento[campo]:
                coluna = mapeamento[campo]
                valores = df[coluna]
                vazios = valores.isna().sum()
                problemas.append(f"Coluna '{coluna}' ({campo}): {vazios} vazios de {len(valores)}")
        
        return {
            'sucesso': True,
            'estrutura': estrutura,
            'analise_dados': analise_dados,
            'mapeamento': mapeamento,
            'problemas_detectados': problemas,
            'recomendacao': 'Verifique se as colunas de número e nome estão preenchidas corretamente'
        }
        
    except Exception as e:
        logger.error(f"Erro no diagnóstico: {e}")
        return {'sucesso': False, 'erro': str(e)}

# Manter funções antigas para compatibilidade
def processar_dataframe_importacao(df: pd.DataFrame, db_path: str, apagar_dados_antes: bool = False) -> Dict[str, Any]:
    """Wrapper para compatibilidade"""
    return processar_dataframe_importacao_robusta(df, db_path, apagar_dados_antes)

def detectar_colunas(df: pd.DataFrame) -> Dict[str, Any]:
    """Wrapper para compatibilidade"""
    return detectar_colunas_robusto(df)