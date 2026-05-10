/**
 * crm/static/crm/js/theme.js
 * Funciones JS globales que aplican a todas las páginas CRM.
 * - Theme toggle (claro/oscuro)
 * - Helpers (getCookie, getTenantSlug)
 */

(function() {
    'use strict';

    var CONFIG = {
        THEME_STORAGE_KEY: 'sama-crm-theme',
    };

    // ─── HELPERS GLOBALES ───

    window.SAMA = window.SAMA || {};

    SAMA.getCookie = function(name) {
        var value = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    value = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return value;
    };

    SAMA.getTenantSlug = function() {
        return document.body.getAttribute('data-tenant-slug');
    };

    // ─── THEME TOGGLE ───

    function initThemeToggle() {
        var toggle = document.getElementById('theme-toggle');
        if (!toggle) return;

        var savedTheme = localStorage.getItem(CONFIG.THEME_STORAGE_KEY) || 'dark';
        applyTheme(savedTheme);

        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            var current = document.body.classList.contains('theme-light') ? 'light' : 'dark';
            applyTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    function applyTheme(theme) {
        var isLight = theme === 'light';
        document.body.classList.toggle('theme-light', isLight);
        localStorage.setItem(CONFIG.THEME_STORAGE_KEY, theme);

        var toggle = document.getElementById('theme-toggle');
        if (!toggle) return;
        var icon = toggle.querySelector('i');
        if (icon) {
            if (isLight) {
                icon.className = 'bi bi-moon-stars';
                toggle.setAttribute('aria-label', 'Cambiar a tema oscuro');
            } else {
                icon.className = 'bi bi-sun';
                toggle.setAttribute('aria-label', 'Cambiar a tema claro');
            }
        }

        window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme: theme } }));
    }

    // ─── INIT ───

    function init() {
        initThemeToggle();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();