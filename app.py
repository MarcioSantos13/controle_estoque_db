# INÍCIO: app.py CORRIGIDO - VERSÃO ESTÁVEL
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
# CONFIGURAÇÃO ROBUSTA MULTI-AMBIENTE
# ==============================
class Config:
    """Configuração centralizada com detecção automática de ambiente"""
    
    # Caminhos absolutos robustos
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_RELATIVE_PATH = os.path.join("relatorios", "controle_patrimonial.db")
    DB_PATH = os.path.join(BASE_DIR, DB_RELATIVE_PATH)
    
    # Configurações por ambiente
    ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = ENV == 'development'
    TESTING = ENV == 'testing'
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SESSION_COOKIE_SECURE = ENV == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload e limites
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'temp')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Performance
    PAGINATION_SIZE = 200
    EXPORT_CHUNK_SIZE = 1000
    JSON_SORT_KEYS = False
    
    # Logging
    LOG_LEVEL = 'DEBUG' if DEBUG else 'WARNING'

class ProductionConfig(Config):
    """Configuração específica para produção"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError("SECRET_KEY must be set in production environment")
        return key

class DevelopmentConfig(Config):
    """Configuração específica para desenvolvimento"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False

def get_config():
    """Retorna configuração baseada no ambiente"""
    env = os.environ.get('FLASK_ENV', 'development')
    return ProductionConfig() if env == 'production' else DevelopmentConfig()

# Inicialização da aplicação
config = get_config()
app = Flask(__name__)
app.config.from_object(config)

# Importar handlers APÓS configuração
try:
    from utils.db_handler import (
        verificar_bem, marcar_bem_localizado, gerar_planilhas_localizacao,
        buscar_localizacao_existente, obter_bem_por_numero, atualizar_bem,
        excluir_bem, criar_novo_bem, buscar_bens_por_nome, contar_bens,
        obter_bens_paginados, obter_localidades, obter_bens_por_localidade,
        obter_todos_bens_por_localidade, verificar_localidade_existe,
        verificar_numero_existe, obter_bem_por_id, criar_tabela_atualizada
    )
    from utils.excel_importer import importar_excel_para_sqlite, verificar_estrutura_excel, importar_csv_para_sqlite
    from utils.logger import logger
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

# ==============================
# SISTEMA DE SEGURANÇA
# ==============================
def setup_security(app):
    """Configura segurança baseada no ambiente"""
    try:
        from flask_talisman import Talisman
        
        csp = {
            'default-src': ["'self'"],
            'script-src': [
                "'self'", 
                'https://cdn.jsdelivr.net',
                'https://unpkg.com',
                "'unsafe-inline'"
            ],
            'style-src': [
                "'self'",
                'https://cdn.jsdelivr.net',
                "'unsafe-inline'"
            ],
            'img-src': ["'self'", 'data:', 'blob:'],
            'media-src': ["'self'", 'blob:']
        }
        
        if app.config['ENV'] == 'production':
            Talisman(
                app,
                content_security_policy=csp,
                force_https=True,
                session_cookie_secure=True,
                strict_transport_security=True
            )
            logger.info("🔒 Segurança de produção configurada")
        else:
            # Desenvolvimento: segurança relaxada
            Talisman(app, content_security_policy=None)
            logger.info("🔓 Modo desenvolvimento - segurança reduzida")
            
    except ImportError:
        logger.warning("⚠️ Flask-Talisman não instalado - executando sem CSP")

# Configurar segurança
setup_security(app)

# ==============================
# VALIDAÇÃO E SEGURANÇA DE DADOS
# ==============================
class InputValidator:
    """Validação robusta de entrada de dados"""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 255) -> str:
        """Remove caracteres perigosos e limita tamanho"""
        if not text:
            return ""
        
        # Remove caracteres de controle e limita tamanho
        sanitized = re.sub(r'[\x00-\x1F\x7F]', '', str(text))
        return sanitized[:max_length].strip()
    
    @staticmethod
    def validate_number_format(numero: str) -> Tuple[bool, str]:
        """Valida formato do número do bem"""
        if not numero or not numero.strip():
            return False, "Número do bem é obrigatório"
        
        numero = numero.strip()
        
        if len(numero) > 50:
            return False, "Número do bem muito longo (máx. 50 caracteres)"
        
        if not re.match(r'^[A-Za-z0-9\-\s\.]+$', numero):
            return False, "Número deve conter apenas letras, números, hífens, pontos ou espaços"
        
        return True, ""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Valida formato de e-mail"""
        if not email or '@' not in email:
            return False, "E-mail inválido"
        
        if len(email) > 254:
            return False, "E-mail muito longo"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Formato de e-mail inválido"
        
        return True, ""

class ErrorHandler:
    """Manipulação centralizada de erros"""
    
    @staticmethod
    def handle_database_error(e: Exception, operation: str = "operacao") -> str:
        """Log e trata erros de banco de dados"""
        error_msg = f"Erro de banco na {operation}: {str(e)}"
        logger.error(error_msg)
        
        if "no such table" in str(e).lower():
            return "Erro: Estrutura do banco de dados corrompida"
        elif "disk i/o" in str(e).lower():
            return "Erro de acesso ao banco de dados"
        elif "locked" in str(e).lower():
            return "Banco de dados temporariamente indisponível"
        else:
            return "Erro interno do sistema"

    @staticmethod
    def handle_file_error(e: Exception, operation: str = "operacao") -> str:
        """Log e trata erros de arquivo"""
        error_msg = f"Erro de arquivo na {operation}: {str(e)}"
        logger.error(error_msg)
        
        if "permission" in str(e).lower():
            return "Erro de permissão de arquivo"
        elif "no space" in str(e).lower():
            return "Espaço em disco insuficiente"
        else:
            return "Erro de processamento de arquivo"

# ==============================
# SERVIÇOS PRINCIPAIS
# ==============================
class BemService:
    """Serviço centralizado para operações com bens"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def processar_localizacao(self, numero_bem: str, localizacao: str = None) -> Dict[str, Any]:
        """Processa a localização de um bem com validação"""
        try:
            # Validar entrada
            valido, mensagem_validacao = InputValidator.validate_number_format(numero_bem)
            if not valido:
                return {
                    'mensagem': mensagem_validacao,
                    'bem_detalhes': None,
                    'localizacao_informada': localizacao,
                    'show_modal': False
                }
            
            numero_clean = InputValidator.sanitize_input(numero_bem)
            localizacao_clean = InputValidator.sanitize_input(localizacao) if localizacao else None
            
            if not localizacao_clean:
                localizacao_clean = buscar_localizacao_existente(numero_clean, self.db_path)
            
            encontrado, erro = verificar_bem(numero_clean, self.db_path)
            if not encontrado:
                return {
                    'mensagem': erro or 'Bem não encontrado.',
                    'bem_detalhes': None,
                    'localizacao_informada': localizacao_clean,
                    'show_modal': False
                }
            
            mensagem = marcar_bem_localizado(numero_clean, self.db_path, localizacao_clean)
            bem_detalhes = self._obter_detalhes_bem(numero_clean, localizacao_clean)
            
            return {
                'mensagem': mensagem,
                'bem_detalhes': bem_detalhes,
                'localizacao_informada': localizacao_clean,
                'show_modal': True
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar bem {numero_bem}: {str(e)}")
            return {
                'mensagem': 'Erro interno ao processar o bem.',
                'bem_detalhes': None,
                'localizacao_informada': localizacao,
                'show_modal': False
            }
    
    def _obter_detalhes_bem(self, numero_bem: str, localizacao: str = None) -> Dict[str, Any] | None:
        """Busca detalhes de um bem específico"""
        try:
            bem = obter_bem_por_numero(self.db_path, numero_bem)

            if bem:
                localizacao_final = localizacao or bem.get('localizacao') or 'Não informada'

                return {
                    'id': bem.get('id'),
                    'nome': bem.get('nome') or 'Não informado',
                    'numero': bem.get('numero') or 'Não informado',
                    'situacao': bem.get('situacao') or 'Pendente',
                    'localizacao': localizacao_final,
                    'responsavel': bem.get('responsavel') or 'Não informado',
                    'data_ultima_vistoria': bem.get('data_ultima_vistoria') or 'Não informada',
                    'data_vistoria_atual': bem.get('data_vistoria_atual') or 'Não informada',
                    'auditor': bem.get('auditor') or 'Não informado',
                    'data_criacao': bem.get('data_criacao'),
                    'data_localizacao': bem.get('data_localizacao')
                }

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do bem {numero_bem}: {str(e)}")
            return None

    def criar_bem(self, dados: Dict[str, Any]) -> Tuple[bool, str]:
        """Cria um novo bem no sistema com validação"""
        try:
            # Validar dados obrigatórios
            if not dados.get('numero') or not dados.get('numero').strip():
                return False, "Número do bem é obrigatório"
            
            if not dados.get('nome') or not dados.get('nome').strip():
                return False, "Nome do bem é obrigatório"
            
            valido, mensagem_validacao = InputValidator.validate_number_format(dados['numero'])
            if not valido:
                return False, mensagem_validacao

            if verificar_numero_existe(self.db_path, dados['numero']):
                return False, "Já existe um bem com este número!"

            dados_completos = {
                'numero': InputValidator.sanitize_input(dados['numero']),
                'nome': InputValidator.sanitize_input(dados['nome']),
                'situacao': InputValidator.sanitize_input(dados.get('situacao', 'Pendente')),
                'localizacao': InputValidator.sanitize_input(dados.get('localizacao', '')),
                'responsavel': InputValidator.sanitize_input(dados.get('responsavel', '')),
                'data_ultima_vistoria': dados.get('data_ultima_vistoria'),
                'data_vistoria_atual': dados.get('data_vistoria_atual'),
                'auditor': InputValidator.sanitize_input(dados.get('auditor', '')),
                'observacoes': InputValidator.sanitize_input(dados.get('observacoes', ''))
            }

            return criar_novo_bem(self.db_path, dados_completos)

        except Exception as e:
            logger.error(f"Erro ao criar bem: {str(e)}")
            return False, f"Erro interno: {str(e)}"

    def exportar_bens_por_tipo(self, tipo: str) -> Response:
        """Exporta bens por tipo incluindo novos campos"""
        try:
            import pandas as pd

            if tipo == 'localizados':
                query = """
                    SELECT numero, nome, situacao, localizacao, responsavel, 
                           data_ultima_vistoria, data_vistoria_atual, auditor 
                    FROM bens 
                    WHERE situacao = 'OK'
                """
                nome_arquivo = 'bens_localizados'
            elif tipo == 'nao-localizados':
                query = """
                    SELECT numero, nome, situacao, localizacao, responsavel, 
                           data_ultima_vistoria, data_vistoria_atual, auditor 
                    FROM bens 
                    WHERE situacao != 'OK' OR situacao IS NULL
                """
                nome_arquivo = 'bens_nao_localizados'
            else:
                abort(400, description="Tipo inválido")

            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                abort(404, description="Nenhum dado encontrado para exportação")

            if 'numero' in df.columns:
                df = df.sort_values(by='numero')

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            caminho_arquivo = os.path.join(
                os.path.dirname(self.db_path),
                f"{nome_arquivo}_{timestamp}.xlsx"
            )

            df.to_excel(caminho_arquivo, index=False)
            logger.info(f"Relatório exportado: {caminho_arquivo} ({len(df)} registros)")

            return send_file(caminho_arquivo, as_attachment=True)

        except ImportError:
            abort(500, description="Pandas não está instalado")
        except Exception as e:
            logger.error(f"Erro na exportação: {str(e)}")
            abort(500, description="Erro ao exportar dados")

    def exportar_localidade(self, localidade: str) -> Any:
        """Exporta bens por localidade"""
        try:
            import pandas as pd
            
            registros = obter_todos_bens_por_localidade(self.db_path, localidade)
            
            if not registros:
                abort(404, description=f"Nenhum bem encontrado para a localidade: {localidade}")
            
            df = pd.DataFrame(registros)
            if 'numero' in df.columns:
                df = df.sort_values(by='numero')
            
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            nome_seguro = re.sub(r'[^\w\s-]', '', localidade).strip().lower()
            nome_seguro = re.sub(r'[-\s]+', '_', nome_seguro)
            
            caminho_arquivo = os.path.join(
                os.path.dirname(self.db_path),
                f"bens_localidade_{nome_seguro}_{timestamp}.xlsx"
            )
            
            df.to_excel(caminho_arquivo, index=False)
            logger.info(f"Relatório por localidade exportado: {caminho_arquivo}")
            
            return send_file(caminho_arquivo, as_attachment=True)
            
        except Exception as e:
            logger.error(f"Erro ao exportar localidade: {str(e)}")
            abort(500, description="Erro ao exportar dados da localidade")

# ==============================
# INICIALIZAÇÃO DE SERVIÇOS
# ==============================
DB_PATH = app.config['DB_PATH']
bem_service = BemService(DB_PATH)
export_service = bem_service

# ==============================
# MIDDLEWARE DE ESTABILIDADE
# ==============================
@app.before_request
def stability_middleware():
    """Middleware para garantir estabilidade em todas as requisições"""
    # Verificar banco de dados para rotas críticas
    critical_routes = ['index', 'visualizar', 'exportar', 'sistema_crud', 'api_bens']
    
    if request.endpoint in critical_routes:
        if not os.path.exists(DB_PATH):
            logger.error(f"Banco de dados não encontrado: {DB_PATH}")
            
            # Tentar criar estrutura se possível
            try:
                criar_estrutura_diretorios()
                criar_tabela_atualizada(DB_PATH)
                
                if request.endpoint and 'api' in request.endpoint:
                    return jsonify({
                        'success': False, 
                        'message': 'Sistema em inicialização'
                    }), 503
                else:
                    flash('Sistema em inicialização. Tente novamente em alguns segundos.', 'warning')
                    return render_template('loading.html')
            except Exception as e:
                logger.error(f"Falha na recuperação: {e}")
                if 'api' in request.endpoint:
                    return jsonify({
                        'success': False,
                        'message': 'Sistema temporariamente indisponível'
                    }), 503
                else:
                    abort(503)

@app.after_request
def security_headers(response):
    """Adiciona headers de segurança"""
    if response.content_type and 'text/html' in response.content_type:
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if app.config['ENV'] == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response

# ==============================
# SISTEMA DE AUTENTICAÇÃO
# ==============================
def hash_senha(senha):
    """Gera hash da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_login(email, senha):
    """Verifica se o login é válido"""
    try:
        conn = sqlite3.connect(DB_PATH)
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
        logger.error(f"Erro ao verificar login: {str(e)}")
        return None

def criar_tabela_usuarios_se_nao_existir():
    """Cria a tabela de usuários se não existir"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if not cursor.fetchone():
            logger.info("Criando tabela usuarios...")
            
            cursor.execute('''
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    senha_hash TEXT NOT NULL,
                    tipo TEXT DEFAULT 'usuario',
                    departamento TEXT,
                    telefone TEXT,
                    ativo INTEGER DEFAULT 1,
                    criado_por INTEGER,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultimo_login TIMESTAMP,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            logger.info("Tabela usuarios criada com sucesso!")
        else:
            logger.info("Tabela usuarios já existe")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela de usuários: {str(e)}")
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
    """Carrega contagens do banco de forma otimizada"""
    try:
        contagens = contar_bens(DB_PATH)
        return {
            'localizados_count': contagens['localizados'],
            'nao_localizados_count': contagens['nao_localizados'],
            'total_count': contagens['total']
        }
    except Exception as e:
        logger.error(f"Erro ao carregar contagens do banco: {str(e)}")
        return {'localizados_count': 0, 'nao_localizados_count': 0, 'total_count': 0}

def criar_estrutura_diretorios():
    """Garante que todos os diretórios necessários existam"""
    diretorios = [
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['BASE_DIR'], 'logs'),
        os.path.dirname(app.config['DB_PATH']),
        os.path.join(os.path.dirname(app.config['DB_PATH']), 'backups')
    ]
    
    for diretorio in diretorios:
        try:
            os.makedirs(diretorio, exist_ok=True)
            # Dar permissões apropriadas
            os.chmod(diretorio, 0o755)
            logger.info(f"✅ Diretório criado/verificado: {diretorio}")
        except Exception as e:
            logger.error(f"⚠️ Erro ao criar diretório {diretorio}: {e}")

def verificar_permissoes_arquivos():
    """Verifica permissões de arquivos necessários"""
    arquivos_verificar = [
        DB_PATH,
        os.path.join(app.config['BASE_DIR'], 'logs', 'app.log')
    ]
    
    for arquivo in arquivos_verificar:
        diretorio = os.path.dirname(arquivo)
        if not os.path.exists(diretorio):
            os.makedirs(diretorio, mode=0o755, exist_ok=True)
        if os.path.exists(arquivo):
            try:
                os.chmod(arquivo, 0o644)
            except:
                pass

def create_backup_before_operation(operation_name):
    """Cria backup antes de operações críticas"""
    backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{operation_name}_{timestamp}.db")
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        logger.info(f"Backup criado: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Falha ao criar backup: {e}")
        return None

# ==============================
# FILTROS TEMPLATE
# ==============================
@app.template_filter('number_format')
def number_format_filter(value):
    """Filtro para formatar números com separadores de milhar"""
    try:
        if value is None:
            return "0"
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('pluralize')
def pluralize_filter(value, singular, plural):
    """Filtro para pluralizar palavras baseado no valor"""
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
    """Página inicial do sistema"""
    mensagem_sucesso = request.args.get('mensagem', None)
    
    if not os.path.exists(DB_PATH):
        mensagem = "Banco de dados não encontrado. Execute a migração do Excel para SQLite antes de usar o sistema."
        logger.warning(mensagem)
        return render_template('index.html', 
                             mensagem=mensagem, 
                             bem_detalhes=None,
                             **carregar_dados_bancos())
    
    if request.method == 'POST':
        numero_bem = request.form.get('numero_bem', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        
        valido, mensagem_validacao = InputValidator.validate_number_format(numero_bem)
        if not valido:
            return render_template('index.html', 
                                 mensagem=mensagem_validacao,
                                 **carregar_dados_bancos())
        
        resultado = bem_service.processar_localizacao(numero_bem, localizacao)
        return render_template('index.html', 
                             **carregar_dados_bancos(),
                             **resultado)
    
    return render_template('index.html', 
                         mensagem=None,
                         mensagem_sucesso=mensagem_sucesso,
                         show_modal=False,
                         **carregar_dados_bancos())

@app.route('/visualizar/<tipo>')
@login_required
def visualizar(tipo: str):
    """Página de visualização de bens com paginação"""
    if not os.path.exists(DB_PATH):
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
        
        paginacao = obter_bens_paginados(DB_PATH, tipo, pagina, por_pagina)
        
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
        logger.error(f"Erro em /visualizar/{tipo}: {str(e)}")
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

@app.route('/exportar/<tipo>')
@login_required
def exportar(tipo: str):
    """Exporta relatórios para Excel"""
    if not os.path.exists(DB_PATH):
        abort(404, description="Banco de dados não encontrado.")
    
    if tipo not in ['localizados', 'nao-localizados']:
        abort(400, description="Tipo inválido.")
    
    return export_service.exportar_bens_por_tipo(tipo)

@app.route('/exportar-localidade/<localidade>')
@login_required
def exportar_localidade(localidade: str):
    """Exporta relatório por localidade para Excel"""
    if not os.path.exists(DB_PATH):
        abort(404, description="Banco de dados não encontrado.")
    
    return export_service.exportar_localidade(localidade)

# ==============================
# ROTAS DA API
# ==============================
@app.route('/api/bens', methods=['POST'])
@login_required
def api_criar_bem():
    """Cria um novo bem - ROTA PRINCIPAL"""
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400
        
        # Validar dados
        if not dados.get('numero') or not dados.get('numero').strip():
            return jsonify({'success': False, 'message': 'Número do bem é obrigatório'}), 400
        
        if not dados.get('nome') or not dados.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do bem é obrigatório'}), 400
            
        numero = InputValidator.sanitize_input(dados['numero'])
        nome = InputValidator.sanitize_input(dados['nome'])
        
        # Verificar se número já existe
        if verificar_numero_existe(DB_PATH, numero):
            return jsonify({'success': False, 'message': 'Número do bem já existe'}), 400
        
        # Criar bem
        success, message = criar_novo_bem(DB_PATH, {
            'numero': numero,
            'nome': nome,
            'situacao': InputValidator.sanitize_input(dados.get('situacao', 'Pendente')),
            'localizacao': InputValidator.sanitize_input(dados.get('localizacao', '')),
            'responsavel': InputValidator.sanitize_input(dados.get('responsavel', '')),
            'data_ultima_vistoria': dados.get('data_ultima_vistoria'),
            'data_vistoria_atual': dados.get('data_vistoria_atual'),
            'auditor': InputValidator.sanitize_input(dados.get('auditor', '')),
            'observacoes': InputValidator.sanitize_input(dados.get('observacoes', ''))
        })
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        logger.error(f"Erro ao criar bem: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/api/bens/<int:bem_id>', methods=['GET'])
@login_required
def api_obter_bem(bem_id):
    """Obtém dados de um bem pelo ID"""
    try:
        bem = obter_bem_por_id(DB_PATH, bem_id)
        
        if bem:
            return jsonify({'success': True, 'data': bem})
        else:
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
            
    except Exception as e:
        logger.error(f"Erro ao obter bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bens/<int:bem_id>', methods=['PUT'])
@login_required
def api_atualizar_bem(bem_id):
    """Atualiza um bem existente"""
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400
        
        success, message = atualizar_bem(DB_PATH, bem_id, {
            'nome': InputValidator.sanitize_input(dados.get('nome')),
            'situacao': InputValidator.sanitize_input(dados.get('situacao')),
            'localizacao': InputValidator.sanitize_input(dados.get('localizacao')),
            'responsavel': InputValidator.sanitize_input(dados.get('responsavel')),
            'data_ultima_vistoria': dados.get('data_ultima_vistoria'),
            'data_vistoria_atual': dados.get('data_vistoria_atual'),
            'auditor': InputValidator.sanitize_input(dados.get('auditor')),
            'observacoes': InputValidator.sanitize_input(dados.get('observacoes'))
        })
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        logger.error(f"Erro ao atualizar bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bens/<int:bem_id>', methods=['DELETE'])
@login_required
def api_excluir_bem(bem_id):
    """Exclui um bem"""
    try:
        success, message = excluir_bem(DB_PATH, bem_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        logger.error(f"Erro ao excluir bem {bem_id}: {str(e)}")
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
            flash('Por favor, informe um e-mail institucional válido.', 'error')
            return render_template('login.html')
        
        usuario = verificar_login(email, senha)
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_email'] = usuario['email']
            session['usuario_nome'] = usuario['nome']
            session['usuario_tipo'] = usuario['tipo']
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (usuario['id'],))
            conn.commit()
            conn.close()
            
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
        
        # Obter parâmetros
        aba_nome = request.form.get('aba_nome', 'Estoque')
        criar_backup = request.form.get('backup') == 'on'
        apagar_dados = request.form.get('apagar_dados') == 'on'
        
        # Salvar arquivo temporariamente
        temp_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_path)
        
        try:
            # Verificar estrutura
            resultado_verificacao = verificar_estrutura_excel(temp_path, aba_nome)
            
            if not resultado_verificacao['sucesso']:
                flash(f"❌ Erro na estrutura do arquivo: {resultado_verificacao['mensagem']}", 'error')
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return redirect(url_for('index'))
            
            # Importar dados
            if file_ext == '.csv':
                resultado_importacao = importar_csv_para_sqlite(temp_path, DB_PATH)
            else:
                resultado_importacao = importar_excel_para_sqlite(
                    temp_path, DB_PATH, aba_nome, criar_backup, apagar_dados
                )
            
            # Processar resultado
            if resultado_importacao['sucesso']:
                if apagar_dados:
                    flash('🗑️ TODOS OS DADOS ANTERIORES FORAM REMOVIDOS!', 'warning')
                
                flash(f"✅ {resultado_importacao['mensagem']}", 'success')
                
                if resultado_importacao['registros_inseridos'] > 0:
                    flash(f"📥 {resultado_importacao['registros_inseridos']} novos registros inseridos", 'info')
                
                if resultado_importacao['registros_atualizados'] > 0:
                    flash(f"🔄 {resultado_importacao['registros_atualizados']} registros atualizados", 'info')
                
                if resultado_importacao['registros_erro'] > 0:
                    flash(f"⚠️ {resultado_importacao['registros_erro']} registros com erro", 'warning')
                
                if criar_backup and not apagar_dados:
                    flash("📦 Backup do banco anterior criado com sucesso", 'info')
                    
            else:
                flash(f"❌ {resultado_importacao['mensagem']}", 'error')
            
        except Exception as e:
            error_msg = f"❌ Erro durante o processo de importação: {str(e)}"
            flash(error_msg, 'error')
            logger.error(f"Erro na importação: {str(e)}")
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        return redirect(url_for('index'))
        
    except Exception as e:
        error_msg = f"❌ Erro interno na importação: {str(e)}"
        logger.error(f"Erro na importação do Excel/CSV: {str(e)}")
        flash(error_msg, 'error')
        return redirect(url_for('index'))

# ==============================
# ROTAS ADICIONAIS (mantidas para compatibilidade)
# ==============================
@app.route('/sistema-crud')
@login_required
def sistema_crud():
    """Página completa de CRUD para gerenciamento de bens"""
    try:
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        termo_busca = request.args.get('q', '').strip()
        
        paginacao = obter_bens_paginados(DB_PATH, 'todos', pagina, por_pagina)
        estatisticas = carregar_dados_bancos()
        
        return render_template('sistema_crud.html',
                            paginacao=paginacao,
                            termo_busca=termo_busca,
                            **estatisticas,
                            mensagem=None)
        
    except Exception as e:
        logger.error(f"Erro na página CRUD: {str(e)}")
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
    logger.error(f"Erro interno: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    return render_template('500.html'), 500

@app.errorhandler(503)
def service_unavailable(error):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Serviço temporariamente indisponível'}), 503
    return render_template('503.html'), 503

# ==============================
# INICIALIZAÇÃO
# ==============================
if __name__ == '__main__':
    # Criar estrutura de diretórios
    criar_estrutura_diretorios()
    verificar_permissoes_arquivos()
    
    # Criar tabelas
    criar_tabela_usuarios_se_nao_existir()
    criar_tabela_atualizada(DB_PATH)
    
    logger.info("Iniciando aplicação Flask")
    
    # Configurar host e porta baseados no ambiente
    if os.environ.get('FLASK_ENV') == 'production':
        host = '0.0.0.0'
        port = 5000
        debug = False
        logger.info("🚀 Iniciando em modo PRODUÇÃO")
    else:
        host = '0.0.0.0'
        port = 5000
        debug = True
        logger.info("🔧 Iniciando em modo DESENVOLVIMENTO")
    
    logger.info(f"🌐 Servidor iniciado em http://{host}:{port}")
    
    app.run(
        debug=debug,
        host=host,
        port=port,
        threaded=True
    )
# FIM: app.py CORRIGIDO - VERSÃO ESTÁVEL