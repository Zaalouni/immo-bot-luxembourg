/**
 * City Name Normalization Utility
 * Standardizes city names across the dashboard
 * Handles whitespace, case sensitivity, HTML entities, duplicates
 */

'use strict';

const CityNormalizer = {
    /**
     * Normalize a single city name
     * @param {string} city - City name to normalize
     * @returns {string} Normalized city name
     */
    normalize: function(city) {
        if (!city || typeof city !== 'string') return '';

        return city
            // Decode HTML entities
            .replace(/&nbsp;/g, ' ')
            .replace(/&amp;/g, '&')
            .trim()
            // Remove extra whitespace
            .replace(/\s+/g, ' ')
            // Remove leading/trailing hyphens
            .replace(/^-+|-+$/g, '')
            .trim();
    },

    /**
     * Normalize all cities in a listings array
     * @param {Array} listings - Array of listing objects
     * @returns {Array} Listings with normalized city names
     */
    normalizeListings: function(listings) {
        if (!Array.isArray(listings)) return [];

        return listings.map(listing => ({
            ...listing,
            city: this.normalize(listing.city)
        }));
    },

    /**
     * Get unique cities from listings
     * @param {Array} listings - Array of listing objects
     * @returns {Array} Sorted array of unique city names
     */
    getUniqueCities: function(listings) {
        if (!Array.isArray(listings)) return [];

        const cities = new Set(
            listings
                .map(l => this.normalize(l.city))
                .filter(city => city && city !== 'N/A' && city !== '')
        );

        return Array.from(cities).sort();
    },

    /**
     * Group cities for display (optional grouping by region)
     * Can group Luxembourg districts together
     * @param {Array} cities - Array of city names
     * @param {boolean} groupLuxembourg - Whether to group Luxembourg districts
     * @returns {Object} Grouped cities {groupName: [cities]}
     */
    groupCities: function(cities, groupLuxembourg = false) {
        const grouped = {};

        cities.forEach(city => {
            let groupKey = city;

            if (groupLuxembourg && city.startsWith('Luxembourg-')) {
                groupKey = 'Luxembourg';
            }

            if (!grouped[groupKey]) {
                grouped[groupKey] = [];
            }
            grouped[groupKey].push(city);
        });

        return grouped;
    },

    /**
     * Deduplicate cities based on normalized names
     * Keeps first occurrence of each unique city
     * @param {Array} cities - Array of city names
     * @returns {Array} Deduplicated array
     */
    deduplicate: function(cities) {
        const seen = new Set();
        return cities.filter(city => {
            const normalized = this.normalize(city);
            if (seen.has(normalized)) return false;
            seen.add(normalized);
            return true;
        });
    },

    /**
     * Get city statistics
     * @param {Array} listings - Array of listing objects
     * @returns {Object} Statistics about cities
     */
    getStats: function(listings) {
        const normalized = this.normalizeListings(listings);
        const unique = this.getUniqueCities(normalized);
        const grouped = this.groupCities(unique, true);

        const stats = {
            total: listings.length,
            before: {
                count: new Set(listings.map(l => l.city)).size,
                cities: Array.from(new Set(listings.map(l => l.city))).sort()
            },
            after: {
                count: unique.length,
                cities: unique
            },
            grouped: grouped,
            groupedCount: Object.keys(grouped).length
        };

        return stats;
    }
};

// Export for use in browser environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CityNormalizer;
}
