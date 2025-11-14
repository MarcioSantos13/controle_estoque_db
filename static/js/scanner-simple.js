// ===== SCANNER SUPER SIMPLES E ROBUSTO =====
class SimpleScanner {
    constructor() {
        this.isScanning = false;
        this.stream = null;
    }

    init() {
        console.log("🎯 Scanner simples inicializado");
        this.setupScannerButton();
    }

    setupScannerButton() {
        const btnCamera = document.getElementById('btnCamera');
        if (btnCamera) {
            btnCamera.addEventListener('click', () => {
                this.openSimpleScanner();
            });
        }
    }

    async openSimpleScanner() {
        console.log("📱 Abrindo scanner simples...");
        
        // Verificar suporte básico
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError("Seu navegador não suporta acesso à câmera.");
            return;
        }

        try {
            await this.startCamera();
        } catch (error) {
            console.error("❌ Erro:", error);
            this.showError(this.getErrorMessage(error));
        }
    }

    async startCamera() {
        // Parar câmera anterior se estiver ativa
        if (this.stream) {
            this.stopCamera();
        }

        // Configuração mínima
        const constraints = {
            video: {
                facingMode: 'environment', // Priorizar câmera traseira
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };

        // Iniciar câmera
        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Mostrar modal com a câmera
        this.showCameraModal();
    }

    showCameraModal() {
        // Criar modal simples
        const modalHTML = `
            <div class="modal fade" id="simpleScannerModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-camera me-2"></i>Escanear Código
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-0">
                            <div class="camera-container">
                                <video id="simpleCameraView" autoplay playsinline muted class="w-100"></video>
                                <div class="scan-frame"></div>
                            </div>
                            <div class="p-3 bg-light border-top">
                                <p class="mb-2 text-center">
                                    <i class="bi bi-info-circle me-1"></i>
                                    Aponte a câmera para o código de barras
                                </p>
                                <div class="text-center">
                                    <button class="btn btn-success btn-sm me-2" onclick="simpleScanner.captureManualCode()">
                                        <i class="bi bi-keyboard me-1"></i>Digitar Código
                                    </button>
                                    <button class="btn btn-secondary btn-sm" onclick="simpleScanner.stopCamera()" data-bs-dismiss="modal">
                                        <i class="bi bi-x-circle me-1"></i>Fechar
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Adicionar modal ao body se não existir
        if (!document.getElementById('simpleScannerModal')) {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        // Configurar vídeo
        const video = document.getElementById('simpleCameraView');
        if (video && this.stream) {
            video.srcObject = this.stream;
        }

        // Mostrar modal
        const modal = new bootstrap.Modal(document.getElementById('simpleScannerModal'));
        modal.show();

        // Evento quando modal fechar
        document.getElementById('simpleScannerModal').addEventListener('hidden.bs.modal', () => {
            this.stopCamera();
        });

        this.isScanning = true;
    }

    stopCamera() {
        console.log("🛑 Parando câmera...");
        
        this.isScanning = false;

        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
            });
            this.stream = null;
        }

        const video = document.getElementById('simpleCameraView');
        if (video) {
            video.srcObject = null;
        }
    }

    captureManualCode() {
        this.stopCamera();
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('simpleScannerModal'));
        if (modal) {
            modal.hide();
        }

        // Pedir código manualmente
        setTimeout(() => {
            const code = prompt("Digite o número do patrimônio:");
            if (code && code.trim()) {
                const input = document.getElementById('numero_bem');
                if (input) {
                    input.value = code.trim().toUpperCase();
                    input.focus();
                }
            }
        }, 300);
    }

    getErrorMessage(error) {
        if (error.name === 'NotAllowedError') {
            return "Permissão da câmera negada. Por favor, permita o acesso à câmera nas configurações do seu navegador.";
        } else if (error.name === 'NotFoundError') {
            return "Nenhuma câmera encontrada no dispositivo.";
        } else if (error.name === 'NotSupportedError') {
            return "Seu navegador não suporta acesso à câmera.";
        } else {
            return "Erro ao acessar a câmera. Tente novamente.";
        }
    }

    showError(message) {
        alert(`❌ ${message}\n\n📝 Você pode digitar o código manualmente no campo "Número do Bem".`);
        
        // Focar no campo de entrada
        const input = document.getElementById('numero_bem');
        if (input) {
            input.focus();
        }
    }
}

// ===== SCANNER COM CÓDIGO DE BARRAS (OPCIONAL) =====
class BarcodeScanner extends SimpleScanner {
    async startCamera() {
        await super.startCamera();
        
        // Iniciar detecção de código de barras se ZXing estiver disponível
        if (typeof ZXing !== 'undefined') {
            this.startBarcodeDetection();
        }
    }

    startBarcodeDetection() {
        try {
            const { BrowserMultiFormatReader } = ZXing;
            this.codeReader = new BrowserMultiFormatReader();

            const video = document.getElementById('simpleCameraView');
            if (!video) return;

            this.codeReader.decodeFromVideoElement(video, (result, error) => {
                if (result && this.isScanning) {
                    console.log("✅ Código detectado:", result.text);
                    this.onBarcodeDetected(result.text);
                }
            });

        } catch (error) {
            console.log("⚠️ Detecção de código não disponível");
        }
    }

    onBarcodeDetected(code) {
        // Parar detecção
        if (this.codeReader) {
            this.codeReader.reset();
        }

        // Preencher campo
        const input = document.getElementById('numero_bem');
        if (input) {
            input.value = code.trim().toUpperCase();
            input.focus();
        }

        // Fechar modal
        this.stopCamera();
        const modal = bootstrap.Modal.getInstance(document.getElementById('simpleScannerModal'));
        if (modal) {
            modal.hide();
        }

        // Feedback
        this.showSuccess();
    }

    showSuccess() {
        // Feedback visual simples
        const input = document.getElementById('numero_bem');
        if (input) {
            input.style.backgroundColor = '#d4edda';
            setTimeout(() => {
                input.style.backgroundColor = '';
            }, 1000);
        }
    }
}

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function() {
    // Usar scanner simples como fallback
    window.simpleScanner = new SimpleScanner();
    window.simpleScanner.init();
    
    // Tentar usar scanner com código de barras se possível
    try {
        window.barcodeScanner = new BarcodeScanner();
    } catch (error) {
        console.log("Usando scanner simples");
    }
});

// ===== FUNÇÃO GLOBAL SIMPLES =====
function openScanner() {
    if (window.simpleScanner) {
        window.simpleScanner.openSimpleScanner();
    } else {
        // Fallback ultimate - abrir prompt manual
        const code = prompt("Digite o número do patrimônio:");
        if (code) {
            const input = document.getElementById('numero_bem');
            if (input) {
                input.value = code;
                input.focus();
            }
        }
    }
}