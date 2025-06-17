document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('flashcard-form');
    const fileInput = document.getElementById('json_file');
    const textArea = document.getElementById('json_text');
    
    // Clear the other input when one is selected
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            textArea.value = '';
        }
    });
    
    textArea.addEventListener('input', function() {
        if (this.value.trim()) {
            fileInput.value = '';
        }
    });
    
    // Form validation
    form.addEventListener('submit', function(e) {
        const hasFile = fileInput.files.length > 0;
        const hasText = textArea.value.trim();
        
        if (!hasFile && !hasText) {
            e.preventDefault();
            alert('Please provide JSON data either by uploading a file or entering text.');
            return false;
        }
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Processing...';
        submitBtn.disabled = true;
        
        // Re-enable button after a delay in case of error
        setTimeout(function() {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }, 10000);
    });
    
    // Auto-resize textarea
    textArea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.max(this.scrollHeight, 200) + 'px';
    });
    
    // JSON validation and formatting
    let validationTimeout;
    textArea.addEventListener('input', function() {
        clearTimeout(validationTimeout);
        validationTimeout = setTimeout(validateJSON, 500);
    });
    
    function validateJSON() {
        const text = textArea.value.trim();
        if (!text) return;
        
        try {
            const parsed = JSON.parse(text);
            textArea.classList.remove('is-invalid');
            textArea.classList.add('is-valid');
        } catch (e) {
            textArea.classList.remove('is-valid');
            textArea.classList.add('is-invalid');
        }
    }
    
    // Sample data button functionality
    const sampleBtn = document.createElement('button');
    sampleBtn.type = 'button';
    sampleBtn.className = 'btn btn-outline-secondary btn-sm mt-2';
    sampleBtn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Load Sample Data';
    sampleBtn.addEventListener('click', function() {
        const sampleData = {
            "deck_name": "Medical Sample Deck",
            "cards": [
                {
                    "question": "What is the mechanism of action of <span class='highlight-red'>Aspirin</span>?",
                    "answer": "Irreversibly inhibits COX-1 and COX-2 enzymes, preventing prostaglandin synthesis",
                    "notes": "Key drug for cardiovascular protection and pain management",
                    "tags": "Pharmacology::NSAIDs::Aspirin"
                },
                {
                    "cloze_text": "{{c1::Myocardial infarction}} occurs when {{c2::coronary artery}} becomes {{c3::occluded}}",
                    "notes": "Essential pathophysiology concept for USMLE",
                    "tags": "Cardiology::Pathophysiology::MI",
                    "high_yield_flag": "high-yield"
                },
                {
                    "question": "What are the signs of <span class='highlight-red'>diabetic ketoacidosis</span>?",
                    "answer": "Hyperglycemia, ketosis, metabolic acidosis, dehydration",
                    "notes": "Emergency condition requiring immediate treatment",
                    "tags": "Endocrinology::Diabetes::DKA"
                }
            ]
        };
        textArea.value = JSON.stringify(sampleData, null, 2);
        fileInput.value = '';
        validateJSON();
    });
    
    textArea.parentNode.appendChild(sampleBtn);
});
