#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Configuration for Controle de Estoque Flask App
Otimizado com correção de permissões
"""

import sys
import os
import logging

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definir diretório da aplicação
APP_DIR = '/var/www/controle_estoque_db'
sys.path.insert(0, APP_DIR)

# Mudar para diretório da aplicação
os.chdir(APP_DIR)

# Variáveis de ambiente
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'production'

# Middleware para subdiretório /estoque
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = '/estoque'
        environ['SCRIPT_NAME'] = script_name
        path_info = environ['PATH_INFO']
        if path_info.startswith(script_name):
            environ['PATH_INFO'] = path_info[len(script_name):]
        return self.app(environ, start_response)

try:
    logger.info("Carregando aplicação Flask...")
    
    # Importar aplicação
    import app
    
    # Tentar diferentes formas de obter a aplicação Flask
    if hasattr(app, 'app'):
        application = app.app
        logger.info("Aplicação encontrada em app.app")
    elif hasattr(app, 'create_app'):
        application = app.create_app()
        logger.info("Aplicação criada via app.create_app()")
    elif hasattr(app, 'application'):
        application = app.application
        logger.info("Aplicação encontrada em app.application")
    else:
        # Procurar por instância Flask no módulo
        from flask import Flask
        flask_instances = [getattr(app, attr) for attr in dir(app) 
                          if isinstance(getattr(app, attr), Flask)]
        if flask_instances:
            application = flask_instances[0]
            logger.info("Instância Flask encontrada automaticamente")
        else:
            raise Exception("Nenhuma instância Flask encontrada no módulo app")
    
    # Configurações de produção
    application.config['DEBUG'] = False
    application.config['TESTING'] = False
    
    # Aplicar middleware para subdiretório
    application = ReverseProxied(application)
    
    logger.info("✅ Aplicação Flask configurada com sucesso")

except Exception as ex:
    import traceback
    from flask import Flask, request

    STARTUP_ERROR = repr(ex)
    STARTUP_TRACE = traceback.format_exc()

    application = Flask(__name__)

    @application.route('/', defaults={'path': ''})
    @application.route('/<path:path>')
    def error_info(path=''):
        # Usa as variáveis persistentes do módulo, não 'e'
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Controle de Estoque - Erro de Configuração</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .error {{ background: #ffebee; border: 1px solid #f44336; padding: 15px; border-radius: 5px; }}
                .code {{ background: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; white-space: pre-wrap; }}
                h1 {{ color: #d32f2f; }}
                h2 {{ color: #1976d2; }}
            </style>
        </head>
        <body>
            <h1>🚨 Controle de Estoque - Erro de Configuração</h1>

            <div class="error">
                <h2>Erro Principal:</h2>
                <p><strong>{STARTUP_ERROR}</strong></p>
            </div>

            <h2>📋 Informações de Debug:</h2>
            <ul>
                <li><strong>Diretório atual:</strong> {os.getcwd()}</li>
                <li><strong>Python Path[0]:</strong> {sys.path[0]}</li>
                <li><strong>Usuário:</strong> {os.getenv("USER", "desconhecido")}</li>
                <li><strong>Caminho solicitado:</strong> {request.path}</li>
            </ul>

            <h2>📂 Arquivos no Diretório:</h2>
            <div class="code">
{chr(10).join(os.listdir(APP_DIR))}
            </div>

            <h2>🔧 Detalhes do Erro:</h2>
            <div class="code">{STARTUP_TRACE}</div>

            <h2>✅ Próximos Passos:</h2>
            <ol>
                <li>Verifique se <code>app.py</code> existe e exporta <code>app</code> ou <code>create_app()</code></li>
                <li>Reveja variáveis de ambiente/credenciais de DB</li>
                <li>Logs: <code>tail -f /var/log/httpd/error_log</code></li>
            </ol>
        </body>
        </html>
        ''', 500

    
    application = ReverseProxied(application)

if __name__ == "__main__":
    application.run()
