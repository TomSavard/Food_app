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
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
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
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
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
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
}

