<template>
  <div class="space-y-6">
    <!-- HIGH PRICES -->
    <div>
      <h2 class="text-2xl font-bold text-danger mb-4">
        🚨 Annonces Chères ({{ highPriced.length }})
      </h2>
      <p class="text-sm text-gray-600 mb-4">
        Ces annonces coûtent plus de 2.5x la médiane pour leur ville
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <a
          v-for="listing in highPriced"
          :key="listing.listing_id"
          :href="listing.url"
          target="_blank"
          class="card border-l-4 border-danger hover:shadow-lg transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <span
              class="site-badge text-xs"
              :style="{ backgroundColor: stats.getSiteColor(listing.site) }"
            >
              {{ listing.site.split('.')[0] }}
            </span>
            <span class="badge bg-danger text-white">{{ Math.round((listing.price / getMedianPrice(listing.city)) * 100) }}%</span>
          </div>

          <h3 class="font-bold text-gray-800 mb-2">{{ truncate(listing.title, 50) }}</h3>

          <div class="grid grid-cols-2 gap-2 text-sm mb-3">
            <div>
              <span class="text-gray-600">Prix:</span>
              <p class="font-bold text-primary">{{ formatCurrency(listing.price) }}</p>
            </div>
            <div>
              <span class="text-gray-600">Médiane:</span>
              <p class="font-bold">{{ formatCurrency(getMedianPrice(listing.city)) }}</p>
            </div>
          </div>

          <p class="text-xs text-gray-600">{{ listing.city }} • {{ listing.surface }}m²</p>
        </a>
      </div>

      <div v-if="highPriced.length === 0" class="card text-center py-8 text-gray-500">
        <p>Aucune annonce chère 👍</p>
      </div>
    </div>

    <!-- GOOD DEALS -->
    <div>
      <h2 class="text-2xl font-bold text-success mb-4">
        🎉 Bonnes Affaires ({{ goodDeals.length }})
      </h2>
      <p class="text-sm text-gray-600 mb-4">
        Ces annonces coûtent moins de 0.7x la médiane pour leur ville
      </p>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <a
          v-for="listing in goodDeals"
          :key="listing.listing_id"
          :href="listing.url"
          target="_blank"
          class="card border-l-4 border-success hover:shadow-lg transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <span
              class="site-badge text-xs"
              :style="{ backgroundColor: stats.getSiteColor(listing.site) }"
            >
              {{ listing.site.split('.')[0] }}
            </span>
            <span class="badge bg-success text-white">{{ Math.round((listing.price / getMedianPrice(listing.city)) * 100) }}%</span>
          </div>

          <h3 class="font-bold text-gray-800 mb-2">{{ truncate(listing.title, 50) }}</h3>

          <div class="grid grid-cols-2 gap-2 text-sm mb-3">
            <div>
              <span class="text-gray-600">Prix:</span>
              <p class="font-bold text-primary">{{ formatCurrency(listing.price) }}</p>
            </div>
            <div>
              <span class="text-gray-600">Médiane:</span>
              <p class="font-bold">{{ formatCurrency(getMedianPrice(listing.city)) }}</p>
            </div>
          </div>

          <p class="text-xs text-gray-600">{{ listing.city }} • {{ listing.surface }}m²</p>
        </a>
      </div>

      <div v-if="goodDeals.length === 0" class="card text-center py-8 text-gray-500">
        <p>Aucune bonne affaire pour le moment</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useListingsStore } from '../../stores/listings'
import { useStatsStore } from '../../stores/stats'
import { formatCurrency, truncate } from '../../utils/formatting'

const listings = useListingsStore()
const stats = useStatsStore()

const highPriced = computed(() => {
  return listings.appliedFilters.filter(l => l.price_anomaly === 'HIGH')
})

const goodDeals = computed(() => {
  return listings.appliedFilters.filter(l => l.price_anomaly === 'GOOD_DEAL')
})

const getMedianPrice = (city) => {
  const cityListings = listings.allListings.filter(l => l.city === city)
  if (cityListings.length === 0) return 0
  const prices = cityListings.map(l => l.price).sort((a, b) => a - b)
  const mid = Math.floor(prices.length / 2)
  return prices.length % 2 !== 0 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2
}
</script>

<style scoped>
.bg-success {
  background-color: #10B981;
}

.text-success {
  color: #10B981;
}

.border-success {
  border-color: #10B981;
}
</style>
