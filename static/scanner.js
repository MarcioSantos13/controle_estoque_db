// ===== SISTEMA DE SCANNER OTIMIZADO PARA CELULAR =====
class ScannerPatrimonial {
    constructor() {
        this.codeReader = null;
        this.isScanning = false;
        this.scannerModal = null;
        this.currentStream = null;
        this.usingBackCamera = true;
        this.videoElement = null;
        this.scanCallback = null;
    }

    // Inicializar o scanner
    initialize(scanCallback = null) {
        console.log("📱 Inicializando Scanner Patrimonial");
        
        this.scanCallback = scanCallback;
        this.setupModal();
        this.setupEventListeners();
        
        return this;
    }

    // Configurar modal do scanner
    setupModal() {
        this.scannerModal = new bootstrap.Modal(document.getElementById('scannerModal'));
        
        // Eventos do modal
        document.getElementById('scannerModal').addEventListener('shown.bs.modal', () => {
            setTimeout(() => this.startScanner(), 300);
        });

        document.getElementById('scannerModal').addEventListener('hidden.bs.modal', () => {
            this.stopScanner();
        });
    }

    // Configurar event listeners
    setupEventListeners() {
        // Botão da câmera na página principal
        document.getElementById('btnCamera')?.addEventListener('click', () => {
            this.openScanner();
        });

        // Botões do modal do scanner
        document.getElementById('usar-codigo-btn')?.addEventListener('click', () => this.useScannedCode());
        document.getElementById('ler-outro-btn')?.addEventListener('click', () => this.scanAgain());
        document.getElementById('digitar-manual-btn')?.addEventListener('click', () => this.manualEntry());
        document.getElementById('trocar-camera-btn')?.addEventListener('click', () => this.switchCamera());
    }

    // Abrir scanner
    openScanner() {
        if (!this.checkCameraCompatibility()) {
            this.showCompatibilityError();
            return;
        }
        
        this.resetScannerUI();
        this.scannerModal.show();
    }

    // Verificar compatibilidade da câmera
    checkCameraCompatibility() {
        return !!(navigator.mediaDevices && 
                 navigator.mediaDevices.getUserMedia &&
                 (window.BarcodeDetector || typeof ZXing !== 'undefined'));
    }

    // Mostrar erro de compatibilidade
    showCompatibilityError() {
        alert("📱 Seu navegador não suporta leitura de código de barras pela câmera.\n\n" +
              "📝 Você pode:\n" +
              "• Usar um aplicativo dedicado de scanner\n" +
              "• Digitar o código manualmente\n" +
              "• Tentar em outro navegador (Chrome recomendado)");
    }

    // Iniciar scanner
    async startScanner() {
        if (this.isScanning) return;
        
        this.showLoading();
        this.updateStatus("🔍 Iniciando câmera...");

        try {
            // Tentar API nativa do navegador primeiro (mais rápida)
            if (window.BarcodeDetector) {
                await this.tryNativeBarcodeDetector();
            } else if (typeof ZXing !== 'undefined') {
                await this.tryZXingScanner();
            } else {
                throw new Error("Nenhuma biblioteca de scanner disponível");
            }
            
            this.isScanning = true;
            this.hideLoading();
            
        } catch (error) {
            console.error("❌ Erro no scanner:", error);
            this.handleScannerError(error);
        }
    }

    // Tentar API nativa do navegador (Chrome/Edge)
    async tryNativeBarcodeDetector() {
        if (!window.BarcodeDetector) {
            throw new Error("BarcodeDetector não suportado");
        }

        const barcodeDetector = new BarcodeDetector({
            formats: ['code_128', 'ean_13', 'ean_8', 'code_39', 'upc_a']
        });

        this.updateStatus("📱 Usando scanner nativo...");

        await this.setupCamera();
        
        const detectBarcode = async () => {
            if (!this.isScanning) return;
            
            try {
                const barcodes = await barcodeDetector.detect(this.videoElement);
                
                if (barcodes.length > 0) {
                    const code = barcodes[0].rawValue;
                    console.log("✅ Código detectado (nativo):", code);
                    this.onScanSuccess(code);
                    return;
                }
            } catch (error) {
                console.log("Detecção:", error.message);
            }
            
            requestAnimationFrame(detectBarcode);
        };

        detectBarcode();
    }

    // Tentar ZXing (fallback)
    async tryZXingScanner() {
        if (typeof ZXing === 'undefined') {
            throw new Error("ZXing não carregado");
        }

        const { BrowserMultiFormatReader } = ZXing;
        this.codeReader = new BrowserMultiFormatReader();

        this.updateStatus("📦 Aponte para o código de barras");

        await this.setupCamera();

        this.codeReader.decodeFromVideoElement(this.videoElement, (result, error) => {
            if (result) {
                console.log("✅ Código detectado (ZXing):", result.text);
                this.onScanSuccess(result.text);
            }

            if (error && !error.message.includes('NotFoundException')) {
                console.log("Scanning:", error.message);
            }
        });
    }

    // Configurar câmera
    async setupCamera() {
        const constraints = {
            video: {
                facingMode: this.usingBackCamera ? "environment" : "user",
                width: { min: 320, ideal: 1280, max: 1920 },
                height: { min: 240, ideal: 720, max: 1080 },
                aspectRatio: { ideal: 1.333 }
            },
            audio: false
        };

        this.videoElement = document.getElementById('scanner-viewport');
        if (!this.videoElement) {
            throw new Error("Elemento de vídeo não encontrado");
        }

        this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
        this.videoElement.srcObject = this.currentStream;

        await new Promise((resolve) => {
            this.videoElement.onloadedmetadata = () => {
                this.videoElement.play();
                resolve();
            };
        });
    }

    // Sucesso na leitura
    onScanSuccess(decodedText) {
        const cleanCode = this.cleanCode(decodedText);
        if (!cleanCode) return;

        this.beep();
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);

        this.showResult(cleanCode);
        this.stopScanner();
    }

    // Limpar código lido
    cleanCode(code) {
        return code.trim()
            .replace(/[^\w\-\s]/g, '')
            .replace(/\s+/g, ' ')
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
            // Audio opcional - não quebra se não funcionar
        }
    }

    // Mostrar resultado
    showResult(code) {
        document.getElementById("scanned-code").textContent = code;
        document.getElementById("scanner-status").classList.add("d-none");
        document.getElementById("scan-result").classList.remove("d-none");
    }

    // Usar código escaneado
    useScannedCode() {
        const code = document.getElementById("scanned-code").textContent;
        
        if (this.scanCallback && typeof this.scanCallback === 'function') {
            this.scanCallback(code);
        } else {
            // Fallback: preencher campo padrão
            const numeroBemInput = document.getElementById('numero_bem');
            if (numeroBemInput && code) {
                numeroBemInput.value = code;
            }
        }
        
        this.scannerModal.hide();
    }

    // Parar scanner
    async stopScanner() {
        this.isScanning = false;

        if (this.codeReader) {
            try {
                this.codeReader.reset();
                this.codeReader = null;
            } catch (error) {
                console.warn("Scanner já parado");
            }
        }

        if (this.currentStream) {
            this.currentStream.getTracks().forEach(track => track.stop());
            this.currentStream = null;
        }

        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    }

    // Reiniciar scanner
    scanAgain() {
        this.hideResult();
        this.updateStatus("🔄 Reiniciando scanner...");
        setTimeout(() => this.startScanner(), 500);
    }

    // Entrada manual
    manualEntry() {
        this.scannerModal.hide();
        setTimeout(() => {
            const numeroBemInput = document.getElementById('numero_bem');
            if (numeroBemInput) {
                numeroBemInput.focus();
            }
        }, 300);
    }

    // Trocar câmera
    async switchCamera() {
        this.usingBackCamera = !this.usingBackCamera;
        await this.stopScanner();
        setTimeout(() => this.startScanner(), 500);
    }

    // UI helpers
    showLoading() {
        const scannerContainer = document.querySelector(".scanner-container");
        if (scannerContainer) {
            scannerContainer.innerHTML = `
                <div class="scanner-loading text-center p-4">
                    <i class="bi bi-camera" style="font-size: 3rem;"></i>
                    <div class="mt-2">Iniciando câmera...</div>
                </div>
            `;
        }
    }

    hideLoading() {
        const scannerContainer = document.querySelector(".scanner-container");
        if (scannerContainer) {
            scannerContainer.innerHTML = `
                <video id="scanner-viewport" class="scanner-viewport" muted playsinline></video>
                <div class="scanner-overlay">
                    <div class="scanner-frame"></div>
                </div>
            `;
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
        document.getElementById("scan-result")?.classList.add("d-none");
        document.getElementById("scanner-status")?.classList.remove("d-none");
    }

    resetScannerUI() {
        this.hideResult();
        this.updateStatus("Preparando scanner...");
    }

    handleScannerError(error) {
        let errorMessage = "Erro na câmera";

        if (error.name === "NotAllowedError") {
            errorMessage = "Permissão da câmera negada. Permita o acesso nas configurações do navegador.";
        } else if (error.name === "NotFoundError") {
            errorMessage = "Nenhuma câmera encontrada.";
        } else if (error.name === "NotSupportedError") {
            errorMessage = "Navegador não suporta acesso à câmera.";
        } else if (error.name === "NotReadableError") {
            errorMessage = "Câmera já está em uso.";
        }

        this.updateStatus(`❌ ${errorMessage}`);
        this.showErrorUI(errorMessage);
    }

    showErrorUI(message) {
        const scannerContainer = document.querySelector(".scanner-container");
        if (scannerContainer) {
            scannerContainer.innerHTML = `
                <div class="scanner-error text-center p-4 text-white">
                    <i class="bi bi-camera-video-off" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">${message}</h5>
                    <div class="mt-3">
                        <button class="btn btn-light btn-sm me-2" onclick="window.scanner.manualEntry()">
                            <i class="bi bi-keyboard"></i> Digitar
                        </button>
                        <button class="btn btn-outline-light btn-sm" onclick="window.scanner.scanAgain()">
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
    // Inicializar scanner com callback personalizado
    window.scanner = new ScannerPatrimonial().initialize(function(scannedCode) {
        // Callback quando código é escaneado
        const numeroBemInput = document.getElementById('numero_bem');
        if (numeroBemInput) {
            numeroBemInput.value = scannedCode;
            numeroBemInput.focus();
        }
    });
    
    console.log("📱 Scanner patrimonial inicializado");
});