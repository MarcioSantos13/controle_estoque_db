#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Configuration for Controle de Estoque Flask App
VERSÃO BLINDADA PARA PRODUÇÃO
"""

import sys
import os
import logging
from datetime import datetime

# ==============================
# CONFIGURAÇÃO INICIAL ROBUSTA
# ==============================

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Definir diretório da aplicação
APP_DIR = '/var/www/controle_estoque_db'
sys.path.insert(0, APP_DIR)

# Mudar para diretório da aplicação
os.chdir(APP_DIR)

# Variáveis de ambiente ESSENCIAIS
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONPATH'] = APP_DIR

# ==============================
# MIDDLEWARE AVANÇADO
# ==============================

class ReverseProxied(object):
    """Middleware robusto para subdiretório /estoque"""
    
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = '/estoque'
        
        # Aplicar script_name consistentemente
        environ['SCRIPT_NAME'] = script_name
        path_info = environ['PATH_INFO']
        
        if path_info.startswith(script_name):
            environ['PATH_INFO'] = path_info[len(script_name):]
        
        # Headers de segurança adicionais
        def custom_start_response(status, headers, exc_info=None):
            # Adicionar headers de segurança
            security_headers = [
                ('X-Content-Type-Options', 'nosniff'),
                ('X-Frame-Options', 'SAMEORIGIN'),
                ('X-XSS-Protection', '1; mode=block'),
            ]
            headers.extend(security_headers)
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)

# ==============================
# CARREGAMENTO DA APLICAÇÃO
# ==============================

def load_application():
    """Carrega a aplicação Flask de forma robusta"""
    
    startup_errors = []
    
    try:
        logger.info("🚀 Iniciando carregamento da aplicação Flask...")
        
        # Verificar se o diretório existe
        if not os.path.exists(APP_DIR):
            startup_errors.append(f"Diretório da aplicação não existe: {APP_DIR}")
            raise FileNotFoundError(f"Diretório {APP_DIR} não encontrado")
        
        # Verificar arquivos essenciais
        essential_files = ['app.py', 'relatorios/controle_patrimonial.db']
        for file in essential_files:
            file_path = os.path.join(APP_DIR, file)
            if not os.path.exists(file_path):
                startup_errors.append(f"Arquivo essencial não encontrado: {file}")
        
        # Tentar importar a aplicação
        logger.info("📦 Importando módulo app...")
        import app as app_module
        
        # Estratégias de fallback para encontrar a aplicação
        application = None
        strategies = [
            # Estratégia 1: app.app
            ('app.app', lambda: getattr(app_module, 'app')),
            # Estratégia 2: create_app()
            ('app.create_app()', lambda: app_module.create_app()),
            # Estratégia 3: application
            ('app.application', lambda: getattr(app_module, 'application')),
            # Estratégia 4: Procurar instâncias Flask
            ('Busca automática', lambda: find_flask_instance(app_module)),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                application = strategy_func()
                if application:
                    logger.info(f"✅ Aplicação encontrada via: {strategy_name}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ Estratégia {strategy_name} falhou: {e}")
                continue
        
        if not application:
            startup_errors.append("Nenhuma estratégia de carregamento funcionou")
            raise Exception("Não foi possível carregar a aplicação Flask")
        
        # Configurações de produção
        application.config.update({
            'DEBUG': False,
            'TESTING': False,
            'PROPAGATE_EXCEPTIONS': True,
            'JSONIFY_PRETTYPRINT_REGULAR': False
        })
        
        logger.info("✅ Aplicação Flask carregada com sucesso")
        return application
        
    except Exception as ex:
        startup_errors.append(f"Erro durante carregamento: {str(ex)}")
        logger.error(f"💥 Erro crítico no carregamento: {ex}")
        raise

def find_flask_instance(module):
    """Encontra instância Flask automaticamente no módulo"""
    from flask import Flask
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, Flask):
            logger.info(f"🔍 Encontrada instância Flask: {attr_name}")
            return attr
    return None

# ==============================
# APLICAÇÃO DE FALLBACK
# ==============================

def create_fallback_app():
    """Cria aplicação de fallback para erros"""
    from flask import Flask, request, jsonify
    
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/', defaults={'path': ''})
    @fallback_app.route('/<path:path>')
    def error_handler(path):
        error_id = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # API requests
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'message': 'Sistema temporariamente indisponível',
                'error_id': error_id,
                'timestamp': datetime.now().isoformat()
            }), 503
        
        # HTML response
        return f'''
        <!DOCTYPE html>
        <html lang="pt-br">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sistema Patrimonial - Manutenção</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
                .error-container {{ background: white; border-radius: 15px; padding: 2rem; margin-top: 5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-md-8">
                        <div class="error-container text-center">
                            <h1 class="text-danger mb-4">
                                <i class="bi bi-exclamation-triangle-fill"></i> Sistema em Manutenção
                            </h1>
                            
                            <div class="alert alert-warning">
                                <h4>O sistema está passando por uma manutenção rápida</h4>
                                <p class="mb-0">Estaremos de volta em alguns instantes.</p>
                            </div>
                            
                            <div class="card mt-4">
                                <div class="card-header">
                                    <strong>Informações Técnicas</strong>
                                </div>
                                <div class="card-body text-start">
                                    <p><strong>ID do Erro:</strong> <code>{error_id}</code></p>
                                    <p><strong>Horário:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                                    <p><strong>URL:</strong> {request.path}</p>
                                </div>
                            </div>
                            
                            <div class="mt-4">
                                <button class="btn btn-primary" onclick="window.location.reload()">
                                    <i class="bi bi-arrow-clockwise"></i> Tentar Novamente
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''', 503
    
    return fallback_app

# ==============================
# INICIALIZAÇÃO PRINCIPAL
# ==============================

try:
    logger.info("🎯 Iniciando sistema patrimonial...")
    
    # Carregar aplicação principal
    application = load_application()
    
    # Aplicar middleware
    application = ReverseProxied(application)
    
    logger.info("✅ WSGI configurado com sucesso para produção")
    logger.info(f"📁 Diretório: {APP_DIR}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"📦 Caminho: {sys.path}")

except Exception as ex:
    logger.critical(f"💥 FALHA CRÍTICA: {ex}")
    
    # Criar aplicação de fallback
    application = create_fallback_app()
    application = ReverseProxied(application)
    
    logger.info("🔄 Aplicação de fallback ativada")

# ==============================
# HANDLER PARA EXCEÇÕES NÃO CAPTURADAS
# ==============================

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Handler global para exceções não capturadas"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Não logar KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.critical(
        "💥 Exceção não capturada",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_uncaught_exception

if __name__ == "__main__":
    logger.info("🔧 Executando em modo desenvolvimento WSGI")
    application.run(host='0.0.0.0', port=5000, debug=False)