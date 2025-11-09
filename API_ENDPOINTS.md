# Recipe API Endpoints

## 📋 Available Endpoints

### 1. List Recipes
**GET** `/api/recipes`

**Query Parameters:**
- `skip` (int, default: 0) - Number of recipes to skip
- `limit` (int, default: 100) - Maximum number of recipes to return
- `search` (string, optional) - Search in recipe name or description
- `cuisine` (string, optional) - Filter by cuisine type

**Response:**
```json
{
  "recipes": [
    {
      "recipe_id": "uuid",
      "name": "Recipe Name",
      "description": "Description",
      "prep_time": 30,
      "cook_time": 45,
      "servings": 4,
      "cuisine_type": "Italian",
      "tags": ["dinner", "pasta"],
      "utensils": ["pot", "pan"],
      "ingredients": [
        {
          "ingredient_id": "uuid",
          "name": "Tomato",
          "quantity": 500,
          "unit": "g",
          "notes": ""
        }
      ],
      "instructions": [
        {
          "instruction_id": "uuid",
          "step_number": 1,
          "instruction_text": "First step"
        }
      ],
      "created_at": "2025-11-09T18:00:00",
      "updated_at": "2025-11-09T18:00:00"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl https://food-app-907w.onrender.com/api/recipes
curl https://food-app-907w.onrender.com/api/recipes?search=pasta&limit=10
```

---

### 2. Get Single Recipe
**GET** `/api/recipes/{recipe_id}`

**Response:**
```json
{
  "recipe_id": "uuid",
  "name": "Recipe Name",
  "description": "Description",
  "prep_time": 30,
  "cook_time": 45,
  "servings": 4,
  "cuisine_type": "Italian",
  "tags": ["dinner", "pasta"],
  "utensils": ["pot", "pan"],
  "ingredients": [...],
  "instructions": [...],
  "created_at": "2025-11-09T18:00:00",
  "updated_at": "2025-11-09T18:00:00"
}
```

**Example:**
```bash
curl https://food-app-907w.onrender.com/api/recipes/{recipe_id}
```

---

### 3. Create Recipe
**POST** `/api/recipes`

**Request Body:**
```json
{
  "name": "Spaghetti Carbonara",
  "description": "Classic Italian pasta dish",
  "prep_time": 15,
  "cook_time": 20,
  "servings": 4,
  "cuisine_type": "Italian",
  "tags": ["dinner", "pasta", "quick"],
  "utensils": ["pot", "pan", "whisk"],
  "ingredients": [
    {
      "name": "Spaghetti",
      "quantity": 400,
      "unit": "g",
      "notes": ""
    },
    {
      "name": "Eggs",
      "quantity": 4,
      "unit": "",
      "notes": "Large eggs"
    }
  ],
  "instructions": [
    {
      "instruction_text": "Boil water in a large pot"
    },
    {
      "instruction_text": "Cook spaghetti according to package directions"
    },
    {
      "instruction_text": "Mix eggs with cheese while pasta cooks"
    }
  ]
}
```

**Response:** Created recipe (same format as GET)

**Example:**
```bash
curl -X POST https://food-app-907w.onrender.com/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spaghetti Carbonara",
    "prep_time": 15,
    "cook_time": 20,
    "servings": 4,
    "ingredients": [
      {"name": "Spaghetti", "quantity": 400, "unit": "g"}
    ],
    "instructions": [
      {"instruction_text": "Boil water"}
    ]
  }'
```

---

### 4. Update Recipe
**PUT** `/api/recipes/{recipe_id}`

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "prep_time": 20,
  "ingredients": [
    {"name": "New Ingredient", "quantity": 100, "unit": "g"}
  ]
}
```

**Response:** Updated recipe

**Example:**
```bash
curl -X PUT https://food-app-907w.onrender.com/api/recipes/{recipe_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

---

### 5. Delete Recipe
**DELETE** `/api/recipes/{recipe_id}`

**Response:** 204 No Content

**Example:**
```bash
curl -X DELETE https://food-app-907w.onrender.com/api/recipes/{recipe_id}
```

---

## 🧪 Testing

### Using Browser
Visit: https://food-app-907w.onrender.com/docs

Interactive API documentation (Swagger UI) where you can test all endpoints!

### Using curl

**List recipes:**
```bash
curl https://food-app-907w.onrender.com/api/recipes
```

**Create recipe:**
```bash
curl -X POST https://food-app-907w.onrender.com/api/recipes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Recipe",
    "prep_time": 10,
    "cook_time": 20,
    "servings": 2,
    "ingredients": [
      {"name": "Test Ingredient", "quantity": 100, "unit": "g"}
    ],
    "instructions": [
      {"instruction_text": "Test instruction"}
    ]
  }'
```

---

## 📝 Notes

- All endpoints return JSON
- Recipe IDs are UUIDs
- Ingredients and instructions are automatically linked to recipes
- Deleting a recipe also deletes its ingredients and instructions (cascade)
- Search is case-insensitive
- Pagination uses `skip` and `limit`

