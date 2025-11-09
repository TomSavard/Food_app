// API Configuration
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/api'
    : 'https://food-app-907w.onrender.com/api'; // Update with your Render URL

// API Functions
const api = {
    /**
     * Get all recipes with optional filters
     */
    async getRecipes(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.search) queryParams.append('search', params.search);
        if (params.cuisine) queryParams.append('cuisine', params.cuisine);
        if (params.ingredient) queryParams.append('ingredient', params.ingredient);
        if (params.tag) queryParams.append('tag', params.tag);
        if (params.skip) queryParams.append('skip', params.skip);
        if (params.limit) queryParams.append('limit', params.limit);
        
        const url = `${API_BASE}/recipes${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching recipes:', error);
            throw error;
        }
    },

    /**
     * Get a single recipe by ID
     */
    async getRecipe(recipeId) {
        try {
            const response = await fetch(`${API_BASE}/recipes/${recipeId}`);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Recipe not found');
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching recipe:', error);
            throw error;
        }
    },

    /**
     * Create a new recipe
     */
    async createRecipe(recipeData) {
        try {
            const response = await fetch(`${API_BASE}/recipes`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(recipeData),
            });
            
            if (!response.ok) {
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    // FastAPI returns errors in 'detail' field, can be string or array
                    if (errorData.detail) {
                        if (typeof errorData.detail === 'string') {
                            errorMessage = errorData.detail;
                        } else if (Array.isArray(errorData.detail)) {
                            // Validation errors - format them nicely
                            errorMessage = errorData.detail.map(err => {
                                if (typeof err === 'object' && err.msg) {
                                    return `${err.loc ? err.loc.join('.') : 'Erreur'}: ${err.msg}`;
                                }
                                return String(err);
                            }).join('\n');
                        } else {
                            errorMessage = JSON.stringify(errorData.detail);
                        }
                    }
                } catch (e) {
                    // If JSON parsing fails, use status text
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error creating recipe:', error);
            throw error;
        }
    },

    /**
     * Update an existing recipe
     */
    async updateRecipe(recipeId, recipeData) {
        try {
            const response = await fetch(`${API_BASE}/recipes/${recipeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(recipeData),
            });
            
            if (!response.ok) {
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    // FastAPI returns errors in 'detail' field, can be string or array
                    if (errorData.detail) {
                        if (typeof errorData.detail === 'string') {
                            errorMessage = errorData.detail;
                        } else if (Array.isArray(errorData.detail)) {
                            // Validation errors - format them nicely
                            errorMessage = errorData.detail.map(err => {
                                if (typeof err === 'object' && err.msg) {
                                    return `${err.loc ? err.loc.join('.') : 'Erreur'}: ${err.msg}`;
                                }
                                return String(err);
                            }).join('\n');
                        } else {
                            errorMessage = JSON.stringify(errorData.detail);
                        }
                    }
                } catch (e) {
                    // If JSON parsing fails, use status text
                    errorMessage = response.statusText || errorMessage;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error updating recipe:', error);
            throw error;
        }
    },

    /**
     * Delete a recipe
     */
    async deleteRecipe(recipeId) {
        try {
            const response = await fetch(`${API_BASE}/recipes/${recipeId}`, {
                method: 'DELETE',
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return true;
        } catch (error) {
            console.error('Error deleting recipe:', error);
            throw error;
        }
    },

    /**
     * Get nutrition information for a recipe
     */
    async getRecipeNutrition(recipeId) {
        try {
            const response = await fetch(`${API_BASE}/recipes/${recipeId}/nutrition`);
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Recipe not found');
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching recipe nutrition:', error);
            throw error;
        }
    },

    /**
     * Search ingredients by name (autocomplete)
     */
    async searchIngredients(query, limit = 20) {
        try {
            const response = await fetch(`${API_BASE}/ingredients/search?q=${encodeURIComponent(query)}&limit=${limit}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error searching ingredients:', error);
            return [];
        }
    },

           /**
            * Calculate nutrition for ingredients (client-side preview)
            * This is a preview - actual calculation happens on server
            */
           async calculateNutritionPreview(ingredients) {
               // For now, we'll calculate on the server when saving
               // This could be enhanced with client-side calculation
               return null;
           },

           /**
            * Shopping List API
            */
           async getShoppingList(includeChecked = true) {
               try {
                   const response = await fetch(`${API_BASE}/shopping-list?include_checked=${includeChecked}`);
                   if (!response.ok) {
                       throw new Error(`HTTP error! status: ${response.status}`);
                   }
                   const data = await response.json();
                   return data.items || [];
               } catch (error) {
                   console.error('Error fetching shopping list:', error);
                   throw error;
               }
           },

           async createShoppingListItem(item) {
               try {
                   const response = await fetch(`${API_BASE}/shopping-list`, {
                       method: 'POST',
                       headers: {
                           'Content-Type': 'application/json',
                       },
                       body: JSON.stringify(item)
                   });
                   if (!response.ok) {
                       const errorData = await response.json().catch(() => ({}));
                       throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                   }
                   return await response.json();
               } catch (error) {
                   console.error('Error creating shopping list item:', error);
                   throw error;
               }
           },

           async updateShoppingListItem(itemId, updates) {
               try {
                   const response = await fetch(`${API_BASE}/shopping-list/${itemId}`, {
                       method: 'PUT',
                       headers: {
                           'Content-Type': 'application/json',
                       },
                       body: JSON.stringify(updates)
                   });
                   if (!response.ok) {
                       const errorData = await response.json().catch(() => ({}));
                       throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                   }
                   return await response.json();
               } catch (error) {
                   console.error('Error updating shopping list item:', error);
                   throw error;
               }
           },

           async deleteShoppingListItem(itemId) {
               try {
                   const response = await fetch(`${API_BASE}/shopping-list/${itemId}`, {
                       method: 'DELETE'
                   });
                   if (!response.ok) {
                       const errorData = await response.json().catch(() => ({}));
                       throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                   }
                   return true;
               } catch (error) {
                   console.error('Error deleting shopping list item:', error);
                   throw error;
               }
           },

           async clearShoppingList() {
               try {
                   const response = await fetch(`${API_BASE}/shopping-list`, {
                       method: 'DELETE'
                   });
                   if (!response.ok) {
                       const errorData = await response.json().catch(() => ({}));
                       throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
                   }
                   return true;
               } catch (error) {
                   console.error('Error clearing shopping list:', error);
                   throw error;
               }
           }
       };

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
}

