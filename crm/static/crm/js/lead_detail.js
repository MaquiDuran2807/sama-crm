function initLeadDetail(leadId, tenantSlug, csrfToken) {
    var apiBase = '/api/crm/leads/' + leadId;
    var apiQuery = '?tenant_slug=' + encodeURIComponent(tenantSlug);

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
                        alert('Error en la solicitud: ' + response.statusText);
                        reject(response);
                        return;
                    }
                    resolve(response.json());
                })
                .catch(function(error) {
                    reject(error);
                });
        });
    };

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

    document.addEventListener('DOMContentLoaded', function() {
        var modal = document.getElementById('activityModal');
        if (!modal) return;
        var saveBtn = modal.querySelector('#save-activity-btn');
        var textarea = modal.querySelector('#activity-description');
        if (saveBtn) {
            saveBtn.addEventListener('click', function() {
                var desc = textarea.value.trim();
                if (!desc) return;
                apiCall(apiBase + '/add_activity/' + apiQuery, 'POST', { description: desc })
                    .then(function() {
                        var modalObj = bootstrap.Modal.getInstance(modal);
                        if (modalObj) modalObj.hide();
                        location.reload();
                    });
            });
        }
    });

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

    document.addEventListener('DOMContentLoaded', function() {
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
                        var modal = bootstrap.Modal.getInstance(document.getElementById('deleteLeadModal'));
                        if (modal) modal.hide();
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
    });
}