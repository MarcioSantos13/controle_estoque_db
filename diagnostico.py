#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de deploy
"""
import os
import sys
import sqlite3
from flask import Flask, render_template_string

def diagnostico_servidor():
    print("🔍 INICIANDO DIAGNÓSTICO DO SERVIDOR")
    print("=" * 50)
    
    # Informações do sistema
    print("📋 Informações do Sistema:")
    print(f"  Python: {sys.version}")
    print(f"  Diretório atual: {os.getcwd()}")
    print(f"  Usuário: {os.getenv('USER', 'Não identificado')}")
    
    # Verificar estrutura de diretórios
    print("\n📁 Estrutura de Diretórios:")
    diretorios = ['static', 'templates', 'instance', 'uploads']
    for dir in diretorios:
        existe = os.path.exists(dir)
        permissao = os.access(dir, os.W_OK) if existe else False
        print(f"  {dir}: {'✅ Existe' if existe else '❌ Não existe'} {'(Gravação ✅)' if permissao else '(Gravação ❌)'}")
    
    # Verificar arquivos importantes
    print("\n📄 Arquivos Importantes:")
    arquivos = ['app.py', 'models.py', 'database.db', 'requirements.txt']
    for arquivo in arquivos:
        existe = os.path.exists(arquivo)
        print(f"  {arquivo}: {'✅ Existe' if existe else '❌ Não existe'}")
    
    # Verificar banco de dados
    print("\n🗄️ Verificação do Banco de Dados:")
    try:
        if os.path.exists('database.db'):
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            
            # Verificar tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tabelas = cursor.fetchall()
            print(f"  Tabelas no banco: {[t[0] for t in tabelas]}")
            
            # Verificar dados
            for tabela in ['bem_patrimonial', 'usuario']:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    count = cursor.fetchone()[0]
                    print(f"  Registros em {tabela}: {count}")
                except:
                    print(f"  Tabela {tabela}: ❌ Não existe ou erro")
            
            conn.close()
            print("  Conexão com banco: ✅ OK")
        else:
            print("  Banco de dados: ❌ Não existe")
    except Exception as e:
        print(f"  Erro no banco: {e}")
    
    # Verificar permissões
    print("\n🔐 Permissões:")
    try:
        # Testar escrita
        with open('teste_permissao.txt', 'w') as f:
            f.write('teste')
        os.remove('teste_permissao.txt')
        print("  Permissão de escrita: ✅ OK")
    except Exception as e:
        print(f"  Permissão de escrita: ❌ {e}")
    
    # Verificar variáveis de ambiente
    print("\n🌐 Variáveis de Ambiente:")
    env_vars = ['FLASK_ENV', 'DATABASE_URL', 'SECRET_KEY']
    for var in env_vars:
        valor = os.getenv(var, 'Não definida')
        print(f"  {var}: {valor}")
    
    print("\n" + "=" * 50)
    print("🎯 RECOMENDAÇÕES:")
    
    problemas = []
    
    if not os.path.exists('database.db'):
        problemas.append("• Banco de dados não existe - execute python init_db.py")
    
    if not os.path.exists('templates'):
        problemas.append("• Diretório templates não existe")
    
    if problemas:
        for problema in problemas:
            print(f"  {problema}")
    else:
        print("  ✅ Nenhum problema crítico identificado")
    
    return problemas

def criar_app_teste():
    """Criar uma app Flask mínima para teste"""
    app = Flask(__name__)
    app.secret_key = 'teste123'
    
    @app.route('/teste')
    def teste():
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Teste</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h1 class="text-success">✅ Servidor Funcionando!</h1>
                <p>Se você está vendo esta página, o Flask está rodando corretamente.</p>
                <div class="alert alert-info">
                    <h4>Informações:</h4>
                    <ul>
                        <li>Python: {{ python_version }}</li>
                        <li>Diretório: {{ diretorio }}</li>
                        <li>Flask: OK</li>
                    </ul>
                </div>
                <a href="/" class="btn btn-primary">Voltar para a aplicação principal</a>
            </div>
        </body>
        </html>
        """, python_version=sys.version, diretorio=os.getcwd())
    
    return app

if __name__ == '__main__':
    problemas = diagnostico_servidor()
    
    if problemas:
        print(f"\n🚨 {len(problemas)} problema(s) identificado(s)")
        resposta = input("Deseja iniciar o servidor de teste? (s/n): ")
        if resposta.lower() == 's':
            app = criar_app_teste()
            print("\n🌐 Iniciando servidor de teste em http://localhost:5001/teste")
            app.run(host='0.0.0.0', port=5001, debug=True)
    else:
        print("\n🎉 Ambiente parece OK! Tente iniciar a aplicação principal.")