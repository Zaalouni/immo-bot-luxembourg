<template>
  <div class="space-y-6">
    <div
      v-for="(range, label) in priceRanges"
      :key="label"
      class="card"
      :style="{ borderLeft: `4px solid ${range.color}` }"
    >
      <h3 class="text-lg font-semibold mb-3" :style="{ color: range.color }">
        {{ label }}
        <span class="text-sm font-normal text-gray-600">({{ range.listings.length }} annonces)</span>
      </h3>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <a
          v-for="listing in range.listings.slice(0, 6)"
          :key="listing.listing_id"
          :href="listing.url"
          target="_blank"
          class="border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-2">
            <span class="font-bold text-primary">{{ formatCurrency(listing.price) }}</span>
            <AnomalyBadge :flag="listing.price_anomaly" />
          </div>
          <p class="text-sm font-medium text-gray-800">{{ listing.city }}</p>
          <p class="text-xs text-gray-600">{{ listing.surface }}m² - {{ formatNumber(listing.price_m2, 0) }}€/m²</p>
          <p class="text-xs text-gray-500 mt-2">{{ truncate(listing.title, 50) }}</p>
        </a>
      </div>

      <button
        v-if="range.listings.length > 6"
        @click="expandedRanges.add(label)"
        v-show="!expandedRanges.has(label)"
        class="btn btn-secondary text-sm mt-3 w-full"
      >
        Voir {{ range.listings.length - 6 }} autres ({{ range.listings.length }} total)
      </button>

      <!-- Expanded view -->
      <div v-if="expandedRanges.has(label)" class="mt-4 pt-4 border-t border-gray-200">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <a
            v-for="listing in range.listings.slice(6)"
            :key="listing.listing_id"
            :href="listing.url"
            target="_blank"
            class="border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow"
          >
            <div class="flex justify-between items-start mb-2">
              <span class="font-bold text-primary">{{ formatCurrency(listing.price) }}</span>
              <AnomalyBadge :flag="listing.price_anomaly" />
            </div>
            <p class="text-sm font-medium text-gray-800">{{ listing.city }}</p>
            <p class="text-xs text-gray-600">{{ listing.surface }}m² - {{ formatNumber(listing.price_m2, 0) }}€/m²</p>
            <p class="text-xs text-gray-500 mt-2">{{ truncate(listing.title, 50) }}</p>
          </a>
        </div>
        <button
          @click="expandedRanges.delete(label)"
          class="btn btn-secondary text-sm mt-3 w-full"
        >
          Réduire
        </button>
      </div>
    </div>

    <div v-if="totalListings === 0" class="card text-center py-8 text-gray-500">
      <i class="fas fa-inbox text-2xl mb-2"></i>
      <p>Aucune annonce ne correspond à vos filtres</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useListingsStore } from '../../stores/listings'
import { useStatsStore } from '../../stores/stats'
import { formatCurrency, formatNumber, truncate } from '../../utils/formatting'
import { groupByPriceRange } from '../../utils/calculations'
import AnomalyBadge from '../common/AnomalyBadge.vue'

const listings = useListingsStore()
const stats = useStatsStore()
const expandedRanges = ref(new Set())

const priceRanges = computed(() => {
  return groupByPriceRange(listings.appliedFilters)
})

const totalListings = computed(() => {
  return listings.appliedFilters.length
})
</script>
