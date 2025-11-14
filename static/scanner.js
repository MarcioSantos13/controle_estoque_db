// scanner.js - VERSÃO SUPER SIMPLES SEM CÂMERA
console.log("🎯 SCANNER SIMPLES CARREGADO - SEM CÂMERA");

class ScannerSimples {
    constructor() {
        this.init();
    }
    
    init() {
        console.log("🔧 Iniciando scanner simples...");
        this.configurarBotao();
    }
    
    configurarBotao() {
        const btnCamera = document.getElementById('btnCamera');
        
        if (btnCamera) {
            console.log("📷 Botão encontrado, configurando...");
            
            // Remove eventos antigos
            const novoBotao = btnCamera.cloneNode(true);
            btnCamera.parentNode.replaceChild(novoBotao, btnCamera);
            
            // Adiciona evento simples
            document.getElementById('btnCamera').addEventListener('click', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                
                console.log("🎯 Botão clicado - Abrindo prompt...");
                this.abrirScannerSimples();
            });
            
            console.log("✅ Scanner simples configurado!");
        } else {
            console.log("❌ Botão não encontrado");
        }
    }
    
    abrirScannerSimples() {
        // Método 100% funcional - usa prompt do navegador
        const codigo = prompt("🔢 DIGITE O NÚMERO DO PATRIMÔNIO:\n\nExemplos:\n• PAT-001\n• COMP-123\n• SALA-101");
        
        if (codigo && codigo.trim()) {
            this.inserirNoCampo(codigo);
            return true;
        }
        
        return false;
    }
    
    inserirNoCampo(codigo) {
        const input = document.getElementById('numero_bem');
        
        if (input) {
            // Limpa e formata o código
            const codigoLimpo = codigo.trim().toUpperCase();
            
            // Insere no campo
            input.value = codigoLimpo;
            input.focus();
            
            // Feedback visual
            this.mostrarConfirmacao(input);
            
            console.log("✅ Código inserido:", codigoLimpo);
        }
    }
    
    mostrarConfirmacao(input) {
        // Efeito visual de confirmação
        input.style.border = '2px solid #28a745';
        input.style.backgroundColor = '#f8fff9';
        
        setTimeout(() => {
            input.style.border = '';
            input.style.backgroundColor = '';
        }, 1500);
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 DOM Carregado - Iniciando scanner simples");
    window.scannerSimples = new ScannerSimples();
});

console.log("🏁 Scanner simples carregado com sucesso!");