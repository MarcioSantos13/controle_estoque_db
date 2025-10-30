import sqlite3
import pandas as pd
from openpyxl import load_workbook
import os
import shutil
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, date
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# ==============================
# FUNÇÕES AUXILIARES
# ==============================

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Conexão simples com o banco SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela_atualizada(db_path: str) -> None:
    """Cria a tabela bens com a nova estrutura completa"""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Criar tabela principal
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
                data_localizacao DATETIME
            )
        ''')
        
        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(bens)")
        colunas_existentes = [col[1] for col in cursor.fetchall()]
        
        # Colunas novas para adicionar se não existirem
        novas_colunas = [
            ('responsavel', 'TEXT'),
            ('data_ultima_vistoria', 'DATE'),
            ('data_vistoria_atual', 'DATE'),
            ('auditor', 'TEXT')
        ]
        
        for coluna, tipo in novas_colunas:
            if coluna not in colunas_existentes:
                try:
                    cursor.execute(f"ALTER TABLE bens ADD COLUMN {coluna} {tipo}")
                    print(f"Coluna {coluna} adicionada à tabela bens")
                except sqlite3.OperationalError:
                    # Coluna já existe, ignorar erro
                    pass
        
        conn.commit()
        conn.close()
        print("Tabela bens criada/atualizada com sucesso")
        
    except Exception as e:
        print(f"Erro ao criar/atualizar tabela: {str(e)}")
        raise

def processar_data_excel(valor: Any) -> Optional[date]:
    """Processa datas do Excel para formato Python"""
    try:
        if valor is None or pd.isna(valor):
            return None
        
        if isinstance(valor, datetime):
            return valor.date()
        elif isinstance(valor, date):
            return valor
        elif isinstance(valor, str) and valor.strip():
            # Tentar diferentes formatos de data
            formatos = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%Y/%m/%d']
            for formato in formatos:
                try:
                    return datetime.strptime(valor.strip(), formato).date()
                except ValueError:
                    continue
            return None
        else:
            return None
    except Exception:
        return None

def normalizar_valor(valor: Any) -> Optional[str]:
    """Normaliza valores para evitar problemas de tipo e formato"""
    if pd.isna(valor) or valor is None:
        return None
    
    try:
        valor_str = str(valor).strip()
        return valor_str if valor_str else None
    except Exception:
        return None

# ==============================
# FUNÇÃO PARA APAGAR TODOS OS DADOS
# ==============================

def apagar_todos_dados(db_path: str) -> Tuple[bool, str]:
    """
    Apaga TODOS os dados da tabela bens
    Retorna: (sucesso, mensagem)
    """
    try:
        print("🗑️  INICIANDO LIMPEZA COMPLETA DO BANCO DE DADOS...")
        
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Contar registros antes
        cursor.execute("SELECT COUNT(*) FROM bens")
        total_antes = cursor.fetchone()[0]
        
        if total_antes == 0:
            conn.close()
            return True, "ℹ️  O banco já estava vazio. Nenhum registro para apagar."
        
        # Apagar todos os registros
        cursor.execute("DELETE FROM bens")
        
        # Resetar a sequência autoincrement
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'bens'")
        
        conn.commit()
        conn.close()
        
        mensagem = f"✅ LIMPEZA CONCLUÍDA! {total_antes:,} registros removidos."
        print(mensagem)
        
        return True, mensagem
        
    except Exception as e:
        error_msg = f"❌ Erro ao apagar dados: {str(e)}"
        print(error_msg)
        return False, error_msg

# ==============================
# FUNÇÃO DE DETECÇÃO DE COLUNAS - CORRIGIDA
# ==============================

def detectar_colunas(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detecta automaticamente as colunas relevantes no DataFrame
    CORREÇÃO: Mapeamento específico para a estrutura informada
    """
    # CORREÇÃO: Remover espaços extras dos nomes das colunas
    df.columns = [str(col).strip() for col in df.columns]
    
    mapeamento_colunas = {
        'numero': None,
        'nome': None,
        'situacao': None,
        'localizacao': None,
        'responsavel': None,
        'data_ultima_vistoria': None,
        'data_vistoria_atual': None,
        'auditor': None
    }
    
    print(f"🔍 Colunas encontradas no arquivo: {df.columns.tolist()}")
    
    # CORREÇÃO: Mapeamento direto baseado na estrutura informada
    mapeamento_direto = {
        'NOME': 'nome',
        'NUMERO DO BEM': 'numero', 
        'SITUAÇÃO': 'situacao',
        'LOCALIZAÇÃO': 'localizacao',
        'Responsavel': 'responsavel',
        'Data da ultima vistoria': 'data_ultima_vistoria',
        'Data da vistoria atual': 'data_vistoria_atual',
        'Auditor': 'auditor'
    }
    
    # Primeiro tentar mapeamento direto
    for coluna_excel, coluna_alvo in mapeamento_direto.items():
        for coluna_df in df.columns:
            if coluna_excel.upper() == coluna_df.upper():
                mapeamento_colunas[coluna_alvo] = coluna_df
                print(f"✅ Coluna '{coluna_alvo}' detectada como: '{coluna_df}'")
                break
    
    # Se mapeamento direto não funcionar, tentar por similaridade
    if not mapeamento_colunas['numero']:
        possiveis_nomes = {
            'numero': ['número do bem', 'numero do bem', 'nº do bem', 'patrimonio', 'patrimônio', 'numero', 'número', 'codigo', 'código', 'num', 'nº'],
            'nome': ['nome', 'descrição', 'descricao', 'item', 'equipamento', 'bem', 'denominação', 'denominacao'],
            'situacao': ['situação', 'situacao', 'status', 'estado', 'condição', 'condicao'],
            'localizacao': ['localização', 'localizacao', 'local', 'setor', 'departamento', 'localidade'],
            'responsavel': ['responsavel', 'responsável', 'encarregado', 'curador', 'responsavel pela vistoria'],
            'data_ultima_vistoria': ['data da ultima vistoria', 'última vistoria', 'data ultima vistoria', 'data última vistoria', 'ultima vistoria'],
            'data_vistoria_atual': ['data da vistoria atual', 'vistoria atual', 'data vistoria atual', 'data vistoria', 'vistoria atual'],
            'auditor': ['auditor', 'auditor responsavel', 'inspetor', 'vistoriador']
        }
        
        # Converter nomes das colunas para minúsculas
        colunas_df = [str(col).strip().lower() for col in df.columns]
        
        # Procurar correspondências
        for coluna_alvo, possibilidades in possiveis_nomes.items():
            if mapeamento_colunas[coluna_alvo]:  # Já foi mapeada
                continue
                
            for possibilidade in possibilidades:
                for idx, coluna_df in enumerate(colunas_df):
                    if possibilidade in coluna_df:
                        mapeamento_colunas[coluna_alvo] = df.columns[idx]
                        print(f"✅ Coluna '{coluna_alvo}' detectada como: '{df.columns[idx]}'")
                        break
                if mapeamento_colunas[coluna_alvo]:
                    break
    
    return mapeamento_colunas

# ==============================
# FUNÇÃO PARA IMPORTAR CSV
# ==============================

def importar_csv_para_sqlite(caminho_csv: str, db_path: str, delimiter: str = ',') -> Dict[str, Any]:
    """
    Importa dados de arquivo CSV para SQLite
    Retorna: Dict com resultados detalhados
    """
    try:
        print(f"📁 Iniciando importação do arquivo CSV: {caminho_csv}")
        
        # Verificar se arquivo existe
        if not os.path.exists(caminho_csv):
            return {
                'sucesso': False, 
                'mensagem': f"❌ Arquivo CSV não encontrado: {caminho_csv}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Criar/atualizar tabela primeiro
        criar_tabela_atualizada(db_path)
        
        # Ler arquivo CSV
        try:
            # Tentar detectar encoding
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(caminho_csv, delimiter=delimiter, encoding=encoding)
                    print(f"✅ CSV lido com encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                return {
                    'sucesso': False,
                    'mensagem': "❌ Não foi possível ler o arquivo CSV com nenhum encoding comum",
                    'registros_processados': 0,
                    'registros_inseridos': 0,
                    'registros_atualizados': 0,
                    'registros_erro': 0
                }
                
            print(f"📊 DataFrame CSV carregado com {len(df)} linhas e {len(df.columns)} colunas")
        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': f"❌ Erro ao ler arquivo CSV: {str(e)}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        if df.empty:
            return {
                'sucesso': False,
                'mensagem': "❌ O arquivo CSV está vazio ou não contém dados",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Detectar mapeamento de colunas
        mapeamento = detectar_colunas(df)
        print(f"🗂️  Mapeamento de colunas: {mapeamento}")
        
        # Verificar colunas obrigatórias
        if not mapeamento['numero']:
            colunas_encontradas = ", ".join(df.columns.tolist())
            return {
                'sucesso': False,
                'mensagem': f"❌ Coluna do número do bem não detectada. Colunas encontradas: {colunas_encontradas}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        if not mapeamento['nome']:
            colunas_encontradas = ", ".join(df.columns.tolist())
            return {
                'sucesso': False,
                'mensagem': f"❌ Coluna do nome não detectada. Colunas encontradas: {colunas_encontradas}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Processar e importar dados
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        registros_inseridos = 0
        registros_atualizados = 0
        registros_erro = 0
        
        print("\n🔄 Iniciando processamento dos registros CSV...")
        
        for index, row in df.iterrows():
            linha_csv = index + 2  # +2 porque CSV tem cabeçalho na linha 1
            try:
                # Pular linhas vazias
                if row.isnull().all():
                    continue
                
                # Extrair dados básicos
                numero = normalizar_valor(row[mapeamento['numero']])
                nome = normalizar_valor(row[mapeamento['nome']])
                
                if not numero or not nome:
                    registros_erro += 1
                    print(f"⚠️  Linha {linha_csv}: Número ou nome vazio - Número: '{numero}', Nome: '{nome}'")
                    continue
                
                # Extrair dados opcionais
                situacao = normalizar_valor(row.get(mapeamento.get('situacao'), 'Pendente')) or 'Pendente'
                localizacao = normalizar_valor(row.get(mapeamento.get('localizacao'))) or ''
                responsavel = normalizar_valor(row.get(mapeamento.get('responsavel'))) or ''
                auditor = normalizar_valor(row.get(mapeamento.get('auditor'))) or ''
                
                # Processar datas
                data_ultima_vistoria = processar_data_excel(row.get(mapeamento.get('data_ultima_vistoria')))
                data_vistoria_atual = processar_data_excel(row.get(mapeamento.get('data_vistoria_atual')))
                
                # Verificar se registro já existe
                cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
                registro_existente = cursor.fetchone()
                
                if registro_existente:
                    # Atualizar registro existente
                    cursor.execute('''
                        UPDATE bens SET 
                        nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                        data_ultima_vistoria = ?, data_vistoria_atual = ?, auditor = ?,
                        data_localizacao = CASE WHEN ? != '' AND localizacao != ? THEN CURRENT_TIMESTAMP ELSE data_localizacao END
                        WHERE numero = ?
                    ''', (nome, situacao, localizacao, responsavel, 
                         data_ultima_vistoria, data_vistoria_atual, auditor,
                         localizacao, localizacao, numero))
                    
                    registros_atualizados += 1
                    print(f"🔄 Linha {linha_csv}: ATUALIZADO - {numero}")
                        
                else:
                    # Inserir novo registro
                    cursor.execute('''
                        INSERT INTO bens 
                        (numero, nome, situacao, localizacao, responsavel, 
                         data_ultima_vistoria, data_vistoria_atual, auditor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (numero, nome, situacao, localizacao, responsavel,
                         data_ultima_vistoria, data_vistoria_atual, auditor))
                    registros_inseridos += 1
                    print(f"✅ Linha {linha_csv}: NOVO - {numero} - {nome}")
                
            except Exception as e:
                registros_erro += 1
                print(f"❌ Linha {linha_csv}: ERRO - {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        # RELATÓRIO FINAL
        total_processados = registros_inseridos + registros_atualizados + registros_erro
        
        print("\n" + "="*70)
        print("📊 RELATÓRIO FINAL DA IMPORTAÇÃO CSV")
        print("="*70)
        print(f"✅ NOVOS REGISTROS INSERIDOS: {registros_inseridos}")
        print(f"🔄 REGISTROS ATUALIZADOS: {registros_atualizados}")
        print(f"❌ REGISTROS COM ERRO: {registros_erro}")
        print(f"📈 TOTAL PROCESSADO: {total_processados}")
        print("="*70)
        
        # MENSAGEM SIMPLIFICADA PARA USUÁRIO
        if registros_erro == 0:
            if registros_inseridos > 0 and registros_atualizados > 0:
                mensagem_user = f"✅ Importação concluída! {registros_inseridos} novos e {registros_atualizados} atualizados"
            elif registros_inseridos > 0:
                mensagem_user = f"✅ Importação concluída! {registros_inseridos} novos registros"
            else:
                mensagem_user = f"✅ Importação concluída! {registros_atualizados} registros atualizados"
        else:
            mensagem_user = f"⚠️ Importação com {registros_erro} erros! {total_processados - registros_erro} registros processados"
        
        return {
            'sucesso': True,
            'mensagem': mensagem_user,
            'registros_processados': total_processados,
            'registros_inseridos': registros_inseridos,
            'registros_atualizados': registros_atualizados,
            'registros_erro': registros_erro
        }
        
    except Exception as e:
        error_msg = f"❌ Erro crítico na importação CSV: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            'sucesso': False,
            'mensagem': error_msg,
            'registros_processados': 0,
            'registros_inseridos': 0,
            'registros_atualizados': 0,
            'registros_erro': 0
        }

# ==============================
# FUNÇÃO PRINCIPAL DE IMPORTAÇÃO - CORRIGIDA
# ==============================

def importar_excel_para_sqlite(caminho_excel: str, db_path: str, aba_nome: str = 'Estoque', criar_backup: bool = True, apagar_dados_antes: bool = False) -> Dict[str, Any]:
    """
    Importa dados do Excel para SQLite com nova estrutura completa
    CORREÇÃO: Melhor tratamento de erros e validações
    Retorna: Dict com resultados detalhados
    """
    try:
        print(f"📁 Iniciando importação do arquivo: {caminho_excel}")
        print(f"📊 Aba: {aba_nome}")
        print(f"🗄️  Banco de dados: {db_path}")
        print(f"🗑️  Apagar dados antes: {apagar_dados_antes}")
        
        # Verificar se arquivo existe
        if not os.path.exists(caminho_excel):
            return {
                'sucesso': False,
                'mensagem': f"❌ Arquivo não encontrado: {caminho_excel}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Verificar extensão do arquivo
        extensao = os.path.splitext(caminho_excel)[1].lower()
        if extensao == '.csv':
            return importar_csv_para_sqlite(caminho_excel, db_path)
        
        # APAGAR DADOS ANTES DA IMPORTAÇÃO (se solicitado)
        if apagar_dados_antes:
            print("🗑️  Solicitada limpeza do banco antes da importação...")
            sucesso_limpeza, mensagem_limpeza = apagar_todos_dados(db_path)
            if not sucesso_limpeza:
                return {
                    'sucesso': False,
                    'mensagem': f"❌ Falha ao apagar dados: {mensagem_limpeza}",
                    'registros_processados': 0,
                    'registros_inseridos': 0,
                    'registros_atualizados': 0,
                    'registros_erro': 0
                }
            print(f"✅ {mensagem_limpeza}")
        
        # Criar/atualizar tabela primeiro
        criar_tabela_atualizada(db_path)
        
        # Fazer backup se necessário
        backup_path = ""
        if criar_backup and os.path.exists(db_path) and not apagar_dados_antes:
            backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"backup_controle_{timestamp}.db")
            shutil.copy2(db_path, backup_path)
            mensagem_backup = f"Backup criado: {os.path.basename(backup_path)}"
            print(f"📦 {mensagem_backup}")
        else:
            mensagem_backup = ""
            print("ℹ️  Backup não criado (solicitada limpeza ou configuração)")
        
        # Carregar arquivo Excel
        try:
            wb = load_workbook(caminho_excel, read_only=True, data_only=True)
        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': f"❌ Erro ao abrir arquivo Excel: {str(e)}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        if aba_nome not in wb.sheetnames:
            abas_disponiveis = ", ".join(wb.sheetnames)
            wb.close()
            return {
                'sucesso': False,
                'mensagem': f"❌ Aba '{aba_nome}' não encontrada. Abas disponíveis: {abas_disponiveis}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        wb.close()
        
        # Ler dados com pandas
        try:
            df = pd.read_excel(caminho_excel, sheet_name=aba_nome)
            print(f"📊 DataFrame carregado com {len(df)} linhas e {len(df.columns)} colunas")
        except Exception as e:
            return {
                'sucesso': False,
                'mensagem': f"❌ Erro ao ler dados do Excel: {str(e)}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        if df.empty:
            return {
                'sucesso': False,
                'mensagem': "❌ O arquivo Excel está vazio ou não contém dados",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Detectar mapeamento de colunas
        mapeamento = detectar_colunas(df)
        print(f"🗂️  Mapeamento de colunas: {mapeamento}")
        
        # Verificar colunas obrigatórias
        if not mapeamento['numero']:
            colunas_encontradas = ", ".join(df.columns.tolist())
            return {
                'sucesso': False,
                'mensagem': f"❌ Coluna do número do bem não detectada. Colunas encontradas: {colunas_encontradas}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        if not mapeamento['nome']:
            colunas_encontradas = ", ".join(df.columns.tolist())
            return {
                'sucesso': False,
                'mensagem': f"❌ Coluna do nome não detectada. Colunas encontradas: {colunas_encontradas}",
                'registros_processados': 0,
                'registros_inseridos': 0,
                'registros_atualizados': 0,
                'registros_erro': 0
            }
        
        # Processar e importar dados
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        registros_inseridos = 0
        registros_atualizados = 0
        registros_erro = 0
        
        print("\n🔄 Iniciando processamento dos registros...")
        
        for index, row in df.iterrows():
            linha_excel = index + 2  # +2 porque Excel começa na linha 1 e pandas na 0
            try:
                # Pular linhas vazias
                if row.isnull().all():
                    continue
                
                # Extrair dados básicos
                numero = normalizar_valor(row[mapeamento['numero']])
                nome = normalizar_valor(row[mapeamento['nome']])
                
                if not numero or not nome:
                    registros_erro += 1
                    print(f"⚠️  Linha {linha_excel}: Número ou nome vazio - Número: '{numero}', Nome: '{nome}'")
                    continue
                
                # Extrair dados opcionais
                situacao = normalizar_valor(row.get(mapeamento.get('situacao'), 'Pendente')) or 'Pendente'
                localizacao = normalizar_valor(row.get(mapeamento.get('localizacao'))) or ''
                responsavel = normalizar_valor(row.get(mapeamento.get('responsavel'))) or ''
                auditor = normalizar_valor(row.get(mapeamento.get('auditor'))) or ''
                
                # Processar datas
                data_ultima_vistoria = processar_data_excel(row.get(mapeamento.get('data_ultima_vistoria')))
                data_vistoria_atual = processar_data_excel(row.get(mapeamento.get('data_vistoria_atual')))
                
                # Verificar se registro já existe
                cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
                registro_existente = cursor.fetchone()
                
                if registro_existente:
                    # Atualizar registro existente
                    cursor.execute('''
                        UPDATE bens SET 
                        nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                        data_ultima_vistoria = ?, data_vistoria_atual = ?, auditor = ?,
                        data_localizacao = CASE WHEN ? != '' AND localizacao != ? THEN CURRENT_TIMESTAMP ELSE data_localizacao END
                        WHERE numero = ?
                    ''', (nome, situacao, localizacao, responsavel, 
                         data_ultima_vistoria, data_vistoria_atual, auditor,
                         localizacao, localizacao, numero))
                    
                    registros_atualizados += 1
                    print(f"🔄 Linha {linha_excel}: ATUALIZADO - {numero}")
                        
                else:
                    # Inserir novo registro
                    cursor.execute('''
                        INSERT INTO bens 
                        (numero, nome, situacao, localizacao, responsavel, 
                         data_ultima_vistoria, data_vistoria_atual, auditor)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (numero, nome, situacao, localizacao, responsavel,
                         data_ultima_vistoria, data_vistoria_atual, auditor))
                    registros_inseridos += 1
                    print(f"✅ Linha {linha_excel}: NOVO - {numero} - {nome}")
                
                # Log a cada 20 registros para melhor acompanhamento
                total_processados = registros_inseridos + registros_atualizados
                if total_processados % 20 == 0:
                    print(f"📈 Progresso: {total_processados} registros processados...")
                
            except Exception as e:
                registros_erro += 1
                print(f"❌ Linha {linha_excel}: ERRO - {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        # RELATÓRIO FINAL DETALHADO
        total_processados = registros_inseridos + registros_atualizados + registros_erro
        
        print("\n" + "="*70)
        print("📊 RELATÓRIO FINAL DA IMPORTAÇÃO")
        print("="*70)
        print(f"✅ NOVOS REGISTROS INSERIDOS: {registros_inseridos}")
        print(f"🔄 REGISTROS ATUALIZADOS: {registros_atualizados}")
        print(f"❌ REGISTROS COM ERRO: {registros_erro}")
        print(f"📈 TOTAL PROCESSADO: {total_processados}")
        
        if registros_erro > 0:
            print(f"\n⚠️  {registros_erro} registros não puderam ser processados. Verifique os logs acima.")
        
        if mensagem_backup:
            print(f"\n📦 {mensagem_backup}")
        
        print("="*70)
        
        # MENSAGEM SIMPLIFICADA PARA USUÁRIO
        if registros_erro == 0:
            if apagar_dados_antes:
                mensagem_user = f"✅ Importação concluída! {total_processados} registros importados"
            else:
                if registros_inseridos > 0 and registros_atualizados > 0:
                    mensagem_user = f"✅ Importação concluída! {registros_inseridos} novos e {registros_atualizados} atualizados"
                elif registros_inseridos > 0:
                    mensagem_user = f"✅ Importação concluída! {registros_inseridos} novos registros"
                else:
                    mensagem_user = f"✅ Importação concluída! {registros_atualizados} registros atualizados"
        else:
            mensagem_user = f"⚠️ Importação com {registros_erro} erros! {total_processados - registros_erro} registros processados"

        return {
            'sucesso': True,
            'mensagem': mensagem_user,
            'registros_processados': total_processados,
            'registros_inseridos': registros_inseridos,
            'registros_atualizados': registros_atualizados,
            'registros_erro': registros_erro
        }
        
    except Exception as e:
        error_msg = f"❌ Erro crítico na importação: {str(e)}"
        print(error_msg)
        import traceback
        print("📋 Traceback completo:")
        traceback.print_exc()
        return {
            'sucesso': False,
            'mensagem': error_msg,
            'registros_processados': 0,
            'registros_inseridos': 0,
            'registros_atualizados': 0,
            'registros_erro': 0
        }

# ==============================
# FUNÇÕES DE VERIFICAÇÃO - CORRIGIDAS
# ==============================

def verificar_estrutura_excel(file_path: str, aba_nome: str = 'Estoque') -> Dict[str, Any]:
    """Verifica se a planilha tem a estrutura esperada - CORRIGIDA"""
    try:
        # Se for um objeto de arquivo do Flask, salvar temporariamente
        if hasattr(file_path, 'filename'):
            temp_path = f"temp_{file_path.filename}"
            file_path.save(temp_path)
            file_to_check = temp_path
        else:
            file_to_check = file_path
        
        if not os.path.exists(file_to_check):
            return {'sucesso': False, 'mensagem': f"Arquivo não encontrado: {file_to_check}"}
        
        extensao = os.path.splitext(file_to_check)[1].lower()
        
        if extensao == '.csv':
            # Verificar CSV
            try:
                df = pd.read_csv(file_to_check, nrows=1)
                colunas = df.columns.tolist()
                return {
                    'sucesso': True, 
                    'mensagem': f"Estrutura CSV válida. Colunas: {', '.join(colunas)}",
                    'colunas': colunas
                }
            except Exception as e:
                return {'sucesso': False, 'mensagem': f"Erro ao ler CSV: {str(e)}"}
        else:
            # Verificar Excel
            try:
                wb = load_workbook(file_to_check, read_only=True)
                
                if aba_nome not in wb.sheetnames:
                    abas_disponiveis = ", ".join(wb.sheetnames)
                    wb.close()
                    if hasattr(file_path, 'filename'):
                        os.remove(temp_path)
                    return {
                        'sucesso': False, 
                        'mensagem': f"Aba '{aba_nome}' não encontrada. Abas disponíveis: {abas_disponiveis}"
                    }
                
                ws = wb[aba_nome]
                
                # Obter cabeçalhos
                cabecalhos = []
                for cell in ws[1]:
                    if cell.value:
                        cabecalhos.append(str(cell.value).strip())
                
                wb.close()
                
                # Limpar arquivo temporário se existir
                if hasattr(file_path, 'filename') and os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Verificar campos obrigatórios
                campos_obrigatorios = ['numero', 'nome']
                campos_encontrados = [col.lower() for col in cabecalhos]
                
                # Verificar se temos pelo menos número e nome
                tem_numero = any('numero' in campo or 'número' in campo or 'patrimonio' in campo for campo in campos_encontrados)
                tem_nome = any('nome' in campo for campo in campos_encontrados)
                
                if not tem_numero or not tem_nome:
                    return {
                        'sucesso': False, 
                        'mensagem': f"Campos obrigatórios não encontrados. Campos disponíveis: {cabecalhos}"
                    }
                
                return {
                    'sucesso': True, 
                    'mensagem': f"Estrutura válida. Campos encontrados: {len(cabecalhos)}",
                    'colunas': cabecalhos
                }
                
            except Exception as e:
                if hasattr(file_path, 'filename') and os.path.exists(temp_path):
                    os.remove(temp_path)
                return {'sucesso': False, 'mensagem': f"Erro ao verificar estrutura: {str(e)}"}
        
    except Exception as e:
        return {'sucesso': False, 'mensagem': f"Erro geral na verificação: {str(e)}"}

def obter_colunas_excel(arquivo_excel: str, aba_nome: str = 'Estoque') -> List[str]:
    """Retorna as colunas disponíveis no arquivo Excel"""
    try:
        df = pd.read_excel(arquivo_excel, sheet_name=aba_nome, nrows=1)
        return df.columns.tolist()
    except Exception as e:
        print(f"Erro ao obter colunas: {str(e)}")
        return []

# ==============================
# FUNÇÃO PARA VERIFICAÇÃO DE PERMISSÕES
# ==============================

def verificar_permissoes_importacao(db_path: str, temp_dir: str) -> Tuple[bool, str]:
    """
    Verifica se temos permissões necessárias para importação
    Retorna: (sucesso, mensagem)
    """
    try:
        # Verificar permissão de escrita no diretório do banco
        db_dir = os.path.dirname(db_path)
        if not os.access(db_dir, os.W_OK):
            return False, f"Sem permissão de escrita no diretório: {db_dir}"
        
        # Verificar permissão de escrita no diretório temporário
        if not os.access(temp_dir, os.W_OK):
            return False, f"Sem permissão de escrita no diretório temporário: {temp_dir}"
        
        # Verificar se podemos criar arquivos no diretório do banco
        test_file = os.path.join(db_dir, 'test_permission.tmp')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            return False, f"Sem permissão para criar arquivos em: {db_dir}"
        
        return True, "Permissões verificadas com sucesso"
        
    except Exception as e:
        return False, f"Erro ao verificar permissões: {str(e)}"

# ==============================
# FUNÇÃO PARA LIMPEZA SEGURA DE ARQUIVOS TEMPORÁRIOS
# ==============================

def limpar_arquivos_temporarios(temp_dir: str, extensoes: List[str] = ['.tmp', '.xlsx', '.xls', '.csv']):
    """
    Limpa arquivos temporários antigos
    """
    try:
        if not os.path.exists(temp_dir):
            return
        
        agora = datetime.now()
        for arquivo in os.listdir(temp_dir):
            if any(arquivo.endswith(ext) for ext in extensoes):
                caminho_arquivo = os.path.join(temp_dir, arquivo)
                try:
                    # Remover arquivos com mais de 1 hora
                    tempo_criacao = datetime.fromtimestamp(os.path.getctime(caminho_arquivo))
                    diferenca = agora - tempo_criacao
                    if diferenca.total_seconds() > 3600:  # 1 hora
                        os.remove(caminho_arquivo)
                        print(f"🧹 Arquivo temporário removido: {arquivo}")
                except Exception as e:
                    print(f"⚠️  Não foi possível remover {arquivo}: {e}")
    except Exception as e:
        print(f"⚠️  Erro na limpeza de arquivos temporários: {e}")

def formatar_mensagem_importacao(resultado: Dict[str, Any], apagar_dados: bool = False) -> str:
    """Formata mensagem detalhada da importação para exibição ao usuário"""
    
    if not resultado['sucesso']:
        return resultado['mensagem']
    
    partes = []
    
    # Mensagem principal baseada no tipo de operação
    if apagar_dados:
        partes.append("🗑️ BANCO DE DADOS LIMPO E IMPORTADO COM SUCESSO!")
    else:
        partes.append("✅ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    
    # Detalhes dos registros
    if resultado['registros_inseridos'] > 0:
        partes.append(f"📥 Novos: {resultado['registros_inseridos']}")
    
    if resultado['registros_atualizados'] > 0:
        partes.append(f"🔄 Atualizados: {resultado['registros_atualizados']}")
    
    if resultado['registros_erro'] > 0:
        partes.append(f"⚠️ Erros: {resultado['registros_erro']}")
    
    partes.append(f"📊 Total processado: {resultado['registros_processados']}")
    
    return " | ".join(partes)



# ==============================
# FUNÇÃO PARA TESTE/DEBUG
# ==============================

def testar_importacao():
    """Função para testar a importação diretamente"""
    try:
        print("=== TESTANDO IMPORTAÇÃO EXCEL ===")
        
        # Caminho correto para o arquivo Excel
        excel_path = "relatorios/controle_patrimonial.xlsx"
        db_path = "relatorios/controle_patrimonial.db"
        
        print(f"📁 Procurando arquivo: {excel_path}")
        
        if not os.path.exists(excel_path):
            print(f"❌ Arquivo não encontrado: {excel_path}")
            print("📂 Conteúdo da pasta relatorios:")
            if os.path.exists("relatorios"):
                for item in os.listdir("relatorios"):
                    print(f"   - {item}")
            return
        
        print("✅ Arquivo Excel encontrado!")
        
        # Criar pasta do banco se não existir
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Testar verificação de estrutura
        print("\n1. Verificando estrutura do Excel...")
        resultado = verificar_estrutura_excel(excel_path)
        print(f"📋 {resultado['mensagem']}")
        
        if resultado['sucesso']:
            # Testar obtenção de colunas
            print("\n2. Obtendo colunas do Excel...")
            colunas = obter_colunas_excel(excel_path)
            print(f"📊 Colunas encontradas: {colunas}")
            
            # Testar importação
            print("\n3. Iniciando importação...")
            resultado_importacao = importar_excel_para_sqlite(
                excel_path, db_path, 'Estoque', 
                criar_backup=False, apagar_dados_antes=False
            )
            print(f"🎯 Resultado: {'SUCESSO' if resultado_importacao['sucesso'] else 'FALHA'}")
            print(f"💬 {resultado_importacao['mensagem']}")
        else:
            print("❌ Estrutura inválida, importação cancelada.")
            
    except Exception as e:
        print(f"💥 Erro no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    testar_importacao()