#!/usr/bin/env python3
"""
Teste específico do fluxo AJAX
"""
import requests
import json

def testar_fluxo_ajax():
    print("🧪 TESTE DO FLUXO AJAX")
    print("=" * 50)
    
    # URL da aplicação
    url = "http://localhost/"
    
    # Dados de teste
    test_data = {
        'numero_bem': 'TESTE001',
        'localizacao': 'Sala de Teste AJAX'
    }
    
    print("📨 Enviando requisição AJAX...")
    print(f"   URL: {url}")
    print(f"   Dados: {test_data}")
    
    try:
        # Fazer requisição POST com header AJAX
        response = requests.post(
            url,
            data=test_data,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        print(f"📨 Resposta recebida:")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Não informado')}")
        
        # Verificar se é JSON
        if 'application/json' in response.headers.get('content-type', ''):
            try:
                data = response.json()
                print(f"   ✅ Resposta JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if data.get('success'):
                    print("🎉 AJAX funcionando corretamente!")
                    print("   O sistema deve limpar o campo automaticamente")
                else:
                    print("⚠️  AJAX respondeu mas com erro")
                    
            except json.JSONDecodeError:
                print("❌ Resposta não é JSON válido")
                print(f"   Conteúdo: {response.text[:200]}...")
        else:
            print("❌ Resposta não é JSON (método tradicional)")
            print(f"   Conteúdo: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == '__main__':
    testar_fluxo_ajax()