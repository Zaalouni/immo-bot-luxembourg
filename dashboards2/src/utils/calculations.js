export function calculateMedian(values) {
  if (!values || values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2
}

export function calculateAverage(values) {
  if (!values || values.length === 0) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

export function getAnomalyFlag(price, median) {
  if (!price || !median) return null
  if (price > median * 2.5) return 'HIGH'
  if (price < median * 0.7) return 'GOOD_DEAL'
  return null
}

export function groupByCity(listings) {
  const grouped = {}
  listings.forEach(listing => {
    if (!grouped[listing.city]) grouped[listing.city] = []
    grouped[listing.city].push(listing)
  })
  return grouped
}

export function groupByPriceRange(listings) {
  const ranges = {
    '< 1500€': { min: 0, max: 1500, listings: [] },
    '1500€ - 2000€': { min: 1500, max: 2000, listings: [] },
    '2000€ - 2500€': { min: 2000, max: 2500, listings: [] },
    '> 2500€': { min: 2500, max: Infinity, listings: [] }
  }

  listings.forEach(listing => {
    for (const [key, range] of Object.entries(ranges)) {
      if (listing.price >= range.min && listing.price < range.max) {
        range.listings.push(listing)
        break
      }
    }
  })

  return ranges
}

export function groupBySite(listings) {
  const grouped = {}
  listings.forEach(listing => {
    if (!grouped[listing.site]) grouped[listing.site] = []
    grouped[listing.site].push(listing)
  })
  return grouped
}

export function calculateCityStats(listings, city) {
  const cityListings = listings.filter(l => l.city === city)
  if (cityListings.length === 0) return null

  const prices = cityListings.map(l => l.price)
  const surfaces = cityListings.map(l => l.surface).filter(s => s > 0)

  return {
    count: cityListings.length,
    avg_price: Math.round(calculateAverage(prices)),
    median_price: Math.round(calculateMedian(prices)),
    min_price: Math.min(...prices),
    max_price: Math.max(...prices),
    avg_surface: surfaces.length > 0 ? Math.round(calculateAverage(surfaces)) : 0,
    avg_price_m2: surfaces.length > 0
      ? Math.round(calculateAverage(prices.map((p, i) => surfaces[i] > 0 ? p / surfaces[i] : 0)))
      : 0
  }
}

export function getPriceRangeLabel(price) {
  if (price < 1500) return '< 1500€'
  if (price < 2000) return '1500€ - 2000€'
  if (price < 2500) return '2000€ - 2500€'
  return '> 2500€'
}

export function getPriceRangeColor(price) {
  if (price < 1500) return '#10B981'
  if (price < 2000) return '#3B82F6'
  if (price < 2500) return '#F59E0B'
  return '#EF4444'
}

export function sortListings(listings, field, ascending = true) {
  const sorted = [...listings]
  sorted.sort((a, b) => {
    let aVal = a[field]
    let bVal = b[field]

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = bVal.toLowerCase()
      return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }

    if (ascending) return aVal - bVal
    return bVal - aVal
  })

  return sorted
}

export function calculatePercentiles(listings, field) {
  if (!listings.length) return { p25: 0, p50: 0, p75: 0 }

  const values = listings.map(l => l[field]).sort((a, b) => a - b)
  const len = values.length

  return {
    p25: values[Math.floor(len * 0.25)],
    p50: values[Math.floor(len * 0.5)],
    p75: values[Math.floor(len * 0.75)]
  }
}

export function calculateSimilarity(listing1, listing2) {
  let similarity = 0
  const maxDist = 2

  // Same city
  if (listing1.city === listing2.city) similarity += 0.3

  // Similar price (within 5%)
  const priceDiff = Math.abs(listing1.price - listing2.price) / listing1.price
  if (priceDiff < 0.05) similarity += 0.3

  // Similar surface (within 10m²)
  const surfaceDiff = Math.abs(listing1.surface - listing2.surface)
  if (surfaceDiff <= 10) similarity += 0.2

  // Similar location (within 2km)
  const distance = Math.sqrt(
    Math.pow(listing1.latitude - listing2.latitude, 2) +
    Math.pow(listing1.longitude - listing2.longitude, 2)
  )
  if (distance <= maxDist) similarity += 0.2

  return Math.min(similarity, 1)
}
