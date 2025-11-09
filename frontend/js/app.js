// App State
let allRecipes = [];
let filteredRecipes = [];
let currentFilter = 'all';

// DOM Elements
const recipeList = document.getElementById('recipeList');
const loadingState = document.getElementById('loadingState');
const errorState = document.getElementById('errorState');
const emptyState = document.getElementById('emptyState');
const searchInput = document.getElementById('searchInput');
const filterButtons = document.querySelectorAll('.filter-btn');
const recipeModal = document.getElementById('recipeModal');
const recipeDetail = document.getElementById('recipeDetail');
const addRecipeModal = document.getElementById('addRecipeModal');
const addRecipeBtn = document.getElementById('addRecipeBtn');
const recipeForm = document.getElementById('recipeForm');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    loadRecipes();
    setupEventListeners();
    // Initialize form with empty fields (will be populated when form opens)
    if (document.getElementById('ingredientsContainer')) {
        addIngredientField();
        addInstructionField();
    }
});

// Event Listeners
function setupEventListeners() {
    // Search
    searchInput.addEventListener('input', debounce(handleSearch, 300));
    
    // Filter buttons
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            applyFilters();
        });
    });
    
    // Modal close
    document.getElementById('closeModal').addEventListener('click', () => {
        closeRecipeModal();
    });
    
    document.getElementById('closeAddModal').addEventListener('click', () => {
        addRecipeModal.style.display = 'none';
    });
    
    document.getElementById('cancelAdd').addEventListener('click', () => {
        addRecipeModal.style.display = 'none';
    });
    
    // Close modal on outside click
    recipeModal.addEventListener('click', (e) => {
        if (e.target === recipeModal) {
            closeRecipeModal();
        }
    });
    
    addRecipeModal.addEventListener('click', (e) => {
        if (e.target === addRecipeModal) {
            addRecipeModal.style.display = 'none';
        }
    });
    
    // Add recipe button
    addRecipeBtn.addEventListener('click', () => {
        document.querySelector('#addRecipeModal h2').textContent = 'Nouvelle Recette';
        recipeForm.dataset.mode = 'create';
        recipeForm.reset();
        // Clear dynamic fields
        document.getElementById('ingredientsContainer').innerHTML = '';
        document.getElementById('instructionsContainer').innerHTML = '';
        addIngredientField();
        addInstructionField();
        addRecipeModal.style.display = 'flex';
    });
    
    // Form submit
    recipeForm.addEventListener('submit', handleFormSubmit);
}

// Load Recipes
async function loadRecipes() {
    try {
        showLoading();
        const data = await api.getRecipes({ limit: 200 });
        allRecipes = data.recipes || [];
        filteredRecipes = allRecipes;
        hideLoading();
        renderRecipes();
    } catch (error) {
        console.error('Failed to load recipes:', error);
        showError();
    }
}

// Render Recipes
function renderRecipes() {
    if (filteredRecipes.length === 0) {
        recipeList.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    recipeList.innerHTML = filteredRecipes.map(recipe => `
        <div class="recipe-card" onclick="showRecipeDetail('${recipe.recipe_id}')">
            <h3>${escapeHtml(recipe.name)}</h3>
            ${recipe.description ? `<p class="description">${escapeHtml(recipe.description)}</p>` : ''}
            <div class="recipe-meta">
                ${recipe.prep_time > 0 ? `<span>⏱️ ${recipe.prep_time} min</span>` : ''}
                ${recipe.cook_time > 0 ? `<span>🔥 ${recipe.cook_time} min</span>` : ''}
                ${recipe.servings > 0 ? `<span>👥 ${recipe.servings}</span>` : ''}
            </div>
            ${recipe.tags && recipe.tags.length > 0 ? `
                <div class="recipe-tags">
                    ${recipe.tags.slice(0, 3).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// Close Recipe Modal and ensure recipes are visible
function closeRecipeModal() {
    recipeModal.style.display = 'none';
    // Ensure loading and error states are hidden
    hideLoading();
    errorState.style.display = 'none';
    // Ensure recipes are still rendered with current filters
    if (filteredRecipes.length === 0 && allRecipes.length > 0) {
        // If no filtered recipes but we have recipes, reapply filters
        applyFilters();
    } else if (filteredRecipes.length > 0) {
        // Just re-render to ensure visibility
        renderRecipes();
    } else if (allRecipes.length === 0) {
        // No recipes at all, show empty state
        recipeList.innerHTML = '';
        emptyState.style.display = 'block';
    }
}

// Show Recipe Detail
let currentRecipeId = null;
async function showRecipeDetail(recipeId) {
    try {
        showLoading();
        const [recipe, nutrition] = await Promise.all([
            api.getRecipe(recipeId),
            api.getRecipeNutrition(recipeId).catch(() => null) // Nutrition is optional
        ]);
        hideLoading();
        currentRecipeId = recipeId;
        
        // Build nutrition HTML if available
        let nutritionHtml = '';
        if (nutrition && nutrition.calories > 0) {
            nutritionHtml = `
                <section class="nutrition-section">
                    <h3>📊 Valeurs Nutritionnelles</h3>
                    <div class="nutrition-box">
                        <div class="nutrition-total">
                            <h4>Total (${nutrition.servings} portion${nutrition.servings > 1 ? 's' : ''})</h4>
                            <div class="nutrition-grid">
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Calories</span>
                                    <span class="nutrition-value">${nutrition.calories} kcal</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Protéines</span>
                                    <span class="nutrition-value">${nutrition.proteins} g</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Lipides</span>
                                    <span class="nutrition-value">${nutrition.lipides} g</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Glucides</span>
                                    <span class="nutrition-value">${nutrition.glucides} g</span>
                                </div>
                            </div>
                        </div>
                        ${nutrition.per_serving ? `
                        <div class="nutrition-per-serving">
                            <h4>Par portion</h4>
                            <div class="nutrition-grid">
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Calories</span>
                                    <span class="nutrition-value">${nutrition.per_serving.calories} kcal</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Protéines</span>
                                    <span class="nutrition-value">${nutrition.per_serving.proteins} g</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Lipides</span>
                                    <span class="nutrition-value">${nutrition.per_serving.lipides} g</span>
                                </div>
                                <div class="nutrition-item">
                                    <span class="nutrition-label">Glucides</span>
                                    <span class="nutrition-value">${nutrition.per_serving.glucides} g</span>
                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                </section>
            `;
        }
        
        recipeDetail.innerHTML = `
            <div class="recipe-detail-header">
                <h2>${escapeHtml(recipe.name)}</h2>
                <div class="recipe-actions">
                    <button class="btn-icon-small" onclick="editRecipe('${recipe.recipe_id}')" aria-label="Modifier">
                        ✏️
                    </button>
                    <button class="btn-icon-small btn-danger" onclick="deleteRecipe('${recipe.recipe_id}')" aria-label="Supprimer">
                        🗑️
                    </button>
                </div>
            </div>
            ${recipe.description ? `<p class="recipe-description">${escapeHtml(recipe.description)}</p>` : ''}
            
            <div class="meta">
                ${recipe.prep_time > 0 ? `<div class="meta-item">⏱️ Préparation: ${recipe.prep_time} min</div>` : ''}
                ${recipe.cook_time > 0 ? `<div class="meta-item">🔥 Cuisson: ${recipe.cook_time} min</div>` : ''}
                ${recipe.servings > 0 ? `<div class="meta-item">👥 Portions: ${recipe.servings}</div>` : ''}
                ${recipe.cuisine_type ? `<div class="meta-item">🌍 ${escapeHtml(recipe.cuisine_type)}</div>` : ''}
            </div>
            
            ${nutritionHtml}
            
            ${recipe.ingredients && recipe.ingredients.length > 0 ? `
                <section>
                    <h3>Ingrédients</h3>
                    <ul class="ingredient-list">
                        ${recipe.ingredients.map(ing => `
                            <li>
                                <span class="ingredient-name">${escapeHtml(ing.name)}</span>
                                <span class="ingredient-quantity">
                                    ${ing.quantity > 0 ? ing.quantity : ''} ${ing.unit || ''} ${ing.notes ? `(${escapeHtml(ing.notes)})` : ''}
                                </span>
                            </li>
                        `).join('')}
                    </ul>
                </section>
            ` : '<section><p class="text-muted">Aucun ingrédient</p></section>'}
            
            ${recipe.instructions && recipe.instructions.length > 0 ? `
                <section>
                    <h3>Instructions</h3>
                    <ol class="instruction-list">
                        ${recipe.instructions.map(instr => `
                            <li>${escapeHtml(instr.instruction_text)}</li>
                        `).join('')}
                    </ol>
                </section>
            ` : '<section><p class="text-muted">Aucune instruction</p></section>'}
            
            ${recipe.tags && recipe.tags.length > 0 ? `
                <section>
                    <h3>Tags</h3>
                    <div class="recipe-tags">
                        ${recipe.tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                </section>
            ` : ''}
        `;
        
        recipeModal.style.display = 'flex';
    } catch (error) {
        hideLoading();
        alert('Erreur lors du chargement de la recette: ' + error.message);
    }
}

// Edit Recipe
async function editRecipe(recipeId) {
    try {
        const recipe = await api.getRecipe(recipeId);
        currentRecipeId = recipeId;
        
        // Populate form
        document.getElementById('recipeName').value = recipe.name;
        document.getElementById('recipeDescription').value = recipe.description || '';
        document.getElementById('prepTime').value = recipe.prep_time || 0;
        document.getElementById('cookTime').value = recipe.cook_time || 0;
        document.getElementById('servings').value = recipe.servings || 1;
        document.getElementById('cuisineType').value = recipe.cuisine_type || '';
        
        // Populate ingredients
        const ingredientsContainer = document.getElementById('ingredientsContainer');
        ingredientsContainer.innerHTML = '';
        if (recipe.ingredients && recipe.ingredients.length > 0) {
            recipe.ingredients.forEach(ing => {
                addIngredientField(ing.name, ing.quantity, ing.unit, ing.notes);
            });
        } else {
            addIngredientField();
        }
        
        // Populate instructions
        const instructionsContainer = document.getElementById('instructionsContainer');
        instructionsContainer.innerHTML = '';
        if (recipe.instructions && recipe.instructions.length > 0) {
            recipe.instructions.forEach(instr => {
                addInstructionField(instr.instruction_text);
            });
        } else {
            addInstructionField();
        }
        
        // Update form title and submit handler
        document.querySelector('#addRecipeModal h2').textContent = 'Modifier la Recette';
        recipeForm.dataset.mode = 'edit';
        recipeForm.dataset.recipeId = recipeId;
        
        // Close detail modal and open form modal
        closeRecipeModal();
        addRecipeModal.style.display = 'flex';
    } catch (error) {
        alert('Erreur lors du chargement de la recette: ' + error.message);
    }
}

// Delete Recipe
async function deleteRecipe(recipeId) {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette recette ?')) {
        return;
    }
    
    try {
        await api.deleteRecipe(recipeId);
        closeRecipeModal();
        loadRecipes(); // Reload list
    } catch (error) {
        alert('Erreur lors de la suppression: ' + error.message);
    }
}

// Handle Search
function handleSearch() {
    applyFilters();
}

// Apply Filters
function applyFilters() {
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    filteredRecipes = allRecipes.filter(recipe => {
        // Search filter
        const matchesSearch = !searchTerm || 
            recipe.name.toLowerCase().includes(searchTerm) ||
            (recipe.description && recipe.description.toLowerCase().includes(searchTerm));
        
        // Tag filter
        const matchesFilter = currentFilter === 'all' || 
            (recipe.tags && recipe.tags.some(tag => tag.toLowerCase() === currentFilter));
        
        return matchesSearch && matchesFilter;
    });
    
    renderRecipes();
}

// Handle Form Submit
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Collect ingredients
    const ingredients = [];
    document.querySelectorAll('.ingredient-row').forEach(row => {
        const nameInput = row.querySelector('.ingredient-name-input');
        const qtyInput = row.querySelector('.ingredient-quantity-input');
        const unitInput = row.querySelector('.ingredient-unit-input');
        const notesInput = row.querySelector('.ingredient-notes-input');
        
        const name = nameInput ? nameInput.value.trim() : '';
        if (name) {
            // Get unit value - handle both select and input
            let unit = '';
            if (unitInput) {
                if (unitInput.tagName === 'SELECT') {
                    unit = unitInput.value || '';
                } else {
                    unit = unitInput.value.trim() || '';
                }
            }
            
            ingredients.push({
                name: name,
                quantity: qtyInput ? (parseFloat(qtyInput.value) || 0) : 0,
                unit: unit || "",
                notes: notesInput ? (notesInput.value.trim() || "") : ""
            });
        }
    });
    
    // Collect instructions
    const instructions = [];
    document.querySelectorAll('.instruction-row').forEach(row => {
        const text = row.querySelector('.instruction-text-input').value.trim();
        if (text) {
            instructions.push({
                instruction_text: text
            });
        }
    });
    
    const formData = {
        name: document.getElementById('recipeName').value,
        description: document.getElementById('recipeDescription').value || null,
        prep_time: parseInt(document.getElementById('prepTime').value) || 0,
        cook_time: parseInt(document.getElementById('cookTime').value) || 0,
        servings: parseInt(document.getElementById('servings').value) || 1,
        cuisine_type: document.getElementById('cuisineType').value || null,
        tags: [],
        utensils: [],
        ingredients: ingredients,
        instructions: instructions
    };
    
    try {
        let savedRecipe;
        if (recipeForm.dataset.mode === 'edit') {
            savedRecipe = await api.updateRecipe(recipeForm.dataset.recipeId, formData);
        } else {
            savedRecipe = await api.createRecipe(formData);
        }
        
        // Get nutrition info after saving
        try {
            const nutrition = await api.getRecipeNutrition(savedRecipe.recipe_id).catch(() => null);
            if (nutrition && nutrition.calories > 0) {
                const servings = savedRecipe.servings || 1;
                const perServing = nutrition.per_serving || {};
                alert(`✅ Recette enregistrée!\n\n📊 Valeurs nutritionnelles (total pour ${servings} portion${servings > 1 ? 's' : ''}):\n- Calories: ${nutrition.calories} kcal\n- Protéines: ${nutrition.proteins} g\n- Lipides: ${nutrition.lipides} g\n- Glucides: ${nutrition.glucides} g\n\nPar portion:\n- Calories: ${perServing.calories || 0} kcal\n- Protéines: ${perServing.proteins || 0} g\n- Lipides: ${perServing.lipides || 0} g\n- Glucides: ${perServing.glucides || 0} g`);
            } else {
                alert('✅ Recette enregistrée!\n\n⚠️ Aucune donnée nutritionnelle disponible. Vérifiez que les ingrédients correspondent exactement aux noms de la base de données.');
            }
        } catch (e) {
            alert('✅ Recette enregistrée!');
        }
        
        addRecipeModal.style.display = 'none';
        recipeForm.reset();
        recipeForm.dataset.mode = 'create';
        // Clear dynamic fields
        document.getElementById('ingredientsContainer').innerHTML = '';
        document.getElementById('instructionsContainer').innerHTML = '';
        addIngredientField();
        addInstructionField();
        loadRecipes(); // Reload recipes
    } catch (error) {
        // Better error handling - handle different error types
        let errorMessage = 'Une erreur est survenue';
        if (error instanceof Error) {
            errorMessage = error.message;
        } else if (typeof error === 'string') {
            errorMessage = error;
        } else if (error && error.detail) {
            errorMessage = error.detail;
        } else if (error && typeof error === 'object') {
            errorMessage = JSON.stringify(error);
        }
        console.error('Recipe save error:', error);
        alert('Erreur: ' + errorMessage);
    }
}

// Add Ingredient Field with Autocomplete
function addIngredientField(name = '', quantity = '', unit = '', notes = '') {
    const container = document.getElementById('ingredientsContainer');
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    const rowId = `ingredient-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    row.id = rowId;
    
    row.innerHTML = `
        <div class="form-row">
            <div class="form-group autocomplete-wrapper" style="flex: 2;">
                <input 
                    type="text" 
                    class="ingredient-name-input" 
                    placeholder="Rechercher un ingrédient..." 
                    value="${escapeHtml(name)}" 
                    autocomplete="off"
                    data-row-id="${rowId}"
                    required>
                <div class="autocomplete-dropdown" id="${rowId}-dropdown" style="display: none;"></div>
            </div>
            <div class="form-group" style="flex: 1;">
                <input type="number" class="ingredient-quantity-input" placeholder="Quantité" step="0.1" value="${quantity}">
            </div>
            <div class="form-group" style="flex: 1;">
                <select class="ingredient-unit-input">
                    <option value="g" ${unit === 'g' ? 'selected' : ''}>g</option>
                    <option value="kg" ${unit === 'kg' ? 'selected' : ''}>kg</option>
                    <option value="mg" ${unit === 'mg' ? 'selected' : ''}>mg</option>
                    <option value="ml" ${unit === 'ml' ? 'selected' : ''}>ml</option>
                    <option value="cl" ${unit === 'cl' ? 'selected' : ''}>cl</option>
                    <option value="l" ${unit === 'l' ? 'selected' : ''}>l</option>
                    <option value="" ${!unit ? 'selected' : ''}>-</option>
                </select>
            </div>
            <div class="form-group" style="flex: 1;">
                <input type="text" class="ingredient-notes-input" placeholder="Notes" value="${escapeHtml(notes)}">
            </div>
            <button type="button" class="btn-remove" onclick="this.closest('.ingredient-row').remove(); updateNutritionPreview();">×</button>
        </div>
    `;
    container.appendChild(row);
    
    // Setup autocomplete for this input
    setupIngredientAutocomplete(row.querySelector('.ingredient-name-input'));
    
    // Add event listeners for nutrition calculation
    const nameInput = row.querySelector('.ingredient-name-input');
    const qtyInput = row.querySelector('.ingredient-quantity-input');
    const unitInput = row.querySelector('.ingredient-unit-input');
    
    // Update nutrition preview when ingredient name changes (after autocomplete selection)
    nameInput.addEventListener('blur', () => {
        setTimeout(updateNutritionPreview, 100);
    });
    qtyInput.addEventListener('input', debounce(updateNutritionPreview, 300));
    unitInput.addEventListener('change', updateNutritionPreview);
}

// Setup autocomplete for ingredient input
function setupIngredientAutocomplete(input) {
    let searchTimeout;
    const dropdown = document.getElementById(input.dataset.rowId + '-dropdown');
    let selectedIndex = -1;
    
    input.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        
        clearTimeout(searchTimeout);
        
        if (query.length < 2) {
            dropdown.style.display = 'none';
            return;
        }
        
        searchTimeout = setTimeout(async () => {
            const results = await api.searchIngredients(query, 10);
            displayAutocompleteResults(dropdown, results, input);
        }, 300);
    });
    
    input.addEventListener('keydown', (e) => {
        const items = dropdown.querySelectorAll('.autocomplete-item');
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, -1);
            updateSelection(items, selectedIndex);
        } else if (e.key === 'Enter' && selectedIndex >= 0) {
            e.preventDefault();
            items[selectedIndex].click();
        } else if (e.key === 'Escape') {
            dropdown.style.display = 'none';
        }
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function displayAutocompleteResults(dropdown, results, input) {
    if (results.length === 0) {
        dropdown.style.display = 'none';
        return;
    }
    
    dropdown.innerHTML = results.map((ing, index) => `
        <div class="autocomplete-item" data-index="${index}" onclick="selectIngredient('${escapeHtml(ing.name)}', '${input.dataset.rowId}')">
            ${escapeHtml(ing.name)}
            ${ing.has_nutrition_data ? '<span class="nutrition-badge">📊</span>' : ''}
        </div>
    `).join('');
    
    dropdown.style.display = 'block';
}

function selectIngredient(name, rowId) {
    const row = document.getElementById(rowId);
    const input = row.querySelector('.ingredient-name-input');
    input.value = name;
    const dropdown = document.getElementById(rowId + '-dropdown');
    dropdown.style.display = 'none';
    
    // Trigger input event to ensure form validation
    input.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Trigger nutrition preview update
    setTimeout(updateNutritionPreview, 100);
}

function updateSelection(items, index) {
    items.forEach((item, i) => {
        item.classList.toggle('selected', i === index);
    });
}

// Update nutrition preview (calculated on server when saving)
async function updateNutritionPreview() {
    // For now, we'll show nutrition after saving
    // Could be enhanced with real-time calculation
    const nutritionPreview = document.getElementById('nutritionPreview');
    if (nutritionPreview) {
        nutritionPreview.innerHTML = '<p class="text-muted">Les valeurs nutritionnelles seront calculées lors de l\'enregistrement</p>';
    }
}

// Add Instruction Field
function addInstructionField(text = '') {
    const container = document.getElementById('instructionsContainer');
    const row = document.createElement('div');
    row.className = 'instruction-row';
    row.innerHTML = `
        <div class="form-group" style="display: flex; gap: 0.5rem;">
            <textarea class="instruction-text-input" placeholder="Étape de préparation" rows="2" required>${escapeHtml(text)}</textarea>
            <button type="button" class="btn-remove" onclick="this.closest('.instruction-row').remove()">×</button>
        </div>
    `;
    container.appendChild(row);
}

// Utility Functions
function showLoading() {
    loadingState.style.display = 'block';
    errorState.style.display = 'none';
    recipeList.innerHTML = '';
}

function hideLoading() {
    loadingState.style.display = 'none';
}

function showError() {
    loadingState.style.display = 'none';
    errorState.style.display = 'block';
    recipeList.innerHTML = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Make functions available globally
window.showRecipeDetail = showRecipeDetail;
window.loadRecipes = loadRecipes;
window.editRecipe = editRecipe;
window.deleteRecipe = deleteRecipe;
window.addIngredientField = addIngredientField;
window.addInstructionField = addInstructionField;
window.selectIngredient = selectIngredient;
window.updateNutritionPreview = updateNutritionPreview;

