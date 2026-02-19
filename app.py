import os
import sys
import re
import sqlite3
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Flask, render_template, request, send_file, abort, jsonify, redirect, url_for

# Importação simplificada
from utils import db_handler
from utils import excel_importer
from utils.logger import logger

app = Flask(__name__)

# ==============================
# Filtros personalizados para Jinja2
# ==============================
@app.template_filter('number_format')
def number_format_filter(value):
    try:
        if value is None:
            return "0"
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('pluralize')
def pluralize_filter(value, singular, plural):
    try:
        num = int(value)
        return singular if num == 1 else plural
    except (ValueError, TypeError):
        return plural

@app.template_filter('format_date')
def format_date_filter(value):
    try:
        if value:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')
        return "Não informada"
    except:
        return str(value) if value else "Não informada"

# ==============================
# Utilitário de caminho
# ==============================
def caminho_relativo(pasta: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, pasta)
    return os.path.join(os.path.abspath("."), pasta)

DB_PATH = os.path.join(caminho_relativo("relatorios"), "controle_patrimonial.db")

# ==============================
# Funções auxiliares
# ==============================
def _carregar_dados_bancos():
    try:
        contagens = db_handler.contar_bens(DB_PATH)
        return {
            'localizados_count': contagens['localizados'],
            'nao_localizados_count': contagens['nao_localizados'],
            'total_count': contagens['total']
        }
    except Exception as e:
        logger.error(f"Erro ao carregar contagens do banco: {str(e)}")
        return {'localizados_count': 0, 'nao_localizados_count': 0, 'total_count': 0}
    
def _processar_bem(numero_bem: str, localizacao: str = None):
    try:
        if not localizacao:
            localizacao = db_handler.buscar_localizacao_existente(numero_bem, DB_PATH)

        encontrado, erro = db_handler.verificar_bem(numero_bem, DB_PATH)
        if encontrado:
            mensagem = db_handler.marcar_bem_localizado(numero_bem, DB_PATH, localizacao)
        else:
            mensagem = erro or 'Bem não encontrado.'
            
        bem_detalhes = _buscar_detalhes_bem(numero_bem, localizacao)
        
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
            'show_modal': True
        }

def _buscar_detalhes_bem(numero_bem: str, localizacao: str = None):
    try:
        bem = db_handler.obter_bem_por_numero(DB_PATH, numero_bem)
        
        if bem:
            localizacao_final = localizacao or bem['localizacao'] or 'Não informada'
            
            return {
                'id': bem['id'],
                'nome': bem['nome'] or 'Não informado',
                'numero': bem['numero'] or 'Não informado',
                'situacao': bem['situacao'] or 'Pendente',
                'localizacao': localizacao_final,
                'responsavel': bem['responsavel'],
                'detentor': bem['detentor'],
                'lotacao_detentor': bem['lotacao_detentor'],
                'data_ultima_vistoria': bem['data_ultima_vistoria'],
                'data_vistoria_atual': bem['data_vistoria_atual'],
                'auditor': bem['auditor'],
                'status': bem['status'],
                'observacao': bem['observacao'],
                'data_criacao': bem['data_criacao'],
                'data_localizacao': bem['data_localizacao']
            }
        else:
            logger.warning(f"Bem {numero_bem} não encontrado no banco")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do bem {numero_bem}: {str(e)}")
        return None

# ==============================
# Rotas Principais
# ==============================
@app.route('/', methods=['GET', 'POST'])
def index():
    mensagem_sucesso = request.args.get('mensagem', None)
    
    if not os.path.exists(DB_PATH):
        mensagem = "Banco de dados não encontrado. Execute a migração primeiro."
        return render_template('index.html', mensagem=mensagem, bem_detalhes=None, **_carregar_dados_bancos())
    
    if request.method == 'POST':
        numero_bem = request.form.get('numero_bem', '').strip()
        localizacao = request.form.get('localizacao', '').strip()
        
        if not numero_bem:
            return render_template('index.html', 
                                 mensagem='Por favor, digite o número do bem.',
                                 **_carregar_dados_bancos())
        
        if not re.match(r'^[A-Za-z0-9-]+$', numero_bem):
            return render_template('index.html',
                                 mensagem='Número do bem inválido.',
                                 **_carregar_dados_bancos())
        
        resultado = _processar_bem(numero_bem, localizacao)
        return render_template('index.html', 
                             **_carregar_dados_bancos(),
                             **resultado)
    
    return render_template('index.html', 
                         mensagem=None,
                         mensagem_sucesso=mensagem_sucesso,
                         show_modal=False,
                         **_carregar_dados_bancos())

@app.route('/visualizar/<tipo>')
def visualizar(tipo: str):
    if not os.path.exists(DB_PATH):
        return render_template('visualizar.html', 
                             titulo='Visualização', 
                             tipo=tipo,
                             paginacao={'dados': [], 'pagina_atual': 1, 'por_pagina': 200, 'total_registros': 0, 'total_paginas': 0},
                             mensagem="Banco de dados não encontrado.")

    try:
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 200, type=int)
        
        pagina = max(1, pagina)
        por_pagina = max(50, min(por_pagina, 1000))
        
        paginacao = db_handler.obter_bens_paginados(DB_PATH, tipo, pagina, por_pagina)
        
        if tipo == 'localizados':
            titulo = 'Bens Localizados'
        elif tipo == 'nao-localizados':
            titulo = 'Bens Não Localizados'
        else:
            titulo = 'Visualização'
            paginacao['dados'] = []
        
        return render_template('visualizar.html', 
                             titulo=titulo,
                             tipo=tipo,
                             paginacao=paginacao)
            
    except Exception as e:
        logger.error(f"Erro em /visualizar/{tipo}: {str(e)}")
        return render_template('visualizar.html', 
                             titulo='Erro',
                             tipo=tipo,
                             paginacao={'dados': [], 'pagina_atual': 1, 'por_pagina': 200, 'total_registros': 0, 'total_paginas': 0},
                             mensagem=f"Erro ao carregar dados: {str(e)}")

@app.route('/exportar/<tipo>')
def exportar(tipo: str):
    """Exporta relatórios para Excel"""
    if not os.path.exists(DB_PATH):
        abort(404, description="Banco de dados não encontrado.")

    try:
        resultado = db_handler.obter_bens_paginados(DB_PATH, tipo, 1, 1000000)
        
        if tipo == 'localizados':
            registros = resultado['dados']
            nome_base = 'bens_localizados'
        elif tipo == 'nao-localizados':
            registros = resultado['dados']
            nome_base = 'bens_nao_localizados'
        else:
            abort(400, description="Tipo inválido.")
            
    except Exception as e:
        logger.error(f"Falha ao preparar dados para exportação: {str(e)}")
        abort(500, description="Erro ao preparar dados para exportação.")

    # Exportar para Excel
    try:
        import pandas as pd
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = caminho_relativo("relatorios")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{nome_base}_{ts}.xlsx")

        df = pd.DataFrame(registros)
        if 'numero' in df.columns:
            df = df.sort_values(by='numero')
        df.to_excel(out_path, index=False)
        
        logger.info(f"Relatório exportado: {out_path} ({len(registros)} registros)")
        return send_file(out_path, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Falha ao exportar Excel: {str(e)}")
        abort(500, description="Erro ao exportar Excel.")

@app.route('/importar-excel', methods=['POST'])
def importar_excel():
    """Rota para importar dados do Excel para o SQLite"""
    try:
        if 'excel_file' not in request.files:
            return render_template('index.html', 
                                 mensagem='Nenhum arquivo selecionado',
                                 **_carregar_dados_bancos())
        
        arquivo = request.files['excel_file']
        
        if arquivo.filename == '':
            return render_template('index.html',
                                 mensagem='Nenhum arquivo selecionado',
                                 **_carregar_dados_bancos())
        
        if not arquivo.filename.lower().endswith(('.xlsx', '.xls')):
            return render_template('index.html',
                                 mensagem='Formato de arquivo inválido. Use .xlsx ou .xls',
                                 **_carregar_dados_bancos())
        
        # Salvar arquivo temporariamente
        filename = secure_filename(arquivo.filename)
        temp_path = os.path.join('temp', filename)
        os.makedirs('temp', exist_ok=True)
        arquivo.save(temp_path)
        
        aba_nome = request.form.get('aba_nome', 'Estoque')
        criar_backup = request.form.get('backup') == 'on'
        
        # Verificar estrutura
        valido, mensagem_verificacao = excel_importer.verificar_estrutura_excel(temp_path, aba_nome)
        
        if not valido:
            colunas_disponiveis = excel_importer.obter_colunas_excel(temp_path, aba_nome)
            mensagem_erro = f"{mensagem_verificacao}. Colunas disponíveis: {', '.join(colunas_disponiveis)}"
            
            try:
                os.remove(temp_path)
            except:
                pass
            
            return render_template('index.html',
                                 mensagem=mensagem_erro,
                                 **_carregar_dados_bancos())
        
        # Executar importação
        sucesso, mensagem = excel_importer.importar_excel_para_sqlite(
            temp_path, aba_nome, DB_PATH, criar_backup
        )
        
        try:
            os.remove(temp_path)
        except:
            pass
        
        dados_banco = _carregar_dados_bancos()
        
        return render_template('index.html',
                             mensagem=mensagem,
                             show_modal=False,
                             **dados_banco)
        
    except Exception as e:
        logger.error(f"Erro na rota de importação: {str(e)}")
        
        try:
            if 'temp_path' in locals():
                os.remove(temp_path)
        except:
            pass
        
        return render_template('index.html',
                             mensagem=f'Erro durante a importação: {str(e)}',
                             **_carregar_dados_bancos())

# ==============================
# Rotas CRUD
# ==============================
@app.route('/api/bem/<numero_bem>')
def api_obter_bem(numero_bem):
    """API para obter dados completos de um bem"""
    try:
        bem = db_handler.obter_bem_por_numero(DB_PATH, numero_bem)
        
        if bem:
            return jsonify({'success': True, 'data': bem})
        else:
            return jsonify({'success': False, 'message': 'Bem não encontrado'})
            
    except Exception as e:
        logger.error(f"Erro ao obter bem {numero_bem}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/bem/editar', methods=['POST'])
def api_editar_bem():
    """API para editar um bem existente"""
    try:
        dados = request.get_json()
        bem_id = dados.get('bem_id')
        
        dados_atualizacao = {
            'nome': dados.get('nome'),
            'situacao': dados.get('situacao'),
            'localizacao': dados.get('localizacao'),
            'responsavel': dados.get('responsavel'),
            'detentor': dados.get('detentor'),
            'lotacao_detentor': dados.get('lotacao_detentor'),
            'data_ultima_vistoria': dados.get('data_ultima_vistoria'),
            'data_vistoria_atual': dados.get('data_vistoria_atual'),
            'auditor': dados.get('auditor'),
            'status': dados.get('status'),
            'observacao': dados.get('observacao')
        }
        
        sucesso, mensagem = db_handler.atualizar_bem(DB_PATH, bem_id, dados_atualizacao)
        return jsonify({'success': sucesso, 'message': mensagem})
        
    except Exception as e:
        logger.error(f"Erro ao editar bem: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/bem/excluir/<int:bem_id>', methods=['DELETE'])
def api_excluir_bem(bem_id):
    """API para excluir um bem"""
    try:
        sucesso, mensagem = db_handler.excluir_bem(DB_PATH, bem_id)
        return jsonify({'success': sucesso, 'message': mensagem})
        
    except Exception as e:
        logger.error(f"Erro ao excluir bem {bem_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/bem/novo', methods=['POST'])
def api_novo_bem():
    """API para criar um novo bem"""
    try:
        dados = {
            'numero': request.form.get('numero'),
            'nome': request.form.get('nome'),
            'situacao': request.form.get('situacao', 'Pendente'),
            'localizacao': request.form.get('localizacao'),
            'responsavel': request.form.get('responsavel'),
            'detentor': request.form.get('detentor'),
            'lotacao_detentor': request.form.get('lotacao_detentor'),
            'data_ultima_vistoria': request.form.get('data_ultima_vistoria'),
            'data_vistoria_atual': request.form.get('data_vistoria_atual'),
            'auditor': request.form.get('auditor'),
            'status': request.form.get('status', 'Ativo'),
            'observacao': request.form.get('observacao')
        }
        
        if db_handler.verificar_numero_existe(DB_PATH, dados['numero']):
            return jsonify({
                'success': False, 
                'message': 'Já existe um bem com este número!'
            })
        
        sucesso, mensagem = db_handler.criar_novo_bem(DB_PATH, dados)
        
        if sucesso:
            return redirect(url_for('index', mensagem=mensagem))
        else:
            return jsonify({'success': False, 'message': mensagem})
        
    except Exception as e:
        logger.error(f"Erro ao criar novo bem: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/buscar')
def buscar_bens():
    """Página de busca avançada"""
    termo = request.args.get('q', '')
    
    resultados = db_handler.buscar_bens_por_nome(DB_PATH, termo) if termo else []
    
    return render_template('buscar.html', 
                         resultados=resultados, 
                         termo_busca=termo,
                         total_resultados=len(resultados))

@app.route('/novo-bem')
def novo_bem():
    """Página para cadastrar novo bem"""
    return render_template('novo_bem.html')

@app.route('/api/verificar-numero', methods=['GET'])
def api_verificar_numero():
    """API para verificar se um número de bem já existe"""
    try:
        numero = request.args.get('numero', '').strip()
        if not numero:
            return jsonify({'exists': False})
        
        existe = db_handler.verificar_numero_existe(DB_PATH, numero)
        return jsonify({'exists': existe})
        
    except Exception as e:
        logger.error(f"Erro ao verificar número: {str(e)}")
        return jsonify({'exists': False})

@app.route('/criar-bem', methods=['POST'])
def criar_bem():
    """Rota tradicional para criar novo bem"""
    try:
        dados = {
            'numero': request.form.get('numero', '').strip(),
            'nome': request.form.get('nome', '').strip(),
            'situacao': request.form.get('situacao', 'Pendente'),
            'localizacao': request.form.get('localizacao', '').strip(),
            'responsavel': request.form.get('responsavel', '').strip(),
            'detentor': request.form.get('detentor', '').strip(),
            'lotacao_detentor': request.form.get('lotacao_detentor', '').strip(),
            'data_ultima_vistoria': request.form.get('data_ultima_vistoria', ''),
            'data_vistoria_atual': request.form.get('data_vistoria_atual', ''),
            'auditor': request.form.get('auditor', '').strip(),
            'status': request.form.get('status', 'Ativo'),
            'observacao': request.form.get('observacao', '').strip()
        }
        
        if not dados['numero'] or not dados['nome']:
            return render_template('novo_bem.html', 
                                 erro='Número e nome são obrigatórios',
                                 dados=dados)
        
        if not re.match(r'^[A-Za-z0-9-]+$', dados['numero']):
            return render_template('novo_bem.html',
                                 erro='Número do bem deve conter apenas letras, números ou hífen',
                                 dados=dados)
        
        if db_handler.verificar_numero_existe(DB_PATH, dados['numero']):
            return render_template('novo_bem.html',
                                 erro='Já existe um bem com este número!',
                                 dados=dados)
        
        sucesso, mensagem = db_handler.criar_novo_bem(DB_PATH, dados)
        
        if sucesso:
            return redirect(url_for('index', mensagem=mensagem))
        else:
            return render_template('novo_bem.html',
                                 erro=mensagem,
                                 dados=dados)
            
    except Exception as e:
        logger.error(f"Erro ao criar bem: {str(e)}")
        return render_template('novo_bem.html',
                             erro=f'Erro interno: {str(e)}',
                             dados=request.form.to_dict())

@app.route('/estatisticas')
def estatisticas():
    """Página de estatísticas avançadas"""
    if not os.path.exists(DB_PATH):
        return render_template('estatisticas.html', 
                             mensagem="Banco de dados não encontrado.",
                             estatisticas={})
    
    try:
        stats = db_handler.obter_estatisticas_avancadas(DB_PATH)
        return render_template('estatisticas.html', estatisticas=stats)
    except Exception as e:
        logger.error(f"Erro ao carregar estatísticas: {str(e)}")
        return render_template('estatisticas.html', 
                             mensagem=f"Erro ao carregar estatísticas: {str(e)}",
                             estatisticas={})

@app.route('/sair')
def sair():
    """Página de encerramento do aplicativo"""
    return render_template('sair.html', 
                         total_count=_carregar_dados_bancos().get('total_count', 0),
                         session_time="5min")




@app.route('/sistema-crud')
def sistema_crud():
    """Sistema CRUD completo para gerenciamento de bens"""
    if not os.path.exists(DB_PATH):
        return render_template('sistema_crud.html', 
                             mensagem="Banco de dados não encontrado.",
                             paginacao={
                                 'dados': [],
                                 'pagina_atual': 1,
                                 'por_pagina': 50,
                                 'total_registros': 0,
                                 'total_paginas': 0
                             },
                             total_count=0,
                             localizados_count=0,
                             nao_localizados_count=0,
                             termo_busca='',
                             situacao_filtro=None,
                             status_filtro=None)

    try:
        # Obter parâmetros
        pagina = request.args.get('pagina', 1, type=int)
        por_pagina = request.args.get('por_pagina', 50, type=int)
        termo_busca = request.args.get('q', '')
        situacao_filtro = request.args.get('situacao')
        status_filtro = request.args.get('status')
        
        # Validar parâmetros
        pagina = max(1, pagina)
        por_pagina = max(10, min(por_pagina, 200))
        
        # Se há termo de busca, usar a função de busca aprimorada
        if termo_busca:
            # Buscar usando a função existente do db_handler
            resultados = db_handler.buscar_bens_por_nome(DB_PATH, termo_busca)
            
            # Aplicar filtros adicionais se existirem
            if situacao_filtro:
                resultados = [bem for bem in resultados if bem.get('situacao') == situacao_filtro]
            
            if status_filtro:
                resultados = [bem for bem in resultados if bem.get('status') == status_filtro]
            
            # Aplicar paginação manualmente
            total_registros = len(resultados)
            total_paginas = (total_registros + por_pagina - 1) // por_pagina
            
            # Calcular índices para a página atual
            inicio = (pagina - 1) * por_pagina
            fim = inicio + por_pagina
            dados_paginados = resultados[inicio:fim]
            
            paginacao = {
                'dados': dados_paginados,
                'pagina_atual': pagina,
                'por_pagina': por_pagina,
                'total_registros': total_registros,
                'total_paginas': total_paginas
            }
        else:
            # Sem termo de busca, usar filtros normais
            if situacao_filtro == 'OK':
                tipo = 'localizados'
            elif situacao_filtro == 'Pendente':
                tipo = 'nao-localizados'
            else:
                tipo = 'todos'
            
            # Usar a função existente do db_handler
            paginacao = db_handler.obter_bens_paginados(DB_PATH, tipo, pagina, por_pagina)
            
            # Aplicar filtro de status se especificado
            if status_filtro:
                paginacao['dados'] = [bem for bem in paginacao['dados'] if bem.get('status') == status_filtro]
                paginacao['total_registros'] = len(paginacao['dados'])
                paginacao['total_paginas'] = (paginacao['total_registros'] + por_pagina - 1) // por_pagina
        
        # Obter contagens para os cards
        contagens = db_handler.contar_bens(DB_PATH)
        
        return render_template('sistema_crud.html',
                             paginacao=paginacao,
                             total_count=contagens['total'],
                             localizados_count=contagens['localizados'],
                             nao_localizados_count=contagens['nao_localizados'],
                             termo_busca=termo_busca,
                             situacao_filtro=situacao_filtro,
                             status_filtro=status_filtro)
            
    except Exception as e:
        logger.error(f"Erro no sistema CRUD: {str(e)}")
        return render_template('sistema_crud.html',
                             mensagem=f"Erro ao carregar dados: {str(e)}",
                             paginacao={
                                 'dados': [],
                                 'pagina_atual': 1,
                                 'por_pagina': 50,
                                 'total_registros': 0,
                                 'total_paginas': 0
                             },
                             total_count=0,
                             localizados_count=0,
                             nao_localizados_count=0,
                             termo_busca='',
                             situacao_filtro=None,
                             status_filtro=None)








# ==============================
# Inicialização
# ==============================
if __name__ == '__main__':
    logger.info("Iniciando aplicação Flask")
    app.run(debug=True)