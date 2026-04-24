// Shopping List Management
let shoppingListItems = [];
let selectedRecipeId = null;

// DOM Elements
const tabRecipes = document.getElementById('tabRecipes');
const tabShopping = document.getElementById('tabShopping');
const tabIngredients = document.getElementById('tabIngredients');
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
    if (tabIngredients) tabIngredients.addEventListener('click', () => switchTab('ingredients'));
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
    } else if (tabName === 'ingredients') {
        if (tabIngredients) tabIngredients.classList.add('active');
        const ingredientsTab = document.getElementById('ingredientsTab');
        if (ingredientsTab) ingredientsTab.classList.add('active');
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

        // Handle recipe selection via click (Event Delegation)
        recipeSearchDropdown.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (item) {
                const index = parseInt(item.dataset.index);
                if (recipeSearchDropdown._results && recipeSearchDropdown._results[index]) {
                    const recipe = recipeSearchDropdown._results[index];
                    selectRecipe(recipe.recipe_id, recipe.name);
                }
            }
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

        // Handle ingredient selection via click (Event Delegation)
        manualIngredientDropdown.addEventListener('click', (e) => {
            const item = e.target.closest('.autocomplete-item');
            if (item) {
                const index = parseInt(item.dataset.index);
                if (manualIngredientDropdown._results && manualIngredientDropdown._results[index]) {
                    const ing = manualIngredientDropdown._results[index];
                    selectIngredientForShopping(ing.name);
                }
            }
        });
    }

    // Add manual ingredient
    if (addManualIngredientBtn) {
        addManualIngredientBtn.addEventListener('click', async () => {
            const name = manualIngredientInput.value.trim();
            const quantity = manualIngredientQuantity.value.trim();

            if (!name) return;

            await addManualIngredient(name, quantity);

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
        clearShoppingListBtn.addEventListener('click', async () => {
            if (confirm('Êtes-vous sûr de vouloir effacer toute la liste de courses ?')) {
                try {
                    await api.clearShoppingList();
                    shoppingListItems = [];
                    renderShoppingList();
                } catch (error) {
                    console.error('Error clearing shopping list:', error);
                    alert('Erreur lors de l\'effacement de la liste: ' + error.message);
                }
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

    // Store results for click handler
    recipeSearchDropdown._results = recipes;

    recipeSearchDropdown.innerHTML = recipes.map((recipe, index) => `
        <div class="autocomplete-item" data-index="${index}">
            <span>${escapeHtml(recipe.name)}</span>
        </div>
    `).join('');
    recipeSearchDropdown.style.display = 'block';
}

// Select recipe from search
window.selectRecipe = function (recipeId, recipeName) {
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

    // Store results for click handler
    manualIngredientDropdown._results = ingredients;

    manualIngredientDropdown.innerHTML = ingredients.map((ing, index) => `
        <div class="autocomplete-item" data-index="${index}">
            <span>${escapeHtml(ing.name)}</span>
            ${ing.has_nutrition_data ? '<span class="nutrition-badge">📊</span>' : ''}
        </div>
    `).join('');
    manualIngredientDropdown.style.display = 'block';
}

// Select ingredient from search
window.selectIngredientForShopping = function (ingredientName) {
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
        const source = `Recette: ${recipe.name} (${servings} portion${servings > 1 ? 's' : ''})`;

        if (recipe.ingredients && recipe.ingredients.length > 0) {
            // Add all ingredients to shopping list via API
            const promises = recipe.ingredients.map(async (ingredient) => {
                const quantity = ingredient.quantity * multiplier;
                const unit = ingredient.unit || '';
                const quantityStr = quantity > 0 ? `${quantity}${unit ? ' ' + unit : ''}` : '';

                return api.createShoppingListItem({
                    name: ingredient.name,
                    quantity: quantityStr,
                    source: source,
                    is_checked: false
                });
            });

            await Promise.all(promises);
        }

        await loadShoppingList();
    } catch (error) {
        console.error('Error adding recipe to shopping list:', error);
        alert('Erreur lors de l\'ajout de la recette à la liste de courses: ' + error.message);
    }
}

// Add manual ingredient
async function addManualIngredient(name, quantity) {
    try {
        await api.createShoppingListItem({
            name: name,
            quantity: quantity || '',
            source: 'Ajouté manuellement',
            is_checked: false
        });
        await loadShoppingList();
    } catch (error) {
        console.error('Error adding manual ingredient:', error);
        alert('Erreur lors de l\'ajout de l\'ingrédient: ' + error.message);
    }
}

// Categorize ingredient by name
function categorizeIngredient(ingredientName) {
    const name = ingredientName.toLowerCase();

    // Fruits
    if (name.match(/\b(pomme|banane|orange|citron|fraise|framboise|myrtille|cerise|raisin|pêche|abricot|mangue|ananas|kiwi|avocat|tomate|concombre|poivron|courgette|aubergine|citrouille|potiron)\b/)) {
        return 'Fruits & Légumes';
    }

    // Viandes
    if (name.match(/\b(poulet|boeuf|porc|agneau|veau|dinde|canard|saucisse|jambon|bacon|lard|viande)\b/)) {
        return 'Viandes & Poissons';
    }

    // Poissons
    if (name.match(/\b(saumon|thon|cabillaud|crevette|moule|huître|crabe|poisson|sardine|maquereau)\b/)) {
        return 'Viandes & Poissons';
    }

    // Produits laitiers
    if (name.match(/\b(lait|fromage|yaourt|crème|beurre|fromage blanc|mozzarella|parmesan|cheddar|emmental)\b/)) {
        return 'Produits Laitiers';
    }

    // Épicerie
    if (name.match(/\b(farine|sucre|sel|poivre|huile|vinaigre|riz|pâtes|semoule|couscous|quinoa|boulgour)\b/)) {
        return 'Épicerie';
    }

    // Épices & Herbes
    if (name.match(/\b(basilic|thym|romarin|persil|ciboulette|ail|oignon|échalote|gingembre|curcuma|cumin|paprika|curry)\b/)) {
        return 'Épices & Herbes';
    }

    // Boissons
    if (name.match(/\b(vin|bière|jus|eau|soda|thé|café|champagne)\b/)) {
        return 'Boissons';
    }

    // Sucreries
    if (name.match(/\b(chocolat|bonbon|gâteau|biscuit|confiture|miel|sirop)\b/)) {
        return 'Sucreries';
    }

    // Autres
    return 'Autres';
}

// Render shopping list grouped by categories
function renderShoppingList() {
    if (shoppingListItems.length === 0) {
        shoppingList.innerHTML = '';
        shoppingEmptyState.style.display = 'block';
        if (clearShoppingListBtn) clearShoppingListBtn.style.display = 'none';
        return;
    }

    shoppingEmptyState.style.display = 'none';
    if (clearShoppingListBtn) clearShoppingListBtn.style.display = 'block';

    // Group items by category
    const itemsByCategory = {};
    shoppingListItems.forEach(item => {
        const category = categorizeIngredient(item.name);
        if (!itemsByCategory[category]) {
            itemsByCategory[category] = [];
        }
        itemsByCategory[category].push(item);
    });

    // Sort categories (checked items last within each category)
    const categoryOrder = [
        'Fruits & Légumes',
        'Viandes & Poissons',
        'Produits Laitiers',
        'Épicerie',
        'Épices & Herbes',
        'Boissons',
        'Sucreries',
        'Autres'
    ];

    // Render by category
    let html = '';
    categoryOrder.forEach(category => {
        if (itemsByCategory[category] && itemsByCategory[category].length > 0) {
            // Sort: unchecked items first
            const sortedItems = itemsByCategory[category].sort((a, b) => {
                if (a.is_checked === b.is_checked) return 0;
                return a.is_checked ? 1 : -1;
            });

            html += `
                <div class="shopping-category">
                    <h4 class="shopping-category-title">${escapeHtml(category)}</h4>
                    <div class="shopping-category-items">
                        ${sortedItems.map((item) => `
                            <div class="shopping-item ${item.is_checked ? 'checked' : ''}" data-item-id="${item.item_id}">
                                <input 
                                    type="checkbox" 
                                    class="shopping-item-checkbox" 
                                    ${item.is_checked ? 'checked' : ''}
                                    onchange="toggleShoppingItem('${item.item_id}')"
                                >
                                <div class="shopping-item-content">
                                    <span class="shopping-item-name">${escapeHtml(item.name)}</span>
                                    ${item.quantity ? `<span class="shopping-item-quantity">${escapeHtml(item.quantity)}</span>` : ''}
                                    <span class="shopping-item-source">${escapeHtml(item.source)}</span>
                                </div>
                                <div class="shopping-item-actions">
                                    <button class="shopping-item-delete" onclick="deleteShoppingItem('${item.item_id}')" aria-label="Supprimer">
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    });

    // Add any categories not in the predefined order
    Object.keys(itemsByCategory).forEach(category => {
        if (!categoryOrder.includes(category)) {
            const sortedItems = itemsByCategory[category].sort((a, b) => {
                if (a.is_checked === b.is_checked) return 0;
                return a.is_checked ? 1 : -1;
            });

            html += `
                <div class="shopping-category">
                    <h4 class="shopping-category-title">${escapeHtml(category)}</h4>
                    <div class="shopping-category-items">
                        ${sortedItems.map((item) => `
                            <div class="shopping-item ${item.is_checked ? 'checked' : ''}" data-item-id="${item.item_id}">
                                <input 
                                    type="checkbox" 
                                    class="shopping-item-checkbox" 
                                    ${item.is_checked ? 'checked' : ''}
                                    onchange="toggleShoppingItem('${item.item_id}')"
                                >
                                <div class="shopping-item-content">
                                    <span class="shopping-item-name">${escapeHtml(item.name)}</span>
                                    ${item.quantity ? `<span class="shopping-item-quantity">${escapeHtml(item.quantity)}</span>` : ''}
                                    <span class="shopping-item-source">${escapeHtml(item.source)}</span>
                                </div>
                                <div class="shopping-item-actions">
                                    <button class="shopping-item-delete" onclick="deleteShoppingItem('${item.item_id}')" aria-label="Supprimer">
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    });

    shoppingList.innerHTML = html;
}

// Toggle shopping item
window.toggleShoppingItem = async function (itemId) {
    try {
        const item = shoppingListItems.find(i => i.item_id === itemId);
        if (item) {
            const updated = await api.updateShoppingListItem(itemId, {
                is_checked: !item.is_checked
            });
            // Update local array
            const index = shoppingListItems.findIndex(i => i.item_id === itemId);
            if (index !== -1) {
                shoppingListItems[index] = updated;
            }
            renderShoppingList();
        }
    } catch (error) {
        console.error('Error toggling shopping item:', error);
        alert('Erreur lors de la mise à jour de l\'élément: ' + error.message);
    }
};

// Delete shopping item
window.deleteShoppingItem = async function (itemId) {
    try {
        await api.deleteShoppingListItem(itemId);
        // Remove from local array
        shoppingListItems = shoppingListItems.filter(item => item.item_id !== itemId);
        renderShoppingList();
    } catch (error) {
        console.error('Error deleting shopping item:', error);
        alert('Erreur lors de la suppression: ' + error.message);
    }
};

// Load shopping list from API
async function loadShoppingList() {
    try {
        shoppingListItems = await api.getShoppingList(true); // Include checked items
        renderShoppingList();
    } catch (error) {
        console.error('Error loading shopping list:', error);
        shoppingListItems = [];
        renderShoppingList();
        // Show error but don't block the UI
        if (shoppingListItems.length === 0) {
            shoppingEmptyState.innerHTML = `
                <p>🛒 Erreur lors du chargement de la liste</p>
                <p class="text-muted">Vérifiez votre connexion internet</p>
            `;
        }
    }
}

// Escape HTML helper
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

