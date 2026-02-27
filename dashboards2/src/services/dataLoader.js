// Helper to get data URL - hardcoded for GitHub Pages
// Note: /dist/ is removed because peaceiris/actions-gh-pages serves from dashboards2/ directly
const API_BASE = 'https://zaalouni.github.io/immo-bot-luxembourg/dashboards2/';

function getDataUrl(filename) {
  return `${API_BASE}data/${filename}`
}

export async function loadAll(listingsStore, statsStore) {
  try {
    const [listings, statsData, anomalies, marketStats] = await Promise.all([
      loadListings(),
      loadStats(),
      loadAnomalies(),
      loadMarketStats()
    ])

    listingsStore.loadListings(listings)
    statsStore.loadStats(statsData)
    statsStore.loadAnomalies(anomalies)
    statsStore.loadMarketStats(marketStats)

    return { listings, statsData, anomalies, marketStats }
  } catch (error) {
    console.error('Failed to load data:', error)
    throw error
  }
}

export async function loadListings() {
  const response = await fetch(getDataUrl('listings.json'))
  if (!response.ok) throw new Error('Failed to load listings')
  return response.json()
}

export async function loadStats() {
  try {
    const response = await fetch(getDataUrl('stats.js'))
    const text = await response.text()
    // Extract STATS object from: const STATS = {...}
    const match = text.match(/const\s+STATS\s*=\s*({[\s\S]*?});/)
    if (!match) throw new Error('STATS not found in stats.js')
    return JSON.parse(match[1])
  } catch (error) {
    console.error('Failed to parse stats.js:', error)
    return {}
  }
}

export async function loadAnomalies() {
  try {
    const response = await fetch(getDataUrl('anomalies.js'))
    const text = await response.text()
    // Extract ANOMALIES object from: const ANOMALIES = {...}
    const match = text.match(/const\s+ANOMALIES\s*=\s*({[\s\S]*?});/)
    if (!match) throw new Error('ANOMALIES not found in anomalies.js')
    const obj = JSON.parse(match[1])
    // Flatten if needed - ANOMALIES might be {listing_id: 'HIGH'}
    return obj
  } catch (error) {
    console.error('Failed to parse anomalies.js:', error)
    return {}
  }
}

export async function loadMarketStats() {
  try {
    const response = await fetch(getDataUrl('market-stats.js'))
    const text = await response.text()
    // Extract MARKET_STATS object from: const MARKET_STATS = {...}
    const match = text.match(/const\s+MARKET_STATS\s*=\s*({[\s\S]*?});/)
    if (!match) throw new Error('MARKET_STATS not found in market-stats.js')
    return JSON.parse(match[1])
  } catch (error) {
    console.error('Failed to parse market-stats.js:', error)
    return {}
  }
}
