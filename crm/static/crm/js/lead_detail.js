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

    var colorInput = document.getElementById('new-tag-color');
    if (colorInput) {
        colorInput.addEventListener('input', function(e) {
            var hexSpan = document.getElementById('color-hex');
            if (hexSpan) hexSpan.textContent = e.target.value;
        });
    }

    var colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e67e22', '#34495e', '#e91e63', '#00bcd4', '#8e44ad', '#27ae60'];
    if (colorInput) {
        colorInput.value = colors[Math.floor(Math.random() * colors.length)];
        var hexSpan = document.getElementById('color-hex');
        if (hexSpan) hexSpan.textContent = colorInput.value;
    }

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
                renderModalCurrentTags();
            })
            .catch(function() {
                currentTags = [];
            });
    }

    function loadAvailableTags() {
        apiCall(tenantApiBase, 'GET', null)
            .then(function(tags) {
                availableTags = tags || [];
                renderModalAvailableTags();
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

    function renderModalCurrentTags() {
        var container = document.getElementById('modal-current-tags');
        if (!container) return;

        if (currentTags.length === 0) {
            container.innerHTML = '<span class="text-muted small">Sin etiquetas asignadas</span>';
            return;
        }

        container.innerHTML = currentTags.map(function(tag) {
            var textColor = window.getContrastColor(tag.color);
            return '<span class="tag-badge" style="background-color: ' + tag.color + '; color: ' + textColor + ';">' +
                '<span class="tag-name">' + tag.name + '</span>' +
                '<button type="button" class="tag-remove-btn" onclick="removeTag(' + tag.id + ')" title="Quitar etiqueta" style="color: ' + textColor + ';">&times;</button>' +
                '</span>';
        }).join('');
    }

    function renderModalAvailableTags() {
        var container = document.getElementById('modal-available-tags');
        if (!container) return;

        var assignedIds = currentTags.map(function(t) { return t.id; });
        var unassignedTags = availableTags.filter(function(tag) {
            return assignedIds.indexOf(tag.id) === -1;
        });

        if (unassignedTags.length === 0) {
            container.innerHTML = '<span class="text-muted small">No hay más etiquetas disponibles</span>';
            return;
        }

        container.innerHTML = unassignedTags.map(function(tag) {
            var textColor = window.getContrastColor(tag.color);
            return '<button type="button" class="btn btn-sm tag-option-btn" style="background-color: ' + tag.color + '; color: ' + textColor + '; border: none;" onclick="addTag(' + tag.id + ')">' +
                '<i class="bi bi-plus"></i> ' + tag.name +
                '</button>';
        }).join('');
    }

    window.openTagsModal = function() {
        loadCurrentTags();
        loadAvailableTags();
        var modalEl = document.getElementById('tagsModal');
        if (modalEl) {
            var modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    };

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
                if (nameInput) nameInput.value = '';
                return addTag(newTag.id);
            })
            .catch(function() {});
    };

    window.openTasksModal = function() {
        loadTasks();
        var modalEl = document.getElementById('tasksModal');
        if (modalEl) {
            var modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    };

    function loadTasks() {
        apiCall(apiBase + '/tasks/' + apiQuery, 'GET', null)
            .then(function(tasks) {
                renderModalTasks(tasks);
            })
            .catch(function() {
                renderModalTasks([]);
            });
    }

    function renderModalTasks(tasks) {
        var container = document.getElementById('modal-tasks-list');
        if (!container) return;

        if (tasks.length === 0) {
            container.innerHTML = '<span class="text-muted small">No hay tareas</span>';
            return;
        }

        var today = new Date().toISOString().split('T')[0];

        container.innerHTML = tasks.map(function(task) {
            var isOverdue = task.due_date && task.due_date < today && !task.is_completed;
            var isCompleted = task.is_completed;
            var dueDateClass = isCompleted ? 'bg-secondary' : (isOverdue ? 'bg-danger' : 'bg-warning');
            var dueDateDisplay = task.due_date ? task.due_date.split('-').reverse().join('/') : '';

            return '<div class="task-item d-flex align-items-center gap-2 p-2" style="background: var(--color-surface-hover); border-radius: 8px; ' + (isCompleted ? 'opacity: 0.6;' : '') + '">' +
                '<input type="checkbox" class="form-check-input" ' + (task.is_completed ? 'checked' : '') + ' onchange="toggleTask(' + task.id + ')" style="margin: 0;">' +
                '<span class="' + (isCompleted ? 'text-decoration-line-through text-muted' : '') + '" style="flex: 1; font-size: .85rem;">' + task.description + '</span>' +
                (task.due_date ? '<span class="badge ' + dueDateClass + '" style="font-size: .7rem;">' + dueDateDisplay + '</span>' : '') +
                '<button type="button" class="btn btn-sm btn-link text-danger p-0" onclick="deleteTask(' + task.id + ')" title="Eliminar">&times;</button>' +
                '</div>';
        }).join('');
    }

    window.createTask = function() {
        var descInput = document.getElementById('new-task-description');
        var dueInput = document.getElementById('new-task-due-date');
        var description = descInput ? descInput.value.trim() : '';
        var due_datetime = dueInput ? dueInput.value : null;

        if (!description) {
            alert('La descripción de la tarea es obligatoria.');
            return;
        }

        var data = { description: description };
        if (due_datetime && due_datetime.trim() !== '') {
            // Convertir de formato local a formato ISO
            var dateObj = new Date(due_datetime);
            if (!isNaN(dateObj.getTime())) {
                // Formato ISO: YYYY-MM-DDTHH:MM:SS
                var isoDate = dateObj.toISOString();
                data.due_date = isoDate;
                console.log('Sending due_date as:', isoDate);
            }
        }

        console.log('Creating task with data:', JSON.stringify(data));

        apiCall(apiBase + '/tasks/' + apiQuery, 'POST', data)
            .then(function(response) {
                console.log('Task created:', response);
                if (descInput) descInput.value = '';
                if (dueInput) dueInput.value = '';
                loadTasks();
                location.reload();
            })
            .catch(function(error) {
                console.error('Error creating task:', error);
                alert('Error al crear la tarea. Verifica los datos e intenta de nuevo.');
            });
    };

    window.toggleTask = function(taskId) {
        apiCall(apiBase + '/tasks/' + taskId + '/' + apiQuery, 'PATCH', { is_completed: true })
            .then(function() {
                loadTasks();
                location.reload();
            })
            .catch(function() {});
    };

    window.deleteTask = function(taskId) {
        if (!confirm('¿Eliminar esta tarea?')) return;
        apiCall(apiBase + '/tasks/' + taskId + '/' + apiQuery, 'DELETE', null)
            .then(function() {
                loadTasks();
                location.reload();
            })
            .catch(function() {});
    };
}