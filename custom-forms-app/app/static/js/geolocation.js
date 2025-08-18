/**
 * Géolocalisation - Récupération des coordonnées GPS et adresse
 */

// Import Leaflet library
const L = window.L

class GeolocationManager {
  constructor() {
    this.position = null
    this.address = null
    this.watchId = null
    this.options = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 300000, // 5 minutes
    }
  }

  /**
   * Demander la géolocalisation à l'utilisateur
   */
  requestLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("La géolocalisation n'est pas supportée par ce navigateur."))
        return
      }

      this.showStatus("Demande de localisation en cours...", "loading")

      navigator.geolocation.getCurrentPosition(
        (position) => {
          this.position = position
          this.showStatus(
            `Position obtenue: ${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`,
            "success",
          )
          this.updateHiddenFields(position)

          // Récupérer l'adresse
          this.reverseGeocode(position.coords.latitude, position.coords.longitude)

          resolve(position)
        },
        (error) => {
          this.handleError(error)
          reject(error)
        },
        this.options,
      )
    })
  }

  /**
   * Géocodage inverse pour obtenir l'adresse
   */
  async reverseGeocode(lat, lng) {
    try {
      // Utiliser l'API Nominatim d'OpenStreetMap (gratuite)
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
        {
          headers: {
            "User-Agent": "FormBuilder/1.0",
          },
        },
      )

      if (response.ok) {
        const data = await response.json()
        if (data && data.display_name) {
          this.address = data.display_name
          this.updateAddressDisplay(data)
        }
      }
    } catch (error) {
      console.error("Erreur lors du géocodage inverse:", error)
      // Essayer avec une API alternative si disponible
      this.tryAlternativeGeocoding(lat, lng)
    }
  }

  /**
   * Essayer une API de géocodage alternative
   */
  async tryAlternativeGeocoding(lat, lng) {
    try {
      // API alternative gratuite
      const response = await fetch(
        `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=fr`,
      )

      if (response.ok) {
        const data = await response.json()
        if (data && data.locality) {
          const address = `${data.locality}, ${data.principalSubdivision}, ${data.countryName}`
          this.address = address
          this.updateAddressDisplay({ display_name: address })
        }
      }
    } catch (error) {
      console.error("Erreur avec l'API alternative:", error)
    }
  }

  /**
   * Mettre à jour l'affichage de l'adresse
   */
  updateAddressDisplay(data) {
    const addressDisplay = document.getElementById("address-display")
    const addressInput = document.getElementById("address")

    if (addressDisplay && data.display_name) {
      addressDisplay.innerHTML = `
        <i class="fas fa-map-marker-alt me-2 text-success"></i>
        <strong>Adresse:</strong> ${data.display_name}
      `
      addressDisplay.style.display = "block"
    }

    if (addressInput) {
      addressInput.value = data.display_name
    }
  }

  /**
   * Surveiller la position en continu
   */
  watchPosition() {
    if (!navigator.geolocation) {
      console.error("Géolocalisation non supportée")
      return
    }

    this.watchId = navigator.geolocation.watchPosition(
      (position) => {
        this.position = position
        this.updateHiddenFields(position)

        // Mettre à jour l'adresse si la position a changé significativement
        if (this.hasPositionChanged(position)) {
          this.reverseGeocode(position.coords.latitude, position.coords.longitude)
        }
      },
      (error) => {
        this.handleError(error)
      },
      this.options,
    )
  }

  /**
   * Vérifier si la position a changé significativement
   */
  hasPositionChanged(newPosition) {
    if (!this.position) return true

    const oldLat = this.position.coords.latitude
    const oldLng = this.position.coords.longitude
    const newLat = newPosition.coords.latitude
    const newLng = newPosition.coords.longitude

    // Seuil de 100 mètres environ
    const threshold = 0.001

    return Math.abs(oldLat - newLat) > threshold || Math.abs(oldLng - newLng) > threshold
  }

  /**
   * Arrêter la surveillance de la position
   */
  stopWatching() {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId)
      this.watchId = null
    }
  }

  /**
   * Mettre à jour les champs cachés avec les coordonnées
   */
  updateHiddenFields(position) {
    const latInput = document.getElementById("latitude")
    const lngInput = document.getElementById("longitude")

    if (latInput) {
      latInput.value = position.coords.latitude
    }

    if (lngInput) {
      lngInput.value = position.coords.longitude
    }

    // Mettre à jour l'affichage si présent
    const locationDisplay = document.getElementById("location-display")
    if (locationDisplay) {
      locationDisplay.innerHTML = `
                <strong>Position actuelle:</strong><br>
                Latitude: ${position.coords.latitude.toFixed(6)}<br>
                Longitude: ${position.coords.longitude.toFixed(6)}<br>
                Précision: ±${position.coords.accuracy.toFixed(0)}m
            `
    }
  }

  /**
   * Gérer les erreurs de géolocalisation
   */
  handleError(error) {
    let message = "Erreur de géolocalisation: "

    switch (error.code) {
      case error.PERMISSION_DENIED:
        message += "Permission refusée par l'utilisateur."
        break
      case error.POSITION_UNAVAILABLE:
        message += "Position non disponible."
        break
      case error.TIMEOUT:
        message += "Délai d'attente dépassé."
        break
      default:
        message += "Erreur inconnue."
        break
    }

    this.showStatus(message, "error")
    console.error("Erreur de géolocalisation:", error)
  }

  /**
   * Afficher le statut de la géolocalisation
   */
  showStatus(message, type) {
    const statusElement = document.getElementById("geolocation-status")
    if (statusElement) {
      statusElement.className = `geolocation-status ${type}`
      statusElement.innerHTML = `
                <i class="fas fa-${this.getStatusIcon(type)} me-2"></i>
                ${message}
            `
      statusElement.style.display = "block"

      // Masquer automatiquement après 5 secondes pour les messages de succès
      if (type === "success") {
        setTimeout(() => {
          statusElement.style.display = "none"
        }, 5000)
      }
    }
  }

  /**
   * Obtenir l'icône appropriée selon le type de statut
   */
  getStatusIcon(type) {
    const icons = {
      loading: "spinner fa-spin",
      success: "check-circle",
      error: "exclamation-triangle",
    }
    return icons[type] || "info-circle"
  }

  /**
   * Obtenir la position actuelle
   */
  getCurrentPosition() {
    return this.position
  }

  /**
   * Obtenir l'adresse actuelle
   */
  getCurrentAddress() {
    return this.address
  }

  /**
   * Calculer la distance entre deux points
   */
  calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371 // Rayon de la Terre en km
    const dLat = this.toRadians(lat2 - lat1)
    const dLon = this.toRadians(lon2 - lon1)

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    return R * c // Distance en km
  }

  /**
   * Convertir les degrés en radians
   */
  toRadians(degrees) {
    return degrees * (Math.PI / 180)
  }
}

// Instance globale du gestionnaire de géolocalisation
let geolocationManager

// Initialisation
document.addEventListener("DOMContentLoaded", () => {
  geolocationManager = new GeolocationManager()

  // Bouton pour demander la localisation
  const locationBtn = document.getElementById("request-location")
  if (locationBtn) {
    locationBtn.addEventListener("click", () => {
      geolocationManager.requestLocation().catch((error) => {
        console.error("Erreur lors de la demande de localisation:", error)
      })
    })
  }

  // Demander automatiquement la localisation si l'option est activée
  const autoLocation = document.getElementById("auto-location")
  if (autoLocation && autoLocation.checked) {
    geolocationManager.requestLocation().catch((error) => {
      console.error("Géolocalisation automatique échouée:", error)
    })
  }

  // Ajouter les champs cachés pour les coordonnées si ils n'existent pas
  const form = document.querySelector("form")
  if (form && !document.getElementById("latitude")) {
    const latInput = document.createElement("input")
    latInput.type = "hidden"
    latInput.id = "latitude"
    latInput.name = "latitude"
    form.appendChild(latInput)

    const lngInput = document.createElement("input")
    lngInput.type = "hidden"
    lngInput.id = "longitude"
    lngInput.name = "longitude"
    form.appendChild(lngInput)

    const addressInput = document.createElement("input")
    addressInput.type = "hidden"
    addressInput.id = "address"
    addressInput.name = "address"
    form.appendChild(addressInput)
  }

  // Nouvelle fonction pour obtenir la localisation
  const addressInput = document.getElementById("address")
  const latitudeInput = document.getElementById("latitude")
  const longitudeInput = document.getElementById("longitude")
  const statusText = document.getElementById("geolocation-status")

  if (addressInput && latitudeInput && longitudeInput && statusText) {
    window.getLocation = () => {
      geolocationManager.getLocation(addressInput, latitudeInput, longitudeInput, statusText)
    }
  }
})

// Ajout de la fonction getLocation dans la classe GeolocationManager
GeolocationManager.prototype.getLocation = (addressInput, latitudeInput, longitudeInput, statusText) => {
  if (navigator.geolocation) {
    statusText.textContent = "Recherche de votre position..."
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude
        const lon = position.coords.longitude
        latitudeInput.value = lat
        longitudeInput.value = lon
        statusText.textContent = `Position trouvée: ${lat}, ${lon}`

        // Utiliser un service de géocodage inverse (ex: OpenStreetMap Nominatim)
        fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}`)
          .then((response) => response.json())
          .then((data) => {
            if (data && data.display_name) {
              addressInput.value = data.display_name
              statusText.textContent = "Adresse trouvée."
            } else {
              addressInput.value = "Adresse non trouvée."
              statusText.textContent = "Adresse non trouvée pour cette position."
            }
          })
          .catch((error) => {
            console.error("Erreur de géocodage inverse:", error)
            addressInput.value = "Erreur de géocodage."
            statusText.textContent = "Erreur lors de la récupération de l'adresse."
          })
      },
      (error) => {
        let errorMessage = "Erreur de géolocalisation: "
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage += "L'utilisateur a refusé la demande de géolocalisation."
            break
          case error.POSITION_UNAVAILABLE:
            errorMessage += "Les informations de localisation ne sont pas disponibles."
            break
          case error.TIMEOUT:
            errorMessage += "La demande de géolocalisation a expiré."
            break
          case error.UNKNOWN_ERROR:
            errorMessage += "Une erreur inconnue est survenue."
            break
        }
        statusText.textContent = errorMessage
        console.error(errorMessage, error)
        addressInput.value = ""
        latitudeInput.value = ""
        longitudeInput.value = ""
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    )
  } else {
    statusText.textContent = "La géolocalisation n'est pas supportée par votre navigateur."
    addressInput.value = ""
    latitudeInput.value = ""
    longitudeInput.value = ""
  }
}

// Nettoyer lors de la fermeture de la page
window.addEventListener("beforeunload", () => {
  if (geolocationManager) {
    geolocationManager.stopWatching()
  }
})

window.geolocationMaps = {} // Stocke les instances de carte Leaflet

function getGeolocation(fieldId) {
  const latInput = document.getElementById(`${fieldId}_lat`)
  const lonInput = document.getElementById(`${fieldId}_lon`)
  const displayInput = document.getElementById(`${fieldId}_display`)
  const mapContainer = document.getElementById(`${fieldId}_map`)

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude
        const lon = position.coords.longitude

        latInput.value = lat
        lonInput.value = lon
        displayInput.value = `${lat.toFixed(6)}, ${lon.toFixed(6)}`

        // Afficher la carte
        mapContainer.style.display = "block"

        // Initialiser ou mettre à jour la carte Leaflet
        if (window.geolocationMaps[fieldId]) {
          window.geolocationMaps[fieldId].setView([lat, lon], 13)
          window.geolocationMaps[fieldId].eachLayer((layer) => {
            if (layer instanceof L.Marker) {
              window.geolocationMaps[fieldId].removeLayer(layer)
            }
          })
          L.marker([lat, lon]).addTo(window.geolocationMaps[fieldId])
        } else {
          const map = L.map(mapContainer).setView([lat, lon], 13)
          L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
          }).addTo(map)
          L.marker([lat, lon]).addTo(map)
          window.geolocationMaps[fieldId] = map
        }
      },
      (error) => {
        console.error("Erreur de géolocalisation:", error)
        displayInput.value = "Impossible d'obtenir la position."
        alert("Impossible d'obtenir votre position. Veuillez autoriser la géolocalisation.")
        mapContainer.style.display = "none"
      },
    )
  } else {
    displayInput.value = "Géolocalisation non supportée."
    alert("Votre navigateur ne supporte pas la géolocalisation.")
    mapContainer.style.display = "none"
  }
}
