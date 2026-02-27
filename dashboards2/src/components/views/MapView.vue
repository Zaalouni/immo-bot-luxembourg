<template>
  <div class="card p-0 overflow-hidden">
    <div v-if="!mapLoaded" class="h-96 flex items-center justify-center bg-gray-100">
      <button @click="initMap" class="btn btn-primary">
        <i class="fas fa-map"></i> Charger la carte
      </button>
    </div>
    <div v-else id="map" style="height: 500px; width: 100%;"></div>

    <div class="p-4 border-t border-gray-200">
      <h3 class="font-semibold mb-3">Légende des sites</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
        <div v-for="site in listings.uniqueSites" :key="site" class="flex items-center gap-2">
          <span
            class="inline-block w-3 h-3 rounded-full"
            :style="{ backgroundColor: stats.getSiteColor(site) }"
          ></span>
          <span>{{ site.split('.')[0] }}</span>
        </div>
      </div>
      <p class="text-xs text-gray-600 mt-3">
        <i class="fas fa-info-circle"></i>
        {{ listings.appliedFilters.length }} annonce(s) avec coordonnées GPS
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useListingsStore } from '../../stores/listings'
import { useStatsStore } from '../../stores/stats'

const listings = useListingsStore()
const stats = useStatsStore()
const mapLoaded = ref(false)

const initMap = async () => {
  // Dynamically import Leaflet
  const L = (await import('leaflet')).default

  // Filter listings with GPS coordinates
  const listingsWithGPS = listings.appliedFilters.filter(l => l.latitude && l.longitude)

  if (listingsWithGPS.length === 0) {
    alert('Aucune annonce avec coordonnées GPS')
    return
  }

  // Initialize map
  const map = L.map('map').setView([49.6116, 6.1319], 9)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map)

  // Add markers for each listing
  listingsWithGPS.forEach(listing => {
    const marker = L.circleMarker(
      [listing.latitude, listing.longitude],
      {
        radius: 8,
        fillColor: stats.getSiteColor(listing.site),
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.7
      }
    ).addTo(map)

    marker.bindPopup(`
      <div style="min-width: 200px;">
        <strong>${listing.city}</strong><br>
        <span style="color: #4F46E5; font-weight: bold;">€${listing.price.toLocaleString('fr-LU')}</span><br>
        ${listing.surface}m² - ${listing.rooms || '—'} pièces<br>
        <small>${listing.site}</small><br>
        <a href="${listing.url}" target="_blank" style="color: #3B82F6; text-decoration: underline;">
          Voir annonce
        </a>
      </div>
    `)
  })

  // Fit map to all markers
  if (listingsWithGPS.length > 0) {
    const bounds = L.latLngBounds(
      listingsWithGPS.map(l => [l.latitude, l.longitude])
    )
    map.fitBounds(bounds, { padding: [50, 50] })
  }

  mapLoaded.value = true
}
</script>

<style scoped>
#map {
  background-color: #f3f4f6;
}
</style>
