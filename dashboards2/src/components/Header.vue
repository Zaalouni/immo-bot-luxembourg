<template>
  <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
    <div class="container mx-auto px-4 py-4">
      <!-- Title and nav -->
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-3xl font-bold text-primary">🏠 ImmoLux Dashboard2</h1>
          <p class="text-sm text-gray-600">Annonces immobilières à Luxembourg</p>
        </div>
        <div class="text-right">
          <p class="text-sm text-gray-600">
            <i class="fas fa-sync"></i>
            Mis à jour: {{ updateTime }}
          </p>
        </div>
      </div>

      <!-- Stats cards -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div class="stat-card animate-fade-in">
          <div class="stat-value">{{ stats.globalStats.total || 0 }}</div>
          <div class="stat-label">Annonces</div>
        </div>

        <div class="stat-card animate-fade-in" style="animation-delay: 0.1s">
          <div class="stat-value">{{ formatCurrency(stats.globalStats.avg_price) }}</div>
          <div class="stat-label">Prix moy.</div>
        </div>

        <div class="stat-card animate-fade-in" style="animation-delay: 0.2s">
          <div class="stat-value">{{ listings.uniqueCities.length }}</div>
          <div class="stat-label">Villes</div>
        </div>

        <div class="stat-card animate-fade-in" style="animation-delay: 0.3s">
          <div class="stat-value">{{ stats.globalStats.avg_surface || 0 }}m²</div>
          <div class="stat-label">Surface moy.</div>
        </div>

        <div class="stat-card animate-fade-in" style="animation-delay: 0.4s">
          <div class="stat-value text-warning">
            {{ stats.highAnomaliesCount }}
            <span class="text-danger">{{ stats.goodDealsCount }}</span>
          </div>
          <div class="stat-label">🚨 / 🎉</div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useListingsStore } from '../stores/listings'
import { useStatsStore } from '../stores/stats'
import { formatCurrency } from '../utils/formatting'

const listings = useListingsStore()
const stats = useStatsStore()

const updateTime = computed(() => {
  const now = new Date()
  return now.toLocaleString('fr-LU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>

<style scoped>
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
  opacity: 0;
}
</style>
