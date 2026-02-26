// Genere le 26/02/2026 22:10
// Statistiques detaillees par ville (median, avg, price_m2, etc.)
const MARKET_STATS = {
  "Bridel": {
    "count": 4,
    "avg_price": 2187,
    "median_price": 2400,
    "min_price": 1850,
    "max_price": 2400,
    "avg_price_m2": 25
  },
  "Schouweiler": {
    "count": 3,
    "avg_price": 2145,
    "median_price": 2050,
    "min_price": 1995,
    "max_price": 2390,
    "avg_price_m2": 23
  },
  "Luxembourg-Dommeldange": {
    "count": 2,
    "avg_price": 2062,
    "median_price": 2450,
    "min_price": 1675,
    "max_price": 2450,
    "avg_price_m2": 18
  },
  "Mondorf-les-Bains": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 14
  },
  "Bettembourg": {
    "count": 2,
    "avg_price": 2475,
    "median_price": 2500,
    "min_price": 2450,
    "max_price": 2500,
    "avg_price_m2": 19
  },
  "Junglinster": {
    "count": 2,
    "avg_price": 2225,
    "median_price": 2500,
    "min_price": 1950,
    "max_price": 2500,
    "avg_price_m2": 22
  },
  "Tétange": {
    "count": 1,
    "avg_price": 2450,
    "median_price": 2450,
    "min_price": 2450,
    "max_price": 2450,
    "avg_price_m2": 23
  },
  "Olm": {
    "count": 2,
    "avg_price": 2200,
    "median_price": 2300,
    "min_price": 2100,
    "max_price": 2300,
    "avg_price_m2": 26
  },
  "Luxembourg-Bonnevoie": {
    "count": 3,
    "avg_price": 2233,
    "median_price": 2250,
    "min_price": 2150,
    "max_price": 2300,
    "avg_price_m2": 26
  },
  "Filsdorf": {
    "count": 1,
    "avg_price": 2350,
    "median_price": 2350,
    "min_price": 2350,
    "max_price": 2350,
    "avg_price_m2": 20
  },
  "Luxembourg-Belair": {
    "count": 6,
    "avg_price": 2304,
    "median_price": 2375,
    "min_price": 2100,
    "max_price": 2500,
    "avg_price_m2": 23
  },
  "Hautcharage": {
    "count": 2,
    "avg_price": 1915,
    "median_price": 1980,
    "min_price": 1850,
    "max_price": 1980,
    "avg_price_m2": 17
  },
  "Luxembourg-Hollerich": {
    "count": 4,
    "avg_price": 2225,
    "median_price": 2250,
    "min_price": 2100,
    "max_price": 2400,
    "avg_price_m2": 27
  },
  "Luxembourg-Kirchberg": {
    "count": 3,
    "avg_price": 2316,
    "median_price": 2350,
    "min_price": 2200,
    "max_price": 2400,
    "avg_price_m2": 27
  },
  "Luxembourg-Pfaffenthal": {
    "count": 1,
    "avg_price": 2200,
    "median_price": 2200,
    "min_price": 2200,
    "max_price": 2200,
    "avg_price_m2": 25
  },
  "Dudelange": {
    "count": 2,
    "avg_price": 2300,
    "median_price": 2400,
    "min_price": 2200,
    "max_price": 2400,
    "avg_price_m2": 24
  },
  "Luxembourg-Hamm": {
    "count": 1,
    "avg_price": 1890,
    "median_price": 1890,
    "min_price": 1890,
    "max_price": 1890,
    "avg_price_m2": 23
  },
  "Luxembourg Neudorf": {
    "count": 1,
    "avg_price": 2000,
    "median_price": 2000,
    "min_price": 2000,
    "max_price": 2000,
    "avg_price_m2": 0
  },
  "Luxembourg Gare": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 0
  },
  "Mondercange": {
    "count": 1,
    "avg_price": 2400,
    "median_price": 2400,
    "min_price": 2400,
    "max_price": 2400,
    "avg_price_m2": 0
  },
  "Luxembourg": {
    "count": 7,
    "avg_price": 1767,
    "median_price": 1850,
    "min_price": 1400,
    "max_price": 2000,
    "avg_price_m2": 0
  },
  "Bertrange": {
    "count": 5,
    "avg_price": 2180,
    "median_price": 2300,
    "min_price": 1500,
    "max_price": 2500,
    "avg_price_m2": 24
  },
  "Niederfeulen": {
    "count": 1,
    "avg_price": 1600,
    "median_price": 1600,
    "min_price": 1600,
    "max_price": 1600,
    "avg_price_m2": 17
  },
  "Lasauvage": {
    "count": 1,
    "avg_price": 1900,
    "median_price": 1900,
    "min_price": 1900,
    "max_price": 1900,
    "avg_price_m2": 21
  },
  "Mamer": {
    "count": 4,
    "avg_price": 2300,
    "median_price": 2400,
    "min_price": 2000,
    "max_price": 2500,
    "avg_price_m2": 23
  },
  "Reuler": {
    "count": 2,
    "avg_price": 1850,
    "median_price": 2100,
    "min_price": 1600,
    "max_price": 2100,
    "avg_price_m2": 15
  },
  "Weiswampach": {
    "count": 1,
    "avg_price": 1500,
    "median_price": 1500,
    "min_price": 1500,
    "max_price": 1500,
    "avg_price_m2": 17
  },
  "Bissen": {
    "count": 1,
    "avg_price": 1950,
    "median_price": 1950,
    "min_price": 1950,
    "max_price": 1950,
    "avg_price_m2": 24
  },
  "Belvaux": {
    "count": 2,
    "avg_price": 2300,
    "median_price": 2450,
    "min_price": 2150,
    "max_price": 2450,
    "avg_price_m2": 20
  },
  "Luxembourg-Beggen": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 17
  },
  "Luxembourg-Limpertsberg": {
    "count": 2,
    "avg_price": 2450,
    "median_price": 2500,
    "min_price": 2400,
    "max_price": 2500,
    "avg_price_m2": 25
  },
  "Luxembourg-Weimerskirch": {
    "count": 1,
    "avg_price": 2200,
    "median_price": 2200,
    "min_price": 2200,
    "max_price": 2200,
    "avg_price_m2": 25
  },
  "Alzingen": {
    "count": 2,
    "avg_price": 2375,
    "median_price": 2400,
    "min_price": 2350,
    "max_price": 2400,
    "avg_price_m2": 28
  },
  "Esch-sur-Alzette": {
    "count": 5,
    "avg_price": 2100,
    "median_price": 2100,
    "min_price": 1750,
    "max_price": 2500,
    "avg_price_m2": 23
  },
  "Hassel": {
    "count": 1,
    "avg_price": 1850,
    "median_price": 1850,
    "min_price": 1850,
    "max_price": 1850,
    "avg_price_m2": 21
  },
  "Pétange": {
    "count": 2,
    "avg_price": 2275,
    "median_price": 2350,
    "min_price": 2200,
    "max_price": 2350,
    "avg_price_m2": 25
  },
  "Schifflange": {
    "count": 1,
    "avg_price": 1900,
    "median_price": 1900,
    "min_price": 1900,
    "max_price": 1900,
    "avg_price_m2": 19
  },
  "Steinsel": {
    "count": 2,
    "avg_price": 2275,
    "median_price": 2300,
    "min_price": 2250,
    "max_price": 2300,
    "avg_price_m2": 23
  },
  "Hesperange": {
    "count": 1,
    "avg_price": 2400,
    "median_price": 2400,
    "min_price": 2400,
    "max_price": 2400,
    "avg_price_m2": 28
  },
  "Luxembourg-Gasperich - Cloche d'or": {
    "count": 1,
    "avg_price": 2250,
    "median_price": 2250,
    "min_price": 2250,
    "max_price": 2250,
    "avg_price_m2": 27
  },
  "Luxembourg-Gare": {
    "count": 2,
    "avg_price": 2420,
    "median_price": 2450,
    "min_price": 2390,
    "max_price": 2450,
    "avg_price_m2": 28
  },
  "Luxembourg-Centre ville": {
    "count": 2,
    "avg_price": 2450,
    "median_price": 2500,
    "min_price": 2400,
    "max_price": 2500,
    "avg_price_m2": 28
  },
  "Senningerberg": {
    "count": 3,
    "avg_price": 2180,
    "median_price": 2290,
    "min_price": 1950,
    "max_price": 2300,
    "avg_price_m2": 21
  },
  "Luxembourg-Eich": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 17
  },
  "Strassen": {
    "count": 1,
    "avg_price": 2350,
    "median_price": 2350,
    "min_price": 2350,
    "max_price": 2350,
    "avg_price_m2": 28
  },
  "Garnich": {
    "count": 1,
    "avg_price": 2400,
    "median_price": 2400,
    "min_price": 2400,
    "max_price": 2400,
    "avg_price_m2": 24
  },
  "Sprinkange": {
    "count": 1,
    "avg_price": 2100,
    "median_price": 2100,
    "min_price": 2100,
    "max_price": 2100,
    "avg_price_m2": 23
  },
  "Belval": {
    "count": 1,
    "avg_price": 2375,
    "median_price": 2375,
    "min_price": 2375,
    "max_price": 2375,
    "avg_price_m2": 24
  },
  "Luxembourg-Cessange": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 27
  },
  "Differdange": {
    "count": 1,
    "avg_price": 2100,
    "median_price": 2100,
    "min_price": 2100,
    "max_price": 2100,
    "avg_price_m2": 24
  },
  "Helmsange": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 30
  },
  "Remich": {
    "count": 1,
    "avg_price": 2500,
    "median_price": 2500,
    "min_price": 2500,
    "max_price": 2500,
    "avg_price_m2": 19
  },
  "Lallange": {
    "count": 2,
    "avg_price": 2075,
    "median_price": 2200,
    "min_price": 1950,
    "max_price": 2200,
    "avg_price_m2": 23
  },
  "Rollingen": {
    "count": 1,
    "avg_price": 2150,
    "median_price": 2150,
    "min_price": 2150,
    "max_price": 2150,
    "avg_price_m2": 21
  },
  "Brouch (Mersch)": {
    "count": 1,
    "avg_price": 2400,
    "median_price": 2400,
    "min_price": 2400,
    "max_price": 2400,
    "avg_price_m2": 13
  },
  "Kahler": {
    "count": 1,
    "avg_price": 2300,
    "median_price": 2300,
    "min_price": 2300,
    "max_price": 2300,
    "avg_price_m2": 18
  },
  "Hobscheid": {
    "count": 1,
    "avg_price": 1900,
    "median_price": 1900,
    "min_price": 1900,
    "max_price": 1900,
    "avg_price_m2": 22
  },
  "Luxembourg-Centre Ville": {
    "count": 1,
    "avg_price": 2350,
    "median_price": 2350,
    "min_price": 2350,
    "max_price": 2350,
    "avg_price_m2": 25
  },
  "Contern": {
    "count": 1,
    "avg_price": 2400,
    "median_price": 2400,
    "min_price": 2400,
    "max_price": 2400,
    "avg_price_m2": 29
  }
};
