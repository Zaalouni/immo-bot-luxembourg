# ImmoLux Dashboard2 - Modern Real Estate Dashboard

Modern, responsive dashboard for viewing Luxembourg real estate listings using Vue 3, Tailwind CSS, and Leaflet maps.

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ and npm (or yarn)

### Installation & Development

```bash
# Install dependencies
npm install

# Start development server (runs on http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
dashboards2/
├── src/
│   ├── main.js                    # Vue app entry point
│   ├── App.vue                    # Root component
│   ├── components/
│   │   ├── Header.vue             # Stats header
│   │   ├── Filters.vue            # Filter controls (5 filters)
│   │   ├── Tabs.vue               # Tab navigation
│   │   ├── views/
│   │   │   ├── TableView.vue      # Sortable table
│   │   │   ├── CityView.vue       # Group by city
│   │   │   ├── PriceView.vue      # Group by price range
│   │   │   └── MapView.vue        # Leaflet map
│   │   ├── detail/
│   │   │   ├── NewListingsPage.vue    # Recent listings
│   │   │   ├── AnomaliesPage.vue      # Price anomalies
│   │   │   ├── StatsPage.vue         # Statistics
│   │   │   ├── PhotosPage.vue        # Photo gallery
│   │   │   ├── MapAdvanced.vue       # Advanced map
│   │   │   └── NearbyPage.vue        # Nearby listings
│   │   └── common/
│   │       └── AnomalyBadge.vue   # Reusable badge
│   ├── stores/
│   │   ├── listings.js            # Pinia: listing state + filters
│   │   └── stats.js               # Pinia: global statistics
│   ├── services/
│   │   └── dataLoader.js          # Load JSON/JS data files
│   ├── utils/
│   │   ├── formatting.js          # Format currency, dates, etc.
│   │   └── calculations.js        # Stats, grouping, sorting
│   └── styles/
│       └── tailwind.css           # Tailwind + custom components
├── public/
│   ├── data/                      # Synced from dashboards/data/
│   ├── manifest.json              # PWA manifest
│   └── sw.js                      # Service worker
├── index.html                     # Entry HTML
├── vite.config.js                 # Build configuration
├── tailwind.config.js             # Tailwind theme
├── postcss.config.js              # PostCSS setup
├── package.json                   # Dependencies
└── README.md                      # This file
```

## 🛠️ Technology Stack

| Technology | Purpose |
|-----------|---------|
| **Vue 3** | UI framework (Composition API) |
| **Vite** | Build tool (fast bundling, hot reload) |
| **Pinia** | State management (Vuex successor) |
| **Tailwind CSS** | Utility-first CSS framework |
| **Leaflet** | Interactive map library |
| **PostCSS** | CSS processing |

## 📊 Features

### Filters (5)
1. **City**: Dropdown with all unique cities
2. **Price**: Min/max range inputs
3. **Site**: Multi-select checkboxes for property websites
4. **Surface**: Minimum surface area (m²)
5. **Date**: Date range picker for publication dates

### Views (8 tabs)
1. **Tableau** (Table): Sortable table with 9 columns (site, city, price, rooms, surface, €/m², time, anomaly, title)
2. **Par Ville** (By City): City grouping cards with stats (count, avg price, median, surface)
3. **Par Prix** (By Price): 4 price ranges with listing cards
4. **Carte** (Map): Leaflet interactive map with color-coded markers by site
5. **Nouveautés** (New): Most recent listings with time badges
6. **Anomalies** (Anomalies): HIGH-priced and GOOD_DEAL listings
7. **Stats** (Statistics): Global stats, per-site distribution, top 10 cities
8. **Photos** (Gallery): Photo gallery grid (placeholder)

### Data
- **Source**: `/public/data/` (synced from `/dashboards/data/`)
- **Files**: listings.json, stats.js, anomalies.js, market-stats.js
- **Updates**: Sync happens automatically when `dashboard_generator.py` runs

## 🎨 UI/UX

### Components
- **Stat Cards**: Display total, avg price, cities, surface, anomalies
- **Filters Panel**: Compact, intuitive filter controls with real-time updates
- **Sortable Table**: Click headers to sort ascending/descending
- **Map**: Lazy-loaded Leaflet map with popup details
- **Price Ranges**: Color-coded grouping (green < 1500€, blue 1500-2000€, orange 2000-2500€, red > 2500€)
- **Anomaly Badges**: Visual indicators for HIGH (🚨) and GOOD_DEAL (🎉) listings

### Responsive Design
- **Mobile**: 1-column layout, touch-friendly
- **Tablet**: 2-column layout, adjusted spacing
- **Desktop**: 3+ column layout, full functionality
- **Dark Mode**: Not implemented (can be added via Tailwind)

## 🔄 Data Flow

```
dashboard_generator.py (Python)
           ↓
   dashboards/data/ (JSON/JS files)
           ↓
   sync_data_to_dashboard2()
           ↓
   dashboards2/public/data/
           ↓
   dataLoader.js (Frontend)
           ↓
   Pinia Stores (listings, stats)
           ↓
   Vue Components (render UI)
```

## 📦 Build & Deployment

### Development Build
```bash
npm run dev
# Runs on http://localhost:5173
# Hot module reload enabled
```

### Production Build
```bash
npm run build
# Creates optimized dist/ folder
# Code splitting: app, pinia, leaflet bundles
# Minified with terser
# ~298 KB total size
```

### Serve Production
```bash
npm run preview
# Serves dist/ folder locally
```

### Deploy to Server
```bash
# Copy dist/ folder to web server
scp -r dist/ user@server:/var/www/dashboard2/

# Or use Docker
docker build -t dashboard2 .
docker run -p 3000:80 dashboard2
```

## 🧪 Testing

### Manual Testing Checklist
- [ ] All 5 filters work and update results
- [ ] All 8 tabs load without errors
- [ ] Table sorting works (click headers)
- [ ] Map loads when tab clicked
- [ ] Price ranges group correctly
- [ ] Anomalies display correctly
- [ ] Mobile responsive (test on phone or devtools)
- [ ] Console has no errors
- [ ] Service worker registers (Application tab)
- [ ] PWA installable (if served over HTTPS)

### Regression Tests
```bash
# From repo root
python -m pytest test_dashboard_regression.py -v
```

## 🔒 PWA (Progressive Web App)

Dashboard2 is PWA-ready:
- **Manifest**: `public/manifest.json` - app metadata
- **Service Worker**: `public/sw.js` - offline support
- **Installation**: "Add to Home Screen" button appears on mobile
- **Offline**: Cached assets available when offline

## 🚀 Performance

- **Build Time**: ~3 seconds
- **Bundle Size**: 298 KB (gzipped)
- **Code Splitting**: 3 chunks (app, pinia, leaflet)
- **Load Time**: ~1 second (on fast connection)
- **Lighthouse**: Target 90+ Performance score

### Optimization Techniques
- Code splitting (Vite automatic)
- Tree-shaking (removes unused code)
- Minification (terser)
- CSS purging (Tailwind)
- Lazy-loading images
- Leaflet loaded on-demand

## 🛣️ Roadmap

### Immediate
- [x] Core filters and views
- [x] Table with sorting
- [x] Map integration
- [x] Statistics page
- [ ] Photo gallery integration (placeholder done)

### Short Term
- [ ] Advanced map features (clustering, heatmap)
- [ ] Geolocation-based nearby listings
- [ ] Export to CSV/PDF
- [ ] Favorites/bookmarking
- [ ] Search bar (free text search)

### Medium Term
- [ ] Dark mode toggle
- [ ] Custom price alerts
- [ ] Saved filters
- [ ] Comparison tool
- [ ] Historical price trends

### Long Term
- [ ] AI-powered recommendations
- [ ] ML-based price predictions
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Social features (sharing, comments)

## 🐛 Troubleshooting

### "npm install fails"
```bash
# Clear cache and retry
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### "Port 5173 is already in use"
```bash
# Use different port
npm run dev -- --port 5174
```

### "Build fails with terser error"
```bash
# Reinstall terser
npm install --save-dev terser@latest
npm run build
```

### "Map not loading"
- Check network tab for Leaflet CDN errors
- Verify leaflet package installed: `npm list leaflet`
- Check browser console for errors

### "Data not loading"
- Verify `public/data/` folder exists and has JSON files
- Check Network tab for 404 errors on /data/ requests
- Verify CORS headers if served from different domain

## 📝 Configuration

### Environment Variables
Create `.env.local` to override defaults:

```env
VITE_API_BASE=http://localhost:3000
VITE_ENABLE_DEBUG=true
```

### Tailwind Customization
Edit `tailwind.config.js` to customize:
- Colors (primary, secondary, danger, etc.)
- Font family
- Breakpoints
- Shadows

### Vite Configuration
Edit `vite.config.js` to modify:
- Build output directory
- Server port
- Public path
- Code splitting chunks

## 📖 Documentation

- [Vue 3 Docs](https://vuejs.org/)
- [Vite Docs](https://vitejs.dev/)
- [Pinia Docs](https://pinia.vuejs.org/)
- [Tailwind CSS Docs](https://tailwindcss.com/)
- [Leaflet Docs](https://leafletjs.com/)

## 📄 License

This project is part of Immo-Bot Luxembourg. All rights reserved.

## 🤝 Contributing

To contribute to Dashboard2:

1. Create a feature branch
2. Make changes
3. Run tests: `npm run test`
4. Submit pull request

## 📞 Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review console errors (F12 → Console)
- Check Network tab for failed requests
- Create an issue on GitHub

---

**Version**: 1.0.0
**Last Updated**: 2026-02-27
**Built with**: Vue 3 + Vite + Tailwind CSS
