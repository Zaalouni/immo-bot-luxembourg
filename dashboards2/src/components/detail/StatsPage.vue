<template>
  <div class="space-y-6">
    <!-- Global stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card">
        <div class="stat-value">{{ stats.globalStats.total || 0 }}</div>
        <div class="stat-label">Annonces Total</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ formatCurrency(stats.globalStats.avg_price) }}</div>
        <div class="stat-label">Prix Moyen</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ formatCurrency(stats.globalStats.min_price) }}</div>
        <div class="stat-label">Prix Min</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ formatCurrency(stats.globalStats.max_price) }}</div>
        <div class="stat-label">Prix Max</div>
      </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div class="card">
        <div class="stat-value">{{ stats.globalStats.avg_surface || 0 }}m²</div>
        <div class="stat-label">Surface Moyenne</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ listings.uniqueCities.length }}</div>
        <div class="stat-label">Villes</div>
      </div>
      <div class="card">
        <div class="stat-value">{{ listings.uniqueSites.length }}</div>
        <div class="stat-label">Sites Source</div>
      </div>
    </div>

    <!-- Distribution by site -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Distribution par Site</h3>
      <div class="space-y-2">
        <div v-for="site in listings.uniqueSites" :key="site" class="flex items-center gap-3">
          <span
            class="inline-block w-3 h-3 rounded-full"
            :style="{ backgroundColor: stats.getSiteColor(site) }"
          ></span>
          <span class="flex-1">{{ site }}</span>
          <span class="font-bold">{{ getSiteCount(site) }}</span>
          <div class="w-32 bg-gray-200 rounded-full h-2">
            <div
              class="h-2 rounded-full"
              :style="{
                width: (getSiteCount(site) / (stats.globalStats.total || 1)) * 100 + '%',
                backgroundColor: stats.getSiteColor(site)
              }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Top 10 cities -->
    <div class="card">
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Top 10 Villes</h3>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="table-header">
            <tr>
              <th class="text-left">Ville</th>
              <th class="text-right">Annonces</th>
              <th class="text-right">Prix moy</th>
              <th class="text-right">Médiane</th>
              <th class="text-right">Min - Max</th>
              <th class="text-right">Surface moy</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="city in stats.topCities.slice(0, 10)" :key="city.city">
              <td class="font-medium">{{ city.city }}</td>
              <td class="text-right">{{ city.count }}</td>
              <td class="text-right">{{ formatCurrency(city.avg_price) }}</td>
              <td class="text-right font-bold">{{ formatCurrency(city.median_price) }}</td>
              <td class="text-right text-xs text-gray-600">
                {{ formatCurrency(city.min_price) }} - {{ formatCurrency(city.max_price) }}
              </td>
              <td class="text-right">{{ city.avg_surface }}m²</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useListingsStore } from '../../stores/listings'
import { useStatsStore } from '../../stores/stats'
import { formatCurrency } from '../../utils/formatting'

const listings = useListingsStore()
const stats = useStatsStore()

const getSiteCount = (site) => {
  return listings.allListings.filter(l => l.site === site).length
}
</script>
