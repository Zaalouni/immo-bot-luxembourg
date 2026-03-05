/**
 * Version Switcher
 * Allows users to toggle between v1 and v2
 */

(function() {
    'use strict';

    function createVersionSwitcher() {
        // Determine current version
        const currentVersion = window.location.pathname.includes('/v1/') ? 'v1' : 'v2';
        const otherVersion = currentVersion === 'v1' ? 'v2' : 'v1';
        const otherVersionLabel = otherVersion === 'v1' ? 'V1 (stable)' : 'V2 (optimisée)';
        const otherVersionUrl = window.location.pathname.replace(`/${currentVersion}/`, `/${otherVersion}/`);

        // Create switcher button
        const switcher = document.createElement('div');
        switcher.id = 'version-switcher';
        switcher.setAttribute('role', 'complementary');
        switcher.setAttribute('aria-label', 'Sélecteur de version');
        switcher.innerHTML = `
            <style>
                #version-switcher {
                    position: fixed;
                    top: 1rem;
                    right: 6rem;
                    z-index: 1000;
                    background: white;
                    border-radius: 8px;
                    padding: 0.5rem 1rem;
                    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.85rem;
                }

                #version-switcher.dark-mode {
                    background: rgba(255,255,255,0.1);
                    color: #ecf0f1;
                }

                #version-switcher a {
                    padding: 0.5rem 1rem;
                    border-radius: 6px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    font-weight: 600;
                    border: none;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.3rem;
                }

                #version-switcher a:hover {
                    background: #5a6fd6;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(102,126,234,0.3);
                }

                @media (max-width: 768px) {
                    #version-switcher {
                        top: 50px;
                        right: 0.5rem;
                        padding: 0.5rem;
                        font-size: 0.75rem;
                    }

                    #version-switcher a {
                        padding: 0.4rem 0.8rem;
                    }
                }
            </style>

            <span>Version actuelle: <strong>${currentVersion.toUpperCase()}</strong></span>
            <a href="${otherVersionUrl}" title="Basculer vers ${otherVersionLabel}" aria-label="Basculer vers la version ${otherVersion}">
                ↔️ ${otherVersionLabel}
            </a>
        `;

        // Insert into page
        document.body.appendChild(switcher);

        // Sync dark mode state with switcher
        const syncDarkMode = () => {
            if (document.body.classList.contains('dark-mode')) {
                switcher.classList.add('dark-mode');
            } else {
                switcher.classList.remove('dark-mode');
            }
        };

        // Watch for dark mode changes
        const observer = new MutationObserver(syncDarkMode);
        observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

        // Initial sync
        syncDarkMode();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createVersionSwitcher);
    } else {
        createVersionSwitcher();
    }
})();
