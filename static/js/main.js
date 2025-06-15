document.addEventListener('DOMContentLoaded', function() {
    console.log('Analytics Dashboard loaded');
    
    // Fetch some sample data
    fetch('/api/data')
        .then(response => response.json())
        .then(data => {
            console.log('Data loaded:', data);
        })
        .catch(error => {
            console.error('Error loading data:', error);
        });
});