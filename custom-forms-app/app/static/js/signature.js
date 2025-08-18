/**
 * Signature électronique - Gestion du canvas de signature
 */

window.signaturePads = {} // Stocke les instances de SignaturePad

class SignaturePad {
  constructor(canvas, options) {
    this.canvas = canvas
    this.ctx = canvas.getContext("2d")
    this.isDrawing = false
    this.lastX = 0
    this.lastY = 0
    this.backgroundColor = options.backgroundColor || "#ffffff"

    this.setupCanvas()
    this.setupEventListeners()
  }

  setupCanvas() {
    // Configuration du canvas
    this.ctx.strokeStyle = "#000000"
    this.ctx.lineWidth = 2
    this.ctx.lineCap = "round"
    this.ctx.lineJoin = "round"

    // Fond blanc pour le canvas
    this.ctx.fillStyle = this.backgroundColor
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height)
  }

  setupEventListeners() {
    // Événements de souris
    this.canvas.addEventListener("mousedown", this.startDrawing.bind(this))
    this.canvas.addEventListener("mousemove", this.draw.bind(this))
    this.canvas.addEventListener("mouseup", this.stopDrawing.bind(this))
    this.canvas.addEventListener("mouseout", this.stopDrawing.bind(this))

    // Événements tactiles pour mobile
    this.canvas.addEventListener("touchstart", this.handleTouch.bind(this))
    this.canvas.addEventListener("touchmove", this.handleTouch.bind(this))
    this.canvas.addEventListener("touchend", this.stopDrawing.bind(this))

    // Empêcher le défilement sur mobile lors du dessin
    this.canvas.addEventListener("touchstart", (e) => e.preventDefault())
    this.canvas.addEventListener("touchmove", (e) => e.preventDefault())
  }

  startDrawing(e) {
    this.isDrawing = true
    const rect = this.canvas.getBoundingClientRect()
    this.lastX = e.clientX - rect.left
    this.lastY = e.clientY - rect.top
  }

  draw(e) {
    if (!this.isDrawing) return

    const rect = this.canvas.getBoundingClientRect()
    const currentX = e.clientX - rect.left
    const currentY = e.clientY - rect.top

    this.ctx.beginPath()
    this.ctx.moveTo(this.lastX, this.lastY)
    this.ctx.lineTo(currentX, currentY)
    this.ctx.stroke()

    this.lastX = currentX
    this.lastY = currentY
  }

  stopDrawing() {
    this.isDrawing = false
  }

  handleTouch(e) {
    e.preventDefault()
    const touch = e.touches[0]
    const mouseEvent = new MouseEvent(
      e.type === "touchstart" ? "mousedown" : e.type === "touchmove" ? "mousemove" : "mouseup",
      {
        clientX: touch.clientX,
        clientY: touch.clientY,
      },
    )
    this.canvas.dispatchEvent(mouseEvent)
  }

  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
    this.ctx.fillStyle = this.backgroundColor
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height)
  }

  isEmpty() {
    // Vérifier si le canvas est vide (seulement du blanc)
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height)
    const data = imageData.data

    for (let i = 0; i < data.length; i += 4) {
      // Si un pixel n'est pas blanc (255,255,255), le canvas n'est pas vide
      if (data[i] !== 255 || data[i + 1] !== 255 || data[i + 2] !== 255) {
        return false
      }
    }
    return true
  }

  getDataURL() {
    return this.canvas.toDataURL("image/png")
  }

  fromDataURL(dataURL) {
    const img = new Image()
    img.onload = () => {
      this.clear()
      this.ctx.drawImage(img, 0, 0)
    }
    img.src = dataURL
  }
}

function initSignaturePad(canvasId) {
  const canvas = document.getElementById(canvasId)
  if (canvas) {
    const signaturePad = new SignaturePad(canvas, {
      backgroundColor: "rgb(255, 255, 255)", // Couleur de fond pour l'exportation
    })
    window.signaturePads[canvasId] = signaturePad

    // Ajuster la taille du canvas en cas de redimensionnement
    function resizeCanvas() {
      const ratio = Math.max(window.devicePixelRatio || 1, 1)
      canvas.width = canvas.offsetWidth * ratio
      canvas.height = canvas.offsetHeight * ratio
      canvas.getContext("2d").scale(ratio, ratio)
      signaturePad.clear() // Efface la signature après redimensionnement
    }
    window.addEventListener("resize", resizeCanvas)
    resizeCanvas() // Appel initial
  }
}

function clearSignature(canvasId) {
  if (window.signaturePads[canvasId]) {
    window.signaturePads[canvasId].clear()
    document.getElementById(`${canvasId}_data`).value = "" // Efface aussi le champ caché
  }
}

// Initialiser les pads de signature
document.addEventListener("DOMContentLoaded", () => {
  const signatureCanvases = document.querySelectorAll(".signature-canvas")

  signatureCanvases.forEach((canvas) => {
    const canvasId = canvas.id
    initSignaturePad(canvasId)

    // Bouton d'effacement
    const clearBtn = canvas.parentElement.querySelector(".signature-clear")
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        clearSignature(canvasId)
      })
    }
  })
})

// Validation des signatures avant soumission du formulaire
document.addEventListener("submit", (e) => {
  const form = e.target
  const signatureCanvases = form.querySelectorAll(".signature-canvas")

  signatureCanvases.forEach((canvas) => {
    const canvasId = canvas.id
    const signaturePad = window.signaturePads[canvasId]
    if (signaturePad) {
      // Créer un champ caché avec les données de la signature
      const hiddenInput = document.createElement("input")
      hiddenInput.type = "hidden"
      hiddenInput.name = canvas.dataset.fieldName || "signature"
      hiddenInput.id = `${canvasId}_data`
      hiddenInput.value = signaturePad.isEmpty() ? "" : signaturePad.getDataURL()

      form.appendChild(hiddenInput)
    }
  })
})
