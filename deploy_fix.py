#!/usr/bin/env python3
"""
Script para corrigir problemas comuns de deploy
"""
import os
import sqlite3
import shutil
from datetime import datetime

def corrigir_deploy():
    print("🔧 INICIANDO CORREÇÃO DE DEPLOY")
    
    # 1. Criar diretórios se não existirem
    diretorios = ['static', 'templates', 'instance', 'uploads', 'backups']
    for dir in diretorios:
        if not os.path.exists(dir):
            os.makedirs(dir)
            print(f"✅ Criado diretório: {dir}")
    
    # 2. Verificar e reparar banco de dados
    if not os.path.exists('database.db'):
        print("📦 Criando novo banco de dados...")
        from init_db import init_db
        init_db()
    else:
        # Backup do banco atual
        backup_file = f"backups/database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2('database.db', backup_file)
        print(f"✅ Backup criado: {backup_file}")
    
    # 3. Verificar permissões
    print("🔐 Ajustando permissões...")
    for root, dirs, files in os.walk('.'):
        for dir in dirs:
            os.chmod(os.path.join(root, dir), 0o755)
        for file in files:
            os.chmod(os.path.join(root, file), 0o644)
    
    # 4. Criar arquivo de requirements atualizado
    with open('requirements.txt', 'w') as f:
        f.write("""Flask==2.3.3
Werkzeug==2.3.7
Flask-SQLAlchemy==3.0.5
python-dotenv==1.0.0
openpyxl==3.1.2
Pillow==10.0.0
""")
    print("✅ requirements.txt atualizado")
    
    # 5. Criar .htaccess para Apache (se necessário)
    if not os.path.exists('.htaccess'):
        with open('.htaccess', 'w') as f:
            f.write("""
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /index.php?path=$1 [L,QSA]
""")
        print("✅ .htaccess criado")
    
    print("\n🎉 Correção concluída!")
    print("📋 Próximos passos:")
    print("   1. Reinicie o servidor web")
    print("   2. Acesse /debug para verificar o status")
    print("   3. Teste a aplicação principal")

if __name__ == '__main__':
    corrigir_deploy()