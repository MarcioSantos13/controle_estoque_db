# ==============================
# INÍCIO: app.py CORRIGIDO - VERSÃO ESTÁVEL
# ==============================

import os
import sys
import re
import sqlite3
import shutil
import io
import hashlib
from functools import wraps
from datetime import datetime
from typing import Tuple, Dict, Any, List
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for, Response, session, flash

# ==============================
# CONFIGURAÇÃO
# ==============================
class Config:
    """Configuração centralizada"""
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_RELATIVE_PATH = os.path.join("relatorios", "controle_patrimonial.db")
    DB_PATH = os.path.join(BASE_DIR, DB_RELATIVE_PATH)
    
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SESSION_COOKIE_SECURE = ENV == 'production'
    
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'temp')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    PAGINATION_SIZE = 200

# Inicialização da aplicação
app = Flask(__name__)
app.config.from_object(Config())

# ==============================
# CONSTANTES GLOBAIS
# ==============================
DATABASE = app.config['DB_PATH']

# ==============================
# FUNÇÕES AUXILIARES SIMPLIFICADAS
# ==============================
def get_db_connection():
    """Conexão simples com o banco"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela_atualizada(db_path: str) -> None:
    """Garante que a tabela bens existe"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                situacao TEXT DEFAULT 'Pendente',
                localizacao TEXT,
                responsavel TEXT,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
        
        conn.commit()
        conn.close()
        print("✅ Tabela bens criada/verificada")
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        raise

def obter_estatisticas(db_path: str) -> Dict[str, Any]:
    """Obtém estatísticas simplificadas"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Total de bens
        cursor.execute("SELECT COUNT(*) FROM bens")
        total_bens = cursor.fetchone()[0]
        
        # Bens localizados
        cursor.execute("SELECT COUNT(*) FROM bens WHERE situacao = 'Localizado'")
        localizados = cursor.fetchone()[0]
        
        # Bens pendentes
        cursor.execute("SELECT COUNT(*) FROM bens WHERE situacao = 'Pendente' OR situacao IS NULL")
        pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'sucesso': True,
            'estatisticas': {
                'total_bens': total_bens,
                'situacoes': {
                    'Localizado': localizados,
                    'Pendente': pendentes
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        return {'sucesso': False, 'estatisticas': {}}

def obter_bens_paginados(db_path: str, tipo: str = 'todos', pagina: int = 1, por_pagina: int = 50) -> Dict[str, Any]:
    """Obtém bens paginados - VERSÃO COMPLETAMENTE CORRIGIDA"""
    try:
        conn = sqlite3.connect(db_path)
        
        # NÃO usar row_factory para evitar problemas de conversão
        cursor = conn.cursor()
        
        offset = (pagina - 1) * por_pagina
        
        print(f"🔍 Buscando bens - Tipo: {tipo}, Página: {pagina}, Por página: {por_pagina}")
        
        # Query base
        if tipo == 'localizados':
            query = "SELECT * FROM bens WHERE situacao = 'Localizado' ORDER BY numero LIMIT ? OFFSET ?"
            count_query = "SELECT COUNT(*) FROM bens WHERE situacao = 'Localizado'"
            params = (por_pagina, offset)
        elif tipo == 'nao-localizados':
            query = """
                SELECT * FROM bens 
                WHERE situacao != 'Localizado' OR situacao IS NULL OR situacao = 'Pendente'
                ORDER BY numero LIMIT ? OFFSET ?
            """
            count_query = """
                SELECT COUNT(*) FROM bens 
                WHERE situacao != 'Localizado' OR situacao IS NULL OR situacao = 'Pendente'
            """
            params = (por_pagina, offset)
        else:
            query = "SELECT * FROM bens ORDER BY numero LIMIT ? OFFSET ?"
            count_query = "SELECT COUNT(*) FROM bens"
            params = (por_pagina, offset)
        
        # Contar total
        cursor.execute(count_query)
        total_registros = cursor.fetchone()[0]
        print(f"📊 Total de registros: {total_registros}")
        
        # Buscar dados - CONVERSÃO MANUAL PARA EVITAR ERROS
        cursor.execute(query, params)
        colunas = [desc[0] for desc in cursor.description]
        registros = cursor.fetchall()
        
        # Converter manualmente para lista de dicionários
        dados = []
        for registro in registros:
            bem_dict = {}
            for i, valor in enumerate(registro):
                bem_dict[colunas[i]] = valor
            dados.append(bem_dict)
        
        print(f"✅ Dados convertidos: {len(dados)} registros")
        for dado in dados:
            print(f"   - {dado.get('numero')} | {dado.get('nome')} | {dado.get('situacao')}")
        
        conn.close()
        
        total_paginas = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 else 1
        
        return {
            'dados': dados,
            'pagina_atual': pagina,
            'por_pagina': por_pagina,
            'total_registros': total_registros,
            'total_paginas': total_paginas
        }
        
    except Exception as e:
        print(f"❌ Erro CRÍTICO ao obter bens paginados: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'dados': [],
            'pagina_atual': 1,
            'por_pagina': por_pagina,
            'total_registros': 0,
            'total_paginas': 0
        }


def obter_localidades(db_path: str) -> List[str]:
    """Obtém lista de localidades - VERSÃO SIMPLIFICADA"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT localizacao FROM bens WHERE localizacao IS NOT NULL AND localizacao != '' ORDER BY localizacao")
        localidades = [row[0] for row in cursor.fetchall()]
        conn.close()
        return localidades
    except Exception as e:
        print(f"❌ Erro ao obter localidades: {e}")
        return []

def obter_todos_bens_por_localidade(db_path: str, localidade: str) -> List[Dict]:
    """Obtém todos os bens de uma localidade - VERSÃO CORRIGIDA"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM bens WHERE localizacao = ? ORDER BY numero", (localidade,))
        
        # Converter manualmente para evitar erro de dicionário
        colunas = [desc[0] for desc in cursor.description]
        registros = cursor.fetchall()
        
        bens = []
        for registro in registros:
            bem_dict = {}
            for i, valor in enumerate(registro):
                bem_dict[colunas[i]] = valor
            bens.append(bem_dict)
            
        conn.close()
        return bens
    except Exception as e:
        print(f"❌ Erro ao obter bens por localidade: {e}")
        return []


def obter_bem_por_id(db_path: str, bem_id: int) -> Dict[str, Any]:
    """Obtém um bem pelo ID - VERSÃO CORRIGIDA"""
    try:
        print(f"🔍 Buscando bem por ID: {bem_id}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Executar a consulta
        cursor.execute("SELECT * FROM bens WHERE id = ?", (bem_id,))
        resultado = cursor.fetchone()
        
        if resultado:
            # Converter para dicionário manualmente
            colunas = [desc[0] for desc in cursor.description]
            bem_dict = {}
            for i, valor in enumerate(resultado):
                bem_dict[colunas[i]] = valor
            
            print(f"✅ Bem encontrado: {bem_dict.get('numero')} - {bem_dict.get('nome')}")
            conn.close()
            return bem_dict
        else:
            print(f"❌ Bem com ID {bem_id} não encontrado")
            conn.close()
            return {}
        
    except Exception as e:
        print(f"❌ Erro ao obter bem por ID {bem_id}: {e}")
        # Garantir que a conexão seja fechada mesmo em caso de erro
        try:
            conn.close()
        except:
            pass
        return {}

def verificar_numero_existe(db_path: str, numero: str) -> bool:
    """Verifica se número já existe"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bens WHERE numero = ?", (numero,))
        existe = cursor.fetchone() is not None
        conn.close()
        return existe
    except Exception as e:
        print(f"❌ Erro ao verificar número: {e}")
        return False

def criar_novo_bem(db_path: str, dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Cria um novo bem"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO bens (numero, nome, situacao, localizacao, responsavel)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            dados['numero'],
            dados['nome'],
            dados.get('situacao', 'Pendente'),
            dados.get('localizacao', ''),
            dados.get('responsavel', '')
        ))
        
        conn.commit()
        conn.close()
        return True, "Bem criado com sucesso"
        
    except Exception as e:
        print(f"❌ Erro ao criar bem: {e}")
        return False, f"Erro ao criar bem: {str(e)}"

def atualizar_bem(db_path: str, bem_id: int, dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Atualiza um bem existente"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bens 
            SET nome = ?, situacao = ?, localizacao = ?, responsavel = ?
            WHERE id = ?
        ''', (
            dados['nome'],
            dados['situacao'],
            dados.get('localizacao', ''),
            dados.get('responsavel', ''),
            bem_id
        ))
        
        conn.commit()
        conn.close()
        return True, "Bem atualizado com sucesso"
        
    except Exception as e:
        print(f"❌ Erro ao atualizar bem: {e}")
        return False, f"Erro ao atualizar bem: {str(e)}"

def excluir_bem(db_path: str, bem_id: int) -> Tuple[bool, str]:
    """Exclui um bem"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM bens WHERE id = ?", (bem_id,))
        conn.commit()
        conn.close()
        return True, "Bem excluído com sucesso"
        
    except Exception as e:
        print(f"❌ Erro ao excluir bem: {e}")
        return False, f"Erro ao excluir bem: {str(e)}"

# ==============================
# VALIDAÇÃO
# ==============================
class InputValidator:
    """Validação de entrada"""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 255) -> str:
        """Remove caracteres perigosos"""
        if not text:
            return ""
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', str(text))
        return sanitized[:max_length].strip()
    
    @staticmethod
    def validate_number_format(numero: str) -> Tuple[bool, str]:
        """Valida formato do número"""
        if not numero or not numero.strip():
            return False, "Número do bem é obrigatório"
        
        numero = numero.strip()
        
        if len(numero) > 50:
            return False, "Número do bem muito longo"
        
        if not re.match(r'^[A-Za-z0-9\-\s\.]+$', numero):
            return False, "Número deve conter apenas letras, números, hífens, pontos ou espaços"
        
        return True, ""

# ==============================
# SISTEMA DE AUTENTICAÇÃO
# ==============================
def hash_senha(senha):
    """Gera hash da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_login(email, senha):
    """Verifica se o login é válido"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, nome, senha_hash, tipo, ativo 
            FROM usuarios 
            WHERE email = ? AND ativo = 1
        ''', (email,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario and usuario[3] == hash_senha(senha):
            return {
                'id': usuario[0],
                'email': usuario[1],
                'nome': usuario[2],
                'tipo': usuario[4]
            }
        return None
        
    except Exception as e:
        print(f"❌ Erro ao verificar login: {e}")
        return None

def criar_tabela_usuarios_se_nao_existir():
    """Cria a tabela de usuários se não existir"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if not cursor.fetchone():
            print("Criando tabela usuarios...")
            
            cursor.execute('''
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    tipo TEXT DEFAULT 'usuario',
                    ativo INTEGER DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO usuarios (email, nome, senha_hash, tipo, ativo)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                'admin@sistema.com',
                'Administrador',
                hash_senha('admin123'),
                'admin',
                1
            ))
            
            conn.commit()
            print("✅ Tabela usuarios criada com sucesso!")
        else:
            print("ℹ️ Tabela usuarios já existe")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao criar tabela de usuários: {e}")
        raise e

def login_required(f):
    """Decorator para exigir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator para exigir privilégios de admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        if session.get('usuario_tipo') != 'admin':
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
def carregar_dados_bancos() -> Dict[str, int]:
    """Carrega contagens do banco"""
    try:
        estatisticas = obter_estatisticas(DATABASE)
        
        if not estatisticas['sucesso']:
            return {'localizados_count': 0, 'nao_localizados_count': 0, 'total_count': 0}
        
        situacoes = estatisticas['estatisticas'].get('situacoes', {})
        
        localizados = situacoes.get('Localizado', 0)
        pendentes = situacoes.get('Pendente', 0)
        total = estatisticas['estatisticas'].get('total_bens', 0)
        
        return {
            'localizados_count': localizados,
            'nao_localizados_count': pendentes,
            'total_count': total
        }
    except Exception as e:
        print(f"❌ Erro ao carregar contagens do banco: {e}")
        return {'localizados_count': 0, 'nao_localizados_count': 0, 'total_count': 0}

def criar_estrutura_diretorios():
    """Garante que todos os diretórios necessários existam"""
    diretorios = [
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['BASE_DIR'], 'logs'),
        os.path.dirname(DATABASE),
        os.path.join(os.path.dirname(DATABASE), 'backups')
    ]
    
    for diretorio in diretorios:
        try:
            os.makedirs(diretorio, exist_ok=True)
            print(f"✅ Diretório criado/verificado: {diretorio}")
        except Exception as e:
            print(f"⚠️ Erro ao criar diretório {diretorio}: {e}")

# ==============================
# FILTROS TEMPLATE
# ==============================
@app.template_filter('number_format')
def number_format_filter(value):
    """Filtro para formatar números"""
    try:
        if value is None:
            return "0"
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('pluralize')
def pluralize_filter(value, singular, plural):
    """Filtro para pluralizar palavras"""
    try:
        num = int(value)
        return singular if num == 1 else plural
    except (ValueError, TypeError):
        return plural

# ==============================
# ROTAS PRINCIPAIS
# ==============================

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Página inicial - LÓGICA CORRIGIDA: Bem é localizado automaticamente"""
    if request.method == 'POST':
        numero_bem = request.form.get('numero_bem', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        
        print(f"🎯 PROCESSANDO: {numero_bem} | Localização: '{localizacao}'")
        
        valido, mensagem_validacao = InputValidator.validate_number_format(numero_bem)
        if not valido:
            flash(mensagem_validacao, 'error')
            return render_template('index.html', 
                                 mensagem=mensagem_validacao,
                                 **carregar_dados_bancos())

        try:
            if not numero_bem:
                flash('Número do bem é obrigatório.', 'error')
                return redirect(url_for('index'))
            
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            
            # Verificar se o bem existe
            cursor.execute("SELECT numero, nome, situacao, localizacao FROM bens WHERE numero = ?", (numero_bem,))
            resultado = cursor.fetchone()
            
            if not resultado:
                flash(f'❌ Bem {numero_bem} não encontrado no sistema.', 'error')
                conn.close()
                return redirect(url_for('index'))
            
            # Extrair dados
            bem_numero = resultado[0]
            bem_nome = resultado[1]
            bem_situacao_anterior = resultado[2]
            bem_localizacao_anterior = resultado[3]
            
            print(f"📋 Bem: {bem_numero} | Status anterior: {bem_situacao_anterior} | Localização anterior: {bem_localizacao_anterior}")
            
            # LÓGICA PRINCIPAL CORRIGIDA:
            # 1. O bem é SEMPRE marcado como localizado quando encontrado
            # 2. A localização é atualizada se for informada, senão mantém a anterior
            
            if localizacao:
                # Usar a nova localização informada
                nova_localizacao = localizacao
                mensagem_localizacao = f' em: {localizacao}'
            else:
                # Manter a localização anterior se existir
                nova_localizacao = bem_localizacao_anterior if bem_localizacao_anterior else 'Localizado'
                mensagem_localizacao = f' (localização mantida: {bem_localizacao_anterior})' if bem_localizacao_anterior else ''
            
            # ATUALIZAR PARA LOCALIZADO
            cursor.execute(
                "UPDATE bens SET localizacao = ?, situacao = 'Localizado' WHERE numero = ?",
                (nova_localizacao, numero_bem)
            )
            
            linhas_afetadas = cursor.rowcount
            
            if linhas_afetadas > 0:
                conn.commit()
                
                if bem_situacao_anterior == 'Localizado':
                    mensagem = f'🔁 Bem {bem_numero} já estava localizado. Localização atualizada{mensagem_localizacao}'
                    categoria = 'info'
                else:
                    mensagem = f'✅ Bem {bem_numero} localizado com sucesso{mensagem_localizacao}'
                    categoria = 'success'
                
                flash(mensagem, categoria)
                print(f"✅ SUCESSO: {mensagem}")
                
            else:
                flash('⚠️ Bem encontrado, mas não foi possível atualizar o status.', 'warning')
            
            conn.close()
            
            # Focar automaticamente no campo de número para próximo bem
            return render_template('index.html', 
                                 mensagem=None,
                                 focus_numero_bem=True,
                                 **carregar_dados_bancos())
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            flash(f'Erro ao processar o bem: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    # GET request - foco automático no campo de número do bem
    focus_numero_bem = request.args.get('focus_numero_bem', True)
    
    return render_template('index.html', 
                         mensagem=None,
                         show_modal=False,
                         focus_numero_bem=focus_numero_bem,
                         **carregar_dados_bancos())

@app.route('/visualizar/<tipo>')
@login_required
def visualizar(tipo: str):
    """Página de visualização de bens"""
    if not os.path.exists(DATABASE):
        return render_template('visualizar.html', 
                             titulo='Visualização', 
                             tipo=tipo,
                             paginacao={
                                 'dados': [],
                                 'pagina_atual': 1,
                                 'por_pagina': app.config['PAGINATION_SIZE'],
                                 'total_registros': 0,
                                 'total_paginas': 0
                             },
                             mensagem="Banco de dados não encontrado.")

    try:
        pagina = max(1, request.args.get('pagina', 1, type=int))
        por_pagina = max(50, min(
            request.args.get('por_pagina', app.config['PAGINATION_SIZE'], type=int), 
            1000
        ))
        
        paginacao = obter_bens_paginados(DATABASE, tipo, pagina, por_pagina)
        
        titulos = {
            'localizados': 'Bens Localizados',
            'nao-localizados': 'Bens Não Localizados'
        }
        titulo = titulos.get(tipo, 'Visualização')
        
        return render_template('visualizar.html', 
                             titulo=titulo,
                             tipo=tipo,
                             paginacao=paginacao)
            
    except Exception as e:
        print(f"❌ Erro em /visualizar/{tipo}: {e}")
        return render_template('visualizar.html', 
                             titulo='Erro',
                             tipo=tipo,
                             paginacao={
                                 'dados': [],
                                 'pagina_atual': 1,
                                 'por_pagina': app.config['PAGINATION_SIZE'],
                                 'total_registros': 0,
                                 'total_paginas': 0
                             },
                             mensagem=f"Erro ao carregar dados: {str(e)}")



@app.route('/atualizar-status/<numero_bem>/<localizacao>')
@login_required
def atualizar_status(numero_bem: str, localizacao: str):
    """Rota para forçar atualização de status (apenas para teste)"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Atualizar diretamente
        cursor.execute(
            "UPDATE bens SET localizacao = ?, situacao = 'Localizado' WHERE numero = ?",
            (localizacao, numero_bem)
        )
        
        # Verificar
        cursor.execute("SELECT numero, situacao, localizacao FROM bens WHERE numero = ?", (numero_bem,))
        resultado = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Bem {numero_bem} atualizado',
            'novo_status': resultado[1],
            'localizacao': resultado[2]
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)})





@app.route('/exportar/<tipo>')
@login_required
def exportar(tipo: str):
    """Exporta relatórios para Excel"""
    if not os.path.exists(DATABASE):
        abort(404, description="Banco de dados não encontrado.")
    
    if tipo not in ['localizados', 'nao-localizados']:
        abort(400, description="Tipo inválido.")
    
    try:
        import pandas as pd

        if tipo == 'localizados':
            query = "SELECT numero, nome, situacao, localizacao, responsavel FROM bens WHERE situacao = 'Localizado'"
            nome_arquivo = 'bens_localizados'
        else:
            query = "SELECT numero, nome, situacao, localizacao, responsavel FROM bens WHERE situacao != 'Localizado' OR situacao IS NULL"
            nome_arquivo = 'bens_nao_localizados'

        conn = sqlite3.connect(DATABASE)
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            abort(404, description="Nenhum dado encontrado para exportação")

        if 'numero' in df.columns:
            df = df.sort_values(by='numero')

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        caminho_arquivo = os.path.join(
            os.path.dirname(DATABASE),
            f"{nome_arquivo}_{timestamp}.xlsx"
        )

        df.to_excel(caminho_arquivo, index=False)
        print(f"✅ Relatório exportado: {caminho_arquivo} ({len(df)} registros)")

        return send_file(caminho_arquivo, as_attachment=True)

    except ImportError:
        abort(500, description="Pandas não está instalado")
    except Exception as e:
        print(f"❌ Erro na exportação: {e}")
        abort(500, description="Erro ao exportar dados")

@app.route('/exportar-localidade/<localidade>')
@login_required
def exportar_localidade(localidade: str):
    """Exporta relatório por localidade"""
    if not os.path.exists(DATABASE):
        abort(404, description="Banco de dados não encontrado.")
    
    try:
        import pandas as pd
        
        registros = obter_todos_bens_por_localidade(DATABASE, localidade)
        
        if not registros:
            abort(404, description=f"Nenhum bem encontrado para a localidade: {localidade}")
        
        df = pd.DataFrame(registros)
        if 'numero' in df.columns:
            df = df.sort_values(by='numero')
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        nome_seguro = re.sub(r'[^\w\s-]', '', localidade).strip().lower()
        nome_seguro = re.sub(r'[-\s]+', '_', nome_seguro)
        
        caminho_arquivo = os.path.join(
            os.path.dirname(DATABASE),
            f"bens_localidade_{nome_seguro}_{timestamp}.xlsx"
        )
        
        df.to_excel(caminho_arquivo, index=False)
        print(f"✅ Relatório por localidade exportado: {caminho_arquivo}")
        
        return send_file(caminho_arquivo, as_attachment=True)
        
    except Exception as e:
        print(f"❌ Erro ao exportar localidade: {e}")
        abort(500, description="Erro ao exportar dados da localidade")

@app.route('/relatorio-localidades')
@login_required
def relatorio_localidades():
    """Página de relatórios por localidade - VERSÃO CORRIGIDA"""
    try:
        localidades = obter_localidades(DATABASE)
        localidade_selecionada = request.args.get('localidade', '').strip()
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 20, type=int)
        
        print(f"🔍 Relatório Localidades - Selecionada: '{localidade_selecionada}'")
        
        paginacao = None
        mensagem = None
        
        if localidade_selecionada:
            # Buscar bens da localidade selecionada
            bens = obter_todos_bens_por_localidade(DATABASE, localidade_selecionada)
            
            if bens:
                # Aplicar paginação manual
                total_registros = len(bens)
                offset = (pagina - 1) * por_pagina
                dados_paginados = bens[offset:offset + por_pagina]
                total_paginas = (total_registros + por_pagina - 1) // por_pagina
                
                paginacao = {
                    'dados': dados_paginados,
                    'pagina_atual': pagina,
                    'por_pagina': por_pagina,
                    'total_registros': total_registros,
                    'total_paginas': total_paginas
                }
                
                print(f"✅ Encontrados {total_registros} bens em '{localidade_selecionada}'")
            else:
                mensagem = f"Nenhum bem encontrado para a localidade: {localidade_selecionada}"
                print(f"❌ {mensagem}")
        
        return render_template('relatorio_localidades.html', 
                             localidades=localidades,
                             localidade_selecionada=localidade_selecionada,
                             paginacao=paginacao,
                             mensagem=mensagem,
                             total_localidades=len(localidades))
        
    except Exception as e:
        print(f"❌ Erro ao carregar relatório de localidades: {e}")
        flash('Erro ao carregar relatório de localidades.', 'error')
        return redirect(url_for('index'))

@app.route('/debug-bens')
@login_required
def debug_bens():
    """Rota temporária para debug dos bens"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Ver todos os bens
        cursor.execute("SELECT * FROM bens")
        todos_bens = cursor.fetchall()
        
        # Ver bens pendentes
        cursor.execute("SELECT * FROM bens WHERE situacao != 'Localizado' OR situacao IS NULL")
        pendentes = cursor.fetchall()
        
        # Ver bens localizados
        cursor.execute("SELECT * FROM bens WHERE situacao = 'Localizado'")
        localizados = cursor.fetchall()
        
        conn.close()
        
        resultado = {
            'total_bens': len(todos_bens),
            'pendentes': len(pendentes),
            'localizados': len(localizados),
            'dados_pendentes': [dict(row) for row in pendentes],
            'dados_localizados': [dict(row) for row in localizados]
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'erro': str(e)})





# ==============================
# ROTAS DA API
# ==============================
@app.route('/api/bens', methods=['POST'])
@login_required
def api_criar_bem():
    """Cria um novo bem"""
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400
        
        if not dados.get('numero') or not dados.get('numero').strip():
            return jsonify({'success': False, 'message': 'Número do bem é obrigatório'}), 400
        
        if not dados.get('nome') or not dados.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do bem é obrigatório'}), 400
            
        numero = InputValidator.sanitize_input(dados['numero'])
        nome = InputValidator.sanitize_input(dados['nome'])
        
        if verificar_numero_existe(DATABASE, numero):
            return jsonify({'success': False, 'message': 'Número do bem já existe'}), 400
        
        success, message = criar_novo_bem(DATABASE, {
            'numero': numero,
            'nome': nome,
            'situacao': InputValidator.sanitize_input(dados.get('situacao', 'Pendente')),
            'localizacao': InputValidator.sanitize_input(dados.get('localizacao', '')),
            'responsavel': InputValidator.sanitize_input(dados.get('responsavel', ''))
        })
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"❌ Erro ao criar bem: {e}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/api/bens/<int:bem_id>', methods=['GET'])
@login_required
def api_obter_bem(bem_id):
    """Obtém dados de um bem pelo ID - VERSÃO CORRIGIDA"""
    try:
        print(f"🎯 API: Buscando bem ID {bem_id}")
        
        bem = obter_bem_por_id(DATABASE, bem_id)
        
        if bem:
            print(f"✅ API: Bem {bem_id} encontrado - {bem.get('numero')}")
            return jsonify({'success': True, 'data': bem})
        else:
            print(f"❌ API: Bem {bem_id} não encontrado")
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Erro na API ao obter bem {bem_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/bens/<int:bem_id>', methods=['PUT'])
@login_required
def api_atualizar_bem(bem_id):
    """Atualiza um bem existente"""
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400
        
        success, message = atualizar_bem(DATABASE, bem_id, {
            'nome': InputValidator.sanitize_input(dados.get('nome')),
            'situacao': InputValidator.sanitize_input(dados.get('situacao')),
            'localizacao': InputValidator.sanitize_input(dados.get('localizacao')),
            'responsavel': InputValidator.sanitize_input(dados.get('responsavel'))
        })
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"❌ Erro ao atualizar bem {bem_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bens/<int:bem_id>', methods=['DELETE'])
@login_required
def api_excluir_bem(bem_id):
    """Exclui um bem"""
    try:
        success, message = excluir_bem(DATABASE, bem_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        print(f"❌ Erro ao excluir bem {bem_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# ROTAS DE AUTENTICAÇÃO
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if 'usuario_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        if not email or '@' not in email:
            flash('Por favor, informe um e-mail válido.', 'error')
            return render_template('login.html')
        
        usuario = verificar_login(email, senha)
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_email'] = usuario['email']
            session['usuario_nome'] = usuario['nome']
            session['usuario_tipo'] = usuario['tipo']
            
            flash(f'Bem-vindo(a), {usuario["nome"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail ou senha incorretos.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Faz logout do usuário"""
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

# ==============================
# ROTA DE IMPORTAÇÃO
# ==============================
@app.route('/importar-excel', methods=['POST'])
@login_required
@admin_required
def importar_excel():
    """Importa dados do Excel ou CSV para o banco de dados"""
    try:
        if 'excel_file' not in request.files:
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('index'))
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('index'))
        
        # Validar extensão
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Formato de arquivo inválido. Use .xlsx, .xls ou .csv.', 'error')
            return redirect(url_for('index'))
        
        # Salvar arquivo temporariamente
        temp_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_path)
        
        try:
            # Importar usando utils
            from utils.excel_importer import importar_excel_para_sqlite, importar_csv_para_sqlite
            
            if file_ext == '.csv':
                resultado = importar_csv_para_sqlite(temp_path, DATABASE)
            else:
                resultado = importar_excel_para_sqlite(temp_path, DATABASE)
            
            if resultado['sucesso']:
                flash(f"✅ {resultado['mensagem']}", 'success')
            else:
                flash(f"❌ {resultado['mensagem']}", 'error')
            
        except Exception as e:
            flash(f"❌ Erro durante a importação: {str(e)}", 'error')
            print(f"❌ Erro na importação: {e}")
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f"❌ Erro interno na importação: {str(e)}", 'error')
        print(f"❌ Erro na importação do Excel/CSV: {e}")
        return redirect(url_for('index'))

# ==============================
# ROTA DO SISTEMA CRUD
# ==============================
@app.route('/sistema-crud')
@login_required
def sistema_crud():
    """Página completa de CRUD para gerenciamento de bens - VERSÃO CORRIGIDA"""
    try:
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        termo_busca = request.args.get('q', '').strip()
        situacao_filtro = request.args.get('situacao', '').strip()
        responsavel_filtro = request.args.get('responsavel', '').strip()
        
        print(f"🔍 FILTROS APLICADOS:")
        print(f"   - Situação: '{situacao_filtro}'")
        print(f"   - Busca: '{termo_busca}'")
        print(f"   - Responsável: '{responsavel_filtro}'")
        
        # Determinar o tipo baseado no filtro de situação
        tipo = 'todos'
        if situacao_filtro == 'OK':
            tipo = 'localizados'
        elif situacao_filtro == 'Pendente':
            tipo = 'nao-localizados'
        
        paginacao = obter_bens_paginados(DATABASE, tipo, pagina, por_pagina)
        estatisticas = carregar_dados_bancos()
        
        # Aplicar filtros adicionais se necessário
        if termo_busca or responsavel_filtro:
            dados_filtrados = []
            for bem in paginacao['dados']:
                # Filtro por termo de busca
                if termo_busca:
                    termo_match = (termo_busca.lower() in (bem.get('numero', '') or '').lower() or 
                                  termo_busca.lower() in (bem.get('nome', '') or '').lower())
                else:
                    termo_match = True
                
                # Filtro por responsável
                if responsavel_filtro:
                    resp_match = responsavel_filtro.lower() in (bem.get('responsavel', '') or '').lower()
                else:
                    resp_match = True
                
                if termo_match and resp_match:
                    dados_filtrados.append(bem)
            
            paginacao['dados'] = dados_filtrados
            paginacao['total_registros'] = len(dados_filtrados)
        
        return render_template('sistema_crud.html',
                            paginacao=paginacao,
                            termo_busca=termo_busca,
                            **estatisticas,
                            mensagem=None)
        
    except Exception as e:
        print(f"❌ Erro na página CRUD: {e}")
        return render_template('sistema_crud.html',
                            paginacao={
                                'dados': [],
                                'pagina_atual': 1,
                                'por_pagina': 50,
                                'total_registros': 0,
                                'total_paginas': 0
                            },
                            termo_busca='',
                            total_count=0,
                            localizados_count=0,
                            nao_localizados_count=0,
                            mensagem=f"Erro ao carregar dados: {str(e)}")
# ==============================
# HANDLERS DE ERRO
# ==============================
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Recurso não encontrado'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"❌ Erro interno: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    return render_template('500.html'), 500

# ==============================
# ROTAS ADICIONAIS
# ==============================
@app.route('/perfil')
@login_required
def perfil():
    """Rota de perfil do usuário"""
    return redirect(url_for('index'))

@app.route('/cadastrar-usuario')
@login_required
@admin_required
def cadastrar_usuario():
    """Rota para cadastrar usuário"""
    flash('Funcionalidade de cadastro de usuários em desenvolvimento.', 'info')
    return redirect(url_for('sistema_crud'))

@app.route('/listar-usuarios')  
@login_required
@admin_required
def listar_usuarios():
    """Rota para listar usuários"""
    flash('Funcionalidade de gerenciamento de usuários em desenvolvimento.', 'info')
    return redirect(url_for('sistema_crud'))

# ==============================
# ROTAS DE AJUDA
# ==============================
@app.route('/ajuda')
@login_required
def ajuda():
    """Página principal de ajuda"""
    return render_template('ajuda.html')

@app.route('/ajuda/<topico>')
@login_required
def ajuda_topico(topico):
    """Página de tópicos específicos de ajuda"""
    topicos_validos = ['importacao', 'busca', 'exportacao', 'scanner', 'cadastro']
    
    if topico not in topicos_validos:
        flash('Tópico de ajuda não encontrado.', 'error')
        return redirect(url_for('ajuda'))
    
    titulos = {
        'importacao': 'Importação de Dados',
        'busca': 'Busca e Localização',
        'exportacao': 'Exportação de Relatórios', 
        'scanner': 'Uso do Scanner',
        'cadastro': 'Cadastro de Bens'
    }
    
    return render_template('ajuda_topico.html', topico=topico, titulo=titulos.get(topico, 'Ajuda'))


@app.route('/teste-bens-simples')
@login_required
def teste_bens_simples():
    """Teste simples dos bens pendentes"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Buscar bens pendentes de forma simples
        cursor.execute("""
            SELECT id, numero, nome, situacao, localizacao, responsavel 
            FROM bens 
            WHERE situacao != 'Localizado' OR situacao IS NULL OR situacao = 'Pendente'
        """)
        
        bens = cursor.fetchall()
        conn.close()
        
        # Formatar manualmente
        dados_simples = []
        for bem in bens:
            dados_simples.append({
                'id': bem[0],
                'numero': bem[1],
                'nome': bem[2],
                'situacao': bem[3],
                'localizacao': bem[4],
                'responsavel': bem[5]
            })
        
        return jsonify({
            'sucesso': True,
            'total': len(dados_simples),
            'bens': dados_simples
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)})

@app.route('/debug-status-bens')
@login_required
def debug_status_bens():
    """Debug do status dos bens"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Ver todos os bens com seus status
        cursor.execute("SELECT numero, nome, situacao, localizacao FROM bens ORDER BY numero")
        todos_bens = cursor.fetchall()
        
        conn.close()
        
        # Formatar resultado
        resultado = {
            'total_bens': len(todos_bens),
            'bens': []
        }
        
        for bem in todos_bens:
            resultado['bens'].append({
                'numero': bem[0],
                'nome': bem[1],
                'situacao': bem[2],
                'localizacao': bem[3]
            })
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({'erro': str(e)})


# ==============================
# INICIALIZAÇÃO
# ==============================
if __name__ == '__main__':
    # Criar estrutura de diretórios
    criar_estrutura_diretorios()
    
    # Criar tabelas
    criar_tabela_usuarios_se_nao_existir()
    criar_tabela_atualizada(DATABASE)
    
    print("=== SISTEMA INICIADO ===")
    print(f"📁 Diretório de trabalho: {app.config['BASE_DIR']}")
    print(f"🔓 Modo desenvolvimento - segurança reduzida")
    print("Tabela usuarios já existe")
    print("Iniciando aplicação Flask")
    print("🔧 Iniciando em modo DESENVOLVIMENTO")
    print("🌐 Servidor iniciado em http://0.0.0.0:5000")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )