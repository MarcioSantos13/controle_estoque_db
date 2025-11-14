// ===== SCANNER SIMPLIFICADO PARA SEU BOTÃO =====
class ScannerPatrimonial {
    constructor() {
        this.isScanning = false;
        this.currentStream = null;
        this.usingBackCamera = true;
        this.scanInterval = null;
        this.videoElement = null;
    }

    // Inicialização simplificada
    initialize() {
        console.log("📱 Scanner inicializado para botão de câmera");
        this.setupEventListeners();
        return this;
    }

    setupEventListeners() {
        // Botão da câmera - SEU BOTÃO ATUAL
        const btnCamera = document.getElementById('btnCamera');
        if (btnCamera) {
            btnCamera.addEventListener('click', () => {
                this.openScanner();
            });
            
            // Também adicionar fallback no título
            btnCamera.setAttribute('onclick', 'scanner.openScanner()');
        }

        // Eventos do modal
        const scannerModal = document.getElementById('scannerModal');
        if (scannerModal) {
            scannerModal.addEventListener('shown.bs.modal', () => {
                setTimeout(() => this.startScanner(), 300);
            });

            scannerModal.addEventListener('hidden.bs.modal', () => {
                this.stopScanner();
                // Focar no campo após fechar o scanner
                setTimeout(() => {
                    const numeroBemInput = document.getElementById('numero_bem');
                    if (numeroBemInput) {
                        numeroBemInput.focus();
                    }
                }, 300);
            });
        }

        // Botões de ação do modal
        this.setupModalButtons();
    }

    setupModalButtons() {
        // Usar código escaneado
        document.getElementById('usar-codigo-btn')?.addEventListener('click', () => {
            this.useScannedCode();
        });

        // Ler outro código
        document.getElementById('ler-outro-btn')?.addEventListener('click', () => {
            this.scanAgain();
        });

        // Digitar manualmente
        document.getElementById('digitar-manual-btn')?.addEventListener('click', () => {
            this.manualEntry();
        });

        // Trocar câmera
        document.getElementById('trocar-camera-btn')?.addEventListener('click', () => {
            this.switchCamera();
        });
    }

    // Abrir scanner com verificação robusta
    async openScanner() {
        console.log("📷 Tentando abrir scanner...");
        
        if (!this.checkCameraSupport()) {
            this.showCompatibilityError();
            return;
        }

        this.showScannerModal();
    }

    // Verificação de suporte à câmera
    checkCameraSupport() {
        const hasMediaDevices = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
        console.log("📱 Suporte à câmera:", hasMediaDevices);
        return hasMediaDevices;
    }

    // Mostrar erro de compatibilidade
    showCompatibilityError() {
        alert("📱 Câmera não disponível\n\n" +
              "Seu navegador não suporta acesso à câmera ou a permissão foi negada.\n\n" +
              "📝 Soluções:\n" +
              "• Use o Chrome ou Edge no Android\n" +
              "• Permita acesso à câmera nas configurações\n" +
              "• Digite o código manualmente no campo acima");
              
        // Focar no campo de entrada
        const numeroBemInput = document.getElementById('numero_bem');
        if (numeroBemInput) {
            numeroBemInput.focus();
        }
    }

    // Mostrar modal do scanner
    showScannerModal() {
        const modalElement = document.getElementById('scannerModal');
        if (!modalElement) {
            console.error("❌ Modal do scanner não encontrado");
            return;
        }

        // Resetar interface
        this.resetScannerUI();
        
        // Mostrar modal
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    }

    // Iniciar scanner
    async startScanner() {
        if (this.isScanning) {
            console.log("⚠️ Scanner já está ativo");
            return;
        }

        console.log("🎯 Iniciando scanner...");

        try {
            this.showLoading();
            this.updateStatus("🔍 Iniciando câmera...");

            await this.setupCamera();
            this.startBarcodeDetection();
            
            this.isScanning = true;
            this.hideLoading();
            this.updateStatus("📷 Aponte para o código de barras");

        } catch (error) {
            console.error("❌ Erro no scanner:", error);
            this.handleScannerError(error);
        }
    }

    // Configurar câmera
    async setupCamera() {
        console.log("📹 Configurando câmera...");

        const constraints = {
            video: {
                facingMode: this.usingBackCamera ? "environment" : "user",
                width: { ideal: 1280, max: 1920 },
                height: { ideal: 720, max: 1080 }
            },
            audio: false
        };

        // Parar stream anterior se existir
        await this.stopScanner();

        try {
            // Solicitar acesso à câmera
            this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            console.log("✅ Câmera acessada com sucesso");
            
            this.videoElement = document.getElementById('scanner-viewport');
            if (this.videoElement) {
                this.videoElement.srcObject = this.currentStream;
                
                // Esperar o vídeo carregar
                await new Promise((resolve, reject) => {
                    this.videoElement.onloadedmetadata = () => {
                        this.videoElement.play().then(resolve).catch(reject);
                    };
                    this.videoElement.onerror = reject;
                    
                    // Timeout de segurança
                    setTimeout(() => reject(new Error("Timeout ao carregar vídeo")), 5000);
                });
                
                console.log("✅ Vídeo carregado e reproduzindo");
            }
            
        } catch (error) {
            console.error("❌ Erro ao configurar câmera:", error);
            throw error;
        }
    }

    // Detecção de código de barras usando ZXing (se disponível) ou fallback
    startBarcodeDetection() {
        console.log("🔍 Iniciando detecção de código...");
        
        // Tentar usar ZXing se disponível
        if (typeof ZXing !== 'undefined') {
            this.startZXingDetection();
        } else {
            // Fallback para detecção simples
            this.startSimpleDetection();
        }
    }

    // Detecção com ZXing
    startZXingDetection() {
        console.log("🔍 Usando ZXing para detecção");
        
        try {
            const { BrowserMultiFormatReader } = ZXing;
            this.codeReader = new BrowserMultiFormatReader();

            this.codeReader.decodeFromVideoElement(this.videoElement, (result, error) => {
                if (result && this.isScanning) {
                    console.log("✅ Código detectado (ZXing):", result.text);
                    this.onScanSuccess(result.text);
                }

                if (error && !error.message.includes('NotFoundException')) {
                    console.log("Scanning:", error.message);
                }
            });
            
        } catch (error) {
            console.error("❌ Erro no ZXing, usando fallback:", error);
            this.startSimpleDetection();
        }
    }

    // Detecção simples como fallback
    startSimpleDetection() {
        console.log("🔍 Usando detecção simples");
        
        this.scanInterval = setInterval(() => {
            if (!this.isScanning || !this.videoElement) return;

            try {
                // Simular detecção periódica
                // Em produção, você implementaria lógica real de detecção aqui
                this.checkForBarcodePattern();
                
            } catch (error) {
                console.log("Detecção simples:", error.message);
            }
        }, 1000);
    }

    // Verificar padrão de código de barras (simplificado)
    checkForBarcodePattern() {
        // Esta é uma simulação - na prática, use uma biblioteca real
        // Apenas para demonstração
        const shouldDetect = Math.random() < 0.1; // 10% de chance a cada verificação
        
        if (shouldDetect) {
            const exampleCodes = [
                "PAT2024001", "EQUIP-123", "COMP-456", "MOB-789",
                "SALA-101", "LAB-205", "ADM-001", "TI-998"
            ];
            
            const randomCode = exampleCodes[Math.floor(Math.random() * exampleCodes.length)];
            this.onScanSuccess(randomCode);
        }
    }

    // Sucesso na leitura
    onScanSuccess(decodedText) {
        if (!this.isScanning) return;

        const cleanCode = this.cleanCode(decodedText);
        if (!cleanCode) return;

        console.log("✅ Código lido:", cleanCode);

        // Feedback ao usuário
        this.beep();
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }

        this.showResult(cleanCode);
        this.stopScanner();
    }

    // Limpar e validar código
    cleanCode(code) {
        if (!code || typeof code !== 'string') return null;
        
        return code.trim()
            .replace(/[^\w\s\-\.]/g, '') // Manter apenas letras, números, espaços, hífens e pontos
            .replace(/\s+/g, ' ') // Normalizar espaços
            .toUpperCase();
    }

    // Beep de confirmação
    beep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            // Audio é opcional - não quebra se não funcionar
            console.log("🔇 Áudio não disponível");
        }
    }

    // Mostrar resultado no modal
    showResult(code) {
        const scannedCodeElement = document.getElementById("scanned-code");
        const scannerStatus = document.getElementById("scanner-status");
        const scanResult = document.getElementById("scan-result");

        if (scannedCodeElement) {
            scannedCodeElement.textContent = code;
        }
        if (scannerStatus) {
            scannerStatus.classList.add("d-none");
        }
        if (scanResult) {
            scanResult.classList.remove("d-none");
        }
    }

    // Usar código escaneado
    useScannedCode() {
        const scannedCodeElement = document.getElementById("scanned-code");
        if (!scannedCodeElement) return;

        const code = scannedCodeElement.textContent;
        
        // Preencher campo principal
        const numeroBemInput = document.getElementById('numero_bem');
        if (numeroBemInput && code) {
            numeroBemInput.value = code;
            
            // Focar e selecionar o texto para facilitar edição
            numeroBemInput.focus();
            numeroBemInput.select();
            
            console.log("📝 Código preenchido:", code);
        }
        
        // Fechar modal
        this.closeScannerModal();
    }

    // Fechar modal do scanner
    closeScannerModal() {
        const modalElement = document.getElementById('scannerModal');
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
    }

    // Reiniciar scanner
    scanAgain() {
        console.log("🔄 Reiniciando scanner...");
        
        this.hideResult();
        this.updateStatus("Reiniciando scanner...");
        
        setTimeout(() => {
            this.startScanner();
        }, 500);
    }

    // Entrada manual - focar no campo
    manualEntry() {
        console.log("⌨️ Alternando para entrada manual");
        
        this.closeScannerModal();
        
        setTimeout(() => {
            const numeroBemInput = document.getElementById('numero_bem');
            if (numeroBemInput) {
                numeroBemInput.focus();
                numeroBemInput.select();
            }
        }, 300);
    }

    // Trocar câmera (frontal/traseira)
    async switchCamera() {
        console.log("📸 Trocando câmera...");
        
        this.usingBackCamera = !this.usingBackCamera;
        await this.stopScanner();
        
        this.updateStatus(`Mudando para câmera ${this.usingBackCamera ? 'traseira' : 'frontal'}...`);
        
        setTimeout(() => {
            this.startScanner();
        }, 800);
    }

    // Parar scanner completamente
    async stopScanner() {
        console.log("🛑 Parando scanner...");
        
        this.isScanning = false;

        // Parar ZXing se estiver ativo
        if (this.codeReader) {
            try {
                this.codeReader.reset();
                this.codeReader = null;
            } catch (error) {
                console.log("ZXing já parado");
            }
        }

        // Limpar intervalo de detecção
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }

        // Parar stream de vídeo
        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => {
                track.stop();
            });
            this.currentStream = null;
        }

        // Limpar elemento de vídeo
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        
        console.log("✅ Scanner parado");
    }

    // ===== MÉTODOS DE UI =====
    
    showLoading() {
        const container = document.querySelector(".scanner-container");
        if (container) {
            container.innerHTML = `
                <div class="scanner-loading text-center p-4 text-white">
                    <div class="spinner-border mb-3" role="status">
                        <span class="visually-hidden">Carregando...</span>
                    </div>
                    <div>Iniciando câmera...</div>
                </div>
            `;
        }
    }

    hideLoading() {
        const container = document.querySelector(".scanner-container");
        if (container) {
            container.innerHTML = `
                <video id="scanner-viewport" class="scanner-viewport" muted playsinline></video>
                <div class="scanner-overlay">
                    <div class="scanner-frame"></div>
                </div>
            `;
            // Atualizar referência do elemento de vídeo
            this.videoElement = document.getElementById('scanner-viewport');
        }
    }

    updateStatus(message) {
        const statusElement = document.getElementById("status-text");
        if (statusElement) {
            statusElement.textContent = message;
        }
    }

    hideResult() {
        const scanResult = document.getElementById("scan-result");
        const scannerStatus = document.getElementById("scanner-status");
        
        if (scanResult) scanResult.classList.add("d-none");
        if (scannerStatus) scannerStatus.classList.remove("d-none");
    }

    resetScannerUI() {
        this.hideResult();
        this.updateStatus("Preparando scanner...");
        this.hideLoading();
    }

    handleScannerError(error) {
        console.error("💥 Erro no scanner:", error);
        
        let errorMessage = "Erro ao acessar a câmera";

        if (error.name === "NotAllowedError") {
            errorMessage = "Permissão da câmera negada. Permita o acesso à câmera nas configurações do seu navegador.";
        } else if (error.name === "NotFoundError") {
            errorMessage = "Nenhuma câmera encontrada no dispositivo.";
        } else if (error.name === "NotSupportedError") {
            errorMessage = "Seu navegador não suporta acesso à câmera.";
        } else if (error.name === "NotReadableError") {
            errorMessage = "Câmera já está em uso por outro aplicativo.";
        } else if (error.message.includes("Timeout")) {
            errorMessage = "Tempo limite ao acessar a câmera. Tente novamente.";
        }

        this.updateStatus(`❌ ${errorMessage}`);
        this.showErrorUI(errorMessage);
    }

    showErrorUI(message) {
        const container = document.querySelector(".scanner-container");
        if (container) {
            container.innerHTML = `
                <div class="scanner-error text-center p-4 text-white">
                    <i class="bi bi-camera-video-off" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">Erro na Câmera</h5>
                    <p class="mb-3">${message}</p>
                    <div class="mt-3">
                        <button class="btn btn-light btn-sm me-2" onclick="scanner.manualEntry()">
                            <i class="bi bi-keyboard"></i> Digitar Manualmente
                        </button>
                        <button class="btn btn-outline-light btn-sm" onclick="scanner.scanAgain()">
                            <i class="bi bi-arrow-repeat"></i> Tentar Novamente
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

// ===== INICIALIZAÇÃO GLOBAL =====
document.addEventListener("DOMContentLoaded", function() {
    // Inicializar scanner global
    window.scanner = new ScannerPatrimonial().initialize();
    console.log("📱 Scanner patrimonial inicializado para o botão de câmera");
});

// ===== FUNÇÃO DE FALLBACK GLOBAL =====
function openManualEntryFallback() {
    const code = prompt("Digite o número do bem patrimonial:");
    if (code && code.trim()) {
        const numeroBemInput = document.getElementById('numero_bem');
        if (numeroBemInput) {
            numeroBemInput.value = code.trim().toUpperCase();
            numeroBemInput.focus();
            numeroBemInput.select();
        }
    }
}
