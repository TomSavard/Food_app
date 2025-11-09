// Shopping List Management
let shoppingListItems = [];
let selectedRecipeId = null;

// DOM Elements
const tabRecipes = document.getElementById('tabRecipes');
const tabShopping = document.getElementById('tabShopping');
const recipesTab = document.getElementById('recipesTab');
const shoppingTab = document.getElementById('shoppingTab');
const recipeSearchInput = document.getElementById('recipeSearchInput');
const recipeSearchDropdown = document.getElementById('recipeSearchDropdown');
const recipeServings = document.getElementById('recipeServings');
const addRecipeToShoppingBtn = document.getElementById('addRecipeToShoppingBtn');
const manualIngredientInput = document.getElementById('manualIngredientInput');
const manualIngredientDropdown = document.getElementById('manualIngredientDropdown');
const manualIngredientQuantity = document.getElementById('manualIngredientQuantity');
const addManualIngredientBtn = document.getElementById('addManualIngredientBtn');
const shoppingList = document.getElementById('shoppingList');
const shoppingEmptyState = document.getElementById('shoppingEmptyState');
const clearShoppingListBtn = document.getElementById('clearShoppingListBtn');

// Initialize Shopping List
document.addEventListener('DOMContentLoaded', () => {
    if (tabRecipes && tabShopping) {
        setupTabNavigation();
    }
    if (shoppingTab) {
        setupShoppingList();
        loadShoppingList();
    }
});

// Tab Navigation
function setupTabNavigation() {
    tabRecipes.addEventListener('click', () => switchTab('recipes'));
    tabShopping.addEventListener('click', () => switchTab('shopping'));
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    if (tabName === 'recipes') {
        tabRecipes.classList.add('active');
        recipesTab.classList.add('active');
    } else if (tabName === 'shopping') {
        tabShopping.classList.add('active');
        shoppingTab.classList.add('active');
    }
}

// Shopping List Setup
function setupShoppingList() {
    // Recipe search autocomplete
    if (recipeSearchInput) {
        let recipeSearchTimeout;
        recipeSearchInput.addEventListener('input', (e) => {
            clearTimeout(recipeSearchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                recipeSearchDropdown.style.display = 'none';
                selectedRecipeId = null;
                addRecipeToShoppingBtn.disabled = true;
                return;
            }

            recipeSearchTimeout = setTimeout(async () => {
                try {
                    const recipes = await api.getRecipes({ search: query, limit: 10 });
                    displayRecipeSearchResults(recipes.recipes || []);
                } catch (error) {
                    console.error('Error searching recipes:', error);
                }
            }, 300);
        });

        recipeSearchInput.addEventListener('blur', () => {
            setTimeout(() => {
                recipeSearchDropdown.style.display = 'none';
            }, 200);
        });
    }

    // Add recipe to shopping list
    if (addRecipeToShoppingBtn) {
        addRecipeToShoppingBtn.addEventListener('click', async () => {
            if (!selectedRecipeId) return;
            
            const servings = parseInt(recipeServings.value) || 1;
            await addRecipeToShoppingList(selectedRecipeId, servings);
            
            // Reset form
            recipeSearchInput.value = '';
            recipeServings.value = '1';
            selectedRecipeId = null;
            addRecipeToShoppingBtn.disabled = true;
            recipeSearchDropdown.style.display = 'none';
        });
    }

    // Manual ingredient autocomplete
    if (manualIngredientInput) {
        let ingredientSearchTimeout;
        manualIngredientInput.addEventListener('input', (e) => {
            clearTimeout(ingredientSearchTimeout);
            const query = e.target.value.trim();
            
            if (query.length < 2) {
                manualIngredientDropdown.style.display = 'none';
                return;
            }

            ingredientSearchTimeout = setTimeout(async () => {
                try {
                    const ingredients = await api.searchIngredients(query, 10);
                    displayIngredientSearchResults(ingredients);
                } catch (error) {
                    console.error('Error searching ingredients:', error);
                }
            }, 300);
        });

        manualIngredientInput.addEventListener('blur', () => {
            setTimeout(() => {
                manualIngredientDropdown.style.display = 'none';
            }, 200);
        });
    }

    // Add manual ingredient
    if (addManualIngredientBtn) {
        addManualIngredientBtn.addEventListener('click', () => {
            const name = manualIngredientInput.value.trim();
            const quantity = manualIngredientQuantity.value.trim();
            
            if (!name) return;
            
            addManualIngredient(name, quantity);
            
            // Reset form
            manualIngredientInput.value = '';
            manualIngredientQuantity.value = '';
            manualIngredientDropdown.style.display = 'none';
        });
    }

    // Enter key handlers
    if (manualIngredientInput) {
        manualIngredientInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addManualIngredientBtn.click();
            }
        });
    }

    if (manualIngredientQuantity) {
        manualIngredientQuantity.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addManualIngredientBtn.click();
            }
        });
    }

    // Clear shopping list
    if (clearShoppingListBtn) {
        clearShoppingListBtn.addEventListener('click', () => {
            if (confirm('Êtes-vous sûr de vouloir effacer toute la liste de courses ?')) {
                shoppingListItems = [];
                saveShoppingList();
                renderShoppingList();
            }
        });
    }
}

// Display recipe search results
function displayRecipeSearchResults(recipes) {
    if (recipes.length === 0) {
        recipeSearchDropdown.style.display = 'none';
        return;
    }

    recipeSearchDropdown.innerHTML = recipes.map(recipe => `
        <div class="autocomplete-item" onclick="selectRecipe('${recipe.recipe_id}', '${escapeHtml(recipe.name)}')">
            <span>${escapeHtml(recipe.name)}</span>
        </div>
    `).join('');
    recipeSearchDropdown.style.display = 'block';
}

// Select recipe from search
window.selectRecipe = function(recipeId, recipeName) {
    selectedRecipeId = recipeId;
    recipeSearchInput.value = recipeName;
    recipeSearchDropdown.style.display = 'none';
    addRecipeToShoppingBtn.disabled = false;
};

// Display ingredient search results
function displayIngredientSearchResults(ingredients) {
    if (ingredients.length === 0) {
        manualIngredientDropdown.style.display = 'none';
        return;
    }

    manualIngredientDropdown.innerHTML = ingredients.map(ing => `
        <div class="autocomplete-item" onclick="selectIngredientForShopping('${escapeHtml(ing.name)}')">
            <span>${escapeHtml(ing.name)}</span>
            ${ing.has_nutrition_data ? '<span class="nutrition-badge">📊</span>' : ''}
        </div>
    `).join('');
    manualIngredientDropdown.style.display = 'block';
}

// Select ingredient from search
window.selectIngredientForShopping = function(ingredientName) {
    manualIngredientInput.value = ingredientName;
    manualIngredientDropdown.style.display = 'none';
    manualIngredientQuantity.focus();
};

// Add recipe to shopping list
async function addRecipeToShoppingList(recipeId, servings) {
    try {
        const recipe = await api.getRecipe(recipeId);
        const baseServings = recipe.servings || 1;
        const multiplier = servings / baseServings;

        if (recipe.ingredients && recipe.ingredients.length > 0) {
            recipe.ingredients.forEach(ingredient => {
                const quantity = ingredient.quantity * multiplier;
                const unit = ingredient.unit || '';
                const quantityStr = quantity > 0 ? `${quantity}${unit ? ' ' + unit : ''}` : '';
                
                addShoppingListItem({
                    name: ingredient.name,
                    quantity: quantityStr,
                    source: `Recette: ${recipe.name} (${servings} portion${servings > 1 ? 's' : ''})`,
                    checked: false
                });
            });
        }

        saveShoppingList();
        renderShoppingList();
    } catch (error) {
        console.error('Error adding recipe to shopping list:', error);
        alert('Erreur lors de l\'ajout de la recette à la liste de courses');
    }
}

// Add manual ingredient
function addManualIngredient(name, quantity) {
    addShoppingListItem({
        name: name,
        quantity: quantity || '',
        source: 'Ajouté manuellement',
        checked: false
    });
    saveShoppingList();
    renderShoppingList();
}

// Add shopping list item (merge duplicates)
function addShoppingListItem(newItem) {
    // Check if item with same name exists
    const existingIndex = shoppingListItems.findIndex(
        item => item.name.toLowerCase() === newItem.name.toLowerCase() && !item.checked
    );

    if (existingIndex !== -1) {
        // Merge quantities if both have quantities
        const existing = shoppingListItems[existingIndex];
        if (existing.quantity && newItem.quantity) {
            // Try to parse and combine quantities
            // For now, just append
            existing.quantity = `${existing.quantity} + ${newItem.quantity}`;
        } else if (newItem.quantity) {
            existing.quantity = newItem.quantity;
        }
        // Update source if different
        if (existing.source !== newItem.source) {
            existing.source = `${existing.source}, ${newItem.source}`;
        }
    } else {
        shoppingListItems.push(newItem);
    }
}

// Render shopping list
function renderShoppingList() {
    if (shoppingListItems.length === 0) {
        shoppingList.innerHTML = '';
        shoppingEmptyState.style.display = 'block';
        if (clearShoppingListBtn) clearShoppingListBtn.style.display = 'none';
        return;
    }

    shoppingEmptyState.style.display = 'none';
    if (clearShoppingListBtn) clearShoppingListBtn.style.display = 'block';

    shoppingList.innerHTML = shoppingListItems.map((item, index) => `
        <div class="shopping-item ${item.checked ? 'checked' : ''}" data-index="${index}">
            <input 
                type="checkbox" 
                class="shopping-item-checkbox" 
                ${item.checked ? 'checked' : ''}
                onchange="toggleShoppingItem(${index})"
            >
            <div class="shopping-item-content">
                <span class="shopping-item-name">${escapeHtml(item.name)}</span>
                ${item.quantity ? `<span class="shopping-item-quantity">${escapeHtml(item.quantity)}</span>` : ''}
                <span class="shopping-item-source">${escapeHtml(item.source)}</span>
            </div>
            <div class="shopping-item-actions">
                <button class="shopping-item-delete" onclick="deleteShoppingItem(${index})" aria-label="Supprimer">
                    🗑️
                </button>
            </div>
        </div>
    `).join('');
}

// Toggle shopping item
window.toggleShoppingItem = function(index) {
    if (shoppingListItems[index]) {
        shoppingListItems[index].checked = !shoppingListItems[index].checked;
        saveShoppingList();
        renderShoppingList();
    }
};

// Delete shopping item
window.deleteShoppingItem = function(index) {
    shoppingListItems.splice(index, 1);
    saveShoppingList();
    renderShoppingList();
};

// Save shopping list to localStorage
function saveShoppingList() {
    try {
        localStorage.setItem('shoppingList', JSON.stringify(shoppingListItems));
    } catch (error) {
        console.error('Error saving shopping list:', error);
    }
}

// Load shopping list from localStorage
function loadShoppingList() {
    try {
        const saved = localStorage.getItem('shoppingList');
        if (saved) {
            shoppingListItems = JSON.parse(saved);
            renderShoppingList();
        }
    } catch (error) {
        console.error('Error loading shopping list:', error);
        shoppingListItems = [];
    }
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

