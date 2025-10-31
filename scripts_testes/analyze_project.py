# INÍCIO: Analisador de Estrutura de Projeto Flask (CORRIGIDO)
import os
from pathlib import Path
import json

def analyze_flask_project(root_path='.'):
    """
    Analisa a estrutura de um projeto Flask e gera relatório detalhado
    """
    root = Path(root_path)
    project_structure = {
        'project_root': str(root.absolute()),
        'flask_detected': False,
        'main_app_file': None,
        'routes_detected': [],
        'templates': [],
        'static_files': [],
        'python_modules': [],
        'requirements': False,
        'virtual_env': False
    }
    
    # Padrões comuns em projetos Flask
    flask_files = ['app.py', 'application.py', 'wsgi.py', 'run.py']
    
    print("=" * 60)
    print("ANÁLISE DA ESTRUTURA DO PROJETO FLASK")
    print("=" * 60)
    
    # Verifica arquivos principais do Flask
    for file_name in flask_files:
        if (root / file_name).exists():
            project_structure['flask_detected'] = True
            project_structure['main_app_file'] = file_name
            print(f"✓ Arquivo principal Flask: {file_name}")
    
    # Analisa estrutura de pastas
    for item in root.rglob('*'):
        if item.is_dir():
            # Ignora diretórios comuns
            if any(ignore in str(item) for ignore in ['__pycache__', '.git', 'venv', '.vscode', 'env']):
                if 'venv' in str(item) or 'env' in str(item):
                    project_structure['virtual_env'] = True
                continue
            
            relative_path = item.relative_to(root)
            indent = "  " * (len(relative_path.parts) - 1)
            
            if item.name == 'templates':
                project_structure['templates'] = [f.name for f in item.glob('*') if f.is_file()]
                print(f"{indent}📁 {item.name}/ → {len(project_structure['templates'])} templates")
            
            elif item.name == 'static':
                static_files = list(item.rglob('*'))
                project_structure['static_files'] = [str(f.relative_to(item)) for f in static_files if f.is_file()]
                print(f"{indent}📁 {item.name}/ → {len(project_structure['static_files'])} arquivos estáticos")
            
            else:
                print(f"{indent}📁 {item.name}/")
        
        else:  # É arquivo
            if any(ignore in str(item) for ignore in ['__pycache__', '.pyc']):
                continue
                
            relative_path = item.relative_to(root)
            indent = "  " * (len(relative_path.parts) - 1)
            
            if item.suffix == '.py':
                # Detecta possíveis arquivos de rotas
                if 'route' in item.name.lower() or 'view' in item.name.lower():
                    project_structure['routes_detected'].append(str(relative_path))
                    print(f"{indent}🐍 {item.name} → (ROTA)")
                else:
                    project_structure['python_modules'].append(str(relative_path))
                    print(f"{indent}🐍 {item.name}")
            
            elif item.name == 'requirements.txt':
                project_structure['requirements'] = True
                print(f"{indent}📋 {item.name} → Dependências do projeto")
            
            elif item.suffix in ['.html', '.css', '.js', '.sqlite', '.db']:
                icon = "🌐 " if item.suffix == '.html' else "🎨 " if item.suffix == '.css' else "⚡" if item.suffix == '.js' else "🗃️ "
                print(f"{indent}📄 {icon}{item.name}")
            
            else:
                print(f"{indent}📄 {item.name}")
    
    return project_structure

def generate_tree_diagram(root_path='.'):
    """
    Gera um diagrama em árvore da estrutura
    """
    root = Path(root_path)
    
    def build_tree(path, prefix=""):
        contents = list(path.iterdir())
        # Filtra diretórios e arquivos ignorados
        contents = [item for item in contents if not any(ignore in str(item) for ignore in ['__pycache__', '.git', 'venv', '.vscode', '.pyc', 'env'])]
        pointers = ["├── "] * (len(contents) - 1) + ["└── "]
        
        for pointer, item in zip(pointers, sorted(contents)):
            if item.is_dir():
                yield prefix + pointer + "📁 " + item.name
                extension = "│   " if pointer == "├── " else "    "
                yield from build_tree(item, prefix=prefix + extension)
            else:
                # Ícones por tipo de arquivo
                icon = "🐍 " if item.suffix == '.py' else "📄 "
                if item.suffix == '.html':
                    icon = "🌐 "
                elif item.suffix == '.css':
                    icon = "🎨 "
                elif item.suffix == '.js':
                    icon = "⚡ "
                elif item.suffix in ['.db', '.sqlite']:
                    icon = "🗃️ "
                yield prefix + pointer + icon + item.name
    
    print("\n" + "=" * 60)
    print("DIAGRAMA EM ÁRVORE DO PROJETO")
    print("=" * 60)
    print("📁 " + root.name)
    for line in build_tree(root):
        print(line)

def check_virtual_environment():
    """
    Verifica se está rodando em um virtual environment
    """
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    venv_path = os.environ.get('VIRTUAL_ENV', None)
    
    print(f"✅ Virtual Environment ativo: {'Sim' if in_venv else 'Não'}")
    if venv_path:
        print(f"📍 Caminho do VE: {venv_path}")
    return in_venv

# Execução do análise
if __name__ == "__main__":
    import sys
    
    print("🔍 INICIANDO ANÁLISE DO PROJETO FLASK")
    print("=" * 60)
    
    # Verifica virtual environment primeiro
    check_virtual_environment()
    print()
    
    # Analisa estrutura do projeto
    project_info = analyze_flask_project()  # CORREÇÃO: variável renomeada
    generate_tree_diagram()
    
    # Resumo final - CORREÇÃO: usando project_info
    print("\n" + "=" * 60)
    print("RESUMO DA ANÁLISE")
    print("=" * 60)
    print(f"📊 Total de módulos Python: {len(project_info['python_modules'])}")
    print(f"🎯 Arquivos de rota detectados: {len(project_info['routes_detected'])}")
    print(f"📝 Templates encontrados: {len(project_info['templates'])}")
    print(f"🖼️ Arquivos estáticos: {len(project_info['static_files'])}")
    print(f"✅ Virtual Environment: {'Sim' if project_info['virtual_env'] else 'Não'}")  # CORREÇÃO
    print(f"✅ requirements.txt: {'Encontrado' if project_info['requirements'] else 'Não encontrado'}")
    print(f"✅ Flask detectado: {'Sim' if project_info['flask_detected'] else 'Não'}")
    if project_info['main_app_file']:
        print(f"📍 Arquivo principal: {project_info['main_app_file']}")
    
    print("\n" + "=" * 60)
    print("PRÓXIMOS PASSOS RECOMENDADOS")
    print("=" * 60)
    
    # Recomendações baseadas na análise
    if not project_info['virtual_env']:
        print("⚠️  RECOMENDAÇÃO: Crie um virtual environment para isolar dependências")
        print("   python -m venv venv")
    
    if not project_info['requirements']:
        print("⚠️  RECOMENDAÇÃO: Crie um requirements.txt para gerenciar dependências")
        print("   pip freeze > requirements.txt")
    
    if not project_info['flask_detected']:
        print("⚠️  ALERTA: Nenhum arquivo principal Flask detectado")
    
    print("✅ Análise concluída!")
# FIM: Analisador de Estrutura de Projeto Flask (CORRIGIDO)