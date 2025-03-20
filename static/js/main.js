// main.js - Employee Management System

document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on small screens
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-collapsed');
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.toggle('d-none');
        });
    }

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Dashboard counter animation
    const counters = document.querySelectorAll('.counter');
    if (counters.length > 0) {
        const animateCounters = () => {
            counters.forEach(counter => {
                const target = parseInt(counter.textContent);
                const count = +counter.innerText;
                
                const speed = 200; // Animation speed - lower is faster
                const inc = target / speed;
                
                if (count < target) {
                    counter.innerText = Math.ceil(count + inc);
                    setTimeout(animateCounters, 1);
                } else {
                    counter.innerText = target;
                }
            });
        };
        
        // Start counter animations after a short delay to ensure they're visible
        setTimeout(animateCounters, 500);
    }
    
    // Animate elements when they come into view
    const animateOnScroll = () => {
        const elements = document.querySelectorAll('.fadeIn, .slide-in-left, .slide-in-right');
        elements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            if (elementTop < window.innerHeight - elementVisible) {
                element.style.opacity = '1';
            }
        });
    };
    
    // Run animation check on scroll and on initial load
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll();
    
    // Task status update buttons
    const statusButtons = document.querySelectorAll('.task-status-btn');
    statusButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to update this task status?')) {
                this.closest('form').submit();
            }
        });
    });

    // Confirmation for delete actions
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                this.closest('form').submit();
            }
        });
    });

    // Date range validation for leave forms
    const leaveForm = document.getElementById('leaveForm');
    if (leaveForm) {
        leaveForm.addEventListener('submit', function(e) {
            const startDate = new Date(document.getElementById('start_date').value);
            const endDate = new Date(document.getElementById('end_date').value);
            
            if (endDate < startDate) {
                e.preventDefault();
                alert('End date cannot be earlier than start date');
            }
        });
    }

    // Auto-calculate net pay in payroll form
    const payrollForm = document.getElementById('payrollForm');
    if (payrollForm) {
        const calculateNetPay = function() {
            const baseSalary = parseFloat(document.getElementById('base_salary').value) || 0;
            const bonus = parseFloat(document.getElementById('bonus').value) || 0;
            const deductions = parseFloat(document.getElementById('deductions').value) || 0;
            
            const netPay = baseSalary + bonus - deductions;
            document.getElementById('net_pay').value = netPay.toFixed(2);
        };
        
        document.getElementById('bonus').addEventListener('input', calculateNetPay);
        document.getElementById('deductions').addEventListener('input', calculateNetPay);
    }

    // Print functionality
    const printButtons = document.querySelectorAll('.print-btn');
    printButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            window.print();
        });
    });
});
