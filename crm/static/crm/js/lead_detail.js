function initLeadDetail(leadId, tenantSlug, csrfToken) {
    var apiBase = '/api/crm/leads/' + leadId;
    var apiQuery = '?tenant_slug=' + encodeURIComponent(tenantSlug);
    var tenantApiBase = '/api/crm/tenants/' + tenantSlug + '/tags/';
    var currentTags = [];
    var availableTags = [];

    window.getContrastColor = function(hexColor) {
        var hex = hexColor.replace('#', '');
        var r = parseInt(hex.substr(0, 2), 16);
        var g = parseInt(hex.substr(2, 2), 16);
        var b = parseInt(hex.substr(4, 2), 16);
        var brightness = (r * 299 + g * 587 + b * 114) / 1000;
        return brightness > 128 ? '#1e293b' : '#ffffff';
    };

    window.apiCall = function(url, method, body) {
        return new Promise(function(resolve, reject) {
            var options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
            };
            if (body) options.body = JSON.stringify(body);
            fetch(url, options)
                .then(function(response) {
                    if (!response.ok) {
                        if (response.status === 403) {
                            alert('No tienes permiso para realizar esta acción.');
                        } else if (response.status === 404) {
                            alert('Recurso no encontrado.');
                        } else {
                            response.json().then(function(data) {
                                var errorMsg = data.detail || JSON.stringify(data);
                                alert('Error: ' + errorMsg);
                            }).catch(function() {
                                alert('Error en la solicitud: ' + response.statusText);
                            });
                        }
                        reject(response);
                        return;
                    }
                    if (response.status === 204 || response.status === 200) {
                        resolve(response.json().catch(function() { return {}; }));
                    } else {
                        resolve(response.json());
                    }
                })
                .catch(function(error) {
                    reject(error);
                });
        });
    };

    loadCurrentTags();
    loadAvailableTags();

    window.updateStage = function() {
        var newStage = document.getElementById('stage-select').value;
        apiCall(apiBase + '/' + apiQuery, 'PATCH', { current_stage: newStage })
            .then(function() {
                location.reload();
            });
    };

    window.addNote = function() {
        var note = document.getElementById('note-text').value.trim();
        if (!note) return alert('Escribe una nota.');
        apiCall(apiBase + '/add_note/' + apiQuery, 'POST', { note: note })
            .then(function() {
                location.reload();
            });
    };

    window.addActivity = function() {
        var modal = document.getElementById('activityModal');
        if (!modal) return;
        var textarea = modal.querySelector('#activity-description');
        textarea.value = '';
        var modalObj = new bootstrap.Modal(modal);
        modalObj.show();
    };

    window.openDeleteModalLeadDetail = function(leadId) {
        var modalEl = document.getElementById('deleteLeadModal');
        if (modalEl) {
            var modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    };

    var modal = document.getElementById('activityModal');
    var saveBtn = modal ? modal.querySelector('#save-activity-btn') : null;
    var textarea = modal ? modal.querySelector('#activity-description') : null;
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            var desc = textarea.value.trim();
            if (!desc) return;
            apiCall(apiBase + '/add_activity/' + apiQuery, 'POST', { description: desc })
                .then(function() {
                    var modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) modalInstance.hide();
                    location.reload();
                });
        });
    }

    var confirmBtn = document.getElementById('confirm-delete-btn-detail');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            var url = '/api/crm/leads/' + leadId + '/?tenant_slug=' + encodeURIComponent(tenantSlug);

            fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
            })
            .then(function(response) {
                if (response.ok || response.status === 204) {
                    var modalInstance = bootstrap.Modal.getInstance(document.getElementById('deleteLeadModal'));
                    if (modalInstance) modalInstance.hide();
                    window.location.href = '/crm/' + tenantSlug + '/dashboard/';
                } else {
                    alert('Error al eliminar lead');
                }
            })
            .catch(function(error) {
                console.error('Error:', error);
                alert('Error al eliminar lead');
            });
        });
    }

    function loadCurrentTags() {
        apiCall(apiBase + apiQuery, 'GET', null)
            .then(function(data) {
                currentTags = data.tags || [];
                renderCurrentTags();
            })
            .catch(function() {
                currentTags = [];
            });
    }

    function loadAvailableTags() {
        apiCall(tenantApiBase, 'GET', null)
            .then(function(tags) {
                availableTags = tags || [];
                renderAvailableTagsDropdown();
            })
            .catch(function() {
                availableTags = [];
            });
    }

    function renderCurrentTags() {
        var container = document.getElementById('current-tags');
        var noTagsMsg = document.getElementById('no-tags-message');
        if (!container) return;

        if (currentTags.length === 0) {
            container.innerHTML = '';
            if (noTagsMsg) noTagsMsg.style.display = 'block';
            return;
        }

        if (noTagsMsg) noTagsMsg.style.display = 'none';

        container.innerHTML = currentTags.map(function(tag) {
            var textColor = window.getContrastColor(tag.color);
            return '<span class="tag-badge" style="background-color: ' + tag.color + '; color: ' + textColor + ';">' +
                '<span class="tag-name">' + tag.name + '</span>' +
                '<button type="button" class="tag-remove-btn" onclick="removeTag(' + tag.id + ')" title="Quitar etiqueta" style="color: ' + textColor + ';">&times;</button>' +
                '</span>';
        }).join('');
    }

    function renderAvailableTagsDropdown() {
        var container = document.getElementById('available-tags-list');
        var noTagsAvailable = document.getElementById('no-tags-available');
        if (!container) return;

        var assignedIds = currentTags.map(function(t) { return t.id; });
        var unassignedTags = availableTags.filter(function(tag) {
            return assignedIds.indexOf(tag.id) === -1;
        });

        if (unassignedTags.length === 0) {
            container.innerHTML = '';
            if (noTagsAvailable) noTagsAvailable.style.display = 'block';
            return;
        }

        if (noTagsAvailable) noTagsAvailable.style.display = 'none';

        container.innerHTML = unassignedTags.map(function(tag) {
            var textColor = window.getContrastColor(tag.color);
            return '<li><a class="dropdown-item" href="#" onclick="addTag(' + tag.id + '); return false;" style="display: flex; align-items: center; gap: 8px;">' +
                '<span style="display: inline-block; width: 12px; height: 12px; border-radius: 3px; background-color: ' + tag.color + ';"></span>' +
                '<span style="color: var(--color-text-primary);">' + tag.name + '</span>' +
                '</a></li>';
        }).join('');
    }

    window.addTag = function(tagId) {
        apiCall(apiBase + '/add_tag/' + apiQuery, 'POST', { tag_id: tagId })
            .then(function() {
                loadCurrentTags();
                loadAvailableTags();
            })
            .catch(function() {});
    };

    window.removeTag = function(tagId) {
        if (!confirm('¿Quitar esta etiqueta del lead?')) return;
        apiCall(apiBase + '/remove_tag/' + apiQuery, 'POST', { tag_id: tagId })
            .then(function() {
                loadCurrentTags();
                loadAvailableTags();
            })
            .catch(function() {});
    };

    window.showNewTagForm = function() {
        var form = document.getElementById('new-tag-form');
        if (form) {
            form.style.display = 'block';
            var input = document.getElementById('new-tag-name');
            if (input) input.focus();
            var colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4'];
            var randomColor = colors[Math.floor(Math.random() * colors.length)];
            var colorInput = document.getElementById('new-tag-color');
            if (colorInput) colorInput.value = randomColor;
        }
    };

    window.hideNewTagForm = function() {
        var form = document.getElementById('new-tag-form');
        if (form) form.style.display = 'none';
        var input = document.getElementById('new-tag-name');
        if (input) input.value = '';
    };

    window.createAndAssignTag = function() {
        var nameInput = document.getElementById('new-tag-name');
        var colorInput = document.getElementById('new-tag-color');
        var name = nameInput ? nameInput.value.trim() : '';
        var color = colorInput ? colorInput.value : '#3498db';

        if (!name) {
            alert('El nombre de la etiqueta es obligatorio.');
            return;
        }

        apiCall(tenantApiBase, 'POST', { name: name, color: color })
            .then(function(newTag) {
                hideNewTagForm();
                return addTag(newTag.id);
            })
            .catch(function() {});
    };
}