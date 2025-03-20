
function updateTimer() {
    const timerElements = document.querySelectorAll('.time-blocks[data-deadline]');
    
    timerElements.forEach(element => {
        const deadline = new Date(element.dataset.deadline);
        const now = new Date();
        const diff = deadline - now;
        
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            element.querySelector('.days').textContent = String(days).padStart(2, '0');
            element.querySelector('.hours').textContent = String(hours).padStart(2, '0');
            element.querySelector('.minutes').textContent = String(minutes).padStart(2, '0');
            element.querySelector('.seconds').textContent = String(seconds).padStart(2, '0');
        } else {
            element.querySelector('.days').textContent = '00';
            element.querySelector('.hours').textContent = '00';
            element.querySelector('.minutes').textContent = '00';
            element.querySelector('.seconds').textContent = '00';
        }
    });
}

setInterval(updateTimer, 1000); // Update every second
updateTimer(); // Initial update
