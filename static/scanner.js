// scanner.js - VERSÃO MINIMALISTA
// Apenas transfere texto para o campo ao clicar na câmera

class ScannerMinimal {
    constructor() {
        this.init();
    }
    
    init() {
        console.log("🎯 Scanner minimalista carregado");
        this.setupScannerButton();
    }
    
    setupScannerButton() {
        const btnCamera = document.getElementById('btnCamera');
        if (btnCamera) {
            // Remove qualquer evento anterior e adiciona o nosso
            btnCamera.replaceWith(btnCamera.cloneNode(true));
            const newBtn = document.getElementById('btnCamera');
            
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openScanner();
            });
            
            console.log("✅ Botão scanner configurado");
        } else {
            console.log("❌ Botão da câmera não encontrado");
        }
    }
    
    openScanner() {
        console.log("📷 Abrindo scanner...");
        
        // Método super simples: prompt do navegador
        const codigo = prompt("🔢 DIGITE O NÚMERO DO PATRIMÔNIO:\n\nExemplo: PAT-001, COMP-123, SALA-101");
        
        if (codigo && codigo.trim()) {
            this.transferToInput(codigo);
            return true;
        }
        
        return false;
    }
    
    transferToInput(codigo) {
        const input = document.getElementById('numero_bem');
        if (input) {
            // Limpa e formata o código
            const codigoLimpo = codigo.trim().toUpperCase();
            
            // Transfere para o campo
            input.value = codigoLimpo;
            input.focus();
            
            // Feedback visual opcional
            this.showSuccessFeedback(input);
            
            console.log("✅ Código transferido:", codigoLimpo);
        }
    }
    
    showSuccessFeedback(input) {
        // Efeito visual simples de confirmação
        const originalBorder = input.style.border;
        const originalBackground = input.style.backgroundColor;
        
        input.style.border = '2px solid #28a745';
        input.style.backgroundColor = '#f8fff9';
        
        setTimeout(() => {
            input.style.border = originalBorder;
            input.style.backgroundColor = originalBackground;
        }, 1000);
    }
}

// Inicialização automática quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    window.scanner = new ScannerMinimal();
});