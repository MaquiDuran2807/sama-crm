/**
 * crm/static/crm/js/dashboard.js
 * Dashboard Kanban del CRM SAMA AdTech
 * 
 * Funcionalidades:
 * - Filtrado de leads en tiempo real
 * - Drag & Drop entre columnas con sincronización API
 * - Tema claro/oscuro con persistencia en localStorage
 * - Actualización de contadores dinámicos
 */

(function() {
    'use strict';

    // ─── CONFIGURACIÓN ─── 
    const CONFIG = {
        API_BASE: '/api/crm/leads/',
        THEME_STORAGE_KEY: 'sama-crm-theme',
        DRAG_FEEDBACK_CLASS: 'dragging',
        DRAG_OVER_CLASS: 'drag-over',
    };

    const DOM = {
        searchInput: document.getElementById('lead-search'),
        searchClear: document.getElementById('search-clear'),
        leadCards: document.querySelectorAll('.lead-card'),
        kanbanColumns: document.querySelectorAll('.kanban-column'),
        kanbanBoard: document.getElementById('kanban-board'),
        themeToggle: document.getElementById('theme-toggle'),
        tenantSlug: document.body.getAttribute('data-tenant-slug'),
    };

    // ─── INICIALIZACIÓN ─── 
    function init() {
        initThemeToggle();
        initSearch();
        initDragDrop();
    }

    // ─── THEME MANAGEMENT ─── 
    /**
     * Inicializa el selector de tema (claro/oscuro)
     * Lee localStorage y aplica el tema guardado
     */
    function initThemeToggle() {
        if (!DOM.themeToggle) return;

        const savedTheme = localStorage.getItem(CONFIG.THEME_STORAGE_KEY) || 'dark';
        applyTheme(savedTheme);

        DOM.themeToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleTheme();
        });
    }

    /**
     * Alterna entre tema oscuro y claro
     */
    function toggleTheme() {
        const currentTheme = document.body.classList.contains('theme-light') ? 'light' : 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    }

    /**
     * Aplica un tema específico (dark/light)
     * @param {string} theme - 'dark' o 'light'
     */
    function applyTheme(theme) {
        const isLight = theme === 'light';
        
        // Aplicar clase al body
        document.body.classList.toggle('theme-light', isLight);
        
        // Guardar en localStorage
        localStorage.setItem(CONFIG.THEME_STORAGE_KEY, theme);
        
        // Actualizar el icon del botón
        if (DOM.themeToggle) {
            const icon = DOM.themeToggle.querySelector('i');
            if (icon) {
                if (isLight) {
                    icon.className = 'bi bi-moon-stars';
                    DOM.themeToggle.setAttribute('aria-label', 'Cambiar a tema oscuro');
                } else {
                    icon.className = 'bi bi-sun';
                    DOM.themeToggle.setAttribute('aria-label', 'Cambiar a tema claro');
                }
            }
        }
    }

    // ─── STATS REFRESH ───
    /**
     * Refresca las tarjetas de estadísticas desde la API
     */
    function refreshStats() {
        if (!DOM.tenantSlug) return;

        const url = `${CONFIG.API_BASE}stats/?tenant_slug=${encodeURIComponent(DOM.tenantSlug)}`;

        fetch(url)
            .then(function(response) {
                if (response.ok) return response.json();
                throw new Error('Error al obtener estadísticas');
            })
            .then(function(data) {
                var totalEl = document.getElementById('stat-total');
                var newEl = document.getElementById('stat-new');
                var activeEl = document.getElementById('stat-active');
                var closedEl = document.getElementById('stat-closed');

                if (totalEl) totalEl.textContent = data.total_leads || '0';
                if (newEl) newEl.textContent = data.leads_nuevos_hoy || '0';
                if (activeEl) activeEl.textContent = data.active_leads || '0';
                if (closedEl) closedEl.textContent = data.won_leads || '0';
            })
            .catch(function(error) {
                console.error('Error al refrescar estadísticas:', error);
            });
    }

    // ─── SEARCH FUNCTIONALITY ─── 
    /**
     * Inicializa el filtrado de búsqueda
     */
    function initSearch() {
        if (!DOM.searchInput) return;

        DOM.searchInput.addEventListener('input', function(e) {
            filterLeads(e.target.value);
        });

        if (DOM.searchClear) {
            DOM.searchClear.addEventListener('click', function() {
                DOM.searchInput.value = '';
                filterLeads('');
                DOM.searchInput.focus();
            });

            DOM.searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    DOM.searchInput.value = '';
                    filterLeads('');
                    DOM.searchInput.blur();
                }
            });
        }
    }

    /**
     * Filtra las tarjetas de leads según el término de búsqueda
     * @param {string} term - Término de búsqueda
     * @returns {number} Número de leads visibles
     */
    function filterLeads(term) {
        const query = term.toLowerCase().trim();
        let totalVisible = 0;

        DOM.leadCards.forEach(function(card) {
            const name = card.getAttribute('data-name') || '';
            const phone = card.getAttribute('data-phone') || '';
            const product = card.getAttribute('data-product') || '';

            const matches = name.includes(query) ||
                            phone.includes(query) ||
                            product.includes(query);

            card.style.display = matches ? '' : 'none';
            if (matches) totalVisible++;
        });

        // Actualizar opacidad de columnas vacías
        DOM.kanbanColumns.forEach(function(column) {
            const visibleCards = column.querySelectorAll('.lead-card[style*="display: none"]').length;
            const totalCards = column.querySelectorAll('.lead-card').length;

            if (query && visibleCards === totalCards) {
                column.style.opacity = '0.4';
            } else {
                column.style.opacity = '1';
            }
        });

        // Mostrar/ocultar botón de limpiar
        if (DOM.searchClear) {
            DOM.searchClear.style.display = query ? '' : 'none';
        }

        updateColumnCounts();

        return totalVisible;
    }

    // ─── DRAG & DROP ─── 
    /**
     * Inicializa la funcionalidad de Drag & Drop
     */
    function initDragDrop() {
        DOM.leadCards.forEach(function(card) {
            card.addEventListener('dragstart', onDragStart);
            card.addEventListener('dragend', onDragEnd);
        });

        DOM.kanbanColumns.forEach(function(column) {
            column.addEventListener('dragover', onDragOver);
            column.addEventListener('dragleave', onDragLeave);
            column.addEventListener('drop', onDrop);
        });
    }

    let draggedCard = null;
    let sourceColumn = null;

    /**
     * Maneja el inicio del drag
     */
    function onDragStart(e) {
        draggedCard = this;
        sourceColumn = this.closest('.kanban-column');
        this.classList.add(CONFIG.DRAG_FEEDBACK_CLASS);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.innerHTML);
    }

    /**
     * Maneja el fin del drag
     */
    function onDragEnd(e) {
        this.classList.remove(CONFIG.DRAG_FEEDBACK_CLASS);
        
        // Limpiar todas las columnas del estado de drag-over
        DOM.kanbanColumns.forEach(function(column) {
            column.classList.remove(CONFIG.DRAG_OVER_CLASS);
        });
    }

    /**
     * Maneja el dragover en las columnas
     */
    function onDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }

        e.dataTransfer.dropEffect = 'move';
        this.classList.add(CONFIG.DRAG_OVER_CLASS);
        return false;
    }

    /**
     * Maneja el dragleave en las columnas
     */
    function onDragLeave(e) {
        // Solo remover la clase si el cursor sale completamente de la columna
        if (e.target === this) {
            this.classList.remove(CONFIG.DRAG_OVER_CLASS);
        }
    }

    /**
     * Maneja el drop de un lead en una nueva columna
     */
    function onDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }

        this.classList.remove(CONFIG.DRAG_OVER_CLASS);

        if (!draggedCard || !sourceColumn) return;

        const targetColumn = this;
        const newStage = targetColumn.getAttribute('data-stage');
        const leadId = draggedCard.getAttribute('data-lead-id');
        const movedCard = draggedCard;
        const originalColumn = sourceColumn;

        // Si se suelta en la misma columna, no hacer nada
        if (targetColumn === sourceColumn) {
            draggedCard = null;
            sourceColumn = null;
            return;
        }

        // Movimiento visual optimista
        moveCardUI(movedCard, targetColumn);

        // Sincronizar con la API
        updateLeadStageAPI(leadId, newStage, function(success) {
            if (!success) {
                // Revertir el cambio si falla
                moveCardUI(movedCard, originalColumn);
                console.error('Error al actualizar la etapa del lead');
            }
        });

        draggedCard = null;
        sourceColumn = null;

        return false;
    }

    /**
     * Mueve la tarjeta de forma visual entre columnas
     */
    function moveCardUI(card, targetColumn) {
        // Obtener el contenedor de tarjetas dentro de la columna
        const cardsContainer = targetColumn.querySelector('.kanban-cards');
        
        if (cardsContainer) {
            cardsContainer.appendChild(card);
        }

        // Actualizar contadores de todas las columnas
        updateColumnCounts();
    }

    /**
     * Actualiza la etapa del lead a través de la API
     */
    function updateLeadStageAPI(leadId, newStage, callback) {
        if (!DOM.tenantSlug) {
            console.error('tenant_slug no disponible');
            if (callback) callback(false);
            return;
        }

        const url = `${CONFIG.API_BASE}${leadId}/?tenant_slug=${encodeURIComponent(DOM.tenantSlug)}`;

        fetch(url, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                current_stage: newStage,
            }),
        })
        .then(function(response) {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Error en la respuesta de la API');
            }
        })
        .then(function(data) {
            console.log('Lead actualizado exitosamente:', data);
            refreshStats();
            if (callback) callback(true);
        })
        .catch(function(error) {
            console.error('Error al actualizar el lead:', error);
            if (callback) callback(false);
        });
    }

    /**
     * Obtiene el CSRF token de las cookies
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ─── COLUMN MANAGEMENT ─── 
    /**
     * Actualiza los contadores de leads en las columnas
     */
    function updateColumnCounts() {
        DOM.kanbanColumns.forEach(function(column) {
            const visibleCards = column.querySelectorAll('.lead-card:not([style*="display: none"])').length;
            const countBadge = column.querySelector('.kanban-stage-count');
            
            if (countBadge) {
                countBadge.textContent = visibleCards;
            }
        });
    }

    // ─── INICIALIZACIÓN AL CARGAR ─── 
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Actualizar conteos iniciales
    updateColumnCounts();

})();
