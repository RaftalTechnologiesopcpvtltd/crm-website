
function updateTimer() {
    const timerElements = document.querySelectorAll('.time-blocks[data-deadline]');
    
    timerElements.forEach(element => {
        const deadline = new Date(element.dataset.deadline + 'T23:59:59');  // Add time component
        const now = new Date();
        let diff = deadline - now;
        
        // Handle case when time is up
        if (diff <= 0) {
            element.querySelector('.days').textContent = '00';
            element.querySelector('.hours').textContent = '00';
            element.querySelector('.minutes').textContent = '00';
            element.querySelector('.seconds').textContent = '00';
            return;
        }
        
        // Calculate time components
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        diff -= days * (1000 * 60 * 60 * 24);
        
        const hours = Math.floor(diff / (1000 * 60 * 60));
        diff -= hours * (1000 * 60 * 60);
        
        const minutes = Math.floor(diff / (1000 * 60));
        diff -= minutes * (1000 * 60);
        
        const seconds = Math.floor(diff / 1000);
        
        // Update display
        element.querySelector('.days').textContent = String(days).padStart(2, '0');
        element.querySelector('.hours').textContent = String(hours).padStart(2, '0');
        element.querySelector('.minutes').textContent = String(minutes).padStart(2, '0');
        element.querySelector('.seconds').textContent = String(seconds).padStart(2, '0');
    });
}

// Start the timer when the page loads
document.addEventListener('DOMContentLoaded', () => {
    updateTimer();
    setInterval(updateTimer, 1000);
});
