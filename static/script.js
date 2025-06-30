let cards = [];
let currentPreview = null;

// Form submission
document.getElementById('flashcardForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const card = {
        clinical_vignette: document.getElementById('vignette').value,
        front: document.getElementById('question').value,
        back: document.getElementById('answer').value,
        explanation: document.getElementById('explanation').value,
        mnemonic: document.getElementById('mnemonic').value,
        category: document.getElementById('category').value,
        tags: document.getElementById('tags').value.split(',').map(tag => tag.trim()).filter(tag => tag)
    };
    
    cards.push(card);
    updateCardsList();
    updatePreview(card);
    
    // Reset form
    this.reset();
    document.getElementById('generateBtn').disabled = false;
});

// Update preview
function updatePreview(card) {
    const previewDiv = document.getElementById('previewCard');
    
    let html = '<div class="space-y-3">';
    
    if (card.clinical_vignette) {
        html += `<div class="clinical-vignette">${escapeHtml(card.clinical_vignette)}</div>`;
    }
    
    html += `
        <div class="font-semibold text-lg text-gray-800">${escapeHtml(card.front)}</div>
        <div class="border-t pt-3">
            <div class="bg-green-50 p-3 rounded text-green-800">${escapeHtml(card.back)}</div>
        </div>
    `;
    
    if (card.explanation) {
        html += `<div class="explanation">${escapeHtml(card.explanation)}</div>`;
    }
    
    if (card.mnemonic) {
        html += `<div class="mnemonic">${escapeHtml(card.mnemonic)}</div>`;
    }
    
    if (card.tags.length > 0) {
        html += '<div class="flex flex-wrap gap-2 mt-3">';
        card.tags.forEach(tag => {
            html += `<span class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">${escapeHtml(tag)}</span>`;
        });
        html += '</div>';
    }
    
    html += '</div>';
    previewDiv.innerHTML = html;
}

// Update cards list
function updateCardsList() {
    const listDiv = document.getElementById('cardsList');
    const countSpan = document.getElementById('cardCount');
    
    countSpan.textContent = cards.length;
    
    if (cards.length === 0) {
        listDiv.innerHTML = '<p class="text-gray-400 text-center py-4">No cards added yet</p>';
        return;
    }
    
    listDiv.innerHTML = cards.map((card, index) => `
        <div class="card-item flex justify-between items-center">
            <div class="flex-1">
                <p class="font-medium text-sm">${escapeHtml(card.front.substring(0, 50))}${card.front.length > 50 ? '...' : ''}</p>
                <p class="text-xs text-gray-500">${card.category} • ${card.tags.length} tags</p>
            </div>
            <button onclick="removeCard(${index})" class="text-red-500 hover:text-red-700 p-2">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

// Remove card
function removeCard(index) {
    cards.splice(index, 1);
    updateCardsList();
    if (cards.length === 0) {
        document.getElementById('generateBtn').disabled = true;
        document.getElementById('previewCard').innerHTML = `
            <div class="text-center text-gray-400 py-12">
                <i class="fas fa-clipboard text-4xl mb-3"></i>
                <p>Your flashcard preview will appear here</p>
            </div>
        `;
    }
}

// Clear all cards
function clearAllCards() {
    if (confirm('Are you sure you want to clear all cards?')) {
        cards = [];
        updateCardsList();
        document.getElementById('generateBtn').disabled = true;
    }
}

// Generate deck
async function generateDeck() {
    const btn = document.getElementById('generateBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Generating...';
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(cards)
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('downloadLink').href = data.download_url;
            document.getElementById('successModal').classList.remove('hidden');
            
            // Clear cards after successful generation
            cards = [];
            updateCardsList();
        } else {
            alert('Error generating deck. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating deck. Please try again.');
    } finally {
        btn.disabled = cards.length === 0;
        btn.innerHTML = '<i class="fas fa-download mr-2"></i>Generate Anki Deck';
    }
}

// Close modal
function closeModal() {
    document.getElementById('successModal').classList.add('hidden');
}

// Theme toggle
function toggleTheme() {
    document.body.classList.toggle('dark');
    localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
}

// Load theme on startup
document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark');
    }
});

// Escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}