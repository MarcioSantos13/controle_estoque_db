import os
import sys
import re
import sqlite3
import shutil
import io
import hashlib
from functools import wraps
from datetime import datetime
from typing import Tuple, Dict, Any, List  # ← Adicione List aqui
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
    DB_PATH = os.path.join(os.path.abspath("."), "relatorios", "controle_patrimonial.db")
    UPLOAD_FOLDER = 'temp'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    PAGINATION_SIZE = 200
    EXPORT_CHUNK_SIZE = 1000

app = Flask(__name__)
app.secret_key = '123'  # Altere para uma chave segura
app.config.from_object(Config)

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


    """Serviço centralizado para operações com bens"""
   
class BemService:
    """Serviço centralizado para operações com bens"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def processar_localizacao(self, numero_bem: str, localizacao: str = None) -> Dict[str, Any]:
        """Processa a localização de um bem - VERSÃO CORRIGIDA"""
        try:
            # Se localização não foi informada, tenta completar do banco
            if not localizacao:
                localizacao = buscar_localizacao_existente(numero_bem, self.db_path)
            
            # Verifica se o bem existe
            encontrado, erro = verificar_bem(numero_bem, self.db_path)
            if not encontrado:
                return {
                    'mensagem': erro or 'Bem não encontrado.',
                    'bem_detalhes': None,
                    'localizacao_informada': localizacao,
                    'show_modal': False
                }
            
            # Marca como localizado
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
            
def buscar_bens_por_nome_com_id(db_path: str, termo: str) -> list:  # ← Use 'list' em vez de 'List'
    """Busca bens por nome INCLUINDO ID - VERSÃO CORRIGIDA"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                id,  -- ← AGORA INCLUINDO O ID
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
            # Garantir que o ID seja um inteiro
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
def caminho_relativo(pasta: str) -> str:
    """Retorna caminho absoluto, mesmo empacotado com PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, pasta)
    return os.path.join(os.path.abspath("."), pasta)

# Configurar caminho do banco
DB_PATH = app.config['DB_PATH']
bem_service = BemService(DB_PATH)
export_service = bem_service  # Corrigido: usar bem_service para exportação


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

# ==== INSIRA A FUNÇÃO AQUI ====
def criar_tabela_usuarios_se_nao_existir():
    """Cria a tabela de usuários se não existir"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
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
                    ultimo_login TIMESTAMP
                )
            ''')
            
            # Criar um usuário admin padrão
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
    
    # Verificar se o banco existe
    if not os.path.exists(DB_PATH):
        mensagem = "Banco de dados não encontrado. Execute a migração do Excel para SQLite antes de usar o sistema."
        logger.warning(mensagem)
        return render_template('index.html', 
                             mensagem=mensagem, 
                             bem_detalhes=None,
                             **carregar_dados_bancos())
    
    # Processar requisição POST
    if request.method == 'POST':
        numero_bem = request.form.get('numero_bem', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        
        # Validação do número do bem
        valido, mensagem_validacao = BemValidator.validar_numero(numero_bem)
        if not valido:
            return render_template('index.html', 
                                 mensagem=mensagem_validacao,
                                 **carregar_dados_bancos())
        
        # Processar o bem
        resultado = bem_service.processar_localizacao(numero_bem, localizacao)
        return render_template('index.html', 
                             **carregar_dados_bancos(),
                             **resultado)
    
    # Requisição GET
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
        # Obter parâmetros de paginação
        pagina = max(1, request.args.get('pagina', 1, type=int))
        por_pagina = max(50, min(
            request.args.get('por_pagina', app.config['PAGINATION_SIZE'], type=int), 
            1000
        ))
        
        # Obter dados paginados
        paginacao = obter_bens_paginados(DB_PATH, tipo, pagina, por_pagina)
        
        # Definir título
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
def exportar(tipo: str):
    """Exporta relatórios para Excel"""
    if not os.path.exists(DB_PATH):
        abort(404, description="Banco de dados não encontrado.")
    
    if tipo not in ['localizados', 'nao-localizados']:
        abort(400, description="Tipo inválido.")
    
    return export_service.exportar_bens_por_tipo(tipo)

@app.route('/exportar-localidade/<localidade>')
def exportar_localidade(localidade: str):
    """Exporta relatório por localidade para Excel"""
    if not os.path.exists(DB_PATH):
        abort(404, description="Banco de dados não encontrado.")
    
    return export_service.exportar_localidade(localidade)

@app.route('/importar-excel', methods=['POST'])
def importar_excel():
    """Rota para importar dados do Excel para o SQLite"""
    try:
        # Verificar se arquivo foi enviado
        if 'excel_file' not in request.files:
            return render_template('index.html', 
                                 mensagem='Nenhum arquivo selecionado',
                                 **carregar_dados_bancos())
        
        arquivo = request.files['excel_file']
        
        if arquivo.filename == '':
            return render_template('index.html',
                                 mensagem='Nenhum arquivo selecionado',
                                 **carregar_dados_bancos())
        
        # Verificar extensão
        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return render_template('index.html',
                                 mensagem='Formato de arquivo inválido. Use .xlsx ou .xls',
                                 **carregar_dados_bancos())
        
        # Salvar arquivo temporariamente
        filename = secure_filename(arquivo.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        arquivo.save(temp_path)
        
        # Obter parâmetros
        aba_nome = request.form.get('aba_nome', 'Estoque')
        criar_backup = request.form.get('backup') == 'on'
        
        # Verificar estrutura
        valido, mensagem_verificacao = verificar_estrutura_excel(temp_path, aba_nome)
        
        if not valido:
            from utils.excel_importer import obter_colunas_excel
            colunas_disponiveis = obter_colunas_excel(temp_path, aba_nome)
            mensagem_erro = f"{mensagem_verificacao}. Colunas disponíveis: {', '.join(colunas_disponiveis)}"
            
            try:
                os.remove(temp_path)
            except:
                pass
            
            return render_template('index.html',
                                 mensagem=mensagem_erro,
                                 **carregar_dados_bancos())
        
        # Executar importação
        sucesso, mensagem = importar_excel_para_sqlite(
            temp_path, aba_nome, DB_PATH, criar_backup
        )
        
        # Limpar arquivo temporário
        try:
            os.remove(temp_path)
        except:
            pass
        
        return render_template('index.html',
                             mensagem=mensagem,
                             show_modal=False,
                             **carregar_dados_bancos())
        
    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}")
        
        try:
            if 'temp_path' in locals():
                os.remove(temp_path)
        except:
            pass
        
        return render_template('index.html',
                             mensagem=f'Erro durante a importação: {str(e)}',
                             **carregar_dados_bancos())

# ==============================
# Rotas CRUD Unificadas
# ==============================
@app.route('/api/bens', methods=['POST'])
@login_required
def api_criar_bem():
    """API unificada para criar bem (JSON e Form)"""
    try:
        # Obter dados conforme o tipo de requisição
        if request.is_json:
            dados = request.get_json()
        else:
            dados = request.form.to_dict()
        
        # Criar bem
        sucesso, mensagem = bem_service.criar_bem(dados)
        
        # Retorno adaptável ao tipo de requisição
        if request.is_json:
            return jsonify({'success': sucesso, 'message': mensagem})
        else:
            if sucesso:
                return redirect(url_for('index', mensagem=mensagem))
            else:
                return render_template('novo_bem.html',
                                     erro=mensagem,
                                     dados=dados)
        
    except Exception as e:
        logger.error(f"Erro ao criar bem: {str(e)}")
        
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)})
        else:
            return render_template('novo_bem.html',
                                 erro=f'Erro interno: {str(e)}',
                                 dados=request.form.to_dict())

@app.route('/api/bens/<numero_bem>')
def api_obter_bem(numero_bem):
    """API para obter dados de um bem pelo número"""
    try:
        bem = obter_bem_por_numero(DB_PATH, numero_bem)
        
        if bem:
            return jsonify({'success': True, 'data': bem})
        else:
            return jsonify({'success': False, 'message': 'Bem não encontrado'})
            
    except Exception as e:
        logger.error(f"Erro ao obter bem {numero_bem}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    
@app.route('/api/bens/<int:bem_id>', methods=['PUT'])
@login_required
def api_editar_bem(bem_id):
    """API para editar um bem existente - COM OBSERVAÇÕES"""
    try:
        dados = request.get_json()
        print(f"✏️ Editando bem ID {bem_id} com dados:", dados)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Primeiro verificar se o bem existe
        cursor.execute("SELECT id FROM bens WHERE id = ?", (bem_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Bem não encontrado'})
        
        # Atualizar o bem (com observacoes)
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
            dados.get('observacoes'),  # Nova coluna
            bem_id
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Bem {bem_id} atualizado com sucesso")
        return jsonify({'success': True, 'message': 'Bem atualizado com sucesso!'})
        
    except Exception as e:
        print(f"💥 Erro ao editar bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/bens/<int:bem_id>', methods=['DELETE'])
@login_required
def api_excluir_bem(bem_id):
    """API para excluir um bem"""
    try:
        sucesso, mensagem = excluir_bem(DB_PATH, bem_id)
        return jsonify({'success': sucesso, 'message': mensagem})
        
    except Exception as e:
        logger.error(f"Erro ao excluir bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/verificar-numero', methods=['GET'])
def api_verificar_numero():
    """API para verificar se um número de bem já existe"""
    try:
        numero = request.args.get('numero', '').strip()
        if not numero:
            return jsonify({'exists': False})
        
        existe = verificar_numero_existe(DB_PATH, numero)
        return jsonify({'exists': existe})
        
    except Exception as e:
        logger.error(f"Erro ao verificar número: {str(e)}")
        return jsonify({'exists': False})

# ==============================
# Rotas de Autenticação
# ==============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    # Se já estiver logado, redireciona para a página inicial
    if 'usuario_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        
        # Validar e-mail institucional
        if not email or '@' not in email:
            flash('Por favor, informe um e-mail institucional válido.', 'error')
            return render_template('login.html')
        
        usuario = verificar_login(email, senha)
        
        if usuario:
            # Login bem-sucedido
            session['usuario_id'] = usuario['id']
            session['usuario_email'] = usuario['email']
            session['usuario_nome'] = usuario['nome']
            session['usuario_tipo'] = usuario['tipo']
            
            # Atualizar último login
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




    
    
def obter_estatisticas_crud():
    """Obtém estatísticas para a página CRUD com fallback seguro"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
        if not cursor.fetchone():
            return {
                'total_count': 0,
                'localizados_count': 0,
                'nao_localizados_count': 0
            }
        
        # Contar totais
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
def buscar_bens():
    """Página de busca avançada"""
    termo = request.args.get('q', '')
    resultados = buscar_bens_por_nome(DB_PATH, termo) if termo else []
    
    return render_template('buscar.html', 
                         resultados=resultados, 
                         termo_busca=termo,
                         total_resultados=len(resultados))

@app.route('/novo-bem')
def novo_bem():
    """Página para cadastrar novo bem"""
    return render_template('novo_bem.html')

@app.route('/relatorio/localidades')
def relatorio_localidades():
    """Relatório de bens por localidade - COM FILTROS AVANÇADOS"""
    try:
        localidade_selecionada = request.args.get('localidade', '').strip()
        situacao_filtro = request.args.get('situacao', 'OK')  # Novo filtro
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 20, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar localidades distintas (com filtro de situação)
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
            # Query com filtro de situação
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
                'situacao_filtro': situacao_filtro  # Para usar no template
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
        
def obter_bens_paginados_com_id(db_path: str, tipo: str, pagina: int = 1, por_pagina: int = 50, situacao: str = '') -> Dict[str, Any]:
    """Obtém bens paginados INCLUINDO ID - VERSÃO CORRIGIDA"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Construir query base
        query_base = "FROM bens WHERE 1=1"
        params = []
        
        # Aplicar filtro de situação se especificado
        if situacao and situacao != 'todos':
            if situacao == 'OK':
                query_base += " AND situacao = 'OK'"
            elif situacao == 'Pendente':
                query_base += " AND (situacao != 'OK' OR situacao IS NULL)"
        
        # Contar total
        cursor.execute(f"SELECT COUNT(*) {query_base}", params)
        total_registros = cursor.fetchone()[0]
        
        # Calcular paginação
        offset = (pagina - 1) * por_pagina
        total_paginas = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 else 1
        
        # Query principal COM ID
        query = f"""
            SELECT 
                id,  -- ← AGORA INCLUINDO O ID
                numero, 
                nome, 
                situacao, 
                localizacao, 
                responsavel, 
                data_ultima_vistoria,
                data_vistoria_atual,
                auditor,
                observacoes,
                data_criacao,
                data_localizacao
            {query_base}
            ORDER BY numero
            LIMIT ? OFFSET ?
        """
        
        params.extend([por_pagina, offset])
        cursor.execute(query, params)
        
        colunas = [desc[0] for desc in cursor.description]
        bens = []
        
        for row in cursor.fetchall():
            bem = dict(zip(colunas, row))
            # Garantir que o ID seja um inteiro
            if bem.get('id'):
                bem['id'] = int(bem['id'])
            bens.append(bem)
        
        conn.close()
        
        return {
            'dados': bens,
            'pagina_atual': pagina,
            'por_pagina': por_pagina,
            'total_registros': total_registros,
            'total_paginas': total_paginas
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter bens paginados: {str(e)}")
        return {
            'dados': [],
            'pagina_atual': 1,
            'por_pagina': por_pagina,
            'total_registros': 0,
            'total_paginas': 0
        }
@app.route('/sistema-crud')
def sistema_crud():
    """Página completa de CRUD para gerenciamento de bens - VERSÃO DEFINITIVA CORRIGIDA"""
    try:
        # Parâmetros de paginação e filtros
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        termo_busca = request.args.get('q', '').strip()
        situacao_filtro = request.args.get('situacao', '')
        
        print(f"🔍 DEBUG - Parâmetros recebidos:")
        print(f"  Página: {pagina}")
        print(f"  Por página: {por_pagina}")
        print(f"  Termo busca: '{termo_busca}'")
        print(f"  Situação: '{situacao_filtro}'")
        
        # CONEXÃO DIRETA COM O BANCO - CONSULTA SIMPLIFICADA
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Construir query base - VERSÃO SIMPLIFICADA
        query_where = "WHERE 1=1"
        params = []
        
        # Aplicar filtro de situação
        if situacao_filtro:
            if situacao_filtro == 'OK':
                query_where += " AND situacao = 'OK'"
            elif situacao_filtro == 'Pendente':
                query_where += " AND (situacao != 'OK' OR situacao IS NULL OR situacao = '')"
        
        # Aplicar filtro de busca
        if termo_busca:
            query_where += " AND (nome LIKE ? OR numero LIKE ?)"
            termo_like = f"%{termo_busca}%"
            params.extend([termo_like, termo_like])
        
        # Contar total de registros
        count_query = f"SELECT COUNT(*) FROM bens {query_where}"
        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()[0]
        print(f"📊 Total de registros encontrados: {total_registros}")
        
        # Calcular paginação
        offset = (pagina - 1) * por_pagina
        total_paginas = (total_registros + por_pagina - 1) // por_pagina if por_pagina > 0 else 1
        
        # Query principal - VERSÃO SIMPLIFICADA E FUNCIONAL
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
        
        print(f"🚀 Executando query: {query}")
        print(f"🚀 Com parâmetros: {params}")
        
        cursor.execute(query, params)
        
        # Processar resultados
        colunas = [desc[0] for desc in cursor.description]
        bens = []
        
        for row in cursor.fetchall():
            bem = dict(zip(colunas, row))
            # Garantir que o ID seja um inteiro
            if bem.get('id') is not None:
                bem['id'] = int(bem['id'])
            bens.append(bem)
        
        print(f"✅ Dados processados: {len(bens)} registros")
        if bens:
            print(f"📝 Primeiro registro: ID={bens[0].get('id')}, Número={bens[0].get('numero')}, Nome={bens[0].get('nome')}")
        
        conn.close()
        
        # Criar objeto de paginação
        paginacao = {
            'dados': bens,
            'pagina_atual': pagina,
            'por_pagina': por_pagina,
            'total_registros': total_registros,
            'total_paginas': total_paginas
        }
        
        # Obter estatísticas
        estatisticas = obter_estatisticas_crud()
        
        return render_template('sistema_crud.html',
                            paginacao=paginacao,
                            termo_busca=termo_busca,
                            **estatisticas,
                            mensagem=None)
        
    except Exception as e:
        logger.error(f"Erro na página CRUD: {str(e)}")
        import traceback
        traceback.print_exc()
        
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
        

@app.route('/api/bens/id/<int:bem_id>')
def api_obter_bem_por_id(bem_id):
    """API para obter dados de um bem pelo ID - COM OBSERVAÇÕES"""
    try:
        print(f"🔍 API - Buscando bem por ID: {bem_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query com colunas existentes (incluindo observacoes)
        cursor.execute('''
            SELECT 
                id, numero, nome, situacao, localizacao, responsavel,
                data_ultima_vistoria, data_vistoria_atual, auditor,
                data_criacao, data_localizacao, observacoes
            FROM bens 
            WHERE id = ?
        ''', (bem_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Mapear para dicionário
            colunas = ['id', 'numero', 'nome', 'situacao', 'localizacao', 'responsavel', 'data_ultima_vistoria', 'data_vistoria_atual', 'auditor', 'data_criacao', 'data_localizacao', 'observacoes']
            
            bem = dict(zip(colunas, row))
            print(f"✅ Bem encontrado: ID={bem['id']}, Número={bem['numero']}, Nome={bem['nome']}")
            
            return jsonify({'success': True, 'data': bem})
        else:
            print(f"❌ Bem não encontrado para ID: {bem_id}")
            return jsonify({'success': False, 'message': 'Bem não encontrado'})
            
    except Exception as e:
        print(f"💥 Erro ao obter bem por ID {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ==============================
# Gerenciamento de Usuários
# ==============================
@app.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_required
@admin_required  # ← ADICIONE ESTA LINHA para garantir que só admins possam cadastrar
def cadastrar_usuario():
    """Página para cadastrar novos usuários"""
    if request.method == 'POST':
        try:
            dados = request.form
            
            # Validar dados obrigatórios
            if not dados.get('nome') or not dados.get('email') or not dados.get('senha'):
                flash('Preencha todos os campos obrigatórios.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            # Validar confirmação de senha
            if dados.get('senha') != dados.get('confirmar_senha', ''):
                flash('As senhas não coincidem.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            # Validar tamanho da senha
            if len(dados.get('senha', '')) < 6:
                flash('A senha deve ter no mínimo 6 caracteres.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            # Validar formato do email
            if '@' not in dados['email']:
                flash('Por favor, informe um e-mail válido.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            # Verificar se e-mail já existe
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (dados['email'].lower(),))
            if cursor.fetchone():
                conn.close()
                flash('Este e-mail já está cadastrado no sistema.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
            # Inserir novo usuário COM TRATAMENTO DE ERRO MELHOR
            try:
                cursor.execute('''
                    INSERT INTO usuarios (
                        email, nome, senha_hash, tipo, departamento, 
                        telefone, ativo, criado_por, data_criacao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                conn.close()
                
                flash(f'Usuário {dados["nome"]} cadastrado com sucesso!', 'success')
                return redirect(url_for('listar_usuarios'))
                
            except sqlite3.Error as e:
                conn.rollback()
                conn.close()
                logger.error(f"Erro de banco ao cadastrar usuário: {str(e)}")
                flash('Erro no banco de dados ao cadastrar usuário.', 'error')
                return render_template('cadastrar_usuario.html', dados=dados)
            
        except Exception as e:
            logger.error(f"Erro inesperado ao cadastrar usuário: {str(e)}")
            flash('Erro interno ao cadastrar usuário.', 'error')
            return render_template('cadastrar_usuario.html', dados=request.form)
    
    # GET request - mostrar formulário vazio
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




    
@app.route('/sair')
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
# Função para Remover Rotas de Debug (Opcional)
# ==============================
def remover_rotas_debug():
    """Remove rotas de debug em produção - opcional"""
    if not app.debug:
        # Em vez de modificar as regras diretamente, simplesmente não registramos as rotas de debug
        # Ou podemos usar condicionais no registro das rotas
        pass

# ==============================
# Rotas de Debug (Apenas em modo desenvolvimento)
# ==============================
if app.debug:
    @app.route('/debug-localidades')
    def debug_localidades():
        """Página de debug para verificar localidades (apenas em desenvolvimento)"""
        from utils.db_handler import debug_localidades_completas
        try:
            resultados = debug_localidades_completas(DB_PATH)
            return render_template('debug_localidades.html', resultados=resultados)
        except Exception as e:
            return f"Erro no debug: {str(e)}"

    @app.route('/teste-consulta-direta/<localidade>')
    def teste_consulta_direta(localidade):
        """Teste de consulta direta no banco (apenas em desenvolvimento)"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) as count_exato FROM bens WHERE localizacao = ?",
                (localidade,)
            )
            count_exato = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) as count_like FROM bens WHERE localizacao LIKE ?",
                (f"%{localidade}%",)
            )
            count_like = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT numero, nome, localizacao FROM bens WHERE localizacao = ? LIMIT 5",
                (localidade,)
            )
            exemplos = cursor.fetchall()
            
            conn.close()
            
            return jsonify({
                'localidade': localidade,
                'count_exato': count_exato,
                'count_like': count_like,
                'exemplos': exemplos
            })
            
        except Exception as e:
            return jsonify({'error': str(e)})

# ==============================
# Inicialização
# ==============================
if __name__ == '__main__':
    # ==== INSIRA ESTA LINHA AQUI ====
    criar_tabela_usuarios_se_nao_existir()  # Garantir que a tabela de usuários existe
    
    logger.info("Iniciando aplicação Flask")
    
    # Criar diretórios necessários
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    app.run(debug=True)
    
# ==============================
# ROTAS DE AJUDA
# ==============================

@app.route('/ajuda')
def ajuda():
    """Página central de ajuda do sistema"""
    return render_template('ajuda.html')

@app.route('/ajuda/<topico>')
def ajuda_topico(topico):
    """Página de ajuda por tópico específico"""
    topicos_validos = ['cadastro', 'localizacao', 'relatorios', 'problemas', 'importacao']
    
    if topico not in topicos_validos:
        abort(404)
    
    return render_template('ajuda.html', topico_selecionado=topico)