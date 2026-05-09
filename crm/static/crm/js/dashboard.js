/**
 * crm/static/crm/js/dashboard.js
 * Dashboard Kanban del CRM SAMA AdTech
 *
 * Funcionalidades:
 * - Filtrado de leads en tiempo real
 * - Drag & Drop con nota obligatoria + modal de etapa cerrada
 * - Tema claro/oscuro con persistencia en localStorage
 * - Actualización de contadores y estadísticas dinámicas
 */

(function() {
    'use strict';

    // ─── CONFIGURACIÓN ───
    var CONFIG = {
        API_BASE: '/api/crm/leads/',
        THEME_STORAGE_KEY: 'sama-crm-theme',
        DRAG_FEEDBACK_CLASS: 'dragging',
        DRAG_OVER_CLASS: 'drag-over',
    };

    var DOM = {};

    // Estado de la operación de drag pendiente
    var pendingDrag = null;

    // ─── HELPERS ───
    function getCookie(name) {
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
    }

    function isClosedStage(stageName) {
        var name = (stageName || '').toLowerCase();
        return name.indexOf('cerrado') !== -1 || name.indexOf('closed') !== -1;
    }

    function hideModal(modalId) {
        var modalEl = document.getElementById(modalId);
        if (!modalEl) return;
        var instance = bootstrap.Modal.getInstance(modalEl);
        if (instance) instance.hide();
    }

    function showModal(modalId) {
        var modalEl = document.getElementById(modalId);
        if (!modalEl) return;
        var modal = new bootstrap.Modal(modalEl);
        modal.show();
    }

    function getTenantSlug() {
        return document.body.getAttribute('data-tenant-slug');
    }

    // ─── STATS REFRESH ───
    function refreshStats() {
        var tenantSlug = getTenantSlug();
        if (!tenantSlug) return;

        var url = CONFIG.API_BASE + 'stats/?tenant_slug=' + encodeURIComponent(tenantSlug);
        fetch(url)
            .then(function(response) {
                if (response.ok) return response.json();
                throw new Error('API error');
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

    // ─── THEME ───
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
    }

    // ─── SEARCH ───
    function initSearch() {
        var searchInput = document.getElementById('lead-search');
        var searchClear = document.getElementById('search-clear');
        if (!searchInput) return;

        searchInput.addEventListener('input', function() {
            filterLeads(searchInput.value);
        });

        if (searchClear) {
            searchClear.addEventListener('click', function() {
                searchInput.value = '';
                filterLeads('');
                searchInput.focus();
            });

            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    filterLeads('');
                    searchInput.blur();
                }
            });
        }
    }

    function filterLeads(term) {
        var query = term.toLowerCase().trim();
        var cards = document.querySelectorAll('.lead-card');
        var columns = document.querySelectorAll('.kanban-column');

        cards.forEach(function(card) {
            var name = card.getAttribute('data-name') || '';
            var phone = card.getAttribute('data-phone') || '';
            var product = card.getAttribute('data-product') || '';

            var matches = name.includes(query) || phone.includes(query) || product.includes(query);
            card.style.display = matches ? '' : 'none';
        });

        columns.forEach(function(col) {
            var hidden = col.querySelectorAll('.lead-card[style*="display: none"]').length;
            var total = col.querySelectorAll('.lead-card').length;
            col.style.opacity = (query && hidden === total) ? '0.4' : '1';
        });

        var searchClear = document.getElementById('search-clear');
        if (searchClear) searchClear.style.display = query ? '' : 'none';

        updateColumnCounts();
    }

    // ─── DRAG & DROP ───
    var draggedCard = null;
    var sourceColumn = null;

    function initDragDrop() {
        document.querySelectorAll('.lead-card').forEach(function(card) {
            card.addEventListener('dragstart', onDragStart);
            card.addEventListener('dragend', onDragEnd);
        });

        document.querySelectorAll('.kanban-column').forEach(function(col) {
            col.addEventListener('dragover', onDragOver);
            col.addEventListener('dragleave', onDragLeave);
            col.addEventListener('drop', onDrop);
        });
    }

    function onDragStart(e) {
        draggedCard = this;
        sourceColumn = this.closest('.kanban-column');
        this.classList.add(CONFIG.DRAG_FEEDBACK_CLASS);
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.innerHTML);
    }

    function onDragEnd(e) {
        this.classList.remove(CONFIG.DRAG_FEEDBACK_CLASS);
        document.querySelectorAll('.kanban-column').forEach(function(col) {
            col.classList.remove(CONFIG.DRAG_OVER_CLASS);
        });
    }

    function onDragOver(e) {
        if (e.preventDefault) e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        this.classList.add(CONFIG.DRAG_OVER_CLASS);
        return false;
    }

    function onDragLeave(e) {
        if (e.target === this) {
            this.classList.remove(CONFIG.DRAG_OVER_CLASS);
        }
    }

    function onDrop(e) {
        if (e.stopPropagation) e.stopPropagation();
        this.classList.remove(CONFIG.DRAG_OVER_CLASS);

        if (!draggedCard || !sourceColumn) return;

        var targetColumn = this;
        var newStage = targetColumn.getAttribute('data-stage');
        var leadId = draggedCard.getAttribute('data-lead-id');
        var sourceStage = sourceColumn.getAttribute('data-stage');

        if (targetColumn === sourceColumn) {
            draggedCard = null;
            sourceColumn = null;
            return;
        }

        pendingDrag = {
            leadId: leadId,
            sourceStage: sourceStage,
            newStage: newStage,
            card: draggedCard,
            sourceCol: sourceColumn,
            targetCol: targetColumn,
        };

        draggedCard = null;
        sourceColumn = null;

        showModal('noteModal');
        return false;
    }

    function moveCardUI(card, targetColumn) {
        var container = targetColumn.querySelector('.kanban-cards');
        if (container) container.appendChild(card);

        var stageColor = targetColumn.getAttribute('data-stage-color');
        if (stageColor) {
            card.style.setProperty('--stage-color', stageColor);
            card.setAttribute('data-stage-color', stageColor);
        }

        updateColumnCounts();
    }

    function revertCard(card, sourceColumn) {
        var container = sourceColumn.querySelector('.kanban-cards');
        if (container) container.appendChild(card);
        var stageColor = sourceColumn.getAttribute('data-stage-color');
        if (stageColor) {
            card.style.setProperty('--stage-color', stageColor);
            card.setAttribute('data-stage-color', stageColor);
        }
        updateColumnCounts();
    }

    // ─── NOTA MODAL ───
    function initNoteModal() {
        var saveBtn = document.getElementById('note-modal-save-btn');
        var modalEl = document.getElementById('noteModal');
        if (!saveBtn || !modalEl) return;

        saveBtn.addEventListener('click', function() {
            var note = document.getElementById('drag-note-text').value.trim();
            var tenantSlug = getTenantSlug();

            hideModal('noteModal');

            if (!note) {
                // Sin nota: solo hacer el movimiento si no es cerrado→activo
                if (!pendingDrag) return;

                if (isClosedStage(pendingDrag.sourceStage) && !isClosedStage(pendingDrag.newStage)) {
                    // Sin nota pero es cerrado→activo: mostrar modal de error/recompra
                    document.getElementById('drag-note-text').value = '';
                    showModal('reopenModal');
                } else {
                    // Movimiento normal sin nota
                    doStageChange(pendingDrag.leadId, pendingDrag.newStage, pendingDrag.targetCol, pendingDrag.card, pendingDrag.sourceCol, note, tenantSlug);
                    pendingDrag = null;
                }
            } else {
                // Con nota: hacer el movimiento y guardar la nota
                if (isClosedStage(pendingDrag.sourceStage) && !isClosedStage(pendingDrag.newStage)) {
                    // Con nota + cerrado→activo: guardar nota y mostrar reopen
                    document.getElementById('drag-note-text').value = '';
                    pendingDrag.note = note;
                    showModal('reopenModal');
                } else {
                    // Con nota + movimiento normal
                    doStageChange(pendingDrag.leadId, pendingDrag.newStage, pendingDrag.targetCol, pendingDrag.card, pendingDrag.sourceCol, note, tenantSlug);
                    pendingDrag = null;
                }
            }
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            if (pendingDrag) {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
                pendingDrag = null;
            }
            document.getElementById('drag-note-text').value = '';
        });
    }

    function doStageChange(leadId, newStage, targetCol, card, sourceCol, note, tenantSlug, callback) {
        var url = CONFIG.API_BASE + leadId + '/?tenant_slug=' + encodeURIComponent(tenantSlug);

        fetch(url, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ current_stage: newStage }),
        })
        .then(function(response) {
            if (!response.ok) throw new Error('API error: ' + response.status);
            return response.json();
        })
        .then(function(data) {
            moveCardUI(card, targetCol);

            if (note) {
                doAddNote(leadId, note, tenantSlug);
            }

            setTimeout(refreshStats, 300);

            if (callback) callback(true);
        })
        .catch(function(error) {
            console.error('Error al actualizar etapa:', error);
            revertCard(card, sourceCol);
            if (callback) callback(false);
        });
    }

    function doAddNote(leadId, note, tenantSlug) {
        var url = CONFIG.API_BASE + leadId + '/add_note/?tenant_slug=' + encodeURIComponent(tenantSlug);
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ note: note }),
        })
        .then(function(response) {
            if (!response.ok) console.error('Error al guardar nota');
        })
        .catch(function(error) {
            console.error('Error al guardar nota:', error);
        });
    }

    // ─── REOPEN MODAL (cerrado → activo) ───
    function initReopenModal() {
        var errorBtn = document.getElementById('reopen-error-btn');
        var newBtn = document.getElementById('reopen-new-btn');
        var modalEl = document.getElementById('reopenModal');
        if (!errorBtn || !newBtn || !modalEl) return;

        errorBtn.addEventListener('click', function() {
            populateErrorRestoreModal();
            setTimeout(function() { showModal('errorRestoreModal'); }, 350);
        });

        newBtn.addEventListener('click', function() {
            var product = document.querySelector('#recompraModal input#recompra-product');
            if (product) product.value = pendingDrag && pendingDrag.card ? pendingDrag.card.getAttribute('data-product') || '' : '';
            setTimeout(function() { showModal('recompraModal'); }, 350);
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            if (pendingDrag) {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
                pendingDrag = null;
            }
        });
    }

    // ─── ERROR RESTORE MODAL (fue un error → mover a etapa activa) ───
    function populateErrorRestoreModal() {
        var select = document.getElementById('error-stage-select');
        if (!select) return;
        select.innerHTML = '';

        document.querySelectorAll('.kanban-column').forEach(function(col) {
            var stageName = col.getAttribute('data-stage');
            var isClosed = col.getAttribute('data-is-closed');
            if (!isClosed && stageName) {
                var opt = document.createElement('option');
                opt.value = stageName;
                opt.textContent = stageName;
                select.appendChild(opt);
            }
        });
    }

    function initErrorRestoreModal() {
        var confirmBtn = document.getElementById('error-confirm-btn');
        var modalEl = document.getElementById('errorRestoreModal');
        if (!confirmBtn || !modalEl) return;

        confirmBtn.addEventListener('click', function() {
            if (!pendingDrag) {
                hideModal('errorRestoreModal');
                return;
            }

            var select = document.getElementById('error-stage-select');
            var targetStage = select ? select.value : pendingDrag.newStage;
            var tenantSlug = getTenantSlug();

            hideModal('errorRestoreModal');
            hideModal('reopenModal');

            // Encontrar la columna destino por nombre de etapa
            var targetCol = null;
            document.querySelectorAll('.kanban-column').forEach(function(col) {
                if (col.getAttribute('data-stage') === targetStage) targetCol = col;
            });

            if (targetCol) {
                // El movimiento visual ya se hizo en drop; revert y re-move a la etapa correcta
                revertCard(pendingDrag.card, pendingDrag.targetCol);
                doStageChange(pendingDrag.leadId, targetStage, targetCol, pendingDrag.card, pendingDrag.sourceCol, pendingDrag.note || '', tenantSlug);
            } else {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
            }

            pendingDrag = null;
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            // No revertir aquí: el flujo es regresar a reopenModal
        });
    }

    // ─── RECOMPRA MODAL ───
    function initRecompraModal() {
        var confirmBtn = document.getElementById('recompra-confirm-btn');
        var modalEl = document.getElementById('recompraModal');
        if (!confirmBtn || !modalEl) return;

        confirmBtn.addEventListener('click', function() {
            if (!pendingDrag) {
                hideModal('recompraModal');
                return;
            }

            var product = document.getElementById('recompra-product').value.trim();
            var notes = document.getElementById('recompra-notes').value.trim();
            var tenantSlug = getTenantSlug();
            var leadId = pendingDrag.leadId;

            hideModal('recompraModal');
            hideModal('reopenModal');

            // Primero: si hay nota, guardarla en el lead original
            if (pendingDrag.note) {
                doAddNote(leadId, pendingDrag.note, tenantSlug);
            }

            // POST /api/crm/leads/{id}/reopen/
            var url = CONFIG.API_BASE + leadId + '/reopen/?tenant_slug=' + encodeURIComponent(tenantSlug);

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ product_of_interest: product, notes: notes }),
            })
            .then(function(response) {
                if (!response.ok) throw new Error('Error en recompra');
                return response.json();
            })
            .then(function(data) {
                pendingDrag = null;
                location.reload();
            })
            .catch(function(error) {
                console.error('Error en recompra:', error);
                pendingDrag = null;
                location.reload();
            });
        });
    }

    // ─── COLUMN COUNTS ───
    function updateColumnCounts() {
        document.querySelectorAll('.kanban-column').forEach(function(col) {
            var visible = 0;
            col.querySelectorAll('.lead-card').forEach(function(card) {
                if (card.style.display !== 'none') visible++;
            });
            var badge = col.querySelector('.kanban-stage-count');
            if (badge) badge.textContent = visible;
        });
    }

    // ─── INIT ───
    function init() {
        DOM.searchInput = document.getElementById('lead-search');
        DOM.searchClear = document.getElementById('search-clear');
        DOM.leadCards = document.querySelectorAll('.lead-card');
        DOM.kanbanColumns = document.querySelectorAll('.kanban-column');
        DOM.themeToggle = document.getElementById('theme-toggle');

        initThemeToggle();
        initSearch();
        initDragDrop();
        initNoteModal();
        initReopenModal();
        initErrorRestoreModal();
        initRecompraModal();
        updateColumnCounts();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();