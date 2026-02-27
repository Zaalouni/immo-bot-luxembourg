import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useStatsStore = defineStore('stats', () => {
  // State
  const globalStats = ref({})
  const anomalies = ref({})
  const marketStats = ref({})
  const SITE_COLORS = {
    'Athome.lu': '#9966FF',
    'Nextimmo.lu': '#FF9F40',
    'VIVI.lu': '#FFCE56',
    'SothebysRealty.lu': '#FF6384',
    'Newimmo.lu': '#36A2EB',
    'Immotop.lu': '#4BC0C0',
    'Floor.lu': '#2ECC71'
  }

  const PRICE_RANGES = [
    { label: '< 1500€', min: 0, max: 1500, color: '#10B981' },
    { label: '1500€ - 2000€', min: 1500, max: 2000, color: '#3B82F6' },
    { label: '2000€ - 2500€', min: 2000, max: 2500, color: '#F59E0B' },
    { label: '> 2500€', min: 2500, max: Infinity, color: '#EF4444' }
  ]

  // Computed
  const highAnomaliesCount = computed(() => {
    return Object.values(anomalies.value).filter(a => a === 'HIGH').length
  })

  const goodDealsCount = computed(() => {
    return Object.values(anomalies.value).filter(a => a === 'GOOD_DEAL').length
  })

  const topCities = computed(() => {
    return Object.entries(marketStats.value)
      .sort(([, a], [, b]) => b.count - a.count)
      .slice(0, 10)
      .map(([city, stats]) => ({ city, ...stats }))
  })

  // Actions
  const loadStats = (data) => {
    globalStats.value = data
  }

  const loadAnomalies = (data) => {
    anomalies.value = data
  }

  const loadMarketStats = (data) => {
    marketStats.value = data
  }

  const getCityStats = (city) => {
    return marketStats.value[city] || {}
  }

  const getSiteColor = (site) => {
    return SITE_COLORS[site] || '#6B7280'
  }

  const getSiteCount = (site, listings) => {
    return listings.filter(l => l.site === site).length
  }

  const getPriceRangeColor = (price) => {
    for (const range of PRICE_RANGES) {
      if (price >= range.min && price < range.max) {
        return range.color
      }
    }
    return '#6B7280'
  }

  return {
    globalStats,
    anomalies,
    marketStats,
    SITE_COLORS,
    PRICE_RANGES,
    highAnomaliesCount,
    goodDealsCount,
    topCities,
    loadStats,
    loadAnomalies,
    loadMarketStats,
    getCityStats,
    getSiteColor,
    getSiteCount,
    getPriceRangeColor
  }
})
