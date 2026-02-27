<template>
  <div>
    <!-- Tab navigation -->
    <div class="flex flex-wrap gap-2 mb-6 border-b border-gray-200 overflow-x-auto">
      <button
        v-for="(tab, index) in tabs"
        :key="index"
        @click="activeTab = index"
        :class="[
          'px-4 py-3 font-medium text-sm whitespace-nowrap border-b-2 transition-colors',
          activeTab === index
            ? 'border-primary text-primary'
            : 'border-transparent text-gray-600 hover:text-gray-800'
        ]"
      >
        {{ tab.icon }} {{ tab.label }}
        <span v-if="tab.badge" class="ml-2 badge bg-primary text-white">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- Tab content -->
    <div class="animate-fade-in">
      <!-- Table View -->
      <TableView v-if="activeTab === 0" />

      <!-- City View -->
      <CityView v-else-if="activeTab === 1" />

      <!-- Price View -->
      <PriceView v-else-if="activeTab === 2" />

      <!-- Map View -->
      <MapView v-else-if="activeTab === 3" />

      <!-- New Listings -->
      <NewListingsPage v-else-if="activeTab === 4" />

      <!-- Anomalies -->
      <AnomaliesPage v-else-if="activeTab === 5" />

      <!-- Stats -->
      <StatsPage v-else-if="activeTab === 6" />

      <!-- Photos -->
      <PhotosPage v-else-if="activeTab === 7" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useListingsStore } from '../stores/listings'
import { useStatsStore } from '../stores/stats'
import TableView from './views/TableView.vue'
import CityView from './views/CityView.vue'
import PriceView from './views/PriceView.vue'
import MapView from './views/MapView.vue'
import NewListingsPage from './detail/NewListingsPage.vue'
import AnomaliesPage from './detail/AnomaliesPage.vue'
import StatsPage from './detail/StatsPage.vue'
import PhotosPage from './detail/PhotosPage.vue'

const activeTab = ref(0)
const listings = useListingsStore()
const stats = useStatsStore()

const tabs = computed(() => [
  {
    label: 'Tableau',
    icon: '📊',
    badge: listings.appliedFilters.length
  },
  {
    label: 'Par Ville',
    icon: '🏙️',
    badge: listings.uniqueCities.length
  },
  {
    label: 'Par Prix',
    icon: '💰',
    badge: null
  },
  {
    label: 'Carte',
    icon: '🗺️',
    badge: null
  },
  {
    label: 'Nouveautés',
    icon: '✨',
    badge: null
  },
  {
    label: 'Anomalies',
    icon: '🚨',
    badge: stats.highAnomaliesCount + stats.goodDealsCount
  },
  {
    label: 'Stats',
    icon: '📈',
    badge: null
  },
  {
    label: 'Photos',
    icon: '🖼️',
    badge: null
  }
])
</script>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-in;
}
</style>
