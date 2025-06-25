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
                    "type": "basic",
                    "front": "What are the signs of <span class='highlight-red'>diabetic ketoacidosis</span>?",
                    "back": "Hyperglycemia, <span class='highlight-red'>ketosis</span>, metabolic acidosis, and <span class='highlight-red'>dehydration</span>",
                    "note": "Emergency condition requiring immediate treatment - can be life-threatening",
                    "tags": ["Endocrinology", "Diabetes", "DKA"],
                    "mnemonic": "<span class='highlight-pink'>DKA Triad</span>: High sugar (hyperglycemia) + Ketones + Acid (acidosis) = Emergency!",
                    "vignette": {
                        "clinical_case": "A 19-year-old college student with Type 1 diabetes is brought to the emergency department by her roommate. She has been vomiting for the past 24 hours and appears dehydrated. Her roommate reports that the patient has been drinking large amounts of water and urinating frequently. Vital signs show tachycardia and tachypnea with a fruity odor on her breath.",
                        "explanation": "Laboratory results show glucose 450 mg/dL, positive serum ketones, and arterial blood gas with pH 7.25. What is the most likely diagnosis? Answer Choices: A. Hyperosmolar hyperglycemic state B. <span class='highlight-red'>Diabetic ketoacidosis</span> C. Severe dehydration D. Gastroenteritis with dehydration Correct Answer: <span class='highlight-red'>B. Diabetic ketoacidosis</span>"
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
