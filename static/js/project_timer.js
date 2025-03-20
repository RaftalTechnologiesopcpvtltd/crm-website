
function updateTimer() {
    const timerElements = document.querySelectorAll('[data-deadline]');
    
    timerElements.forEach(element => {
        const deadline = new Date(element.dataset.deadline);
        const now = new Date();
        const diff = deadline - now;
        
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            
            element.textContent = `${days}d ${hours}h ${minutes}m remaining`;
        } else {
            element.textContent = 'Deadline passed';
            element.classList.add('text-danger');
        }
    });
}

setInterval(updateTimer, 60000); // Update every minute
updateTimer(); // Initial update
