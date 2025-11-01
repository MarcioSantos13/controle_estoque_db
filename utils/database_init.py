# utils/database_init.py - VERSÃO SIMPLIFICADA
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# Caminho absoluto do banco
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'relatorios', 'controle_patrimonial.db')

def inicializar_banco_completo(db_path: str = None) -> bool:
    """Inicializa o banco de dados - VERSÃO SIMPLIFICADA"""
    if db_path is None:
        db_path = DB_PATH
        
    try:
        logger.info(f"🔧 Inicializando banco: {db_path}")
        
        # Garantir que o diretório existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # TABELA BENS - Schema básico mas funcional
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                situacao TEXT DEFAULT 'Pendente',
                localizacao TEXT,
                responsavel TEXT,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                ultima_atualizacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Índices básicos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_numero ON bens(numero)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bens_situacao ON bens(situacao)")
        
        conn.commit()
        
        # Verificar se funcionou
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
        if cursor.fetchone():
            logger.info("✅ Tabela 'bens' criada/verificada com sucesso")
            conn.close()
            return True
        else:
            logger.error("❌ Falha ao criar tabela 'bens'")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {e}")
        return False

def verificar_banco_existe(db_path: str = None) -> bool:
    """Verifica simplesmente se a tabela bens existe"""
    if db_path is None:
        db_path = DB_PATH
        
    try:
        if not os.path.exists(db_path):
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bens'")
        resultado = cursor.fetchone() is not None
        conn.close()
        return resultado
        
    except:
        return False

# Inicialização automática
if not verificar_banco_existe():
    logger.warning("⚠️ Tabela 'bens' não encontrada, criando...")
    inicializar_banco_completo()
else:
    logger.info("✅ Tabela 'bens' já existe")