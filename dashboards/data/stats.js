// Genere le 20/02/2026 14:27
const STATS = {
  "total": 73,
  "avg_price": 2139,
  "min_price": 1500,
  "max_price": 2400,
  "avg_surface": 93,
  "cities": 48,
  "sites": {
    "Remax.lu": 3,
    "Nextimmo.lu": 18,
    "Wortimmo.lu": 3,
    "Newimmo.lu": 3,
    "VIVI.lu": 6,
    "Immotop.lu": 2,
    "Athome.lu": 38
  },
  "by_city": [
    {
      "city": "Bertrange",
      "count": 6,
      "avg_price": 2106
    },
    {
      "city": "Luxembourg-Belair",
      "count": 4,
      "avg_price": 2237
    },
    {
      "city": "Luxembourg-Hollerich",
      "count": 3,
      "avg_price": 2216
    },
    {
      "city": "Luxembourg-Bonnevoie",
      "count": 3,
      "avg_price": 2216
    },
    {
      "city": "Senningerberg",
      "count": 3,
      "avg_price": 2196
    },
    {
      "city": "Luxembourg-Kirchberg",
      "count": 3,
      "avg_price": 2316
    },
    {
      "city": "Dudelange",
      "count": 2,
      "avg_price": 2100
    },
    {
      "city": "Mamer",
      "count": 2,
      "avg_price": 2075
    },
    {
      "city": "Luxembourg",
      "count": 2,
      "avg_price": 1950
    },
    {
      "city": "Reuler",
      "count": 2,
      "avg_price": 1850
    },
    {
      "city": "Hautcharage",
      "count": 2,
      "avg_price": 1915
    },
    {
      "city": "Esch-sur-Alzette",
      "count": 2,
      "avg_price": 1925
    },
    {
      "city": "Belvaux",
      "count": 2,
      "avg_price": 2100
    },
    {
      "city": "Luxembourg-Centre ville",
      "count": 2,
      "avg_price": 2100
    },
    {
      "city": "Bridel",
      "count": 2,
      "avg_price": 2250
    },
    {
      "city": "Emerange",
      "count": 1,
      "avg_price": 2400
    },
    {
      "city": "Luxembourg-Hamm",
      "count": 1,
      "avg_price": 1890
    },
    {
      "city": "Wellenstein",
      "count": 1,
      "avg_price": 1800
    },
    {
      "city": "Olm",
      "count": 1,
      "avg_price": 2300
    },
    {
      "city": "Luxembourg-Pfaffenthal",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Luxembourg Pfaffenthall",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Luxembourg Cents",
      "count": 1,
      "avg_price": 2300
    },
    {
      "city": "Frisange",
      "count": 1,
      "avg_price": 2000
    },
    {
      "city": "Luxembourg Neudorf",
      "count": 1,
      "avg_price": 2000
    },
    {
      "city": "Weiswampach",
      "count": 1,
      "avg_price": 1500
    },
    {
      "city": "Bissen",
      "count": 1,
      "avg_price": 2000
    },
    {
      "city": "Sanem",
      "count": 1,
      "avg_price": 2050
    },
    {
      "city": "Niederanven",
      "count": 1,
      "avg_price": 2000
    },
    {
      "city": "Junglinster",
      "count": 1,
      "avg_price": 1950
    },
    {
      "city": "Filsdorf",
      "count": 1,
      "avg_price": 2350
    },
    {
      "city": "Luxembourg-Weimerskirch",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Alzingen",
      "count": 1,
      "avg_price": 2350
    },
    {
      "city": "Bereldange",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Gonderange",
      "count": 1,
      "avg_price": 2200
    },
    {
      "city": "Hassel",
      "count": 1,
      "avg_price": 1850
    },
    {
      "city": "Steinsel",
      "count": 1,
      "avg_price": 2250
    },
    {
      "city": "Hesperange",
      "count": 1,
      "avg_price": 2400
    },
    {
      "city": "Luxembourg-Gasperich - Cloche d'or",
      "count": 1,
      "avg_price": 2250
    },
    {
      "city": "Luxembourg-Gare",
      "count": 1,
      "avg_price": 2390
    },
    {
      "city": "Roeser",
      "count": 1,
      "avg_price": 2300
    },
    {
      "city": "Mondorf-Les-Bains",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Sprinkange",
      "count": 1,
      "avg_price": 2100
    },
    {
      "city": "Garnich",
      "count": 1,
      "avg_price": 2400
    },
    {
      "city": "Belval",
      "count": 1,
      "avg_price": 2375
    },
    {
      "city": "Brouch (Mersch)",
      "count": 1,
      "avg_price": 2400
    },
    {
      "city": "Rollingen",
      "count": 1,
      "avg_price": 2150
    },
    {
      "city": "Luxembourg-Centre Ville",
      "count": 1,
      "avg_price": 2350
    },
    {
      "city": "Contern",
      "count": 1,
      "avg_price": 2400
    }
  ],
  "by_price_range": {
    "< 1500": 0,
    "1500 - 2000": 15,
    "2000 - 2500": 58,
    "> 2500": 0
  }
};
const SITE_COLORS = {
  "Remax.lu": "#FF6384",
  "Nextimmo.lu": "#36A2EB",
  "Wortimmo.lu": "#FFCE56",
  "Newimmo.lu": "#4BC0C0",
  "VIVI.lu": "#9966FF",
  "Immotop.lu": "#FF9F40",
  "Athome.lu": "#2ECC71"
};
