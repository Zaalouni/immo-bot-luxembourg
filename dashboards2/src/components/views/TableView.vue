<template>
  <div class="card overflow-x-auto">
    <table>
      <thead class="table-header">
        <tr>
          <th @click="toggleSort('site')" class="cursor-pointer">
            Site {{ getSortIcon('site') }}
          </th>
          <th @click="toggleSort('city')" class="cursor-pointer">
            Ville {{ getSortIcon('city') }}
          </th>
          <th @click="toggleSort('price')" class="cursor-pointer">
            Prix {{ getSortIcon('price') }}
          </th>
          <th @click="toggleSort('rooms')" class="cursor-pointer">
            Pièces {{ getSortIcon('rooms') }}
          </th>
          <th @click="toggleSort('surface')" class="cursor-pointer">
            Surface {{ getSortIcon('surface') }}
          </th>
          <th @click="toggleSort('price_m2')" class="cursor-pointer">
            €/m² {{ getSortIcon('price_m2') }}
          </th>
          <th @click="toggleSort('time_ago')" class="cursor-pointer">
            Temps {{ getSortIcon('time_ago') }}
          </th>
          <th>Anomalie</th>
          <th>Titre</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="listing in sortedListings" :key="listing.listing_id">
          <td>
            <span
              class="site-badge"
              :style="{ backgroundColor: stats.getSiteColor(listing.site) }"
            >
              {{ listing.site.split('.')[0] }}
            </span>
          </td>
          <td class="font-medium">{{ listing.city }}</td>
          <td class="font-bold text-primary">{{ formatCurrency(listing.price) }}</td>
          <td>{{ listing.rooms || '—' }}</td>
          <td>{{ listing.surface }}m²</td>
          <td>{{ formatNumber(listing.price_m2, 0) }}€</td>
          <td class="text-sm text-gray-600">{{ listing.time_ago }}</td>
          <td>
            <AnomalyBadge :flag="listing.price_anomaly" />
          </td>
          <td>
            <a
              :href="listing.url"
              target="_blank"
              class="text-blue-600 hover:underline text-sm"
            >
              {{ truncate(listing.title, 40) }}
            </a>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="sortedListings.length === 0" class="text-center py-8 text-gray-500">
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
import { sortListings } from '../../utils/calculations'
import AnomalyBadge from '../common/AnomalyBadge.vue'

const listings = useListingsStore()
const stats = useStatsStore()

const sortColumn = ref('time_ago')
const sortAscending = ref(false)

const sortedListings = computed(() => {
  return sortListings(listings.appliedFilters, sortColumn.value, sortAscending.value)
})

const toggleSort = (column) => {
  if (sortColumn.value === column) {
    sortAscending.value = !sortAscending.value
  } else {
    sortColumn.value = column
    sortAscending.value = true
  }
}

const getSortIcon = (column) => {
  if (sortColumn.value !== column) return '▼'
  return sortAscending.value ? '▲' : '▼'
}
</script>
