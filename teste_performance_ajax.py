#!/usr/bin/env python3
"""
Teste de performance do AJAX
"""
import requests
import time

def teste_performance_ajax():
    print("⚡ TESTE DE PERFORMANCE DO AJAX")
    print("=" * 50)
    
    url = "http://localhost/"
    
    # Testar velocidade de resposta
    tempos = []
    
    for i in range(3):
        codigo = f"PERF-{i+1:03d}"
        
        inicio = time.time()
        
        try:
            response = requests.post(
                url,
                data={'numero_bem': codigo, 'localizacao': 'Teste Performance'},
                headers={'X-Requested-With': 'XMLHttpRequest'},
                timeout=5
            )
            
            fim = time.time()
            tempo_resposta = (fim - inicio) * 1000  # ms
            
            tempos.append(tempo_resposta)
            
            status = "✅" if response.headers.get('content-type', '').startswith('application/json') else "❌"
            
            print(f"{status} Teste {i+1}: {codigo} - {tempo_resposta:.1f}ms")
            
        except Exception as e:
            print(f"❌ Teste {i+1}: Erro - {e}")
    
    if tempos:
        media = sum(tempos) / len(tempos)
        print(f"\n📊 Estatísticas:")
        print(f"   🏎️  Tempo médio: {media:.1f}ms")
        print(f"   🚀 Mais rápido: {min(tempos):.1f}ms")
        print(f"   🐢 Mais lento: {max(tempos):.1f}ms")
        
        if media < 1000:
            print(f"   ✅ Performance EXCELENTE!")
        else:
            print(f"   ⚠️  Performance aceitável")

if __name__ == '__main__':
    teste_performance_ajax()