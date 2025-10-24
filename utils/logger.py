import logging
import sys
import os
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger():
    """Configura o logger robusto para capturar tracebacks completos"""
    logger = logging.getLogger('controle_patrimonial')
    logger.setLevel(logging.INFO)
    
    # Evitar múltiplos handlers
    if logger.handlers:
        return logger
    
    # Criar diretório de logs se não existir
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Caminho completo do arquivo de log
    log_file_path = os.path.join(log_dir, 'app.log')
    
    # Formatter melhorado para incluir tracebacks
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ===== HANDLER PARA ARQUIVO (PRINCIPAL) =====
    # RotatingFileHandler para evitar arquivos muito grandes
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # ===== HANDLER PARA ERROS (ARQUIVO SEPARADO) =====
    error_log_path = os.path.join(log_dir, 'errors.log')
    error_handler = RotatingFileHandler(
        error_log_path,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # ===== HANDLER PARA CONSOLE =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # ===== ADICIONAR HANDLERS =====
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    # Log inicial
    logger.info(f"=== SISTEMA INICIADO ===")
    logger.info(f"Arquivo de log principal: {os.path.abspath(log_file_path)}")
    logger.info(f"Arquivo de erros: {os.path.abspath(error_log_path)}")
    logger.info(f"Diretório de trabalho: {os.getcwd()}")
    
    return logger

def log_exception(exc_type, exc_value, exc_traceback):
    """Função personalizada para log de exceções não capturadas"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Não logar KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = logging.getLogger('controle_patrimonial')
    
    # Capturar traceback completo
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = ''.join(tb_lines)
    
    logger.critical(
        f"EXCEÇÃO NÃO CAPTURADA:\n{tb_text}",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

# Configurar handler global para exceções não capturadas
sys.excepthook = log_exception

# ===== FUNÇÕES AUXILIARES PARA LOG DETALHADO =====

def log_error_with_traceback(message, exc_info=None):
    """Log de erro com traceback completo"""
    logger = logging.getLogger('controle_patrimonial')
    
    if exc_info:
        logger.error(f"{message}", exc_info=exc_info)
    else:
        # Capturar traceback atual
        tb = traceback.format_exc()
        if tb != 'NoneType: None\n':
            logger.error(f"{message}\nTraceback:\n{tb}")
        else:
            logger.error(message)

def log_http_request(request):
    """Log detalhado de requisições HTTP"""
    logger = logging.getLogger('controle_patrimonial')
    
    try:
        log_data = {
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint or 'N/A',
            'user_agent': request.headers.get('User-Agent', 'N/A'),
            'remote_addr': request.remote_addr,
            'user_id': getattr(request, 'usuario_id', 'N/A')
        }
        
        logger.debug(f"HTTP Request: {log_data}")
        
    except Exception as e:
        logger.warning(f"Erro ao logar requisição: {str(e)}")

def log_database_operation(operation, table, details=""):
    """Log de operações no banco de dados"""
    logger = logging.getLogger('controle_patrimonial')
    logger.info(f"DB {operation.upper()} - Tabela: {table} - {details}")

def log_security_event(event_type, user_id, details):
    """Log de eventos de segurança"""
    logger = logging.getLogger('controle_patrimonial')
    logger.warning(f"SEGURANÇA - {event_type} - User: {user_id} - {details}")

def get_log_file_path():
    """Retorna o caminho completo do arquivo de log principal"""
    return os.path.join('logs', 'app.log')

def get_error_log_file_path():
    """Retorna o caminho completo do arquivo de erros"""
    return os.path.join('logs', 'errors.log')

def list_recent_errors(limit=10):
    """Lista os erros mais recentes do arquivo de erros"""
    error_file = get_error_log_file_path()
    
    if not os.path.exists(error_file):
        return ["Arquivo de erros não encontrado"]
    
    try:
        with open(error_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Filtrar apenas linhas de ERROR e CRITICAL
        error_lines = [line for line in lines if 'ERROR' in line or 'CRITICAL' in line]
        return error_lines[-limit:] if error_lines else ["Nenhum erro encontrado"]
    
    except Exception as e:
        return [f"Erro ao ler arquivo de logs: {str(e)}"]

# Criar logger global
logger = setup_logger()

# Log de teste para verificar funcionamento
if __name__ == "__main__":
    logger.info("Teste de logger - sistema funcionando")
    
    try:
        # Teste de exceção
        raise ValueError("Este é um teste de exceção")
    except Exception as e:
        log_error_with_traceback("Erro durante teste", exc_info=True)
    
    # Mostrar informações dos arquivos de log
    print(f"\n📁 Arquivo de log principal: {os.path.abspath(get_log_file_path())}")
    print(f"📁 Arquivo de erros: {os.path.abspath(get_error_log_file_path())}")
    print(f"📁 Diretório atual: {os.getcwd()}")