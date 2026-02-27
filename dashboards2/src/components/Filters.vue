<template>
  <div class="bg-white rounded-lg shadow-sm p-6 mb-6 border border-gray-200">
    <h2 class="text-lg font-semibold text-gray-800 mb-4">
      <i class="fas fa-filter"></i> Filtres
      <span v-if="listings.filterCount > 0" class="badge bg-primary text-white ml-2">
        {{ listings.filterCount }} actif{{ listings.filterCount > 1 ? 's' : '' }}
      </span>
    </h2>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
      <!-- City filter -->
      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Ville</label>
        <select
          v-model="listings.selectedCity"
          class="input-field"
        >
          <option value="">Toutes les villes ({{ listings.uniqueCities.length }})</option>
          <option v-for="city in listings.uniqueCities" :key="city" :value="city">
            {{ city }}
          </option>
        </select>
      </div>

      <!-- Price range filter -->
      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Prix min (€)</label>
        <input
          v-model.number="listings.priceRange.min"
          type="number"
          class="input-field"
          placeholder="0"
        />
      </div>

      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Prix max (€)</label>
        <input
          v-model.number="listings.priceRange.max"
          type="number"
          class="input-field"
          placeholder="10000"
        />
      </div>

      <!-- Surface filter -->
      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Surface min (m²)</label>
        <input
          v-model.number="listings.surfaceMin"
          type="number"
          class="input-field"
          placeholder="0"
        />
      </div>

      <!-- Site filter (compact) -->
      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Sites</label>
        <select
          v-model="listings.selectedSites"
          multiple
          class="input-field"
          size="3"
        >
          <option v-for="site in listings.uniqueSites" :key="site" :value="site">
            {{ site }}
          </option>
        </select>
        <small class="text-gray-500">Ctrl+Click pour multi-sélection</small>
      </div>
    </div>

    <!-- Date range filter -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Date de publication (de)</label>
        <input
          v-model="listings.dateRange.from"
          type="date"
          class="input-field"
        />
      </div>

      <div class="filter-group">
        <label class="block text-sm font-medium text-gray-700 mb-2">Date de publication (à)</label>
        <input
          v-model="listings.dateRange.to"
          type="date"
          class="input-field"
        />
      </div>
    </div>

    <!-- Action buttons -->
    <div class="flex gap-3">
      <button @click="resetFilters" class="btn btn-secondary">
        <i class="fas fa-redo"></i> Réinitialiser
      </button>
      <p class="flex-1 text-sm text-gray-600 self-center">
        <i class="fas fa-list"></i> {{ listings.appliedFilters.length }} annonce(s) trouvée(s)
      </p>
    </div>
  </div>
</template>

<script setup>
import { useListingsStore } from '../stores/listings'

const listings = useListingsStore()

const resetFilters = () => {
  listings.resetFilters()
}
</script>

<style scoped>
.filter-group {
  display: contents;
}
</style>
