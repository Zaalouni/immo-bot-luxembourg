/**
 * ImmoLux Dashboard - Dark Mode Controller
 * Version: 1.0
 * Date: 2026-03-01
 * Description: Gestion du mode sombre avec localStorage
 */

(function() {
    'use strict';

    // Restaurer l'état du dark mode immédiatement (avant DOMContentLoaded)
    // pour éviter le flash de contenu en mode clair
    if (localStorage.getItem("darkMode") === "true") {
        document.documentElement.classList.add("dark-mode");
        if (document.body) {
            document.body.classList.add("dark-mode");
        }
    }

    // Initialiser le toggle button après chargement DOM
    document.addEventListener('DOMContentLoaded', function() {
        const toggle = document.getElementById("darkModeToggle");

        if (!toggle) {
            console.warn('Dark mode toggle button not found (#darkModeToggle)');
            return;
        }

        // Mettre à jour l'icône selon l'état actuel
        updateToggleIcon(toggle);

        // Gérer le clic sur le bouton
        toggle.addEventListener("click", function() {
            document.body.classList.toggle("dark-mode");

            const isDarkMode = document.body.classList.contains("dark-mode");

            // Sauvegarder la préférence
            localStorage.setItem("darkMode", isDarkMode.toString());

            // Mettre à jour l'icône
            updateToggleIcon(toggle);

            // Log pour debugging (optionnel)
            console.log('Dark mode:', isDarkMode ? 'ON' : 'OFF');
        });
    });

    /**
     * Met à jour l'icône du bouton toggle selon l'état dark mode
     * @param {HTMLElement} toggle - Le bouton toggle
     */
    function updateToggleIcon(toggle) {
        const isDarkMode = document.body.classList.contains("dark-mode");

        // Chercher l'icône dans le bouton
        const icon = toggle.querySelector('span');

        if (icon) {
            // Changer l'icône: 🌙 (lune) en mode clair, ☀️ (soleil) en mode sombre
            icon.textContent = isDarkMode ? '☀️' : '🌙';
        } else {
            // Si pas de <span>, modifier directement le contenu du bouton
            toggle.textContent = isDarkMode ? '☀️' : '🌙';
        }

        // Mettre à jour le title pour l'accessibilité
        toggle.title = isDarkMode ? 'Mode clair' : 'Mode sombre';
    }

})();
