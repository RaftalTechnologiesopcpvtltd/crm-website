
function updateTimer() {
    const timerElements = document.querySelectorAll('.time-blocks[data-deadline]');
    
    timerElements.forEach(element => {
        const deadlineStr = element.dataset.deadline;
        if (!deadlineStr) return;
        
        const deadline = new Date(deadlineStr);
        const now = new Date();
        let diff = deadline.getTime() - now.getTime();
        
        if (diff <= 0) {
            element.querySelector('.days').textContent = '00';
            element.querySelector('.hours').textContent = '00';
            element.querySelector('.minutes').textContent = '00';
            element.querySelector('.seconds').textContent = '00';
            return;
        }
        
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        diff = diff % (1000 * 60 * 60 * 24);
        
        const hours = Math.floor(diff / (1000 * 60 * 60));
        diff = diff % (1000 * 60 * 60);
        
        const minutes = Math.floor(diff / (1000 * 60));
        diff = diff % (1000 * 60);
        
        const seconds = Math.floor(diff / 1000);
        
        element.querySelector('.days').textContent = String(days).padStart(2, '0');
        element.querySelector('.hours').textContent = String(hours).padStart(2, '0');
        element.querySelector('.minutes').textContent = String(minutes).padStart(2, '0');
        element.querySelector('.seconds').textContent = String(seconds).padStart(2, '0');
    });
}

document.addEventListener('DOMContentLoaded', () => {
    updateTimer();
    setInterval(updateTimer, 1000);
});
