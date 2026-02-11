
# Créer rapidement les 4 fichiers
for site in luxhome vivi newimmo unicorn; do
    cp scrapers/luxhome_scraper_real.py scrapers/${site}_scraper_real.py
    # Modifier les paramètres spécifiques
    sed -i "s/Luxhome.lu/${site^}/g" scrapers/${site}_scraper_real.py
    sed -i "s/luxhome.lu/${site}.lu/g" scrapers/${site}_scraper_real.py
done
