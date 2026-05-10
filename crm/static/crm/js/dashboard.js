/**
 * crm/static/crm/js/dashboard.js
 * Funciones específicas del Dashboard Kanban CRM SAMA AdTech.
 * NO incluye theme toggle (está en theme.js).
 *
 * Funcionalidades:
 * - Filtrado de leads en tiempo real (search)
 * - Drag & Drop con nota obligatoria + modal de etapa cerrada
 * - Actualización de contadores y estadísticas dinámicas
 */

(function() {
    'use strict';

    // ─── CONFIGURACIÓN ───
    var CONFIG = {
        API_BASE: '/api/crm/leads/',
        DRAG_FEEDBACK_CLASS: 'dragging',
        DRAG_OVER_CLASS: 'drag-over',
    };

    var DOM = {};

    var sidebarOpen = false;

    function toggleSidebar() {
        var sidebar = document.getElementById('sama-sidebar');
        var overlay = document.getElementById('sidebar-overlay');
        console.log('[SAMA] toggleSidebar called');
        console.log('[SAMA] sidebar element:', sidebar);
        console.log('[SAMA] overlay element:', overlay);
        if (!sidebar) {
            console.error('[SAMA] sidebar not found!');
            return;
        }

        sidebarOpen = !sidebarOpen;
        console.log('[SAMA] sidebarOpen:', sidebarOpen);
        if (sidebarOpen) {
            sidebar.classList.add('open');
            document.body.classList.add('sidebar-open');
            if (overlay) overlay.classList.add('visible');
            console.log('[SAMA] sidebar opened - classes:', sidebar.className);
        } else {
            sidebar.classList.remove('open');
            document.body.classList.remove('sidebar-open');
            if (overlay) overlay.classList.remove('visible');
            console.log('[SAMA] sidebar closed - classes:', sidebar.className);
        }
    }

    function closeSidebar() {
        var sidebar = document.getElementById('sama-sidebar');
        var overlay = document.getElementById('sidebar-overlay');
        if (!sidebar) return;

        sidebarOpen = false;
        sidebar.classList.remove('open');
        document.body.classList.remove('sidebar-open');
        if (overlay) overlay.classList.remove('visible');
    }

    var pendingDrag = null;
    var recompraInProgress = false;

    // ─── HELPERS ───
    function isClosedStage(stageName) {
        var name = (stageName || '').toLowerCase();
        return name.indexOf('cerrado') !== -1 || name.indexOf('closed') !== -1;
    }

    function getCookie(name) {
        var cookie = document.cookie.split(';').find(function(c) { return c.trim().startsWith(name + '='); });
        return cookie ? cookie.split('=')[1] : '';
    }

    function hideModal(modalId) {
        var modalEl = document.getElementById(modalId);
        if (!modalEl) return;
        var instance = bootstrap.Modal.getInstance(modalEl);
        if (instance) instance.hide();
    }

    function showModal(modalId) {
        var modalEl = typeof modalId === 'string' ? document.getElementById(modalId) : modalId;
        if (!modalEl) return;
        var instance = bootstrap.Modal.getInstance(modalEl);
        if (instance) {
            instance.show();
        } else {
            new bootstrap.Modal(modalEl).show();
        }
    }

    // ─── STATS REFRESH ───
    function refreshStats() {
        var tenantSlug = SAMA.getTenantSlug ? SAMA.getTenantSlug() : document.body.getAttribute('data-tenant-slug');
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

    function initSidebar() {
        console.log('[SAMA] initSidebar called');
        var toggleBtn = document.getElementById('sidebar-toggle-btn');
        var closeBtn = document.getElementById('sidebar-close-btn');
        var overlay = document.getElementById('sidebar-overlay');
        var applyBtn = document.getElementById('apply-filters-btn');
        var clearBtn = document.getElementById('clear-filters-btn');
        console.log('[SAMA] toggleBtn:', toggleBtn);
        console.log('[SAMA] closeBtn:', closeBtn);
        console.log('[SAMA] overlay:', overlay);
        console.log('[SAMA] applyBtn:', applyBtn);

        if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);
        if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
        if (overlay) overlay.addEventListener('click', closeSidebar);
        if (applyBtn) {
            applyBtn.addEventListener('click', function() {
                console.log('[SAMA] Apply filters clicked');
                applyFilters();
                closeSidebar();
            });
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', function() {
                console.log('[SAMA] Clear filters clicked');
                clearFilters();
            });
        }
        loadTags();

        document.querySelectorAll('.task-filter-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var current = document.querySelector('.task-filter-btn.active');
                if (current === btn) {
                    btn.classList.remove('active');
                } else {
                    if (current) current.classList.remove('active');
                    btn.classList.add('active');
                }
                applyFilters();
            });
        });
    }

    function getFilterValues() {
        var stages = [];
        document.querySelectorAll('.stage-filter:checked').forEach(function(cb) {
            stages.push(cb.value);
        });

        var source = document.getElementById('filter-source');
        var checkedPeriod = document.querySelector('input[name="quickPeriod"]:checked');
        var taskFilter = document.querySelector('.task-filter-btn.active');
        var openOnly = document.getElementById('filter-open-only');
        var tagIds = [];
        document.querySelectorAll('.tag-filter:checked').forEach(function(cb) {
            tagIds.push(cb.value);
        });

        return {
            stages: stages,
            source: source ? source.value : '',
            period: checkedPeriod ? checkedPeriod.value : 'todo',
            taskFilter: taskFilter ? taskFilter.getAttribute('data-task-filter') : 'none',
            openOnly: openOnly ? openOnly.checked : false,
            tagIds: tagIds
        };
    }

    function applyFilters() {
        console.log('[SAMA] applyFilters called');
        var filters = getFilterValues();
        console.log('[SAMA] Filters:', filters);

        var now = new Date();
        var cards = document.querySelectorAll('.lead-card');
        var visibleCount = 0;

        cards.forEach(function(card) {
            var column = card.closest('.kanban-column');
            var stage = card.getAttribute('data-stage') || (column ? column.getAttribute('data-stage') : '');
            var stageMatch = filters.stages.length === 0 || filters.stages.indexOf(stage) !== -1;

            var isClosed = card.getAttribute('data-is-closed') === 'true';
            var closedMatch = !filters.openOnly || !isClosed;

            var source = card.getAttribute('data-source') || '';
            var sourceMatch = !filters.source || source === filters.source;

            var cardTags = (card.getAttribute('data-tags') || '').split(',').filter(function(t) { return t; });
            var tagsMatch = filters.tagIds.length === 0 || filters.tagIds.some(function(tid) { return cardTags.indexOf(tid) !== -1 || cardTags.indexOf(String(tid)) !== -1; });
            console.log('[SAMA] cardTags:', cardTags, 'filters.tagIds:', filters.tagIds, 'tagsMatch:', tagsMatch);

            var hasTask = card.getAttribute('data-has-task') === 'true';
            var taskDate = card.getAttribute('data-task-due');
            var taskMatch = true;
            if (filters.taskFilter && filters.taskFilter !== 'none') {
                var taskDueDate = taskDate ? new Date(taskDate) : null;
                switch (filters.taskFilter) {
                    case 'with_pending':
                        taskMatch = hasTask;
                        break;
                    case 'due_today':
                        taskMatch = taskDueDate && taskDueDate.toDateString() === now.toDateString();
                        break;
                    case 'due_tomorrow':
                        var tomorrow = new Date(now);
                        tomorrow.setDate(tomorrow.getDate() + 1);
                        taskMatch = taskDueDate && taskDueDate.toDateString() === tomorrow.toDateString();
                        break;
                    case 'overdue':
                        taskMatch = taskDueDate && taskDueDate < now;
                        break;
                    case 'none':
                        taskMatch = !hasTask;
                        break;
                }
            }

            var createdStr = card.getAttribute('data-created');
            var createdDate = createdStr ? new Date(createdStr) : null;
            var periodMatch = true;
            if (filters.period && filters.period !== 'todo' && createdDate) {
                var startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                switch (filters.period) {
                    case 'hoy':
                        periodMatch = createdDate >= startOfToday;
                        break;
                    case 'ayer':
                        var yesterday = new Date(startOfToday);
                        yesterday.setDate(yesterday.getDate() - 1);
                        periodMatch = createdDate >= yesterday && createdDate < startOfToday;
                        break;
                    case '7d':
                        var d7 = new Date(startOfToday);
                        d7.setDate(d7.getDate() - 7);
                        periodMatch = createdDate >= d7;
                        break;
                    case '30d':
                        var d30 = new Date(startOfToday);
                        d30.setDate(d30.getDate() - 30);
                        periodMatch = createdDate >= d30;
                        break;
                    case 'mes':
                        var startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
                        periodMatch = createdDate >= startOfMonth;
                        break;
                }
            }

            var show = stageMatch && closedMatch && sourceMatch && tagsMatch && taskMatch && periodMatch;

            card.style.display = show ? '' : 'none';
            if (show) visibleCount++;
        });

        console.log('[SAMA] Visible cards:', visibleCount);
        updateColumnCounts();
    }

    function clearFilters() {
        document.querySelectorAll('.stage-filter').forEach(function(cb) { cb.checked = true; });
        var source = document.getElementById('filter-source');
        if (source) source.value = '';
        var openOnly = document.getElementById('filter-open-only');
        if (openOnly) openOnly.checked = false;
        document.querySelectorAll('.task-filter-btn').forEach(function(btn) { btn.classList.remove('active'); });

        document.querySelectorAll('.lead-card').forEach(function(card) {
            card.style.display = '';
        });
        updateColumnCounts();
    }

    function loadTags() {
        console.log('[SAMA] loadTags called');
        var tenantSlug = document.body.getAttribute('data-tenant-slug');
        if (!tenantSlug) return;

        var url = '/api/crm/tenants/' + tenantSlug + '/tags/';
        fetch(url)
            .then(function(response) {
                if (response.ok) return response.json();
                throw new Error('API error');
            })
            .then(function(tags) {
                console.log('[SAMA] Tags loaded:', tags);
                renderTags(tags);
            })
            .catch(function(error) {
                console.error('[SAMA] Error loading tags:', error);
            });
    }

    function renderTags(tags) {
        var container = document.getElementById('sidebar-tags-list');
        if (!container) return;

        if (!tags || tags.length === 0) {
            container.innerHTML = '<div class="text-muted small">Sin etiquetas</div>';
            return;
        }

        container.innerHTML = tags.map(function(tag) {
            return '<div class="tag-check-item">' +
                '<input class="form-check-input tag-filter" type="checkbox" ' +
                'value="' + tag.id + '" id="tag-' + tag.id + '" checked>' +
                '<span class="tag-color-dot" style="background:' + (tag.color || '#3498db') + ';"></span>' +
                '<label for="tag-' + tag.id + '">' + tag.name + '</label>' +
                '<span class="badge bg-secondary ms-1 tag-count" id="tag-count-' + tag.id + '"></span>' +
                '</div>';
        }).join('');

        container.querySelectorAll('.tag-filter').forEach(function(cb) {
            cb.addEventListener('change', function() {
                updateFilterCounts();
            });
        });
    }

    function updateFilterCounts() {
        var cards = document.querySelectorAll('.lead-card');
        var cardsData = [];
        cards.forEach(function(card) {
            cardsData.push(card);
        });

        var tagCounts = {};
        var taskCounts = {
            with_pending: 0,
            due_today: 0,
            due_tomorrow: 0,
            overdue: 0,
            none: 0
        };
        var now = new Date();

        cardsData.forEach(function(card) {
            var tags = (card.getAttribute('data-tags') || '').split(',').filter(function(t) { return t; });
            tags.forEach(function(tagId) {
                tagCounts[tagId] = (tagCounts[tagId] || 0) + 1;
            });

            var hasTask = card.getAttribute('data-has-task') === 'true';
            var taskDate = card.getAttribute('data-task-due');
            var taskDueDate = taskDate ? new Date(taskDate) : null;

            if (hasTask) taskCounts.with_pending++;
            if (taskDueDate) {
                if (taskDueDate.toDateString() === now.toDateString()) taskCounts.due_today++;
                var tomorrow = new Date(now);
                tomorrow.setDate(tomorrow.getDate() + 1);
                if (taskDueDate.toDateString() === tomorrow.toDateString()) taskCounts.due_tomorrow++;
                if (taskDueDate < now) taskCounts.overdue++;
            }
            if (!hasTask) taskCounts.none++;
        });

        document.querySelectorAll('.tag-count').forEach(function(badge) {
            var tagId = badge.id.replace('tag-count-', '');
            var count = tagCounts[tagId] || 0;
            badge.textContent = count > 0 ? count : '';
        });

        var taskBtnWithPending = document.querySelector('[data-task-filter="with_pending"]');
        var taskBtnDueToday = document.querySelector('[data-task-filter="due_today"]');
        var taskBtnDueTomorrow = document.querySelector('[data-task-filter="due_tomorrow"]');
        var taskBtnOverdue = document.querySelector('[data-task-filter="overdue"]');
        var taskBtnNone = document.querySelector('[data-task-filter="none"]');

        if (taskBtnWithPending) taskBtnWithPending.innerHTML = 'Con tareas pendientes <span class="badge bg-secondary ms-1">' + taskCounts.with_pending + '</span>';
        if (taskBtnDueToday) taskBtnDueToday.innerHTML = 'Vencen hoy <span class="badge bg-secondary ms-1">' + taskCounts.due_today + '</span>';
        if (taskBtnDueTomorrow) taskBtnDueTomorrow.innerHTML = 'Mañana <span class="badge bg-secondary ms-1">' + taskCounts.due_tomorrow + '</span>';
        if (taskBtnOverdue) taskBtnOverdue.innerHTML = 'Vencidas <span class="badge bg-secondary ms-1">' + taskCounts.overdue + '</span>';
        if (taskBtnNone) taskBtnNone.innerHTML = 'Sin tareas <span class="badge bg-secondary ms-1">' + taskCounts.none + '</span>';
    }

    // ─── INIT ───
    function init() {
        console.log('[SAMA] dashboard.js init called');
        // Solo inicializar si estamos en el dashboard (existe lead-search)
        if (!document.getElementById('lead-search')) {
            console.log('[SAMA] lead-search not found, skipping init');
            return;
        }

        DOM.searchInput = document.getElementById('lead-search');
        DOM.searchClear = document.getElementById('search-clear');
        DOM.leadCards = document.querySelectorAll('.lead-card');
        DOM.kanbanColumns = document.querySelectorAll('.kanban-column');

        initSearch();
        initDragDrop();
        initNoteModal();
        initReopenModal();
        initErrorRestoreModal();
        initRecompraModal();
        initSidebar();
        updateFilterCounts();
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
        console.log('[SAMA] onDragStart');
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
        console.log('[SAMA] onDrop');
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
            var tenantSlug = SAMA.getTenantSlug();

            if (!pendingDrag) return;

            var isLeadClosed = pendingDrag.card && pendingDrag.card.getAttribute('data-is-closed') === 'true';
            var isMovingToActive = !isClosedStage(pendingDrag.newStage);

            hideModal('noteModal');

            if (!note) {
                if (isLeadClosed && isMovingToActive) {
                    document.getElementById('drag-note-text').value = '';
                    showModal('reopenModal');
                } else {
                    doStageChange(pendingDrag.leadId, pendingDrag.newStage, pendingDrag.targetCol, pendingDrag.card, pendingDrag.sourceCol, note, tenantSlug);
                    pendingDrag = null;
                }
            } else {
                if (isLeadClosed && isMovingToActive) {
                    document.getElementById('drag-note-text').value = '';
                    pendingDrag.note = note;
                    showModal('reopenModal');
                } else {
                    doStageChange(pendingDrag.leadId, pendingDrag.newStage, pendingDrag.targetCol, pendingDrag.card, pendingDrag.sourceCol, note, tenantSlug);
                    pendingDrag = null;
                }
            }
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            setTimeout(function() {
                if (!document.getElementById('reopenModal').classList.contains('show') &&
                    !document.getElementById('errorRestoreModal').classList.contains('show') &&
                    !document.getElementById('recompraModal').classList.contains('show')) {
                    if (pendingDrag && !pendingDrag._transitioning && !recompraInProgress) {
                        revertCard(pendingDrag.card, pendingDrag.sourceCol);
                        pendingDrag = null;
                    }
                }
            }, 100);
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
                'X-CSRFToken': SAMA.getCookie('csrftoken'),
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
            if (pendingDrag) pendingDrag._transitioning = true;
            if (pendingDrag) {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
                pendingDrag._transitioning = false;
                pendingDrag = null;
            }
            hideModal('reopenModal');
        });

        newBtn.addEventListener('click', function() {
            if (pendingDrag) pendingDrag._transitioning = true;
            var product = document.querySelector('#recompraModal input#recompra-product');
            if (product) product.value = pendingDrag && pendingDrag.card ? pendingDrag.card.getAttribute('data-product') || '' : '';
            hideModal('reopenModal');
            setTimeout(function() { showModal('recompraModal'); }, 350);
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            if (pendingDrag && !pendingDrag._transitioning && !recompraInProgress) {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
                pendingDrag = null;
            }
            if (pendingDrag && pendingDrag._transitioning) {
                pendingDrag._transitioning = false;
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
            var tenantSlug = SAMA.getTenantSlug();

            hideModal('errorRestoreModal');
            hideModal('reopenModal');

            var targetCol = null;
            document.querySelectorAll('.kanban-column').forEach(function(col) {
                if (col.getAttribute('data-stage') === targetStage) targetCol = col;
            });

            if (targetCol) {
                revertCard(pendingDrag.card, pendingDrag.targetCol);
                doStageChange(pendingDrag.leadId, targetStage, targetCol, pendingDrag.card, pendingDrag.sourceCol, pendingDrag.note || '', tenantSlug);
            } else {
                revertCard(pendingDrag.card, pendingDrag.sourceCol);
            }

            if (pendingDrag) pendingDrag._transitioning = false;
            pendingDrag = null;
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            if (pendingDrag && pendingDrag._transitioning) {
                pendingDrag._transitioning = false;
            }
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
            var tenantSlug = SAMA.getTenantSlug();
            var leadId = pendingDrag.leadId;
            var originalCard = pendingDrag.card;

            recompraInProgress = true;

            hideModal('recompraModal');

            if (pendingDrag.note) {
                doAddNote(leadId, pendingDrag.note, tenantSlug);
            }

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
                recompraInProgress = false;
                setTimeout(refreshStats, 300);
                location.reload();
            })
            .catch(function(error) {
                console.error('Error en recompra:', error);
                pendingDrag = null;
                recompraInProgress = false;
                if (originalCard) {
                    revertCard(originalCard, pendingDrag ? pendingDrag.sourceCol : null);
                }
                location.reload();
            });
        });

        modalEl.addEventListener('hidden.bs.modal', function() {
            if (pendingDrag) pendingDrag._transitioning = false;
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();