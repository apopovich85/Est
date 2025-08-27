// Custom JavaScript for the application
document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-dismiss flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm-delete') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Auto-calculate totals in forms
    const priceInputs = document.querySelectorAll('.price-input');
    const quantityInputs = document.querySelectorAll('.quantity-input');
    
    function calculateTotal() {
        const priceInput = document.getElementById('unit_price');
        const quantityInput = document.getElementById('quantity');
        const totalDisplay = document.getElementById('total-display');
        
        if (priceInput && quantityInput && totalDisplay) {
            const price = parseFloat(priceInput.value) || 0;
            const quantity = parseFloat(quantityInput.value) || 0;
            const total = price * quantity;
            totalDisplay.textContent = '$' + total.toFixed(2);
        }
    }
    
    priceInputs.forEach(input => input.addEventListener('input', calculateTotal));
    quantityInputs.forEach(input => input.addEventListener('input', calculateTotal));
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // AJAX form submission helper
    window.submitForm = function(formId, successCallback) {
        const form = document.getElementById(formId);
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (successCallback) successCallback(data);
            } else {
                alert('Error: ' + (data.message || 'Unknown error occurred'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error occurred');
        });
    };
    
    // Component duplication functionality
    window.duplicateComponent = function(componentId, targetAssemblyId) {
        fetch(`/components/${componentId}/duplicate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({
                target_assembly_id: targetAssemblyId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error duplicating component: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error duplicating component');
        });
    };
});