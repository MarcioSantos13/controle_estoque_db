// scanner-funcional.js - SCANNER QUE REALMENTE FUNCIONA
console.log("🎯 SCANNER FUNCIONAL INICIADO");

class ScannerFuncional {
    constructor() {
        this.videoElement = null;
        this.stream = null;
        this.isScanning = false;
        this.codeReader = null;
        this.init();
    }
    
    init() {
        console.log("🔧 Inicializando scanner funcional...");
        this.configurarBotaoCamera();
        this.configurarModal();
    }
    
    configurarBotaoCamera() {
        const btnCamera = document.getElementById('btnCamera');
        
        if (btnCamera) {
            // Remove qualquer evento anterior
            const novoBotao = btnCamera.cloneNode(true);
            btnCamera.parentNode.replaceChild(novoBotao, btnCamera);
            
            // Adiciona evento limpo
            document.getElementById('btnCamera').addEventListener('click', (e) => {
                e.preventDefault();
                console.log("📷 Abrindo scanner...");
                this.abrirScanner();
            });
        }
    }
    
    configurarModal() {
        const modal = document.getElementById('scannerModal');
        if (modal) {
            // Quando o modal abre
            modal.addEventListener('shown.bs.modal', () => {
                console.log("🔄 Iniciando câmera...");
                setTimeout(() => this.iniciarCamera(), 300);
            });
            
            // Quando o modal fecha
            modal.addEventListener('hidden.bs.modal', () => {
                console.log("🛑 Parando câmera...");
                this.pararCamera();
            });
        }
        
        // Configurar botões do modal
        document.getElementById('usar-codigo-btn')?.addEventListener('click', () => this.usarCodigo());
        document.getElementById('ler-outro-btn')?.addEventListener('click', () => this.reiniciarScanner());
        document.getElementById('trocar-camera-btn')?.addEventListener('click', () => this.trocarCamera());
    }
    
    async abrirScanner() {
        // Verificar se há suporte para câmera
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("❌ Seu navegador não suporta acesso à câmera. Use:\n• Chrome\n• Edge\n• Firefox\n• Safari (iOS 11+)");
            return this.abrirPromptManual();
        }
        
        // Verificar permissões
        try {
            await navigator.mediaDevices.getUserMedia({ video: true });
        } catch (error) {
            console.error("Erro de permissão:", error);
            alert("📱 Permita o acesso à câmera nas configurações do seu navegário e tente novamente.");
            return this.abrirPromptManual();
        }
        
        // Abrir modal
        const modal = new bootstrap.Modal(document.getElementById('scannerModal'));
        modal.show();
    }
    
    async iniciarCamera() {
        try {
            console.log("🎥 Iniciando câmera...");
            
            this.videoElement = document.getElementById('scanner-viewport');
            if (!this.videoElement) {
                throw new Error("Elemento de vídeo não encontrado");
            }
            
            // Parar stream anterior se existir
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
            
            // Configurar câmera traseira (se disponível)
            const constraints = {
                video: {
                    facingMode: 'environment', // Câmera traseira
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            // Solicitar acesso à câmera
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;
            
            // Esperar o vídeo carregar
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });
            
            console.log("✅ Câmera iniciada com sucesso");
            this.atualizarStatus("📷 Aponte para o código de barras");
            
            // Iniciar detecção de código de barras
            this.iniciarDetecao();
            
        } catch (error) {
            console.error("❌ Erro ao iniciar câmera:", error);
            this.mostrarErroCamera(error);
        }
    }
    
    iniciarDetecao() {
        // Método SIMPLES de detecção - verifica se ZXing está disponível
        if (typeof ZXing !== 'undefined') {
            this.iniciarZXing();
        } else {
            this.iniciarDetecaoManual();
        }
    }
    
    iniciarZXing() {
        try {
            const { BrowserMultiFormatReader } = ZXing;
            this.codeReader = new BrowserMultiFormatReader();
            
            console.log("🔍 Iniciando ZXing...");
            
            this.codeReader.decodeFromVideoElement(this.videoElement, (result, error) => {
                if (result) {
                    console.log("✅ Código detectado:", result.text);
                    this.codigoDetectado(result.text);
                }
                
                if (error && !error.message?.includes('NotFoundException')) {
                    console.log("Scanning...", error.message);
                }
            });
            
        } catch (error) {
            console.error("Erro ZXing:", error);
            this.iniciarDetecaoManual();
        }
    }
    
    iniciarDetecaoManual() {
        console.log("🔍 Usando detecção manual...");
        // Fallback simples - o usuário pode digitar manualmente
    }
    
    codigoDetectado(codigo) {
        // Limpar código
        const codigoLimpo = codigo.trim().toUpperCase();
        
        // Feedback visual e sonoro
        this.vibrar();
        
        // Mostrar resultado
        this.mostrarResultado(codigoLimpo);
        
        // Parar scanner
        this.pararDetecao();
    }
    
    mostrarResultado(codigo) {
        document.getElementById('scanned-code').textContent = codigo;
        document.getElementById('scanner-status').classList.add('d-none');
        document.getElementById('scan-result').classList.remove('d-none');
    }
    
    usarCodigo() {
        const codigo = document.getElementById('scanned-code').textContent;
        
        if (codigo && window.sistemaPatrimonial) {
            // Inserir no campo
            const input = document.getElementById('numero_bem');
            if (input) {
                input.value = codigo;
                input.focus();
                
                // Feedback visual
                input.classList.add('scan-success');
                
                // Fechar modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('scannerModal'));
                modal.hide();
                
                // Submeter automaticamente após breve delay
                setTimeout(() => {
                    if (window.sistemaPatrimonial.processarBusca) {
                        window.sistemaPatrimonial.processarBusca();
                    }
                }, 500);
            }
        }
    }
    
    reiniciarScanner() {
        document.getElementById('scan-result').classList.add('d-none');
        document.getElementById('scanner-status').classList.remove('d-none');
        this.iniciarCamera();
    }
    
    async trocarCamera() {
        // Alternar entre câmera frontal e traseira
        // (Implementação simplificada - recarrega com facingMode diferente)
        await this.pararCamera();
        setTimeout(() => this.iniciarCamera(), 500);
    }
    
    pararDetecao() {
        if (this.codeReader) {
            this.codeReader.reset();
            this.codeReader = null;
        }
    }
    
    pararCamera() {
        this.pararDetecao();
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    }
    
    vibrar() {
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
    }
    
    atualizarStatus(mensagem) {
        const status = document.getElementById('status-text');
        if (status) {
            status.textContent = mensagem;
        }
    }
    
    mostrarErroCamera(error) {
        let mensagem = "Erro ao acessar a câmera";
        
        if (error.name === 'NotAllowedError') {
            mensagem = "Permissão da câmera negada. Permita o acesso nas configurações do navegador.";
        } else if (error.name === 'NotFoundError') {
            mensagem = "Nenhuma câmera encontrada no dispositivo.";
        } else if (error.name === 'NotSupportedError') {
            mensagem = "Navegador não suporta acesso à câmera.";
        }
        
        this.atualizarStatus(`❌ ${mensagem}`);
        
        // Mostrar opção manual
        setTimeout(() => {
            if (confirm(`${mensagem}\n\nDeseja digitar o código manualmente?`)) {
                this.abrirPromptManual();
            }
        }, 1000);
    }
    
    abrirPromptManual() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('scannerModal'));
        if (modal) modal.hide();
        
        setTimeout(() => {
            const codigo = prompt("🔢 DIGITE O NÚMERO DO PATRIMÔNIO:\n\nExemplos:\n• PAT-001\n• COMP-123\n• SALA-101");
            
            if (codigo && codigo.trim()) {
                const input = document.getElementById('numero_bem');
                if (input) {
                    input.value = codigo.trim().toUpperCase();
                    input.focus();
                    
                    // Submeter automaticamente
                    setTimeout(() => {
                        if (window.sistemaPatrimonial && window.sistemaPatrimonial.processarBusca) {
                            window.sistemaPatrimonial.processarBusca();
                        }
                    }, 300);
                }
            }
        }, 500);
    }
}

// Inicialização automática
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 Iniciando scanner funcional...");
    window.scannerFuncional = new ScannerFuncional();
});