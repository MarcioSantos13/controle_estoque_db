import sqlite3
from typing import List, Dict, Tuple, Optional
from contextlib import contextmanager
from utils.logger import logger

@contextmanager
def get_db_connection(db_path: str):
    """
    Gerenciador de contexto para conexões com o banco de dados
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def verificar_bem(numero_bem: str, db_path: str) -> Tuple[bool, Optional[str]]:
    """Verifica se um bem existe no banco de dados"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bens WHERE numero = ?", (numero_bem,))
            existe = cursor.fetchone()[0] > 0
            
            logger.info(f"Verificação do bem {numero_bem}: {'Encontrado' if existe else 'Não encontrado'}")
            return existe, None if existe else "Bem não encontrado"
            
    except Exception as e:
        logger.error(f"Erro ao verificar bem {numero_bem}: {str(e)}")
        return False, f"Erro ao verificar bem: {str(e)}"

def marcar_bem_localizado(numero_bem: str, db_path: str, localizacao: Optional[str] = None) -> str:
    """Marca um bem como localizado no banco de dados"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Verificar se o bem existe primeiro
            cursor.execute("SELECT COUNT(*) FROM bens WHERE numero = ?", (numero_bem,))
            if cursor.fetchone()[0] == 0:
                return f"Bem {numero_bem} não encontrado no banco de dados"
            
            # Atualizar a situação e localização
            if localizacao:
                cursor.execute("""
                    UPDATE bens 
                    SET situacao = 'OK', localizacao = ?, data_localizacao = datetime('now'),
                        data_atualizacao = datetime('now')
                    WHERE numero = ?
                """, (localizacao, numero_bem))
                mensagem = f"✅ Bem {numero_bem} marcado como localizado em '{localizacao}'!"
            else:
                cursor.execute("""
                    UPDATE bens 
                    SET situacao = 'OK', data_localizacao = datetime('now'),
                        data_atualizacao = datetime('now')
                    WHERE numero = ?
                """, (numero_bem,))
                mensagem = f"✅ Bem {numero_bem} marcado como localizado!"
            
            conn.commit()
            logger.info(mensagem)
            return mensagem
            
    except Exception as e:
        error_msg = f"Erro ao marcar bem {numero_bem} como localizado: {str(e)}"
        logger.error(error_msg)
        return error_msg

def buscar_localizacao_existente(numero_bem: str, db_path: str) -> Optional[str]:
    """Busca a localização atual de um bem no banco de dados"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT localizacao FROM bens WHERE numero = ?", (numero_bem,))
            resultado = cursor.fetchone()
            
            localizacao = resultado['localizacao'] if resultado and resultado['localizacao'] else None
            return localizacao
            
    except Exception as e:
        logger.error(f"Erro ao buscar localização do bem {numero_bem}: {str(e)}")
        return None

def verificar_numero_existe(db_path, numero_bem):
    """Verifica se já existe um bem com o número informado"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bens WHERE numero = ?", (numero_bem,))
            resultado = cursor.fetchone()
            return resultado[0] > 0 if resultado else False
    except Exception as e:
        logger.error(f"Erro ao verificar número do bem: {str(e)}")
        return False

def gerar_planilhas_localizacao(db_path: str) -> Tuple[List[Dict], List[Dict]]:
    """Gera listas de bens localizados e não localizados a partir do banco"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Buscar bens localizados (situacao = 'OK')
            cursor.execute("SELECT * FROM bens WHERE situacao = 'OK'")
            localizados = [dict(row) for row in cursor.fetchall()]
            
            # Buscar bens não localizados (situacao != 'OK' ou NULL)
            cursor.execute("SELECT * FROM bens WHERE situacao != 'OK' OR situacao IS NULL")
            nao_localizados = [dict(row) for row in cursor.fetchall()]
            
            logger.info(f"Geradas listas: {len(localizados)} localizados, {len(nao_localizados)} não localizados")
            return localizados, nao_localizados
            
    except Exception as e:
        logger.error(f"Erro ao gerar planilhas de localização: {str(e)}")
        return [], []

def obter_bens_paginados(db_path: str, tipo: str, pagina: int = 1, por_pagina: int = 200):
    """Obtém bens com paginação"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            offset = (pagina - 1) * por_pagina
            
            if tipo == 'localizados':
                query = "SELECT * FROM bens WHERE situacao = 'OK'"
            elif tipo == 'nao-localizados':
                query = "SELECT * FROM bens WHERE situacao != 'OK' OR situacao IS NULL"
            else:
                query = "SELECT * FROM bens"
            
            query_paginada = f"{query} LIMIT {por_pagina} OFFSET {offset}"
            cursor.execute(query_paginada)
            dados = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute(f"SELECT COUNT(*) FROM ({query})")
            total_registros = cursor.fetchone()[0]
            
            total_paginas = (total_registros + por_pagina - 1) // por_pagina
            
            return {
                'dados': dados,
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

def contar_bens(db_path: str):
    """Retorna contagem total de bens por situação"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN situacao = 'OK' THEN 1 ELSE 0 END) as localizados,
                    SUM(CASE WHEN situacao != 'OK' OR situacao IS NULL THEN 1 ELSE 0 END) as nao_localizados
                FROM bens
            """)
            
            resultado = cursor.fetchone()
            return {
                'total': resultado['total'],
                'localizados': resultado['localizados'],
                'nao_localizados': resultado['nao_localizados']
            }
         
    except Exception as e:
        logger.error(f"Erro ao contar bens: {str(e)}")
        return {'total': 0, 'localizados': 0, 'nao_localizados': 0}
    
def obter_bem_por_numero(db_path: str, numero_bem: str):
    """Obtém todos os dados de um bem específico"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bens WHERE numero = ?
            """, (numero_bem,))
            
            resultado = cursor.fetchone()
            return dict(resultado) if resultado else None
            
    except Exception as e:
        logger.error(f"Erro ao obter bem {numero_bem}: {str(e)}")
        return None

def atualizar_bem(db_path: str, bem_id: int, dados: dict):
    """Atualiza os dados de um bem"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bens 
                SET nome = ?, situacao = ?, localizacao = ?, responsavel = ?,
                    detentor = ?, lotacao_detentor = ?, data_ultima_vistoria = ?,
                    data_vistoria_atual = ?, auditor = ?, status = ?, observacao = ?,
                    data_atualizacao = datetime('now')
                WHERE id = ?
            """, (
                dados['nome'], dados['situacao'], dados['localizacao'],
                dados['responsavel'], dados['detentor'], dados['lotacao_detentor'],
                dados['data_ultima_vistoria'], dados['data_vistoria_atual'],
                dados['auditor'], dados['status'], dados['observacao'], bem_id
            ))
            
            conn.commit()
            logger.info(f"Bem {bem_id} atualizado com sucesso")
            return True, "✅ Bem atualizado com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao atualizar bem {bem_id}: {str(e)}")
        return False, f"❌ Erro ao atualizar bem: {str(e)}"

def criar_novo_bem(db_path: str, dados: dict):
    """Cria um novo bem no sistema"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM bens WHERE numero = ?", (dados['numero'],))
            if cursor.fetchone()[0] > 0:
                return False, "❌ Já existe um bem com este número!"
            
            cursor.execute("""
                INSERT INTO bens (
                    numero, nome, situacao, localizacao, responsavel, detentor,
                    lotacao_detentor, data_ultima_vistoria, data_vistoria_atual,
                    auditor, status, observacao, data_criacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                dados['numero'], dados['nome'], dados['situacao'],
                dados['localizacao'], dados['responsavel'], dados['detentor'],
                dados['lotacao_detentor'], dados['data_ultima_vistoria'],
                dados['data_vistoria_atual'], dados['auditor'], dados['status'],
                dados['observacao']
            ))
            
            conn.commit()
            logger.info(f"Novo bem criado: {dados['numero']} - {dados['nome']}")
            return True, "✅ Bem cadastrado com sucesso!"
            
    except sqlite3.IntegrityError:
        return False, "❌ Erro: Já existe um bem com este número!"
    except Exception as e:
        logger.error(f"Erro ao criar novo bem: {str(e)}")
        return False, f"❌ Erro ao criar bem: {str(e)}"

def excluir_bem(db_path: str, bem_id: int):
    """Exclui um bem do sistema"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT numero FROM bens WHERE id = ?", (bem_id,))
            bem = cursor.fetchone()
            
            cursor.execute("DELETE FROM bens WHERE id = ?", (bem_id,))
            conn.commit()
            
            logger.info(f"Bem {bem['numero']} excluído")
            return True, f"✅ Bem {bem['numero']} excluído com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao excluir bem {bem_id}: {str(e)}")
        return False, f"❌ Erro ao excluir bem: {str(e)}"





def buscar_bens_por_nome(db_path: str, termo_busca: str):
    """Busca bens por nome, número, responsável ou detentor - BUSCA MELHORADA"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Limpar e preparar o termo de busca
            termo_limpo = termo_busca.strip()
            
            # Buscar em múltiplos campos com OR
            cursor.execute("""
                SELECT id, numero, nome, situacao, localizacao, responsavel, detentor, 
                       lotacao_detentor, data_ultima_vistoria, data_vistoria_atual, 
                       auditor, status, observacao, data_criacao, data_localizacao
                FROM bens 
                WHERE 
                    numero LIKE ? OR
                    nome LIKE ? OR 
                    responsavel LIKE ? OR 
                    detentor LIKE ? OR
                    localizacao LIKE ? OR
                    auditor LIKE ? OR
                    observacao LIKE ?
                ORDER BY 
                    CASE 
                        WHEN numero = ? THEN 1
                        WHEN numero LIKE ? THEN 2
                        WHEN nome = ? THEN 3
                        WHEN nome LIKE ? THEN 4
                        ELSE 5
                    END,
                    numero
            """, (
                # Busca parcial para LIKE
                f'%{termo_limpo}%',  # numero LIKE
                f'%{termo_limpo}%',  # nome LIKE
                f'%{termo_limpo}%',  # responsavel LIKE
                f'%{termo_limpo}%',  # detentor LIKE
                f'%{termo_limpo}%',  # localizacao LIKE
                f'%{termo_limpo}%',  # auditor LIKE
                f'%{termo_limpo}%',  # observacao LIKE
                # Busca exata para ordenação
                termo_limpo,         # numero exato
                f'{termo_limpo}%',   # numero começando com
                termo_limpo,         # nome exato
                f'{termo_limpo}%'    # nome começando com
            ))
            
            resultados = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Busca por '{termo_busca}': {len(resultados)} resultados encontrados")
            
            return resultados
            
    except Exception as e:
        logger.error(f"Erro na busca por '{termo_busca}': {str(e)}")
        return []






def obter_estatisticas_avancadas(db_path: str):
    """Obtém estatísticas avançadas do sistema"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Estatísticas por situação
            cursor.execute("""
                SELECT situacao, COUNT(*) as total 
                FROM bens 
                GROUP BY situacao
            """)
            stats_situacao = {row['situacao']: row['total'] for row in cursor.fetchall()}
            
            # Estatísticas por status
            cursor.execute("""
                SELECT status, COUNT(*) as total 
                FROM bens 
                GROUP BY status
            """)
            stats_status = {row['status']: row['total'] for row in cursor.fetchall()}
            
            # Estatísticas por detentor
            cursor.execute("""
                SELECT detentor, COUNT(*) as total 
                FROM bens 
                WHERE detentor IS NOT NULL AND detentor != ''
                GROUP BY detentor
                ORDER BY total DESC
                LIMIT 10
            """)
            stats_detentor = {row['detentor']: row['total'] for row in cursor.fetchall()}
            
            return {
                'situacao': stats_situacao,
                'status': stats_status,
                'top_detentores': stats_detentor
            }
            
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return {}

# Exportação explícita de todas as funções
__all__ = [
    'verificar_bem',
    'marcar_bem_localizado', 
    'buscar_localizacao_existente',
    'verificar_numero_existe',
    'gerar_planilhas_localizacao',
    'obter_bens_paginados',
    'contar_bens',
    'obter_bem_por_numero',
    'atualizar_bem',
    'criar_novo_bem',
    'excluir_bem',
    'buscar_bens_por_nome',
    'obter_estatisticas_avancadas'
]