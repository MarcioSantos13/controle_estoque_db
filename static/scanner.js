// scanner.js - VERSÃO MINIMALISTA
// Apenas transfere texto para o campo ao clicar na câmera
// scanner.js - AGORA NA PASTA JS/
console.log("🎯 SCANNER.JS CARREGADO DA PASTA JS/ - CAMINHO CORRETO!");

// Resto do código continua igual...
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 Scanner da pasta js/ inicializado!");
    
    const btnCamera = document.getElementById('btnCamera');
    if (btnCamera) {
        btnCamera.addEventListener('click', function(e) {
            e.preventDefault();
            console.log("📸 Botão clicado - Scanner da pasta js/!");
            
            const codigo = prompt("DIGITE O NÚMERO DO PATRIMÔNIO:");
            if (codigo) {
                const input = document.getElementById('numero_bem');
                if (input) {
                    input.value = codigo.trim().toUpperCase();
                    input.focus();
                    console.log("✅ Código transferido:", input.value);
                }
            }
        });
        
        console.log("✅ Scanner configurado da pasta js/!");
    }
});




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

// scanner.js - COM DIAGNÓSTICO
console.log("🔍 SCANNER.JS CARREGADO - Arquivo correto!");

// Função super simples de diagnóstico
function diagnosticarScanner() {
    console.log("🎯 DIAGNÓSTICO INICIADO");
    
    // Verificar se o botão existe
    const btnCamera = document.getElementById('btnCamera');
    console.log("📷 Botão da câmera encontrado:", !!btnCamera);
    
    // Verificar se o campo de texto existe
    const inputNumero = document.getElementById('numero_bem');
    console.log("🔤 Campo número_bem encontrado:", !!inputNumero);
    
    // Verificar versão do arquivo
    console.log("🆕 Versão: Scanner Minimalista v2.0");
    
    return {
        botao: !!btnCamera,
        campo: !!inputNumero,
        versao: "Scanner Minimalista v2.0"
    };
}

// Scanner minimalista
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 DOM Carregado - Iniciando scanner...");
    
    const diagnostico = diagnosticarScanner();
    console.log("📊 Diagnóstico completo:", diagnostico);
    
    const btnCamera = document.getElementById('btnCamera');
    if (btnCamera) {
        // Remover eventos antigos
        const novoBotao = btnCamera.cloneNode(true);
        btnCamera.parentNode.replaceChild(novoBotao, btnCamera);
        
        // Novo evento simples
        document.getElementById('btnCamera').addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log("📸 Botão clicado - Scanner acionado!");
            
            // Scanner super simples
            const codigo = prompt("🎯 DIGITE O NÚMERO DO PATRIMÔNIO:");
            if (codigo && codigo.trim()) {
                const input = document.getElementById('numero_bem');
                if (input) {
                    input.value = codigo.trim().toUpperCase();
                    input.focus();
                    console.log("✅ Código inserido:", codigo);
                }
            }
        });
        
        console.log("✅ Scanner configurado com sucesso!");
    } else {
        console.log("❌ ERRO: Botão não encontrado após DOM carregado");
    }
});

// Mensagem final
console.log("🏁 scanner.js carregado completamente");
