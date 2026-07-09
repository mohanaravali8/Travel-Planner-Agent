# ✈️ Atlas — AI-Powered Travel Planner Agent

> **Your AI travel companion** powered by **IBM Watsonx.ai** and **IBM Granite models**

Atlas is a full-stack web application that creates personalized travel itineraries, budget plans, hotel recommendations, destination guides, and packing lists — all powered by IBM's enterprise-grade Granite AI models through the IBM Cloud Lite tier.

---

## 🌟 Features

| Feature | Description |
|---|---|
| 🤖 **AI Chat Interface** | Natural language travel planning with IBM Granite 3 8B |
| 📅 **Itinerary Planner** | Day-by-day personalized travel schedules |
| 💰 **Budget Calculator** | Itemized cost estimates for any destination |
| 🏨 **Hotel Finder** | Recommendations across budget/mid-range/luxury tiers |
| 🌤️ **Weather Widget** | Live or mock weather for any city |
| 📋 **Packing Lists** | Climate and activity-based checklists |
| 🛂 **Visa Advisor** | Entry requirements and travel advisories |
| 🗺️ **Destination Explorer** | 12+ curated destinations with detailed guides |
| 🌍 **Travel Styles** | Family, Solo, Romantic, Adventure, Business, Budget, Luxury |
| 🌙 **Dark Mode** | Full dark/light theme toggle |
| 📱 **Responsive Design** | Mobile-first, Bootstrap 5 |

---

## 🚀 Quick Start

### 1. Clone / Navigate to Project

```bash
cd "Travel Planner Agent"
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example env file
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux
```

Then edit `.env` with your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
FLASK_SECRET_KEY=your_secret_key_here
```

### 5. Run the Application

```bash
python app.py
```

Open your browser at **http://localhost:5000** 🎉

> **Note:** The app runs in **fallback mode** without IBM credentials — you'll see sample itineraries. Configure your IBM keys for full AI functionality.

---

## 🔑 Getting IBM Cloud Credentials (Free)

### Step 1: Create IBM Cloud Account
1. Go to [cloud.ibm.com](https://cloud.ibm.com)
2. Sign up for a **free Lite account** (no credit card required)

### Step 2: Get API Key
1. Navigate to **Manage → IAM → API Keys**
2. Click **Create an IBM Cloud API key**
3. Copy the key to your `.env` as `IBM_API_KEY`

### Step 3: Create a Watsonx.ai Project
1. Go to [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
2. Click **New Project → Create an empty project**
3. Name it (e.g., "Travel Planner")
4. Copy the **Project ID** to `.env` as `IBM_PROJECT_ID`

### Step 4: Associate Watsonx.ai Service
1. In your project, go to **Manage → Services & Integrations**
2. Click **Associate service**
3. Select **Watson Machine Learning** (free Lite tier available)
4. Click **Associate**

> ✅ You're ready! The app will use `ibm/granite-3-8b-instruct` model automatically.

---

## 🔧 Customizing the AI Agent

All agent customization is done in [`app.py`](app.py) inside the `AGENT_CONFIG` dictionary:

```python
AGENT_CONFIG = {
    "PERSONA": {
        "name": "Atlas",              # Change the agent's name
        "tagline": "...",             # Change the tagline
        "personality": "...",         # Describe the agent's core personality
    },
    "TONE": {
        "style": "friendly",          # friendly | professional | casual | luxury
        "use_emojis": True,           # Enable/disable emojis in responses
        "language_complexity": "accessible",  # accessible | technical | simple
    },
    "SPECIALIZATION": {
        "family_travel": True,        # Enable/disable each travel type
        "adventure_travel": True,
        # ... more options
    },
    "SAFETY": {
        "include_visa_info": True,    # Always include visa info
        "warn_high_risk_zones": True, # Warn about unsafe destinations
        # ... more options
    },
    "RECOMMENDATION_STYLE": {
        "itinerary_format": "day_by_day",  # day_by_day | overview | flexible
        "budget_detail": "itemized",        # itemized | summary | range
        "hidden_gems": True,                # Include lesser-known spots
        # ... more options
    },
    "REGIONS": {
        "preferred_regions": [],      # e.g. ["Europe", "Asia"] or [] for all
        "currency_default": "USD",    # Default currency for estimates
        "unit_system": "metric",      # metric | imperial
    },
}
```

---

## 📁 Project Structure

```
Travel Planner Agent/
├── app.py                  # Main Flask application + AGENT_CONFIG
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .env                    # Your actual credentials (gitignored)
├── README.md               # This file
│
├── data/
│   ├── __init__.py
│   └── travel_data.py      # Destinations, travel types, mock data
│
├── templates/
│   ├── base.html           # Base layout (navbar, footer)
│   ├── index.html          # Homepage (hero, travel types, destinations)
│   ├── chat.html           # AI chat interface
│   ├── dashboard.html      # Destination explorer
│   └── planner.html        # Trip planner form
│
└── static/
    ├── css/
    │   └── style.css       # All styles (dark mode, animations, responsive)
    └── js/
        ├── main.js         # Theme toggle, shared utilities
        ├── chat.js         # Chat interface logic
        ├── dashboard.js    # Filters, weather widget, modals
        └── planner.js      # Form handling, itinerary generation
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Homepage |
| `GET` | `/chat` | AI Chat interface |
| `GET` | `/dashboard` | Destination explorer |
| `GET` | `/planner` | Trip planner form |
| `POST` | `/api/chat` | Send message to AI agent |
| `POST` | `/api/chat/clear` | Clear conversation history |
| `POST` | `/api/itinerary` | Generate full itinerary |
| `GET` | `/api/weather?city=Paris` | Get weather for a city |
| `GET` | `/api/destinations` | List/filter destinations |
| `POST` | `/api/budget` | Calculate trip budget |
| `POST` | `/api/recommendations` | Get AI destination recommendations |
| `POST` | `/api/packing-list` | Generate packing checklist |
| `POST` | `/api/visa-info` | Get visa requirements |
| `GET` | `/api/health` | App health check |

---

## 🌐 Deployment

### Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
docker build -t atlas-travel-planner .
docker run -p 5000:5000 --env-file .env atlas-travel-planner
```

### IBM Cloud Code Engine (Serverless)

```bash
# Install IBM Cloud CLI + Code Engine plugin
ibmcloud login --apikey $IBM_API_KEY
ibmcloud ce project create --name atlas-travel
ibmcloud ce app create --name atlas-travel-planner \
  --image icr.io/yournamespace/atlas:latest \
  --port 5000 \
  --env-from-secret atlas-secrets
```

---

## 🛠️ Adding New Destinations

Edit [`data/travel_data.py`](data/travel_data.py) and add a new entry to `FEATURED_DESTINATIONS`:

```python
{
    "id":           13,
    "name":         "Amsterdam",
    "country":      "Netherlands",
    "region":       "Europe",
    "emoji":        "🌷",
    "tagline":      "City of Canals & Culture",
    "description":  "Iconic canals, world-class museums, and vibrant culture.",
    "image_url":    "https://images.unsplash.com/photo-...",
    "best_season":  "April–May (Tulip Season), September",
    "budget_level": "mid-range",
    "types":        ["cultural", "romantic", "solo", "budget"],
    "rating":       4.7,
    "highlights":   ["Anne Frank House", "Rijksmuseum", "Canal Cruise"],
    "cuisine":      ["Stroopwafel", "Haring", "Dutch Pancakes"],
    "avg_costs": {
        "budget":    {"accommodation": 45, "food": 20, "activities": 15, "transport": 10, "misc": 8},
        "mid-range": {"accommodation": 140, "food": 55, "activities": 40, "transport": 20, "misc": 15},
        "luxury":    {"accommodation": 400, "food": 130, "activities": 90, "transport": 50, "misc": 40},
    },
    "visa":     "Schengen Visa",
    "currency": "EUR",
    "language": "Dutch",
    "timezone": "CET (UTC+1)",
    "safety":   "Very Safe",
    "lat":      52.3676,
    "lon":      4.9041,
},
```

---

## 🤝 IBM Technologies Used

| Technology | Purpose | Tier |
|---|---|---|
| **IBM Watsonx.ai** | AI model hosting and inference | Lite (Free) |
| **IBM Granite 3 8B Instruct** | Travel planning AI responses | Included in Lite |
| **IBM Cloud IAM** | API key authentication | Free |

---

## 📝 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ using IBM Watsonx.ai and IBM Granite models*
