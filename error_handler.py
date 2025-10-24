# error_handler.py
import os
import traceback
from datetime import datetime
from flask import render_template, request, jsonify
import logging

class ErrorHandler:
    def __init__(self, app=None, log_file='errors.log'):
        self.app = app
        self.log_file = log_file
        self.setup_logging()
        
        if app is not None:
            self.init_app(app)
    
    def setup_logging(self):
        """Configura o sistema de logging para erros"""
        # Criar diretório de logs se não existir
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_path = os.path.join(log_dir, self.log_file)
        
        # Configurar logging
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('error_handler')
    
    def init_app(self, app):
        """Inicializa o handler de erros no app Flask"""
        self.app = app
        
        # Registrar handlers de erro
        @app.errorhandler(404)
        def not_found_error(error):
            return self.handle_error(error, 404)
        
        @app.errorhandler(500)
        def internal_error(error):
            return self.handle_error(error, 500)
        
        @app.errorhandler(Exception)
        def unhandled_exception(error):
            return self.handle_error(error, 500)
        
        # Log de todas as requisições com erro
        @app.after_request
        def log_response(response):
            if response.status_code >= 400:
                self.log_request(response.status_code)
            return response
    
    def log_error(self, error, status_code=500):
        """Registra erro no log com informações detalhadas"""
        try:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Informações da requisição
            request_info = {
                'method': request.method,
                'url': request.url,
                'endpoint': request.endpoint or 'Unknown',
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'remote_addr': request.remote_addr,
                'referrer': request.referrer or 'Direct'
            }
            
            # Informações do usuário (se disponível)
            user_info = {}
            if hasattr(request, 'usuario'):
                user_info = {
                    'user_id': getattr(request.usuario, 'id', 'Unknown'),
                    'user_email': getattr(request.usuario, 'email', 'Unknown')
                }
            
            # Stack trace
            stack_trace = traceback.format_exc()
            
            # Mensagem de erro formatada
            error_message = f"""
╔═══════════════════════════════════════════════════════════════
║ ERRO {status_code} - {error_time}
╠═══════════════════════════════════════════════════════════════
║ TIPO: {type(error).__name__}
║ MENSAGEM: {str(error)}
║
║ 📍 INFORMAÇÕES DA REQUISIÇÃO:
║    Método: {request_info['method']}
║    URL: {request_info['url']}
║    Endpoint: {request_info['endpoint']}
║    IP: {request_info['remote_addr']}
║    User Agent: {request_info['user_agent']}
║    Referrer: {request_info['referrer']}
║
║ 👤 INFORMAÇÕES DO USUÁRIO:
║    ID: {user_info.get('user_id', 'N/A')}
║    Email: {user_info.get('user_email', 'N/A')}
║
║ 🔍 STACK TRACE:
{stack_trace}
╚═══════════════════════════════════════════════════════════════
"""
            
            # Registrar no log
            self.logger.error(error_message)
            
            # Também salvar em arquivo separado para debug detalhado
            self.save_detailed_error(error_message, request_info, stack_trace)
            
        except Exception as log_error:
            # Fallback se houver erro no próprio sistema de logging
            print(f"❌ ERRO NO SISTEMA DE LOG: {log_error}")
            print(f"❌ ERRO ORIGINAL: {error}")
    
    def save_detailed_error(self, error_message, request_info, stack_trace):
        """Salva erro detalhado em arquivo separado"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            error_dir = os.path.join(os.path.dirname(__file__), 'logs', 'detailed_errors')
            os.makedirs(error_dir, exist_ok=True)
            
            error_file = os.path.join(error_dir, f'error_{timestamp}.log')
            
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(error_message)
                
                # Adicionar dados da sessão se disponíveis
                from flask import session
                if session:
                    f.write(f"\n📋 DADOS DA SESSÃO:\n")
                    for key, value in session.items():
                        if not key.startswith('_') and key != 'senha':  # Não logar dados sensíveis
                            f.write(f"   {key}: {value}\n")
                
                # Adicionar dados do formulário se disponíveis
                if request.form:
                    f.write(f"\n📝 DADOS DO FORMULÁRIO:\n")
                    for key, value in request.form.items():
                        if 'senha' not in key.lower():  # Não logar senhas
                            f.write(f"   {key}: {value}\n")
                
                # Adicionar dados JSON se disponíveis
                if request.is_json and request.get_data():
                    try:
                        json_data = request.get_json()
                        f.write(f"\n📦 DADOS JSON:\n")
                        f.write(f"   {json_data}\n")
                    except:
                        f.write(f"\n📦 DADOS BRUTOS:\n")
                        f.write(f"   {request.get_data()}\n")
                        
        except Exception as e:
            print(f"❌ Erro ao salvar log detalhado: {e}")
    
    def log_request(self, status_code):
        """Registra informações básicas da requisição com erro"""
        try:
            request_info = {
                'timestamp': datetime.now().isoformat(),
                'method': request.method,
                'url': request.url,
                'endpoint': request.endpoint or 'Unknown',
                'status_code': status_code,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
            
            self.logger.info(f"Requisição com erro: {request_info}")
            
        except Exception as e:
            print(f"❌ Erro ao logar requisição: {e}")
    
    def handle_error(self, error, status_code):
        """Manipula e responde aos erros"""
        # Logar o erro
        self.log_error(error, status_code)
        
        # Determinar o tipo de resposta baseado no Accept header
        if request.headers.get('Accept', '').startswith('application/json') or request.path.startswith('/api/'):
            return self.json_error_response(error, status_code)
        else:
            return self.html_error_response(error, status_code)
    
    def json_error_response(self, error, status_code):
        """Resposta de erro em JSON para APIs"""
        response = {
            'success': False,
            'error': {
                'code': status_code,
                'type': type(error).__name__,
                'message': str(error) if status_code != 500 else 'Erro interno do servidor',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Incluir stack trace apenas em modo debug
        if self.app and self.app.debug:
            response['error']['stack_trace'] = traceback.format_exc()
        
        return jsonify(response), status_code
    
    def html_error_response(self, error, status_code):
        """Resposta de erro em HTML para usuários"""
        error_messages = {
            404: 'Página não encontrada',
            500: 'Erro interno do servidor',
            403: 'Acesso negado'
        }
        
        error_context = {
            'error_code': status_code,
            'error_title': error_messages.get(status_code, 'Erro'),
            'error_message': str(error) if status_code != 500 else 'Algo deu errado ao processar sua requisição.',
            'support_contact': 'suporte@empresa.com',
            'show_details': self.app.debug if self.app else False
        }
        
        # Incluir detalhes apenas em modo debug
        if self.app and self.app.debug:
            error_context['error_details'] = traceback.format_exc()
        
        return render_template(f'errors/{status_code}.html', **error_context), status_code

# Instância global
error_handler = ErrorHandler()