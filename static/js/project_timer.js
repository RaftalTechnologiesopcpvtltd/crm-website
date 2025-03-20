
function updateTimer() {
    const timerElements = document.querySelectorAll('.time-blocks[data-deadline]');
    
    timerElements.forEach(element => {
        const deadlineStr = element.dataset.deadline;
        const startDateStr = element.dataset.startDate;
        if (!deadlineStr) return;
        
        const deadline = new Date(deadlineStr);
        const now = new Date();
        const startDate = startDateStr ? new Date(startDateStr) : null;
        let diff = deadline.getTime() - now.getTime();
        
        // Handle overdue projects
        if (diff <= 0) {
            element.querySelector('.days').textContent = '00';
            element.querySelector('.hours').textContent = '00';
            element.querySelector('.minutes').textContent = '00';
            element.querySelector('.seconds').textContent = '00';
            
            // Update progress bar to 100% for overdue projects
            if (element.nextElementSibling && element.nextElementSibling.classList.contains('progress')) {
                const progressBar = element.nextElementSibling.querySelector('.progress-bar');
                progressBar.style.width = '100%';
                progressBar.setAttribute('aria-valuenow', 100);
                progressBar.classList.add('bg-danger');
                
                const progressText = element.nextElementSibling.nextElementSibling.querySelector('.progress-text');
                if (progressText) {
                    progressText.textContent = 'Project overdue';
                    progressText.classList.add('text-danger');
                }
            }
            return;
        }
        
        // Calculate time remaining
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        diff = diff % (1000 * 60 * 60 * 24);
        
        const hours = Math.floor(diff / (1000 * 60 * 60));
        diff = diff % (1000 * 60 * 60);
        
        const minutes = Math.floor(diff / (1000 * 60));
        diff = diff % (1000 * 60);
        
        const seconds = Math.floor(diff / 1000);
        
        // Update timer display
        element.querySelector('.days').textContent = String(days).padStart(2, '0');
        element.querySelector('.hours').textContent = String(hours).padStart(2, '0');
        element.querySelector('.minutes').textContent = String(minutes).padStart(2, '0');
        element.querySelector('.seconds').textContent = String(seconds).padStart(2, '0');
        
        // Calculate and update project progress if we have a start date
        if (startDate && element.nextElementSibling && element.nextElementSibling.classList.contains('progress')) {
            const progressBar = element.nextElementSibling.querySelector('.progress-bar');
            const progressText = element.nextElementSibling.nextElementSibling.querySelector('.progress-text');
            
            // Calculate total project duration and elapsed time
            const totalDuration = deadline.getTime() - startDate.getTime();
            const elapsedTime = now.getTime() - startDate.getTime();
            
            // Calculate percentage
            let percentComplete = 0;
            if (totalDuration > 0) {
                percentComplete = Math.min(Math.round((elapsedTime / totalDuration) * 100), 100);
            }
            
            // Update progress bar
            progressBar.style.width = `${percentComplete}%`;
            progressBar.setAttribute('aria-valuenow', percentComplete);
            
            // Set color based on progress
            if (percentComplete >= 90) {
                progressBar.className = 'progress-bar bg-danger';
            } else if (percentComplete >= 75) {
                progressBar.className = 'progress-bar bg-warning';
            } else if (percentComplete >= 50) {
                progressBar.className = 'progress-bar bg-info';
            } else {
                progressBar.className = 'progress-bar bg-success';
            }
            
            // Update text
            if (progressText) {
                progressText.textContent = `Timeline progress: ${percentComplete}%`;
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    updateTimer();
    setInterval(updateTimer, 1000);
    
    // Also apply gradient card styles to task cards
    const taskCards = document.querySelectorAll('.card:not(.card-gradient-purple, .card-gradient-blue, .card-gradient-green, .card-gradient-orange)');
    const gradientClasses = ['card-gradient-blue', 'card-gradient-green', 'card-gradient-orange', 'developer-gradient', 'accounting-gradient', 'hr-gradient'];
    
    taskCards.forEach((card, index) => {
        // Apply gradient classes to cards
        const gradientClass = gradientClasses[index % gradientClasses.length];
        card.classList.add(gradientClass);
        
        // Make card headers and text white for better contrast
        const cardHeader = card.querySelector('.card-header');
        if (cardHeader) {
            cardHeader.style.borderBottom = 'none';
            const cardTitle = cardHeader.querySelector('.card-title');
            if (cardTitle) cardTitle.classList.add('text-white');
        }
    });
});
