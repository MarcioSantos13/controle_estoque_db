# ==============================
# app.py BLINDADO PARA PRODUÇÃO
# ==============================

import os
import sys
import re
import sqlite3
import shutil
import io
import csv
import pandas as pd
from io import BytesIO
import openpyxl
from openpyxl.styles import Font
import hashlib
import traceback
from functools import wraps
from datetime import datetime
from typing import Tuple, Dict, Any, List
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for, Response, session, flash

# ==============================
# DETECÇÃO DE AMBIENTE
# ==============================
def detect_environment():
    """Detecta se está em desenvolvimento ou produção"""
    is_production = False
    
    # Verifica variáveis de ambiente comuns em servidores
    production_indicators = [
        'WEBSITE_HOSTNAME',  # Azure App Service
        'DYNO',              # Heroku
        'RAILWAY_ENVIRONMENT',  # Railway
        'RENDER',            # Render
        'PYTHONANYWHERE_SITE',  # PythonAnywhere
        'cwd' in os.environ and 'home' in os.environ.get('cwd', '').lower(),  # Muitos servidores
    ]
    
    for indicator in production_indicators:
        if indicator in os.environ:
            is_production = True
            break
    
    # Verifica se está rodando em localhost
    if not is_production:
        try:
            import socket
            hostname = socket.gethostname()
            if 'localhost' in hostname.lower() or '127.0.0.1' in hostname:
                is_production = False
            else:
                is_production = True
        except:
            pass
    
    return is_production

IS_PRODUCTION = detect_environment()

# ==============================
# CONFIGURAÇÃO ADAPTATIVA
# ==============================
class AdaptiveConfig:
    """Configuração que se adapta ao ambiente"""
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Configurações que mudam entre ambientes
    if IS_PRODUCTION:
        print("🚀 EXECUTANDO EM MODO PRODUÇÃO")
        # Produção
        ENV = 'production'
        DEBUG = False
        SECRET_KEY = os.environ.get('SECRET_KEY', 'produção-key-segura-mudar-no-ambiente')
        DB_RELATIVE_PATH = "relatorios/controle_patrimonial.db"
        DB_PATH = os.path.join(BASE_DIR, DB_RELATIVE_PATH)
        UPLOAD_FOLDER = '/tmp/patrimonial_uploads'
        
        # Segurança reforçada
        SESSION_COOKIE_SECURE = True
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
        PREFERRED_URL_SCHEME = 'https'
        
    else:
        print("🔧 EXECUTANDO EM MODO DESENVOLVIMENTO")
        # Desenvolvimento
        ENV = 'development'
        DEBUG = True
        SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-para-desenvolvimento')
        DB_RELATIVE_PATH = "relatorios/controle_patrimonial.db"
        DB_PATH = os.path.join(BASE_DIR, DB_RELATIVE_PATH)
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'temp')
        
        # Segurança relaxada para desenvolvimento
        SESSION_COOKIE_SECURE = False
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configurações comuns
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    PAGINATION_SIZE = 200

# Inicialização da aplicação
app = Flask(__name__)
app.config.from_object(AdaptiveConfig())

# ==============================
# MIDDLEWARE DE SEGURANÇA
# ==============================
@app.after_request
def add_security_headers(response):
    """Adiciona headers de segurança"""
    if IS_PRODUCTION:
        # Headers de segurança para produção
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # CSP para produção (mais restritivo)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self';"
        )
        response.headers['Content-Security-Policy'] = csp_policy
    else:
        # CSP mais permissivo para desenvolvimento
        csp_policy = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self';"
        )
        response.headers['Content-Security-Policy'] = csp_policy
    
    return response

# ==============================
# SISTEMA DE LOGGING ROBUSTO
# ==============================
import logging
from logging.handlers import RotatingFileHandler

def setup_production_logging():
    """Configura logging robusto para produção"""
    try:
        log_dir = os.path.join(app.config['BASE_DIR'], 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'app.log')
        
        # Handler de arquivo com rotação
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Formatter detalhado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Configurar logger principal
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        
        # Remover handler padrão do Flask
        app.logger.handlers = [file_handler]
        
        app.logger.info("=" * 60)
        app.logger.info("🚀 SISTEMA PATRIMONIAL INICIADO EM PRODUÇÃO")
        app.logger.info(f"📁 Diretório: {app.config['BASE_DIR']}")
        app.logger.info(f"🗄️  Banco: {app.config['DB_PATH']}")
        app.logger.info(f"🔧 Ambiente: {app.config['ENV']}")
        app.logger.info(f"🌐 URL Base: {get_base_url()}")
        app.logger.info("=" * 60)
        
    except Exception as e:
        # Fallback para logging básico
        logging.basicConfig(level=logging.INFO)
        print(f"✅ Aplicação iniciada com logging básico: {e}")

def get_base_url():
    """Obtém a URL base correta para o ambiente"""
    if IS_PRODUCTION:
        # Tenta obter a URL do servidor
        server_name = os.environ.get('SERVER_NAME', '')
        if server_name:
            return f"https://{server_name}"
        else:
            return "https://seu-dominio.com"  # Altere para seu domínio
    else:
        return "http://localhost:5000"

# ==============================
# CONEXÃO COM BANCO OTIMIZADA
# ==============================
def get_db_connection():
    """Conexão otimizada com o banco"""
    try:
        conn = sqlite3.connect(app.config['DB_PATH'], timeout=30)
        conn.row_factory = sqlite3.Row
        
        # Otimizações para produção
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance entre performance e segurança
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA foreign_keys=ON")
        
        return conn
    except Exception as e:
        app.logger.error(f"❌ Erro crítico na conexão com o banco: {e}")
        raise

# ==============================
# FUNÇÃO PARA CRIAR ESTRUTURA
# ==============================
def criar_estrutura_segura():
    """Cria estrutura de diretórios de forma segura"""
    diretorios = [
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['BASE_DIR'], 'logs'),
        os.path.dirname(app.config['DB_PATH']),
        os.path.join(os.path.dirname(app.config['DB_PATH']), 'backups')
    ]
    
    for diretorio in diretorios:
        try:
            os.makedirs(diretorio, exist_ok=True)
            
            # Tenta definir permissões seguras (Unix/Linux)
            if hasattr(os, 'chmod'):
                os.chmod(diretorio, 0o755)
                
            app.logger.info(f"✅ Diretório seguro criado: {diretorio}")
        except Exception as e:
            app.logger.warning(f"⚠️ Erro ao criar diretório {diretorio}: {e}")

# ==============================
# SCANNER ADAPTATIVO
# ==============================
def scanner_disponivel():
    """Verifica se o scanner deve estar disponível"""
    if IS_PRODUCTION:
        # Em produção, verifica se é HTTPS e suporte a câmera
        return request.is_secure
    else:
        # Em desenvolvimento, sempre disponível
        return True

# ==============================
# ROTA INDEX BLINDADA
# ==============================
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Página inicial blindada"""
    try:
        # Obter localidades
        localidades = obter_localidades(app.config['DB_PATH'])
        
        # Verificar disponibilidade do scanner
        scanner_habilitado = scanner_disponivel()
        
        if request.method == 'POST':
            numero_bem = request.form.get('numero_bem', '').strip()
            localizacao = request.form.get('localizacao', '').strip()
            
            # Log da tentativa
            app.logger.info(f"🔍 Busca: {numero_bem} | Local: {localizacao} | IP: {request.remote_addr}")
            
            # Validação
            valido, mensagem_validacao = InputValidator.validate_number_format(numero_bem)
            if not valido:
                flash(mensagem_validacao, 'error')
                return render_template('index.html', 
                                     mensagem=mensagem_validacao,
                                     localidades=localidades,
                                     scanner_habilitado=scanner_habilitado,
                                     **carregar_dados_bancos())

            # Processar busca
            return processar_busca_patrimonial(numero_bem, localizacao, localidades, scanner_habilitado)
        
        # GET request
        return render_template('index.html', 
                             mensagem=None,
                             localidades=localidades,
                             scanner_habilitado=scanner_habilitado,
                             **carregar_dados_bancos())
    
    except Exception as e:
        app.logger.error(f"❌ ERRO CRÍTICO na rota index: {e}")
        flash('Erro temporário no sistema. Tente novamente.', 'error')
        return render_template('index.html', 
                             mensagem='Sistema temporariamente indisponível',
                             localidades=[],
                             scanner_habilitado=False,
                             **carregar_dados_bancos())

def processar_busca_patrimonial(numero_bem, localizacao, localidades, scanner_habilitado):
    """Processa a busca de forma isolada"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar bem
        cursor.execute("SELECT numero, nome, situacao, localizacao FROM bens WHERE numero = ?", (numero_bem,))
        resultado = cursor.fetchone()
        
        if not resultado:
            flash(f'❌ Bem {numero_bem} não encontrado.', 'error')
            conn.close()
            return render_template('index.html', 
                                 mensagem=f'Bem {numero_bem} não encontrado',
                                 localidades=localidades,
                                 scanner_habilitado=scanner_habilitado,
                                 **carregar_dados_bancos())
        
        # Extrair dados
        bem_numero, bem_nome, bem_situacao_anterior, bem_localizacao_anterior = resultado
        
        # Determinar nova localização
        nova_localizacao = localizacao if localizacao else (bem_localizacao_anterior or 'Localizado')
        
        # Atualizar
        cursor.execute(
            "UPDATE bens SET localizacao = ?, situacao = 'Localizado' WHERE numero = ?",
            (nova_localizacao, numero_bem)
        )
        
        conn.commit()
        conn.close()
        
        # Mensagem de sucesso
        if bem_situacao_anterior == 'Localizado':
            mensagem = f'🔁 Bem {bem_numero} atualizado. Localização: {nova_localizacao}'
            categoria = 'info'
        else:
            mensagem = f'✅ Bem {bem_numero} localizado em: {nova_localizacao}'
            categoria = 'success'
        
        flash(mensagem, categoria)
        app.logger.info(f"✅ SUCESSO: {mensagem}")
        
        return render_template('index.html', 
                             mensagem=None,
                             localidades=localidades,
                             scanner_habilitado=scanner_habilitado,
                             focus_numero_bem=True,
                             **carregar_dados_bancos())
        
    except Exception as e:
        app.logger.error(f"❌ ERRO no processamento: {e}")
        flash('Erro ao processar o bem. Tente novamente.', 'error')
        return render_template('index.html', 
                             mensagem=f'Erro: {str(e)}',
                             localidades=localidades,
                             scanner_habilitado=scanner_habilitado,
                             **carregar_dados_bancos())

# ==============================
# HANDLER DE ERROS ROBUSTO
# ==============================
@app.errorhandler(404)
def not_found(error):
    app.logger.warning(f"🔍 404 Not Found: {request.url} | IP: {request.remote_addr}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Recurso não encontrado'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"💥 Erro 500: {error} | URL: {request.url} | IP: {request.remote_addr}")
    app.logger.error(f"📋 Traceback: {traceback.format_exc()}")
    
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Erro interno do servidor'}), 500
    
    # Página de erro amigável
    return render_template('500.html', 
                         error_id=datetime.now().strftime('%Y%m%d%H%M%S'),
                         is_production=IS_PRODUCTION), 500

@app.errorhandler(413)
def too_large(error):
    app.logger.warning(f"📦 Arquivo muito grande: {request.url}")
    flash('Arquivo muito grande. O tamanho máximo é 16MB.', 'error')
    return redirect(request.referrer or url_for('index'))

# ==============================
# CONFIGURAÇÃO WSGI COMPATÍVEL
# ==============================

# No final do app.py, adicione:
def create_app():
    """Factory function para WSGI"""
    return app

# Para compatibilidade com WSGI
if __name__ != '__main__':
    # Configurações específicas para WSGI
    app.config.update(
        DEBUG=False,
        TESTING=False,
        PROPAGATE_EXCEPTIONS=True
    )

# Variável padrão para WSGI
application = app






# ==============================
# INICIALIZAÇÃO SEGURA
# ==============================
if __name__ == '__main__':
    # Configurar logging
    setup_production_logging()
    
    # Criar estrutura
    criar_estrutura_segura()
    
    # Criar tabelas
    criar_tabela_usuarios_se_nao_existir()
    criar_tabela_atualizada(app.config['DB_PATH'])
    
    # Configurações do servidor
    host = '0.0.0.0' if IS_PRODUCTION else '127.0.0.1'
    port = int(os.environ.get('PORT', 5000))
    
    app.logger.info(f"🌐 Servidor iniciado em http://{host}:{port}")
    app.logger.info(f"🔧 Debug mode: {app.config['DEBUG']}")
    app.logger.info(f"🔐 Secure cookies: {app.config['SESSION_COOKIE_SECURE']}")
    
    # Iniciar servidor
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        threaded=True
    )