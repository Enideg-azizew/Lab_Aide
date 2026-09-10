/**

 * Author: Enideg Azizew
 * Dependencies: jQuery, Bootstrap
 */

(function() {
    'use strict';


    // DOM Ready Handler

    $(document).ready(function() {
        initTooltips();
        initPopovers();
        initAutoAlerts();
        initConfirmDelete();
        initFormValidation();
        initFileUpload();
    });


    // Initialization Functions


    function initTooltips() {
        const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        if (tooltipTriggers.length) {
            tooltipTriggers.forEach(el => new bootstrap.Tooltip(el));
        }
    }

    function initPopovers() {
        const popoverTriggers = document.querySelectorAll('[data-bs-toggle="popover"]');
        if (popoverTriggers.length) {
            popoverTriggers.forEach(el => new bootstrap.Popover(el));
        }
    }

    function initAutoAlerts() {
        setTimeout(function() {
            document.querySelectorAll('.alert:not(.persistent)').forEach(alert => {
                const bsAlert = bootstrap.Alert.getInstance(alert);
                if (bsAlert) {
                    bsAlert.close();
                } else {
                    alert.classList.add('fade');
                    setTimeout(() => alert.remove(), 500);
                }
            });
        }, 5000);
    }

    function initConfirmDelete() {
        document.querySelectorAll('.confirm-delete, [data-confirm-delete]').forEach(el => {
            el.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to delete this item?')) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        });
    }

    function initFormValidation() {
        document.querySelectorAll('.needs-validation').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!this.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                this.classList.add('was-validated');
            });
        });
    }

    function initFileUpload() {
        document.querySelectorAll('.upload-area').forEach(area => {
            area.addEventListener('dragover', function(e) {
                e.preventDefault();
                this.classList.add('dragover');
            });

            area.addEventListener('dragleave', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
            });

            area.addEventListener('drop', function(e) {
                e.preventDefault();
                this.classList.remove('dragover');
                const files = e.dataTransfer.files;
                const input = this.querySelector('input[type="file"]');
                if (input && files.length) {
                    input.files = files;
                    const label = this.querySelector('.upload-text');
                    if (label) label.textContent = files[0].name;
                }
            });
        });
    }


    // Utility Functions


    /**
     * Format a date to readable string
     * @param {Date|string} date - Date to format
     * @returns {string} Formatted date (e.g., "Jan 15, 2024")
     */
    function formatDate(date) {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    /**
     * Format a number with decimal places
     * @param {number} num - Number to format
     * @param {number} decimals - Decimal places (default: 2)
     * @returns {string} Formatted number
     */
    function formatNumber(num, decimals = 2) {
        return Number(num).toFixed(decimals);
    }

    /**
     * Get Bootstrap badge HTML for a status
     * @param {string} status - Status key ('normal', 'critical', etc.)
     * @returns {string} HTML badge markup
     */
    function getStatusBadge(status) {
        const badges = {
            'normal': '<span class="badge bg-success">Normal</span>',
            'abnormal': '<span class="badge bg-warning text-dark">Abnormal</span>',
            'critical': '<span class="badge bg-danger">Critical</span>',
            'low': '<span class="badge bg-warning text-dark">Low Stock</span>',
            'expired': '<span class="badge bg-danger">Expired</span>',
            'ok': '<span class="badge bg-success">OK</span>',
            'active': '<span class="badge bg-success">Active</span>',
            'inactive': '<span class="badge bg-secondary">Inactive</span>',
        };
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    /**
     * Get CSRF token from cookie
     * @returns {string} CSRF token value
     */
    function getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }

    /**
     * Debounce function for search inputs
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    /**
     * Show a loading spinner on a button
     * @param {HTMLElement} btn - Button element
     * @param {string} text - Loading text (default: 'Loading...')
     */
    function showLoading(btn, text = 'Loading...') {
        const originalText = btn.innerHTML;
        btn.dataset.originalText = originalText;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${text}`;
        btn.disabled = true;
        return function restore() {
            btn.innerHTML = btn.dataset.originalText || originalText;
            btn.disabled = false;
        };
    }


    // Expose utilities globally


    window.LabUtils = {
        formatDate,
        formatNumber,
        getStatusBadge,
        getCSRFToken,
        debounce,
        showLoading
    };


    // Console greeting


    console.log('%cMediLab Clinical Laboratory System', 'font-size: 18px; font-weight: bold; color: #0d6efd;');
    console.log('%cBuilt by Enideg Azizew', 'font-size: 13px; color: #4a5568;');
    console.log('%c© ' + new Date().getFullYear() + ' All rights reserved', 'font-size: 12px; color: #6c757d;');

})();
