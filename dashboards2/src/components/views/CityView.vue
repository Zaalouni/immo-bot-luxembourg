<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div
      v-for="city in listings.uniqueCities"
      :key="city"
      class="card"
    >
      <div class="flex items-start justify-between mb-3">
        <h3 class="text-lg font-semibold text-gray-800">{{ city }}</h3>
        <button
          @click="listings.setSelectedCity(city)"
          class="btn btn-primary text-xs py-1 px-2"
        >
          Filtrer
        </button>
      </div>

      <div class="grid grid-cols-2 gap-2 mb-3 text-sm">
        <div>
          <span class="text-gray-600">Annonces:</span>
          <p class="font-bold text-primary">{{ getCityCount(city) }}</p>
        </div>
        <div>
          <span class="text-gray-600">Prix moy:</span>
          <p class="font-bold">{{ formatCurrency(getCityAvgPrice(city)) }}</p>
        </div>
        <div>
          <span class="text-gray-600">Médiane:</span>
          <p class="font-bold">{{ formatCurrency(getCityMedianPrice(city)) }}</p>
        </div>
        <div>
          <span class="text-gray-600">Surface moy:</span>
          <p class="font-bold">{{ getCityAvgSurface(city) }}m²</p>
        </div>
      </div>

      <!-- Top 3 recent listings in this city -->
      <div class="border-t border-gray-200 pt-3">
        <p class="text-xs font-semibold text-gray-600 mb-2">Dernières annonces</p>
        <div class="space-y-2">
          <a
            v-for="listing in getTopListingsInCity(city, 3)"
            :key="listing.listing_id"
            :href="listing.url"
            target="_blank"
            class="block text-xs text-blue-600 hover:underline truncate"
          >
            {{ formatCurrency(listing.price) }} - {{ truncate(listing.title, 35) }}
          </a>
        </div>
      </div>
    </div>

    <div v-if="listings.uniqueCities.length === 0" class="col-span-full text-center py-8 text-gray-500">
      <i class="fas fa-inbox text-2xl mb-2"></i>
      <p>Aucune ville ne correspond à vos filtres</p>
    </div>
  </div>
</template>

<script setup>
import { useListingsStore } from '../../stores/listings'
import { formatCurrency, truncate } from '../../utils/formatting'
import { calculateCityStats } from '../../utils/calculations'

const listings = useListingsStore()

const getCityListings = (city) => {
  return listings.appliedFilters.filter(l => l.city === city)
}

const getCityCount = (city) => {
  return getCityListings(city).length
}

const getCityAvgPrice = (city) => {
  const cityListings = getCityListings(city)
  if (cityListings.length === 0) return 0
  return Math.round(cityListings.reduce((sum, l) => sum + l.price, 0) / cityListings.length)
}

const getCityMedianPrice = (city) => {
  const cityListings = getCityListings(city)
  if (cityListings.length === 0) return 0
  const prices = cityListings.map(l => l.price).sort((a, b) => a - b)
  const mid = Math.floor(prices.length / 2)
  return prices.length % 2 !== 0 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2
}

const getCityAvgSurface = (city) => {
  const cityListings = getCityListings(city)
  if (cityListings.length === 0) return 0
  const surfaces = cityListings.filter(l => l.surface > 0).map(l => l.surface)
  if (surfaces.length === 0) return 0
  return Math.round(surfaces.reduce((sum, s) => sum + s, 0) / surfaces.length)
}

const getTopListingsInCity = (city, limit) => {
  return getCityListings(city)
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
    .slice(0, limit)
}
</script>
