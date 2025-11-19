import os

class ProductionConfig:
    """Configurações específicas para produção"""
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY', 'seu-secret-key-muito-longo-e-complexo-aqui')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database
    DB_RELATIVE_PATH = "relatorios/controle_patrimonial.db"
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_RELATIVE_PATH)
    
    # Otimizações
    DEBUG = False
    TESTING = False
    
    # Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = '/tmp/patrimonial_uploads'
    
    # Caching
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 ano para arquivos estáticos
    
    # Logging
    LOG_LEVEL = 'INFO'