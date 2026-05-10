function initTrash(tenantSlug) {
    window.restoreLead = function(leadId, btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';

        fetch('/api/crm/leads/' + leadId + '/restore/?tenant_slug=' + tenantSlug, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': SAMA.getCookie('csrftoken'),
            },
        })
        .then(function(response) {
            if (!response.ok) throw new Error('Error');
            var item = document.getElementById('trash-item-' + leadId);
            if (item) {
                item.style.transition = 'opacity 0.3s';
                item.style.opacity = '0';
                setTimeout(function() {
                    item.remove();
                    var remaining = document.querySelectorAll('.trash-item');
                    if (remaining.length === 0) location.reload();
                }, 300);
            }
            showToast('Lead restaurado correctamente');
        })
        .catch(function(error) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Restaurar';
            showToast('Error al restaurar el lead');
        });
    };

    function showToast(msg) {
        var toast = document.getElementById('toast');
        var el = document.getElementById('toast-msg');
        if (el) el.textContent = msg;
        if (toast) {
            toast.style.display = 'block';
            toast.style.animation = 'slideIn 0.3s ease';
            setTimeout(function() { toast.style.display = 'none'; }, 3000);
        }
    }
}