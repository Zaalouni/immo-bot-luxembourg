export function formatCurrency(value) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('fr-LU', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('fr-LU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

export function formatPricePerM2(price, surface) {
  if (!price || !surface || surface === 0) return '—'
  const priceM2 = price / surface
  return formatCurrency(priceM2) + '/m²'
}

export function formatDate(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('fr-LU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(date)
}

export function formatDateTime(dateStr) {
  if (!dateStr) return '—'
  const date = new Date(dateStr)
  return new Intl.DateTimeFormat('fr-LU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export function formatSurface(surface) {
  if (!surface) return '—'
  return formatNumber(surface) + ' m²'
}

export function formatRooms(rooms) {
  if (!rooms) return '—'
  return rooms + ' pièce' + (rooms > 1 ? 's' : '')
}

export function truncate(text, length = 50) {
  if (!text) return '—'
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

export function timeAgo(dateStr) {
  if (!dateStr) return '—'

  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)

  if (seconds < 60) return 'À l\'instant'
  if (seconds < 3600) return Math.floor(seconds / 60) + ' min'
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h'
  if (seconds < 604800) return Math.floor(seconds / 86400) + 'j'

  // More than a week: show date
  return formatDate(dateStr)
}

export function getSiteColor(site) {
  const colors = {
    'Athome.lu': '#9966FF',
    'Nextimmo.lu': '#FF9F40',
    'VIVI.lu': '#FFCE56',
    'SothebysRealty.lu': '#FF6384',
    'Newimmo.lu': '#36A2EB',
    'Immotop.lu': '#4BC0C0',
    'Floor.lu': '#2ECC71'
  }
  return colors[site] || '#6B7280'
}
