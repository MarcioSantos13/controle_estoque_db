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

# Importar handlers
from utils.db_handler import (
    verificar_bem,
    marcar_bem_localizado,
    gerar_planilhas_localizacao,
    buscar_localizacao_existente,
    obter_bem_por_numero,
    atualizar_bem,
    excluir_bem,
    criar_novo_bem,
    buscar_bens_por_nome,
    contar_bens,
    obter_bens_paginados,
    obter_localidades,
    obter_bens_por_localidade,
    obter_todos_bens_por_localidade,
    verificar_localidade_existe,
    verificar_numero_existe,
    obter_bem_por_id 
)

from utils.excel_importer import importar_excel_para_sqlite, verificar_estrutura_excel
from utils.logger import logger

# ==============================
# Configuração e Inicialização
# ==============================
class Config:
    """Configurações centralizadas da aplicação"""
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "relatorios", "controle_patrimonial.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'temp')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    PAGINATION_SIZE = 200
    EXPORT_CHUNK_SIZE = 1000

app = Flask(__name__)
app.secret_key = 'sua-chave-segura-aqui'
app.config.from_object(Config)

# ==============================
# Configuração de Segurança
# ==============================
try:
    from flask_talisman import Talisman
    
    csp = {
        'default-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com'
        ],
        'script-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            'https://unpkg.com',
            '\'unsafe-inline\'',
            '\'unsafe-eval\'',
            'blob:'
        ],
        'style-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            '\'unsafe-inline\''
        ],
        'img-src': [
            '\'self\'',
            'data:',
            'blob:',
            'https:'
        ],
        'media-src': [
            '\'self\'',
            'blob:',
            'data:'
        ],
        'connect-src': [
            '\'self\'',
            'blob:',
            'data:'
        ],
        'frame-src': [
            '\'self\'',
            'blob:',
            'data:'
        ]
    }

    if os.environ.get('FLASK_ENV') == 'production' or not app.debug:
        Talisman(
            app,
            content_security_policy=csp,
            force_https=False,
            session_cookie_secure=False,
            strict_transport_security=False,
            frame_options='SAMEORIGIN'
        )
        logger.info("Modo produção: Segurança configurada para servidor")
    else:
        Talisman(
            app,
            content_security_policy=None,
            force_https=False,
            session_cookie_secure=False,
            strict_transport_security=False
        )
        logger.info("Modo desenvolvimento: Executando com segurança reduzida")
        
except ImportError:
    logger.warning("Flask-Talisman não instalado. Executando sem segurança HTTPS.")
    pass

# ==============================
# Serviços e Validações
# ==============================
class BemValidator:
    """Serviço de validação de dados de bens"""
    
    @staticmethod
    def validar_numero(numero: str) -> Tuple[bool, str]:
        """Valida o formato do número do bem"""
        if not numero or not numero.strip():
            return False, "Número do bem é obrigatório"
        
        if not re.match(r'^[A-Za-z0-9-]+$', numero.strip()):
            return False, "O número do bem deve conter apenas letras, números ou hífen"
        
        return True, ""
    
    @staticmethod
    def validar_dados_criacao(dados: Dict[str, Any]) -> Tuple[bool, str]:
        """Valida dados para criação de bem"""
        if not dados.get('numero') or not dados['numero'].strip():
            return False, "Número do bem é obrigatório"
        
        if not dados.get('nome') or not dados['nome'].strip():
            return False, "Nome do bem é obrigatório"
        
        return BemValidator.validar_numero(dados['numero'])

class BemService:
    """Serviço centralizado para operações com bens"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def processar_localizacao(self, numero_bem: str, localizacao: str = None) -> Dict[str, Any]:
        """Processa a localização de um bem"""
        try:
            if not localizacao:
                localizacao = buscar_localizacao_existente(numero_bem, self.db_path)
            
            encontrado, erro = verificar_bem(numero_bem, self.db_path)
            if not encontrado:
                return {
                    'mensagem': erro or 'Bem não encontrado.',
                    'bem_detalhes': None,
                    'localizacao_informada': localizacao,
                    'show_modal': False
                }
            
            mensagem = marcar_bem_localizado(numero_bem, self.db_path, localizacao)
            bem_detalhes = self._obter_detalhes_bem(numero_bem, localizacao)
            
            return {
                'mensagem': mensagem,
                'bem_detalhes': bem_detalhes,
                'localizacao_informada': localizacao,
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
        """Busca detalhes de um bem específico com todos os campos"""
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
        """Cria um novo bem no sistema com todos os campos"""
        try:
            valido, mensagem = BemValidator.validar_dados_criacao(dados)
            if not valido:
                return False, mensagem

            if verificar_numero_existe(self.db_path, dados['numero']):
                return False, "Já existe um bem com este número!"

            dados_completos = {
                'numero': dados['numero'].strip(),
                'nome': dados['nome'].strip(),
                'situacao': dados.get('situacao', 'Pendente'),
                'localizacao': dados.get('localizacao', '').strip(),
                'responsavel': dados.get('responsavel', '').strip(),
                'data_ultima_vistoria': dados.get('data_ultima_vistoria', ''),
                'data_vistoria_atual': dados.get('data_vistoria_atual', ''),
                'auditor': dados.get('auditor', '').strip(),
                'observacoes': dados.get('observacoes', '').strip()
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
            
def buscar_bens_por_nome_com_id(db_path: str, termo: str) -> list:
    """Busca bens por nome INCLUINDO ID"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                id,
                numero, 
                nome, 
                situacao, 
                localizacao, 
                responsavel, 
                data_ultima_vistoria,
                data_vistoria_atual,
                auditor,
                observacoes
            FROM bens 
            WHERE nome LIKE ? OR numero LIKE ?
            ORDER BY numero
        """
        
        termo_like = f"%{termo}%"
        cursor.execute(query, (termo_like, termo_like))
        
        colunas = [desc[0] for desc in cursor.description]
        resultados = []
        
        for row in cursor.fetchall():
            bem = dict(zip(colunas, row))
            if bem.get('id'):
                bem['id'] = int(bem['id'])
            resultados.append(bem)
        
        conn.close()
        return resultados
        
    except Exception as e:
        logger.error(f"Erro na busca por nome: {str(e)}")
        return []

# ==============================
# Inicialização de Serviços
# ==============================
DB_PATH = app.config['DB_PATH']
bem_service = BemService(DB_PATH)
export_service = bem_service

# ==============================
# Middleware e Validações Globais
# ==============================
@app.before_request
def validar_banco_dados():
    """Middleware para verificar se o banco existe antes de rotas críticas"""
    rotas_criticas = ['index', 'visualizar', 'exportar', 'relatorio_localidades', 'buscar_bens']
    
    if request.endpoint in rotas_criticas:
        if not os.path.exists(DB_PATH):
            if request.endpoint and request.endpoint.startswith('api_'):
                abort(503, description="Banco de dados não disponível")

# ==============================
# Filtros personalizados para Jinja2
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
# Funções Auxiliares
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

# ==============================
# Sistema de Autenticação
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
# Rotas Principais
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
        
        valido, mensagem_validacao = BemValidator.validar_numero(numero_bem)
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
# ROTAS DA API - SEM DUPLICAÇÕES
# ==============================

@app.route('/api/bens', methods=['POST'])
@login_required
def api_criar_bem():
    """Cria um novo bem - ROTA PRINCIPAL"""
    try:
        dados = request.get_json()
        print(f"📥 Dados recebidos para novo bem: {dados}")
        
        # Validação
        if not dados.get('numero') or not dados.get('numero').strip():
            return jsonify({'success': False, 'message': 'Número do bem é obrigatório'}), 400
        
        if not dados.get('nome') or not dados.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do bem é obrigatório'}), 400
            
        numero = dados['numero'].strip()
        nome = dados['nome'].strip()
        
        # Verificar se número já existe
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Número do bem já existe'}), 400
        
        # Inserir novo bem
        cursor.execute('''
            INSERT INTO bens 
            (numero, nome, situacao, localizacao, responsavel, data_ultima_vistoria, data_vistoria_atual, auditor, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero,
            nome,
            dados.get('situacao', 'Pendente'),
            dados.get('localizacao', ''),
            dados.get('responsavel', ''),
            dados.get('data_ultima_vistoria'),
            dados.get('data_vistoria_atual'),
            dados.get('auditor', ''),
            dados.get('observacoes', '')
        ))
        
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Bem criado com sucesso!',
            'id': novo_id
        })
        
    except Exception as e:
        print(f"💥 Erro ao criar bem: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/api/bens/<int:bem_id>', methods=['GET'])
@login_required
def api_obter_bem(bem_id):
    """Obtém dados de um bem pelo ID - ROTA PRINCIPAL ÚNICA"""
    try:
        print(f"🔍 Buscando bem por ID: {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, numero, nome, situacao, localizacao, responsavel, 
                   data_ultima_vistoria, data_vistoria_atual, auditor, observacoes
            FROM bens WHERE id = ?
        ''', (bem_id,))
        
        bem = cursor.fetchone()
        conn.close()
        
        if bem:
            colunas = ['id', 'numero', 'nome', 'situacao', 'localizacao', 'responsavel', 
                      'data_ultima_vistoria', 'data_vistoria_atual', 'auditor', 'observacoes']
            bem_dict = dict(zip(colunas, bem))
            
            # Converter datas para string
            for campo in ['data_ultima_vistoria', 'data_vistoria_atual']:
                if bem_dict[campo]:
                    bem_dict[campo] = str(bem_dict[campo])
            
            return jsonify({'success': True, 'data': bem_dict})
        else:
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
            
    except Exception as e:
        print(f"💥 Erro ao obter bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bens/<int:bem_id>', methods=['PUT'])
@login_required
def api_atualizar_bem(bem_id):
    """Atualiza um bem existente - ROTA PRINCIPAL"""
    try:
        dados = request.get_json()
        print(f"✏️ Atualizando bem ID {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se o bem existe
        cursor.execute("SELECT id FROM bens WHERE id = ?", (bem_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
        
        # Atualizar o bem
        cursor.execute('''
            UPDATE bens SET 
                nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                data_ultima_vistoria = ?, data_vistoria_atual = ?, auditor = ?,
                observacoes = ?
            WHERE id = ?
        ''', (
            dados.get('nome'),
            dados.get('situacao'),
            dados.get('localizacao'),
            dados.get('responsavel'),
            dados.get('data_ultima_vistoria'),
            dados.get('data_vistoria_atual'),
            dados.get('auditor'),
            dados.get('observacoes'),
            bem_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bem atualizado com sucesso!'})
        
    except Exception as e:
        print(f"💥 Erro ao atualizar bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/bens/<int:bem_id>', methods=['DELETE'])
@login_required
def api_excluir_bem(bem_id):
    """Exclui um bem - ROTA PRINCIPAL"""
    try:
        print(f"🗑️ Excluindo bem ID: {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se o bem existe
        cursor.execute("SELECT numero, nome FROM bens WHERE id = ?", (bem_id,))
        bem = cursor.fetchone()
        
        if not bem:
            conn.close()
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
        
        # Excluir o bem
        cursor.execute("DELETE FROM bens WHERE id = ?", (bem_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bem excluído com sucesso!'})
        
    except Exception as e:
        print(f"💥 Erro ao excluir bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# ROTAS ALTERNATIVAS PARA CRUD (FUNCIONAM EM QUALQUER SERVIDOR)
# ==============================

@app.route('/crud/bem/<int:bem_id>')
@login_required
def crud_obter_bem(bem_id):
    """Rota alternativa para obter dados do bem - FUNCIONA EM QUALQUER SERVIDOR"""
    try:
        print(f"🔍 Buscando bem por ID (rota alternativa): {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, numero, nome, situacao, localizacao, responsavel, 
                   data_ultima_vistoria, data_vistoria_atual, auditor, observacoes
            FROM bens WHERE id = ?
        ''', (bem_id,))
        
        bem = cursor.fetchone()
        conn.close()
        
        if bem:
            colunas = ['id', 'numero', 'nome', 'situacao', 'localizacao', 'responsavel', 
                      'data_ultima_vistoria', 'data_vistoria_atual', 'auditor', 'observacoes']
            bem_dict = dict(zip(colunas, bem))
            
            # Converter datas para string
            for campo in ['data_ultima_vistoria', 'data_vistoria_atual']:
                if bem_dict[campo]:
                    bem_dict[campo] = str(bem_dict[campo])
            
            return jsonify({'success': True, 'data': bem_dict})
        else:
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
            
    except Exception as e:
        print(f"💥 Erro ao obter bem {bem_id} (rota alternativa): {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/crud/bem/<int:bem_id>', methods=['POST'])
@login_required
def crud_atualizar_bem(bem_id):
    """Rota alternativa para atualizar bem - FUNCIONA EM QUALQUER SERVIDOR"""
    try:
        dados = request.get_json()
        print(f"✏️ Atualizando bem ID {bem_id} (rota alternativa)")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se o bem existe
        cursor.execute("SELECT id FROM bens WHERE id = ?", (bem_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
        
        # Atualizar o bem
        cursor.execute('''
            UPDATE bens SET 
                nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                data_ultima_vistoria = ?, data_vistoria_atual = ?, auditor = ?,
                observacoes = ?
            WHERE id = ?
        ''', (
            dados.get('nome'),
            dados.get('situacao'),
            dados.get('localizacao'),
            dados.get('responsavel'),
            dados.get('data_ultima_vistoria'),
            dados.get('data_vistoria_atual'),
            dados.get('auditor'),
            dados.get('observacoes'),
            bem_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bem atualizado com sucesso!'})
        
    except Exception as e:
        print(f"💥 Erro ao atualizar bem {bem_id} (rota alternativa): {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/crud/bem/novo', methods=['POST'])
@login_required
def crud_criar_bem():
    """Rota alternativa para criar novo bem - FUNCIONA EM QUALQUER SERVIDOR"""
    try:
        dados = request.get_json()
        print(f"📥 Criando novo bem (rota alternativa)")
        
        # Validação
        if not dados.get('numero') or not dados.get('numero').strip():
            return jsonify({'success': False, 'message': 'Número do bem é obrigatório'}), 400
        
        if not dados.get('nome') or not dados.get('nome').strip():
            return jsonify({'success': False, 'message': 'Nome do bem é obrigatório'}), 400
            
        numero = dados['numero'].strip()
        nome = dados['nome'].strip()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se número já existe
        cursor.execute("SELECT id FROM bens WHERE numero = ?", (numero,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Número do bem já existe'}), 400
        
        # Inserir novo bem
        cursor.execute('''
            INSERT INTO bens 
            (numero, nome, situacao, localizacao, responsavel, data_ultima_vistoria, data_vistoria_atual, auditor, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            numero,
            nome,
            dados.get('situacao', 'Pendente'),
            dados.get('localizacao', ''),
            dados.get('responsavel', ''),
            dados.get('data_ultima_vistoria'),
            dados.get('data_vistoria_atual'),
            dados.get('auditor', ''),
            dados.get('observacoes', '')
        ))
        
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Bem criado com sucesso!',
            'id': novo_id
        })
        
    except Exception as e:
        print(f"💥 Erro ao criar bem (rota alternativa): {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route('/crud/bem/<int:bem_id>', methods=['DELETE'])
@login_required
def crud_excluir_bem(bem_id):
    """Rota alternativa para excluir bem - FUNCIONA EM QUALQUER SERVIDOR"""
    try:
        print(f"🗑️ Excluindo bem ID (rota alternativa): {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se o bem existe
        cursor.execute("SELECT numero, nome FROM bens WHERE id = ?", (bem_id,))
        bem = cursor.fetchone()
        
        if not bem:
            conn.close()
            return jsonify({'success': False, 'message': 'Bem não encontrado'}), 404
        
        # Excluir o bem
        cursor.execute("DELETE FROM bens WHERE id = ?", (bem_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Bem excluído com sucesso!'})
        
    except Exception as e:
        print(f"💥 Erro ao excluir bem {bem_id} (rota alternativa): {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==============================
# Rota de Importação Excel
# ==============================


@app.route('/importar-excel', methods=['POST'])
@login_required
@admin_required
def importar_excel():
    """Importa dados do Excel ou CSV para o banco de dados - CORRIGIDA"""
    try:
        if 'excel_file' not in request.files:
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('index'))
        
        file = request.files['excel_file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'error')
            return redirect(url_for('index'))
        
        # Verificar extensões permitidas
        allowed_extensions = {'.xlsx', '.xls', '.csv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash('Formato de arquivo inválido. Use .xlsx, .xls ou .csv.', 'error')
            return redirect(url_for('index'))
        
        # Obter parâmetros do formulário
        aba_nome = request.form.get('aba_nome', 'Estoque')
        criar_backup = request.form.get('backup') == 'on'
        apagar_dados = request.form.get('apagar_dados') == 'on'  # NOVO PARÂMETRO
        
        print(f"📥 Parâmetros recebidos:")
        print(f"   - Arquivo: {file.filename}")
        print(f"   - Aba: {aba_nome}")
        print(f"   - Backup: {criar_backup}")
        print(f"   - Apagar dados: {apagar_dados}")
        
        # Salvar arquivo temporariamente
        temp_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_path)
        
        print(f"📁 Arquivo salvo temporariamente: {temp_path}")
        
        try:
            # Verificar estrutura do arquivo
            print("🔍 Verificando estrutura do arquivo...")
            resultado_verificacao = verificar_estrutura_excel(temp_path, aba_nome)
            
            if not resultado_verificacao['sucesso']:
                flash(f"❌ Erro na estrutura do arquivo: {resultado_verificacao['mensagem']}", 'error')
                print(f"❌ Estrutura inválida: {resultado_verificacao['mensagem']}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return redirect(url_for('index'))
            
            print("✅ Estrutura do arquivo validada!")
            
            # Importar dados
            print("🔄 Iniciando importação...")
            if file_ext == '.csv':
                resultado_importacao = importar_csv_para_sqlite(temp_path, DB_PATH)
            else:
                resultado_importacao = importar_excel_para_sqlite(
                    temp_path, DB_PATH, aba_nome, criar_backup, apagar_dados
                )
            
            print(f"📊 Resultado da importação: {resultado_importacao}")
            
            # FLASH MENSAGEM DETALHADA (CORREÇÃO)
            if resultado_importacao['sucesso']:
                # Dividir a mensagem em linhas para flash
                mensagens = resultado_importacao['mensagem'].split('\n')
                for msg in mensagens:
                    msg = msg.strip()
                    if msg:  # Só processar mensagens não vazias
                        if '✅' in msg or 'sucesso' in msg.lower():
                            flash(msg, 'success')
                        elif '⚠️' in msg or 'avisos' in msg.lower() or 'aviso' in msg.lower():
                            flash(msg, 'warning')
                        elif '❌' in msg or 'erro' in msg.lower():
                            flash(msg, 'error')
                        elif '🗑️' in msg or 'removidos' in msg.lower():
                            flash(msg, 'info')
                        elif '📦' in msg or 'backup' in msg.lower():
                            flash(msg, 'info')
                        else:
                            flash(msg, 'info')
                
                print("✅ Mensagens de sucesso enviadas para flash")
            else:
                flash(f"❌ {resultado_importacao['mensagem']}", 'error')
                print(f"❌ Erro na importação: {resultado_importacao['mensagem']}")
            
        except Exception as e:
            error_msg = f"❌ Erro durante o processo de importação: {str(e)}"
            flash(error_msg, 'error')
            print(f"💥 Erro no processo: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Limpar arquivo temporário
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print("🧹 Arquivo temporário removido")
        
        print("🔁 Redirecionando para index...")
        return redirect(url_for('index'))
        
    except Exception as e:
        error_msg = f"❌ Erro interno na importação: {str(e)}"
        logger.error(f"Erro na importação do Excel/CSV: {str(e)}")
        flash(error_msg, 'error')
        print(f"💥 Erro geral: {str(e)}")
        return redirect(url_for('index'))







# ==============================
# Rotas de Autenticação
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

@app.route('/perfil')
@login_required
def perfil():
    """Página do perfil do usuário"""
    return render_template('perfil.html', 
                         usuario_nome=session.get('usuario_nome'),
                         usuario_email=session.get('usuario_email'),
                         usuario_tipo=session.get('usuario_tipo'))

# ==============================
# ROTAS DE AJUDA E SUPORTE
# ==============================
@app.route('/ajuda')
@login_required
def ajuda():
    """Página central de ajuda do sistema"""
    return render_template('ajuda.html')

@app.route('/ajuda/<topico>')
@login_required
def ajuda_topico(topico):
    """Página de ajuda por tópico específico"""
    topicos_validos = ['cadastro', 'localizacao', 'relatorios', 'importacao', 'problemas', 'contato']
    
    if topico not in topicos_validos:
        abort(404)
    
    return render_template('ajuda.html', topico_selecionado=topico)

@app.route('/api/ajuda/buscar', methods=['POST'])
@login_required
def api_ajuda_buscar():
    """API para busca na ajuda"""
    try:
        termo = request.json.get('termo', '').lower().strip()
        
        # Base de conhecimento para busca
        base_conhecimento = {
            'cadastrar': ['cadastro', 'novo bem', 'adicionar'],
            'localizar': ['localização', 'encontrar', 'buscar bem'],
            'exportar': ['exportar', 'excel', 'relatório'],
            'importar': ['importar', 'excel', 'planilha'],
            'editar': ['editar', 'modificar', 'alterar'],
            'excluir': ['excluir', 'deletar', 'remover'],
            'problema': ['erro', 'problema', 'não funciona'],
            'contato': ['suporte', 'contato', 'ajuda']
        }
        
        resultados = []
        for categoria, termos in base_conhecimento.items():
            if any(termo in palavra for palavra in termos):
                resultados.append({
                    'categoria': categoria,
                    'relevancia': sum(1 for palavra in termos if termo in palavra)
                })
        
        # Ordenar por relevância
        resultados.sort(key=lambda x: x['relevancia'], reverse=True)
        
        return jsonify({
            'success': True,
            'termo': termo,
            'resultados': resultados[:5]  # Top 5 resultados
        })
        
    except Exception as e:
        logger.error(f"Erro na busca de ajuda: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro na busca'})

@app.route('/api/ajuda/contato', methods=['POST'])
@login_required
def api_ajuda_contato():
    """API para enviar mensagem de contato"""
    try:
        dados = request.json
        
        # Validar dados obrigatórios
        campos_obrigatorios = ['nome', 'email', 'assunto', 'mensagem']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({
                    'success': False, 
                    'message': f'Campo {campo} é obrigatório'
                })
        
        # Registrar no log (em produção, enviaria email)
        logger.info(f"📧 CONTATO RECEBIDO - {dados['assunto']}")
        logger.info(f"👤 De: {dados['nome']} <{dados['email']}>")
        logger.info(f"📝 Mensagem: {dados['mensagem'][:100]}...")
        
        return jsonify({
            'success': True,
            'message': 'Mensagem enviada com sucesso! Retornaremos em até 4 horas úteis.'
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar contato: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao enviar mensagem'})

# ==============================
# Rotas de Usuários
# ==============================
@app.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@admin_required
def cadastrar_usuario():
    """Página para cadastrar novos usuários"""
    if request.method == 'POST':
        conn = None
        try:
            dados = request.form
            
            if not dados.get('nome') or not dados.get('email') or not dados.get('senha'):
                flash('Preencha todos os campos obrigatórios.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            if dados.get('senha') != dados.get('confirmar_senha', ''):
                flash('As senhas não coincidem.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            if len(dados.get('senha', '')) < 6:
                flash('A senha deve ter no mínimo 6 caracteres.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            if '@' not in dados['email']:
                flash('Por favor, informe um e-mail válido.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (dados['email'].lower(),))
            if cursor.fetchone():
                flash('Este e-mail já está cadastrado no sistema.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            cursor.execute('''
                INSERT INTO usuarios (
                    email, nome, senha_hash, tipo, departamento, 
                    telefone, ativo, criado_por
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['email'].lower().strip(),
                dados['nome'].strip(),
                hash_senha(dados['senha']),
                dados.get('tipo', 'usuario'),
                dados.get('departamento', ''),
                dados.get('telefone', ''),
                int(dados.get('ativo', 1)),
                session.get('usuario_id')
            ))
            
            conn.commit()
            flash(f'Usuário {dados["nome"]} cadastrado com sucesso!', 'success')
            return redirect(url_for('listar_usuarios'))
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro ao cadastrar usuário: {str(e)}")
            flash('Erro interno ao cadastrar usuário.', 'error')
            return render_template('cadastrar_usuario.html', dados=dados)
        finally:
            if conn:
                conn.close()
    
    return render_template('cadastrar_usuario.html')

@app.route('/usuarios')
@login_required
def listar_usuarios():
    """Lista todos os usuários do sistema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.email, u.nome, u.tipo, u.departamento, u.ativo, 
                   u.data_criacao, u.ultimo_login, criador.nome as criado_por
            FROM usuarios u
            LEFT JOIN usuarios criador ON u.criado_por = criador.id
            ORDER BY u.data_criacao DESC
        ''')
        
        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'id': row[0],
                'email': row[1],
                'nome': row[2],
                'tipo': row[3],
                'departamento': row[4],
                'ativo': bool(row[5]),
                'data_criacao': row[6],
                'ultimo_login': row[7],
                'criado_por': row[8]
            })
        
        conn.close()
        
        return render_template('listar_usuarios.html', usuarios=usuarios)
        
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {str(e)}")
        flash('Erro ao carregar lista de usuários.', 'error')
        return render_template('listar_usuarios.html', usuarios=[])

def obter_estatisticas_crud():
    """Obtém estatísticas para a página CRUD com fallback seguro"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
        if not cursor.fetchone():
            return {
                'total_count': 0,
                'localizados_count': 0,
                'nao_localizados_count': 0
            }
        
        cursor.execute("SELECT COUNT(*) FROM bens")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bens WHERE situacao = 'OK'")
        localizados_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bens WHERE situacao != 'OK' OR situacao IS NULL OR situacao = ''")
        nao_localizados_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_count': total_count,
            'localizados_count': localizados_count,
            'nao_localizados_count': nao_localizados_count
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return {
            'total_count': 0,
            'localizados_count': 0,
            'nao_localizados_count': 0
        }

# ==============================
# Rotas de Interface
# ==============================
@app.route('/buscar')
@login_required
def buscar_bens():
    """Página de busca avançada"""
    termo = request.args.get('q', '')
    resultados = buscar_bens_por_nome(DB_PATH, termo) if termo else []
    
    return render_template('buscar.html', 
                         resultados=resultados, 
                         termo_busca=termo,
                         total_resultados=len(resultados))

@app.route('/novo-bem')
@login_required
def novo_bem():
    """Página para cadastrar novo bem"""
    return render_template('novo_bem.html')

@app.route('/relatorio/localidades')
@login_required
def relatorio_localidades():
    """Relatório de bens por localidade"""
    try:
        localidade_selecionada = request.args.get('localidade', '').strip()
        situacao_filtro = request.args.get('situacao', 'OK')
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 20, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT DISTINCT localizacao 
            FROM bens 
            WHERE localizacao IS NOT NULL 
            AND localizacao != '' 
            AND localizacao != 'Não informada'
            AND situacao = ?
            ORDER BY localizacao
        ''', (situacao_filtro,))
        localidades = [row[0] for row in cursor.fetchall()]
        
        paginacao = None
        
        if localidade_selecionada:
            cursor.execute('''
                SELECT COUNT(*) FROM bens 
                WHERE localizacao = ? AND situacao = ?
            ''', (localidade_selecionada, situacao_filtro))
            total_registros = cursor.fetchone()[0]
            
            offset = (pagina - 1) * por_pagina
            total_paginas = (total_registros + por_pagina - 1) // por_pagina
            
            cursor.execute('''
                SELECT 
                    numero, nome, situacao, localizacao,
                    data_criacao, data_localizacao
                FROM bens 
                WHERE localizacao = ? AND situacao = ?
                ORDER BY numero
                LIMIT ? OFFSET ?
            ''', (localidade_selecionada, situacao_filtro, por_pagina, offset))
            
            bens = []
            for row in cursor.fetchall():
                bens.append({
                    'numero': row[0],
                    'nome': row[1],
                    'situacao': row[2],
                    'localizacao': row[3],
                    'data_criacao': row[4],
                    'data_localizacao': row[5]
                })
            
            paginacao = {
                'dados': bens,
                'pagina_atual': pagina,
                'por_pagina': por_pagina,
                'total_registros': total_registros,
                'total_paginas': total_paginas,
                'situacao_filtro': situacao_filtro
            }
        
        conn.close()
        
        return render_template('relatorio_localidades.html',
                             localidades=localidades,
                             localidade_selecionada=localidade_selecionada,
                             paginacao=paginacao)
        
    except Exception as e:
        logger.error(f"Erro no relatório de localidades: {str(e)}")
        return render_template('relatorio_localidades.html',
                             mensagem=f"Erro ao gerar relatório: {str(e)}",
                             localidades=[],
                             localidade_selecionada='',
                             paginacao=None)

@app.route('/sistema-crud')
@login_required
def sistema_crud():
    """Página completa de CRUD para gerenciamento de bens"""
    try:
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        termo_busca = request.args.get('q', '').strip()
        situacao_filtro = request.args.get('situacao', '')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query_where = "WHERE 1=1"
        params = []
        
        if situacao_filtro:
            if situacao_filtro == 'OK':
                query_where += " AND situacao = 'OK'"
            elif situacao_filtro == 'Pendente':
                query_where += " AND (situacao != 'OK' OR situacao IS NULL OR situacao = '')"

        responsavel = request.args.get('responsavel', '').strip()
        if responsavel:
            query_where += " AND responsavel = ?"
            params.append(responsavel)
        
        if termo_busca:
            query_where += " AND (nome LIKE ? OR numero LIKE ?)"
            termo_like = f"%{termo_busca}%"
            params.extend([termo_like, termo_like])
        
        count_query = f"SELECT COUNT(*) FROM bens {query_where}"
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()[0]
        
        offset = (pagina - 1) * por_pagina
        total_paginas = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 else 1
        
        query = f"""
            SELECT 
                id,
                numero, 
                nome, 
                situacao, 
                localizacao, 
                responsavel, 
                data_ultima_vistoria
            FROM bens 
            {query_where}
            ORDER BY numero
            LIMIT ? OFFSET ?
        """
        
        params.extend([por_pagina, offset])
        cursor.execute(query, params)
        
        colunas = [desc[0] for desc in cursor.description]
        bens = []
        
        for row in cursor.fetchall():
            bem = dict(zip(colunas, row))
            if bem.get('id') is not None:
                bem['id'] = int(bem['id'])
            bens.append(bem)
        
        conn.close()
        
        paginacao = {
            'dados': bens,
            'pagina_atual': pagina,
            'por_pagina': por_pagina,
            'total_registros': total_registros,
            'total_paginas': total_paginas
        }
        
        estatisticas = obter_estatisticas_crud()
        
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

@app.route('/sair')
@login_required
def sair():
    """Página de encerramento do aplicativo"""
    return render_template('sair.html', total_count=carregar_dados_bancos().get('total_count', 0), session_time="5min")

# ==============================
# Handlers de Erro Globais
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
# Inicialização
# ==============================
if __name__ == '__main__':
    criar_tabela_usuarios_se_nao_existir()
    
    logger.info("Iniciando aplicação Flask")
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    try:
        if os.environ.get('FLASK_ENV') == 'production':
            host = '0.0.0.0'
            port = 5000
            debug = False
            logger.info("🚀 Iniciando em modo PRODUÇÃO (SERVIDOR)")
        else:
            host = '0.0.0.0'
            port = 5000
            debug = True
            logger.info("🔧 Iniciando em modo DESENVOLVIMENTO")
        
        logger.info(f"🌐 Servidor iniciado em http://{host}:{port}")
        logger.info(f"📁 Caminho do banco: {DB_PATH}")
        
        app.run(
            debug=debug,
            host=host,
            port=port,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar servidor: {str(e)}")
        try:
            logger.info("🔄 Tentando porta alternativa 5001...")
            app.run(debug=True, host='0.0.0.0', port=5001)
        except:
            logger.error("💥 Não foi possível iniciar o servidor")