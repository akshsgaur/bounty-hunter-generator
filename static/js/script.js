// Format number with commas
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Apply formatting to credit amounts
document.addEventListener('DOMContentLoaded', function() {
    // Format any credit amounts on the page
    const creditElements = document.querySelectorAll('.reward');
    creditElements.forEach(element => {
        const text = element.textContent;
        if (text.includes('Credits')) {
            const numberPart = text.split(' ')[1].replace(/,/g, '');
            const formattedNumber = formatNumber(numberPart);
            element.textContent = `Reward: ${formattedNumber} Credits`;
        }
    });
    
    // Add loading indicator when form is submitted
    const bountyForm = document.querySelector('form');
    if (bountyForm) {
        bountyForm.addEventListener('submit', function() {
            const submitButton = this.querySelector('button[type="submit"]');
            submitButton.textContent = 'Scanning Galactic Records...';
            submitButton.disabled = true;
            
            // Create and append a loading overlay
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay';
            loadingOverlay.innerHTML = `
                <div class="loading-spinner"></div>
                <p>Searching across the galaxy...</p>
            `;
            document.body.appendChild(loadingOverlay);
        });
    }
     // Yoda advice functionality
     const yodaBtn = document.getElementById('yoda-advice-btn');
     const yodaText = document.getElementById('yoda-advice-text');
     const yodaAudio = document.getElementById('yoda-audio');
     
     if (yodaBtn) {
         yodaBtn.addEventListener('click', async function() {
             // Disable button and show loading state
             yodaBtn.disabled = true;
             yodaBtn.textContent = 'Meditating...';
             yodaBtn.classList.add('pulse');
             yodaText.classList.add('hidden');
             
             try {
                 // Fetch Yoda's advice
                 const response = await fetch(`/get_yoda_advice/1`);
                 const data = await response.json();
                 
                 if (data.error) {
                     throw new Error(data.error);
                 }
                 
                 // Display the advice
                 yodaText.innerHTML = data.advice.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
                 yodaText.classList.remove('hidden');
                 yodaText.classList.add('yoda-speaking');
                 
                 // Remove animation after a delay
                 setTimeout(() => {
                     yodaText.classList.remove('yoda-speaking');
                 }, 3000);
                 
                 // Re-enable button
                 yodaBtn.disabled = false;
                 yodaBtn.textContent = 'Hear More Wisdom';
                 yodaBtn.classList.remove('pulse');
                 
             } catch (error) {
                 console.error('Error getting Yoda advice:', error);
                 yodaText.textContent = 'The Force is not strong with the connection. Try again, you must.';
                 yodaText.classList.remove('hidden');
                 yodaBtn.disabled = false;
                 yodaBtn.textContent = 'Try Again';
                 yodaBtn.classList.remove('pulse');
             }
         });
     }
     const sendEmailBtn = document.getElementById('send-email-btn');
     const emailInput = document.getElementById('email-input');
     const emailStatus = document.getElementById('email-status');
     
     if (sendEmailBtn) {
         sendEmailBtn.addEventListener('click', async function() {
             const email = emailInput.value;
             
             if (!email || !validateEmail(email)) {
                 showEmailStatus('Invalid email address', 'error');
                 return;
             }
             
             // Disable button and show loading state
             sendEmailBtn.disabled = true;
             sendEmailBtn.textContent = 'Transmitting...';
             
             try {
                 const formData = new FormData();
                 formData.append('email', email);
                 
                 const response = await fetch('/email_bounty', {
                     method: 'POST',
                     body: formData
                 });
                 
                 const data = await response.json();
                 
                 if (data.error) {
                     throw new Error(data.error);
                 }
                 
                 showEmailStatus('Bounty transmitted successfully!', 'success');
                 emailInput.value = '';
                 
             } catch (error) {
                 console.error('Error sending email:', error);
                 showEmailStatus('Failed to send bounty. Please try again.', 'error');
             }
             
             // Re-enable button
             sendEmailBtn.disabled = false;
             sendEmailBtn.textContent = 'Transmit Bounty';
         });
     }
     
     function validateEmail(email) {
         const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
         return re.test(email);
     }
     
     function showEmailStatus(message, type) {
         emailStatus.textContent = message;
         emailStatus.className = type;
         emailStatus.classList.remove('hidden');
         
         setTimeout(() => {
             emailStatus.classList.add('hidden');
         }, 5000);
     }


});