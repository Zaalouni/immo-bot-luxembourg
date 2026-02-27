import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useListingsStore = defineStore('listings', () => {
  // State
  const allListings = ref([])
  const selectedCity = ref(null)
  const priceRange = ref({ min: 0, max: 10000 })
  const selectedSites = ref([])
  const surfaceMin = ref(0)
  const dateRange = ref({ from: null, to: null })

  // Computed
  const uniqueCities = computed(() => {
    const cities = [...new Set(allListings.value.map(l => l.city))]
    return cities.sort()
  })

  const uniqueSites = computed(() => {
    return [...new Set(allListings.value.map(l => l.site))]
  })

  const appliedFilters = computed(() => {
    return allListings.value.filter(listing => {
      // City filter
      if (selectedCity.value && listing.city !== selectedCity.value) return false

      // Price range filter
      if (listing.price < priceRange.value.min || listing.price > priceRange.value.max) {
        return false
      }

      // Site filter
      if (selectedSites.value.length && !selectedSites.value.includes(listing.site)) {
        return false
      }

      // Surface filter
      if (listing.surface < surfaceMin.value) return false

      // Date range filter
      if (dateRange.value.from || dateRange.value.to) {
        const pubDate = new Date(listing.published_at)
        if (dateRange.value.from && pubDate < new Date(dateRange.value.from)) return false
        if (dateRange.value.to && pubDate > new Date(dateRange.value.to)) return false
      }

      return true
    })
  })

  const filterCount = computed(() => {
    let count = 0
    if (selectedCity.value) count++
    if (priceRange.value.min > 0 || priceRange.value.max < 10000) count++
    if (selectedSites.value.length) count++
    if (surfaceMin.value > 0) count++
    if (dateRange.value.from || dateRange.value.to) count++
    return count
  })

  // Actions
  const loadListings = (data) => {
    allListings.value = data
  }

  const setSelectedCity = (city) => {
    selectedCity.value = city
  }

  const setPriceRange = (min, max) => {
    priceRange.value = { min, max }
  }

  const toggleSite = (site) => {
    const index = selectedSites.value.indexOf(site)
    if (index > -1) {
      selectedSites.value.splice(index, 1)
    } else {
      selectedSites.value.push(site)
    }
  }

  const setSites = (sites) => {
    selectedSites.value = [...sites]
  }

  const setSurfaceMin = (surface) => {
    surfaceMin.value = surface
  }

  const setDateRange = (from, to) => {
    dateRange.value = { from, to }
  }

  const resetFilters = () => {
    selectedCity.value = null
    priceRange.value = { min: 0, max: 10000 }
    selectedSites.value = []
    surfaceMin.value = 0
    dateRange.value = { from: null, to: null }
  }

  const getListingById = (listingId) => {
    return allListings.value.find(l => l.listing_id === listingId)
  }

  return {
    allListings,
    selectedCity,
    priceRange,
    selectedSites,
    surfaceMin,
    dateRange,
    uniqueCities,
    uniqueSites,
    appliedFilters,
    filterCount,
    loadListings,
    setSelectedCity,
    setPriceRange,
    toggleSite,
    setSites,
    setSurfaceMin,
    setDateRange,
    resetFilters,
    getListingById
  }
})
