#!/usr/bin/env python3
"""
Correção cirúrgica para adicionar suporte AJAX à função index
"""
import os
import re

def correcao_cirurgica_index():
    print("🔧 CORREÇÃO CIRÚRGICA PARA FUNÇÃO INDEX")
    print("=" * 50)
    
    app_path = '/var/www/controle_estoque_db/app.py'
    backup_path = f'{app_path}.backup_pre_correcao_cirurgica'
    
    # Backup
    os.system(f'cp "{app_path}" "{backup_path}"')
    print(f"✅ Backup: {backup_path}")
    
    with open(app_path, 'r') as f:
        conteudo = f.read()
    
    # Encontrar a função index completa
    # Padrão: desde @app.route até o final da função
    padrao = r'(@app\.route\([\'"]\/[\'"], methods=\[.*?POST.*?\].*?def index\(\):.*?)(return render_template\([\'"]index\.html[\'"]\.*)'
    match = re.search(padrao, conteudo, re.DOTALL)
    
    if not match:
        print("❌ Não foi possível encontrar o padrão da função index")
        return False
    
    parte_inicial = match.group(1)
    parte_final = match.group(2)
    
    print(f"📍 Função index encontrada")
    
    # Criar a versão corrigida
    nova_funcao = parte_inicial + '''
    # VERIFICAÇÃO AJAX - CORREÇÃO CIRÚRGICA
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify
        import traceback
        
        try:
            numero_bem = request.form.get('numero_bem', '').strip().upper()
            localizacao = request.form.get('localizacao', '').strip()
            
            app.logger.info(f"🎯 AJAX REQUEST: {numero_bem} | Localização: '{localizacao}'")
            
            # Validação básica
            if not numero_bem:
                return jsonify({
                    "success": False, 
                    "mensagem": "Número do bem é obrigatório."
                }), 400
            
            # Buscar bem no banco
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bem_patrimonial WHERE numero_bem = ?", (numero_bem,))
            bem = cursor.fetchone()
            
            if not bem:
                conn.close()
                return jsonify({
                    "success": False, 
                    "mensagem": f"Bem patrimonial {numero_bem} não encontrado."
                }), 404
            
            # Atualizar como localizado
            cursor.execute('''
                UPDATE bem_patrimonial 
                SET estado = 'localizado', 
                    localizacao = COALESCE(?, localizacao),
                    data_localizacao = CURRENT_TIMESTAMP,
                    data_atualizacao = CURRENT_TIMESTAMP
                WHERE numero_bem = ?
            ''', (localizacao, numero_bem))
            
            conn.commit()
            
            # Buscar estatísticas atualizadas
            cursor.execute("SELECT COUNT(*) FROM bem_patrimonial")
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bem_patrimonial WHERE estado = 'localizado'")
            localizados = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM bem_patrimonial WHERE estado = 'pendente'")
            pendentes = cursor.fetchone()[0]
            
            conn.close()
            
            mensagem = f"✅ Bem {numero_bem} marcado como localizado com sucesso!"
            
            return jsonify({
                "success": True,
                "mensagem": mensagem,
                "estatisticas": {
                    "total": total,
                    "localizados": localizados,
                    "pendentes": pendentes
                }
            })
            
        except Exception as e:
            app.logger.error(f"❌ Erro AJAX: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({
                "success": False,
                "mensagem": f"❌ Erro interno: {str(e)}"
            }), 500
    
    ''' + parte_final
    
    # Substituir no conteúdo
    novo_conteudo = conteudo.replace(parte_inicial + parte_final, nova_funcao)
    
    # Salvar
    with open(app_path, 'w') as f:
        f.write(novo_conteudo)
    
    print("✅ Correção cirúrgica aplicada com sucesso!")
    print("📝 Função index agora suporta requisições AJAX")
    
    return True

if __name__ == '__main__':
    correcao_cirurgica_index()