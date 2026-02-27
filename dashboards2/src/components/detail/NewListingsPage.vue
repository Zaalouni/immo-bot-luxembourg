<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">✨ Annonces Récentes</h2>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <a
        v-for="listing in recentListings"
        :key="listing.listing_id"
        :href="listing.url"
        target="_blank"
        class="card hover:shadow-lg transition-shadow overflow-hidden"
      >
        <div class="flex justify-between items-start mb-2">
          <span
            class="site-badge text-xs"
            :style="{ backgroundColor: stats.getSiteColor(listing.site) }"
          >
            {{ listing.site.split('.')[0] }}
          </span>
          <span class="badge bg-gray-200 text-gray-800 text-xs">
            {{ listing.time_ago }}
          </span>
        </div>

        <h3 class="font-bold text-gray-800 mb-2">{{ truncate(listing.title, 60) }}</h3>

        <div class="flex items-baseline gap-2 mb-3">
          <span class="text-2xl font-bold text-primary">{{ formatCurrency(listing.price) }}</span>
          <span class="text-sm text-gray-600">{{ formatNumber(listing.price_m2, 0) }}€/m²</span>
        </div>

        <div class="grid grid-cols-3 gap-2 text-sm text-gray-600 mb-3 pb-3 border-b border-gray-200">
          <div>
            <i class="fas fa-map-pin text-primary"></i>
            <p>{{ listing.city }}</p>
          </div>
          <div>
            <i class="fas fa-door-open text-primary"></i>
            <p>{{ listing.rooms || '—' }} pièces</p>
          </div>
          <div>
            <i class="fas fa-ruler-combined text-primary"></i>
            <p>{{ listing.surface }}m²</p>
          </div>
        </div>

        <div class="flex justify-between items-center">
          <AnomalyBadge :flag="listing.price_anomaly" />
          <button class="btn btn-primary text-xs py-1 px-2">
            Voir <i class="fas fa-arrow-right"></i>
          </button>
        </div>
      </a>
    </div>

    <div v-if="recentListings.length === 0" class="card text-center py-12 text-gray-500">
      <i class="fas fa-inbox text-3xl mb-2"></i>
      <p>Aucune annonce récente</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useListingsStore } from '../../stores/listings'
import { useStatsStore } from '../../stores/stats'
import { formatCurrency, formatNumber, truncate } from '../../utils/formatting'
import AnomalyBadge from '../common/AnomalyBadge.vue'

const listings = useListingsStore()
const stats = useStatsStore()

const recentListings = computed(() => {
  return listings.appliedFilters
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at))
    .slice(0, 12)
})
</script>
