// map.js - Archivo JavaScript externo

document.addEventListener("DOMContentLoaded", function () {
  
  let map;
  let markers = [];
  let plantacionesData = [];

  function updateMapStatus(message, type = "info", subMessage = "") {
    const statusElement = document.getElementById("mapStatus");
    const loadingOverlay = document.getElementById("mapLoadingOverlay");

    const icons = {
      success: "✅",
      error: "❌",
      warning: "⚠️",
      info: "⏳",
    };

    if (statusElement) {
      statusElement.className = "map-status-bar " + type;

      const statusIcon = statusElement.querySelector(".status-icon");
      const statusTextMain = statusElement.querySelector(".status-text-main");
      const statusTextSub = statusElement.querySelector(".status-text-sub");
      const statusSpinner = statusElement.querySelector(".status-spinner");

      if (statusIcon) statusIcon.textContent = icons[type];
      if (statusTextMain) statusTextMain.textContent = message;
      if (statusTextSub)
        statusTextSub.textContent = subMessage || "Procesando información geográfica";

      if (statusSpinner) {
        statusSpinner.style.display = type === "success" ? "none" : "block";
      }
    }

    if (type === "success" && loadingOverlay) {
      setTimeout(() => {
        loadingOverlay.classList.add("hidden");
      }, 500);
    }
  }

  function getPlantacionesData() {
    try {
      // Acceder a los datos desde la variable global
      const plantacionesRaw = window.DJANGO_DATA.plantaciones;
      console.log("Datos de plantaciones desde Django:", plantacionesRaw);

      if (!plantacionesRaw || !Array.isArray(plantacionesRaw)) {
        throw new Error("No se encontraron datos de plantaciones válidos");
      }

      plantacionesData = plantacionesRaw
        .map((plantacion, index) => {
          const lat = parseFloat(plantacion.latitud);
          const lng = parseFloat(plantacion.longitud);

          if (isNaN(lat) || isNaN(lng)) {
            console.warn(`Plantación ${plantacion.id}: coordenadas inválidas`);
            return null;
          }

          if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
            console.warn(`Plantación ${plantacion.id}: coordenadas fuera de rango`);
            return null;
          }

          return {
            id: plantacion.id,
            nombre: plantacion.nombre || plantacion.nombre_finca || `Plantación ${plantacion.id}`,
            lat: lat,
            lng: lng,
            ubicacion: plantacion.ubicacion || "Ubicación no especificada",
            extension: plantacion.extension_hectareas || "No especificado",
            fecha_registro: plantacion.fecha_registro || "No especificado",
            propietario: plantacion.propietario || "Sin propietario",
          };
        })
        .filter((plantacion) => plantacion !== null);

      console.log(`✓ ${plantacionesData.length} plantaciones válidas procesadas`);
      return plantacionesData;
    } catch (error) {
      console.error("❌ Error al obtener datos de plantaciones:", error);
      updateMapStatus("Error al cargar plantaciones", "error", error.message);
      return [];
    }
  }

  function createCustomIcon(index, isMain = false) {
    const icons = ["🏡", "🌱", "🌾", "🍃", "🌳", "🌿", "🌽", "🍀", "🌸", "🌺"];
    const selectedIcon = isMain ? "🏡" : icons[index % icons.length];

    return L.divIcon({
      html: `<div class="custom-marker ${isMain ? "main-marker" : "secondary-marker"}">${selectedIcon}</div>`,
      iconSize: isMain ? [35, 35] : [30, 30],
      className: "custom-div-icon",
    });
  }

  function createPopupContent(plantacion, isMain = false) {
    const mainBadge = isMain
      ? '<span style="background: #059669; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">PRINCIPAL</span>'
      : "";

    return `
      <div style="text-align: center; min-width: 220px;">
        <div style="margin-bottom: 8px;">
          ${mainBadge}
        </div>
        <h4 style="margin: 0 0 8px 0; color: ${isMain ? "#059669" : "#7c3aed"};">${plantacion.nombre}</h4>
        <p style="margin: 4px 0; color: #374151;">📍 ${plantacion.ubicacion}</p>
        <p style="margin: 4px 0; color: #374151;">👤 ${plantacion.propietario}</p>
        <hr style="margin: 8px 0; border: none; border-top: 1px solid #d1d5db;">
        <div style="text-align: left; font-size: 13px; color: #6b7280;">
          <div style="margin: 2px 0;"><strong>ID:</strong> ${plantacion.id}</div>
          <div style="margin: 2px 0;"><strong>Extensión:</strong> ${plantacion.extension}</div>
          <div style="margin: 2px 0;"><strong>Registro:</strong> ${plantacion.fecha_registro}</div>
          <div style="margin: 4px 0; padding-top: 4px; border-top: 1px solid #e5e7eb;">
            <strong>Coordenadas:</strong><br>
            Lat: ${plantacion.lat.toFixed(6)}<br>
            Lng: ${plantacion.lng.toFixed(6)}
          </div>
        </div>
      </div>
    `;
  }

  function calculateMapCenter(plantaciones) {
    if (plantaciones.length === 0) {
      return { lat: -0.1807, lng: -78.4678, zoom: 6 };
    }

    if (plantaciones.length === 1) {
      return { lat: plantaciones[0].lat, lng: plantaciones[0].lng, zoom: 15 };
    }

    const latSum = plantaciones.reduce((sum, p) => sum + p.lat, 0);
    const lngSum = plantaciones.reduce((sum, p) => sum + p.lng, 0);

    const centerLat = latSum / plantaciones.length;
    const centerLng = lngSum / plantaciones.length;

    const lats = plantaciones.map((p) => p.lat);
    const lngs = plantaciones.map((p) => p.lng);

    const latRange = Math.max(...lats) - Math.min(...lats);
    const lngRange = Math.max(...lngs) - Math.min(...lngs);
    const maxRange = Math.max(latRange, lngRange);

    let zoom = 10;
    if (maxRange < 0.01) zoom = 15;
    else if (maxRange < 0.1) zoom = 12;
    else if (maxRange < 1) zoom = 8;
    else if (maxRange < 5) zoom = 6;
    else zoom = 4;

    return { lat: centerLat, lng: centerLng, zoom: zoom };
  }

  function initializeMapWithPlantations(plantaciones) {
    try {
      console.log(`Inicializando mapa con ${plantaciones.length} plantaciones`);

      // Usar el ID de la variable global
      const plantacionPrincipalId = window.DJANGO_DATA.plantacionPrincipalId;
      console.log("ID de plantación principal:", plantacionPrincipalId);

      const mainPlantation = plantaciones.find(
        (p) => p.id.toString() === plantacionPrincipalId.toString()
      );

      let mapCenter;
      if (mainPlantation) {
        mapCenter = { lat: mainPlantation.lat, lng: mainPlantation.lng, zoom: 15 };
        console.log("Usando plantación principal como centro:", mapCenter);
      } else {
        mapCenter = calculateMapCenter(plantaciones);
        console.log("Centro del mapa calculado (promedio):", mapCenter);
      }

      map = L.map("plantationMap").setView([mapCenter.lat, mapCenter.lng], mapCenter.zoom);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
        minZoom: 1,
      }).addTo(map);

      const markerCluster = L.markerClusterGroup({
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: true,
        zoomToBoundsOnClick: true,
        maxClusterRadius: 40,
      });

      plantaciones.forEach((plantacion, index) => {
        const isMainPlantation = plantacion.id.toString() === plantacionPrincipalId.toString();
        const customIcon = createCustomIcon(index, isMainPlantation);
        const marker = L.marker([plantacion.lat, plantacion.lng], { icon: customIcon });
        const popupContent = createPopupContent(plantacion, isMainPlantation);
        
        marker.bindPopup(popupContent);

        if (isMainPlantation) {
          marker.openPopup();
        }

        markerCluster.addLayer(marker);
        markers.push(marker);

        console.log(`✓ Marcador agregado para plantación ${plantacion.id} (${isMainPlantation ? "PRINCIPAL" : "secundaria"})`);
      });

      map.addLayer(markerCluster);

      if (!mainPlantation && plantaciones.length > 1) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds().pad(0.1));
      }

      map.on("load", function () {
        console.log("✓ Mapa cargado correctamente");
        updateMapStatus("Mapa cargado exitosamente", "success", `${plantaciones.length} plantaciones georeferenciadas`);
      });

      map.on("zoomend", function () {
        console.log(`Zoom cambiado a: ${map.getZoom()}`);
      });

      setTimeout(() => {
        map.invalidateSize();
        updateMapStatus("Sistema GPS activo", "success", `${plantaciones.length} plantaciones cargadas correctamente`);
      }, 100);

      return true;
    } catch (error) {
      console.error("❌ Error al inicializar el mapa:", error);
      updateMapStatus("Error al inicializar mapa", "error", error.message);
      return false;
    }
  }

  function processAllPlantations() {
    try {
      updateMapStatus("Cargando plantaciones", "info", "Obteniendo datos del servidor");

      const plantaciones = getPlantacionesData();

      if (plantaciones.length === 0) {
        throw new Error("No se encontraron plantaciones válidas");
      }

      console.log(`✓ ${plantaciones.length} plantaciones válidas encontradas`);
      updateMapStatus("Plantaciones encontradas", "info", `Procesando ${plantaciones.length} ubicaciones`);

      return initializeMapWithPlantations(plantaciones);
    } catch (error) {
      console.warn("⚠️ Error al procesar plantaciones:", error.message);
      updateMapStatus("Usando ubicación de respaldo", "warning", error.message);

      const fallbackPlantation = [
        {
          id: "fallback",
          nombre: "Ubicación de Respaldo",
          lat: -0.1807,
          lng: -78.4678,
          ubicacion: "Quito, Ecuador",
          extension: "N/A",
          fecha_registro: "N/A",
          propietario: "N/A",
        },
      ];

      console.log("Usando plantación de respaldo");
      updateMapStatus("Ubicación de respaldo activa", "warning", "Quito, Ecuador - Sin datos de plantaciones");

      return initializeMapWithPlantations(fallbackPlantation);
    }
  }

  console.log("Iniciando procesamiento de plantaciones...");

  const mapInitialized = processAllPlantations();

  if (!mapInitialized) {
    console.error("❌ No se pudo inicializar el mapa");
    updateMapStatus("Error crítico del sistema", "error", "No se pudo cargar el mapa");

    const loadingOverlay = document.getElementById("mapLoadingOverlay");
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden");
    }

    const mapContainer = document.getElementById("plantationMap");
    if (mapContainer) {
      mapContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; background: #f9fafb; border: 2px dashed #d1d5db; border-radius: 8px; color: #6b7280; text-align: center; padding: 20px;">
          <div style="font-size: 48px; margin-bottom: 16px;">🗺️</div>
          <h3 style="margin: 0 0 8px 0; color: #374151;">No se pudo cargar el mapa</h3>
          <p style="margin: 0; font-size: 14px;">Verificar coordenadas de las plantaciones</p>
        </div>
      `;
    }
  }

  setupMapControls();

  function setupMapControls() {
    const mapControlBtns = document.querySelectorAll(".map-control-btn");

    mapControlBtns.forEach((btn, index) => {
      btn.addEventListener("click", function () {
        this.style.transform = "scale(0.95)";
        setTimeout(() => {
          this.style.transform = "";
        }, 150);

        switch (index) {
          case 0:
            if (typeof map !== "undefined" && map) {
              console.log("Centrando mapa...");
              updateMapStatus("Centrando vista del mapa", "info", "Ajustando zoom y posición");

              if (markers && markers.length > 0) {
                const group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.1));
              }

              setTimeout(() => {
                updateMapStatus("Vista centrada correctamente", "success", "Mapa ajustado");
              }, 1000);
            }
            break;

          case 1:
            console.log("Cambiando a vista satélite...");
            updateMapStatus("Vista satélite no disponible", "warning", "Función en desarrollo");
            setTimeout(() => {
              updateMapStatus("Sistema GPS activo", "success", "Usando vista de mapa estándar");
            }, 2000);
            break;

          case 2:
            if (typeof map !== "undefined" && map) {
              const mapContainer = document.querySelector(".map-wrapper-premium");
              if (mapContainer) {
                if (!document.fullscreenElement) {
                  mapContainer
                    .requestFullscreen()
                    .then(() => {
                      console.log("Modo pantalla completa activado");
                      setTimeout(() => {
                        map.invalidateSize();
                      }, 100);
                    })
                    .catch((err) => {
                      console.error("Error al activar pantalla completa:", err);
                      updateMapStatus("No se pudo activar pantalla completa", "warning", "Intente de nuevo");
                    });
                } else {
                  document.exitFullscreen();
                  console.log("Modo pantalla completa desactivado");
                  setTimeout(() => {
                    map.invalidateSize();
                  }, 100);
                }
              }
            }
            break;
        }
      });
    });
  }

  function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    const timeElement = document.getElementById("currentTime");
    if (timeElement) {
      timeElement.textContent = timeString;
    }
  }

  updateCurrentTime();
  setInterval(updateCurrentTime, 1000);

  window.addEventListener("resize", function () {
    if (typeof map !== "undefined" && map) {
      setTimeout(() => {
        map.invalidateSize();
        console.log("Mapa redimensionado");
      }, 100);
    }
  });
});
