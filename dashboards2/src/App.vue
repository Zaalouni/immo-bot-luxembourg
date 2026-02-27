<template>
  <div class="min-h-screen bg-gray-50">
    <Header v-if="!loading" />

    <main class="container mx-auto px-4 py-6">
      <div v-if="loading" class="text-center py-12">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p class="mt-4 text-gray-600">Chargement des données...</p>
      </div>

      <template v-else>
        <Filters />
        <Tabs />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useListingsStore } from './stores/listings'
import { useStatsStore } from './stores/stats'
import { loadAll } from './services/dataLoader'
import Header from './components/Header.vue'
import Filters from './components/Filters.vue'
import Tabs from './components/Tabs.vue'

const loading = ref(true)
const listings = useListingsStore()
const stats = useStatsStore()

onMounted(async () => {
  try {
    await loadAll(listings, stats)
  } catch (error) {
    console.error('Error loading data:', error)
  } finally {
    loading.value = false
  }
})
</script>
