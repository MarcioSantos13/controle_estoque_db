# ==============================
# SISTEMA DE LOGGING CORRIGIDO
# ==============================

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import functools

class SafeRotatingFileHandler(RotatingFileHandler):
    """
    Handler de logging seguro que trata erros de permissão
    """
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False, errors=None):
        # Garantir que o diretório existe
        log_dir = os.path.dirname(filename)
        try:
            os.makedirs(log_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            print(f"⚠️  Não foi possível criar diretório de logs: {e}")
            # Fallback para diretório temporário
            filename = os.path.join('/tmp', 'controle_patrimonial.log')
        
        try:
            super().__init__(filename, mode, maxBytes, backupCount, encoding, delay, errors)
        except (OSError, PermissionError) as e:
            print(f"❌ Erro crítico no sistema de logs: {e}")
            # Usar stderr como fallback
            raise

def setup_logger(name='controle_patrimonial', log_level=logging.INFO):
    """
    Configura o sistema de logging com fallbacks seguros
    """
    
    # Criar logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Evitar handlers duplicados
    if logger.handlers:
        return logger
    
    # Formatter comum
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Tentar configurar arquivo de log
    log_configured = False
    
    # Tentativa 1: Log no diretório do projeto
    log_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'app.log'),
        '/var/log/controle_patrimonial/app.log',
        '/tmp/controle_patrimonial.log'
    ]
    
    for log_path in log_paths:
        try:
            # Garantir que o diretório existe
            log_dir = os.path.dirname(log_path)
            os.makedirs(log_dir, exist_ok=True)
            
            # Tentar criar handler de arquivo
            file_handler = SafeRotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            log_configured = True
            print(f"✅ Log configurado em: {log_path}")
            break
            
        except (OSError, PermissionError) as e:
            print(f"⚠️  Não foi possível configurar log em {log_path}: {e}")
            continue
    
    # Fallback: Log para console
    if not log_configured:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        print("✅ Log configurado para console (fallback)")
    
    # Handler para erros críticos (sempre no console)
    error_handler = logging.StreamHandler(sys.stderr)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

# Logger principal
try:
    logger = setup_logger()
except Exception as e:
    print(f"❌ Falha crítica no sistema de logs: {e}")
    # Fallback extremo
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('controle_patrimonial_fallback')

def log_function_call(func):
    """
    Decorator para log de chamadas de função
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Chamando {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} executada com sucesso")
            return result
        except Exception as e:
            logger.error(f"Erro em {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper

def log_database_operation(operation: str, table: str, details: str = ""):
    """
    Log especializado para operações de banco de dados
    """
    message = f"DB {operation} on {table}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_security_event(event: str, user: str = "unknown", ip: str = "unknown"):
    """
    Log para eventos de segurança
    """
    logger.warning(f"SEGURANÇA: {event} - Usuário: {user} - IP: {ip}")

def log_system_event(event: str, details: str = ""):
    """
    Log para eventos do sistema
    """
    message = f"SISTEMA: {event}"
    if details:
        message += f" - {details}"
    logger.info(message)

# Teste do sistema de logs
if __name__ == "__main__":
    logger.info("Sistema de logs inicializado com sucesso")
    logger.debug("Mensagem de debug")
    logger.warning("Mensagem de aviso")
    
    try:
        # Teste de erro
        raise ValueError("Teste de erro no logging")
    except Exception as e:
        logger.error("Erro de teste capturado", exc_info=True)