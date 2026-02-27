<template>
  <div>
    <h2 class="text-2xl font-bold text-gray-800 mb-6">🖼️ Galerie Photos</h2>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <a
        v-for="listing in listingsWithPhotos"
        :key="listing.listing_id"
        :href="listing.url"
        target="_blank"
        class="card p-0 overflow-hidden hover:shadow-lg transition-shadow"
      >
        <div class="bg-gray-300 h-40 flex items-center justify-center">
          <i class="fas fa-image text-gray-400 text-4xl"></i>
        </div>
        <div class="p-3">
          <p class="font-medium text-sm text-gray-800">{{ listing.city }}</p>
          <p class="text-lg font-bold text-primary">{{ formatCurrency(listing.price) }}</p>
          <p class="text-xs text-gray-600">{{ listing.surface }}m² • {{ listing.rooms || '—' }} pièces</p>
        </div>
      </a>
    </div>

    <div v-if="listingsWithPhotos.length === 0" class="card text-center py-12 text-gray-500">
      <i class="fas fa-inbox text-3xl mb-2"></i>
      <p>Aucune photo disponible</p>
      <small class="mt-2 block">Les photos des annonces seront bientôt intégrées</small>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useListingsStore } from '../../stores/listings'
import { formatCurrency } from '../../utils/formatting'

const listings = useListingsStore()

// For now, show all listings (will be replaced with actual photo URLs)
const listingsWithPhotos = computed(() => {
  return listings.appliedFilters.slice(0, 20)
})
</script>
