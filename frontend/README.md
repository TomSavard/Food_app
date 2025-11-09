# Frontend - Food App

## 🚀 Quick Start

### Option 1: Serve via FastAPI (Recommended)

The FastAPI backend automatically serves the frontend. Just start the backend:

```bash
cd /Users/tom.savard/Desktop/Perso/Food_app
./start_local.sh
```

Then open: http://127.0.0.1:8000/

### Option 2: Simple HTTP Server (Development)

For development, you can use Python's built-in server:

```bash
cd frontend
python3 -m http.server 8080
```

Then open: http://127.0.0.1:8080/

**Note**: You'll need to update `API_BASE` in `js/api.js` to point to your backend.

## 📱 Features

- ✅ Recipe list with search and filters
- ✅ Recipe detail view
- ✅ Create new recipes
- ✅ Mobile-friendly responsive design
- ✅ PWA support (installable on mobile)
- ✅ Fast and lightweight

## 🎨 Design

- Mobile-first responsive design
- Modern card-based layout
- Smooth animations and transitions
- Accessible and user-friendly

## 🔧 Configuration

Update `js/api.js` to change the API endpoint:

```javascript
const API_BASE = 'http://127.0.0.1:8000/api'; // Local
// or
const API_BASE = 'https://your-render-url.onrender.com/api'; // Production
```

## 📦 Files

- `index.html` - Main HTML structure
- `css/styles.css` - All styles
- `js/api.js` - API communication
- `js/app.js` - Main application logic
- `manifest.json` - PWA manifest
- `sw.js` - Service worker for offline support

## 🚀 Next Steps

1. Test on mobile device
2. Add edit/delete functionality
3. Add week menu planning
4. Add shopping list generation

