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
                    "type": "basic",
                    "front": "What is the mechanism of action of <span class='highlight-red'>Aspirin</span>?",
                    "back": "Irreversibly inhibits <span class='highlight-red'>COX-1 and COX-2</span> enzymes, reducing prostaglandin synthesis",
                    "note": "Key drug for cardiovascular protection and pain management",
                    "tags": ["Pharmacology", "NSAIDs", "Aspirin"],
                    "mnemonic": "<span class='highlight-pink'>COX Blocker</span>: Aspirin permanently blocks COX enzymes like putting a cork in a bottle",
                    "vignette": {
                        "clinical_case": "A 65-year-old man with a history of myocardial infarction is prescribed daily low-dose aspirin for secondary prevention.",
                        "explanation": "What is the primary mechanism by which aspirin provides cardioprotective effects? Answer Choices: A. Calcium channel blockade B. <span class='highlight-red'>Irreversible COX-1 inhibition</span> C. ACE inhibition D. Beta-receptor blockade Correct Answer: <span class='highlight-red'>B. Irreversible COX-1 inhibition</span>"
                    }
                },
                {
                    "type": "cloze",
                    "front": "{{c1::Myocardial infarction}} occurs when {{c2::coronary artery}} becomes {{c3::occluded}}",
                    "note": "Essential pathophysiology concept for USMLE",
                    "tags": ["Cardiology", "Pathophysiology", "MI"],
                    "mnemonic": "<span class='highlight-pink'>Heart Attack Triad</span>: Blocked artery → Dead tissue → Heart damage",
                    "vignette": {
                        "clinical_case": "A 55-year-old man presents with crushing chest pain, diaphoresis, and nausea. ECG shows ST-elevation in leads II, III, and aVF.",
                        "explanation": "This presentation is most consistent with: Answer Choices: A. Unstable angina B. <span class='highlight-red'>ST-elevation myocardial infarction</span> C. Pericarditis D. Aortic dissection Correct Answer: <span class='highlight-red'>B. ST-elevation myocardial infarction</span>"
                    }
                }
            ]
        };
        textArea.value = JSON.stringify(sampleData, null, 2);
        fileInput.value = '';
        validateJSON();
    });
    
    textArea.parentNode.appendChild(sampleBtn);
});
