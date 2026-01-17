// Ingredients browser UI
(function () {
    const searchInput = document.getElementById('ingredientBrowserSearch');
    const resultsEl = document.getElementById('ingredientBrowserResults');

    if (!searchInput || !resultsEl) return;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderNutritionLine(nut) {
        if (!nut) return '<div class="text-muted">Aucune donnée nutritionnelle</div>';
        const keys = {
            calories: 'Energie, Règlement UE N° 1169/2011 (kcal/100 g)'
        };
        const kcal = nut[keys.calories] ?? nut.calories ?? null;
        const proteins = nut['Protéines, N x facteur de Jones (g/100 g)'] ?? nut.proteins ?? null;
        const lipides = nut['Lipides (g/100 g)'] ?? nut.lipides ?? null;
        const glucides = nut['Glucides (g/100 g)'] ?? nut.glucides ?? null;

        return `
            <div class="nutri-line">
                <strong>Per 100g:</strong>
                <span class="nutri-table">kcal: ${kcal ?? '—'}</span>
                <span class="nutri-table">protein: ${proteins ?? '—'} g</span>
                <span class="nutri-table">carbs: ${glucides ?? '—'} g</span>
                <span class="nutri-table">fat: ${lipides ?? '—'} g</span>
            </div>
        `;
    }

    async function doSearch(q) {
        resultsEl.innerHTML = '<div class="text-muted">Recherche...</div>';
        try {
            const results = await api.searchIngredients(q, 100);
            if (!results || results.length === 0) {
                resultsEl.innerHTML = '<div class="text-muted">Aucun résultat</div>';
                return;
            }

            // For each result, fetch details to show nutrition
            const rows = await Promise.all(results.map(async (r) => {
                let nutHtml = '';
                try {
                    const detail = await api.getIngredient(r.id);
                    nutHtml = renderNutritionLine(detail ? detail.nutrition_data : null);
                } catch (e) {
                    nutHtml = '<div class="text-muted">Erreur lors du chargement</div>';
                }

                return `
                    <div class="ingredient-row" style="padding:8px;border-bottom:1px solid #eee;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div style="flex:1">
                                <div><strong>${escapeHtml(r.name)}</strong></div>
                                <div style="font-size:0.9rem;color:#666">${r.has_nutrition_data ? 'Données disponibles' : 'Pas de données'}</div>
                                ${nutHtml}
                            </div>
                            <div style="margin-left:12px;text-align:right;">
                                <button class="btn-small" data-id="${r.id}">Voir</button>
                            </div>
                        </div>
                    </div>
                `;
            }));

            resultsEl.innerHTML = rows.join('\n');
            // attach view buttons to open a simple alert/detail
            resultsEl.querySelectorAll('button[data-id]').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.dataset.id;
                    const detail = await api.getIngredient(id);
                    if (!detail) return alert('Détails indisponibles');
                    const nut = detail.nutrition_data || {};
                    alert(`${detail.name}\n\n` + JSON.stringify(nut, null, 2));
                });
            });
        } catch (e) {
            console.error('Ingredient search error', e);
            resultsEl.innerHTML = '<div class="text-muted">Erreur lors de la recherche</div>';
        }
    }

    let timeout;
    searchInput.addEventListener('input', (e) => {
        const q = e.target.value.trim();
        clearTimeout(timeout);
        if (q.length < 1) {
            resultsEl.innerHTML = '<div class="text-muted">Tapez au moins 1 caractère pour rechercher</div>';
            return;
        }
        timeout = setTimeout(() => doSearch(q), 300);
    });

    // initial hint
    resultsEl.innerHTML = '<div class="text-muted">Entrez un terme de recherche pour parcourir les ingrédients</div>';
})();
