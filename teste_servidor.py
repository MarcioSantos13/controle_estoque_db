#!/usr/bin/env python3
"""
Teste específico para problemas no servidor
"""
import os
import sys
import sqlite3
from flask import Flask, request, jsonify, session
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def testar_ambiente_servidor():
    """Testar o ambiente do servidor"""
    print("🔍 TESTANDO AMBIENTE DO SERVIDOR")
    print("=" * 50)
    
    # Informações básicas
    print("📋 Informações do Sistema:")
    print(f"  Python: {sys.version}")
    print(f"  Diretório: {os.getcwd()}")
    print(f"  Usuário: {os.getenv('USER', 'Não identificado')}")
    
    # Verificar banco
    caminho_banco = '/var/www/controle_estoque_db/relatorios/controle_patrimonial.db'
    print(f"\n🗄️  Verificando banco: {caminho_banco}")
    
    if os.path.exists(caminho_banco):
        print("  ✅ Banco existe")
        # Testar conexão
        try:
            conn = sqlite3.connect(caminho_banco)
            cursor = conn.cursor()
            
            # Verificar tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabelas = [t[0] for t in cursor.fetchall()]
            print(f"  📊 Tabelas: {tabelas}")
            
            # Verificar permissões
            cursor.execute("SELECT COUNT(*) FROM bem_patrimonial")
            total_bens = cursor.fetchone()[0]
            print(f"  🔢 Total de bens: {total_bens}")
            
            conn.close()
            print("  ✅ Conexão com banco: OK")
            
        except Exception as e:
            print(f"  ❌ Erro no banco: {e}")
    else:
        print("  ❌ Banco não encontrado")
    
    # Verificar arquivos estáticos
    print(f"\n📁 Verificando arquivos estáticos:")
    static_files = ['static/style.css', 'templates/index.html']
    for arquivo in static_files:
        existe = os.path.exists(arquivo)
        print(f"  {arquivo}: {'✅ Existe' if existe else '❌ Não existe'}")
    
    # Testar permissões de escrita
    print(f"\n🔐 Testando permissões:")
    try:
        test_file = 'teste_permissao.txt'
        with open(test_file, 'w') as f:
            f.write('teste')
        os.remove(test_file)
        print("  ✅ Permissão de escrita: OK")
    except Exception as e:
        print(f"  ❌ Permissão de escrita: {e}")
    
    print("\n" + "=" * 50)

def criar_app_teste():
    """Criar app Flask minimalista para teste"""
    app = Flask(__name__)
    app.secret_key = 'teste-servidor-123'
    
    @app.route('/teste-ajax', methods=['POST'])
    def teste_ajax():
        """Teste específico para AJAX"""
        try:
            data = request.get_json()
            numero_bem = data.get('numero_bem', '') if data else request.form.get('numero_bem', '')
            
            logger.info(f"📨 Requisição AJAX recebida: {numero_bem}")
            logger.info(f"📦 Headers: {dict(request.headers)}")
            logger.info(f"📝 Form data: {dict(request.form)}")
            logger.info(f"🔠 JSON data: {data}")
            
            # Simular processamento
            return jsonify({
                'success': True,
                'mensagem': f'✅ Bem {numero_bem} processado com sucesso!',
                'estatisticas': {
                    'total': 100,
                    'localizados': 50,
                    'pendentes': 50
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Erro no teste AJAX: {e}")
            return jsonify({
                'success': False,
                'mensagem': f'❌ Erro: {str(e)}'
            }), 500
    
    @app.route('/teste-scan', methods=['POST'])
    def teste_scan():
        """Teste de scan normal (não-AJAX)"""
        numero_bem = request.form.get('numero_bem', '')
        logger.info(f"📨 Requisição normal recebida: {numero_bem}")
        
        # Simular redirecionamento como na versão antiga
        return f"""
        <html>
        <body>
            <script>
                alert('Bem {numero_bem} processado!');
                window.location.href = '/';
            </script>
        </body>
        </html>
        """
    
    @app.route('/teste-page')
    def teste_page():
        """Página de teste"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Teste Servidor</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h1>🧪 Teste do Servidor</h1>
                
                <div class="card mt-4">
                    <div class="card-header">
                        <h5>Teste AJAX</h5>
                    </div>
                    <div class="card-body">
                        <form id="testFormAjax">
                            <div class="mb-3">
                                <label class="form-label">Número do Bem:</label>
                                <input type="text" name="numero_bem" class="form-control" value="TESTE-001" required>
                            </div>
                            <button type="button" class="btn btn-primary" onclick="testarAjax()">
                                Testar AJAX
                            </button>
                        </form>
                        <div id="resultadoAjax" class="mt-3"></div>
                    </div>
                </div>
                
                <div class="card mt-4">
                    <div class="card-header">
                        <h5>Teste Form Normal</h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="/teste-scan">
                            <div class="mb-3">
                                <label class="form-label">Número do Bem:</label>
                                <input type="text" name="numero_bem" class="form-control" value="TESTE-002" required>
                            </div>
                            <button type="submit" class="btn btn-secondary">
                                Testar Form Normal
                            </button>
                        </form>
                    </div>
                </div>
                
                <div class="mt-4">
                    <a href="/" class="btn btn-outline-primary">Voltar para App Principal</a>
                </div>
            </div>
            
            <script>
            function testarAjax() {
                const formData = new FormData(document.getElementById('testFormAjax'));
                const resultado = document.getElementById('resultadoAjax');
                
                resultado.innerHTML = '<div class="alert alert-info">Enviando...</div>';
                
                fetch('/teste-ajax', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        resultado.innerHTML = `<div class="alert alert-success">${data.mensagem}</div>`;
                    } else {
                        resultado.innerHTML = `<div class="alert alert-danger">${data.mensagem}</div>`;
                    }
                })
                .catch(error => {
                    resultado.innerHTML = `<div class="alert alert-danger">Erro: ${error}</div>`;
                });
            }
            </script>
        </body>
        </html>
        '''
    
    return app

if __name__ == '__main__':
    # Executar diagnóstico
    testar_ambiente_servidor()
    
    # Iniciar servidor de teste
    print("🚀 Iniciando servidor de teste em http://localhost:5002")
    print("📝 Acesse: http://seu-servidor.com:5002/teste-page")
    
    app = criar_app_teste()
    app.run(host='0.0.0.0', port=5002, debug=True)