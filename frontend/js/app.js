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
        recipeModal.style.display = 'none';
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
            recipeModal.style.display = 'none';
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

// Show Recipe Detail
let currentRecipeId = null;
async function showRecipeDetail(recipeId) {
    try {
        showLoading();
        const recipe = await api.getRecipe(recipeId);
        hideLoading();
        currentRecipeId = recipeId;
        
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
        recipeModal.style.display = 'none';
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
        recipeModal.style.display = 'none';
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
        const name = row.querySelector('.ingredient-name-input').value.trim();
        if (name) {
            ingredients.push({
                name: name,
                quantity: parseFloat(row.querySelector('.ingredient-quantity-input').value) || 0,
                unit: row.querySelector('.ingredient-unit-input').value.trim() || null,
                notes: row.querySelector('.ingredient-notes-input').value.trim() || null
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
        if (recipeForm.dataset.mode === 'edit') {
            await api.updateRecipe(recipeForm.dataset.recipeId, formData);
        } else {
            await api.createRecipe(formData);
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
        alert('Erreur: ' + error.message);
    }
}

// Add Ingredient Field
function addIngredientField(name = '', quantity = '', unit = '', notes = '') {
    const container = document.getElementById('ingredientsContainer');
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = `
        <div class="form-row">
            <div class="form-group" style="flex: 2;">
                <input type="text" class="ingredient-name-input" placeholder="Nom de l'ingrédient" value="${escapeHtml(name)}" required>
            </div>
            <div class="form-group" style="flex: 1;">
                <input type="number" class="ingredient-quantity-input" placeholder="Quantité" step="0.1" value="${quantity}">
            </div>
            <div class="form-group" style="flex: 1;">
                <input type="text" class="ingredient-unit-input" placeholder="Unité (g, ml...)" value="${escapeHtml(unit)}">
            </div>
            <div class="form-group" style="flex: 1;">
                <input type="text" class="ingredient-notes-input" placeholder="Notes" value="${escapeHtml(notes)}">
            </div>
            <button type="button" class="btn-remove" onclick="this.closest('.ingredient-row').remove()">×</button>
        </div>
    `;
    container.appendChild(row);
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

