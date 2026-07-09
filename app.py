"""
================================================================================
  TRAVEL PLANNER AGENT - IBM Watsonx.ai + IBM Granite
  Powered by IBM Cloud Lite Services
================================================================================

AGENT_INSTRUCTIONS
==================
You can customize the agent's behavior by modifying the AGENT_CONFIG dictionary
below. Each section controls a different aspect of the agent's personality,
specialization, and response style.

HOW TO CUSTOMIZE:
  1. TONE          → Change how the agent communicates (friendly, professional, etc.)
  2. SPECIALIZATION → Focus on specific travel types (adventure, luxury, budget, etc.)
  3. SAFETY        → Set safety and advisory guidelines
  4. STYLE         → Control recommendation detail and format
  5. REGIONS       → Set preferred or excluded regions
  6. PERSONA       → Give the agent a unique name and personality
================================================================================
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
import data.travel_data as travel_data
from auth import current_user, login_required, login_user, register_user, logout_user

# ─────────────────────────────────────────────────────────────────────────────
# AGENT_INSTRUCTIONS — Customize the Travel Planner Agent behavior here
# ─────────────────────────────────────────────────────────────────────────────
AGENT_CONFIG = {

    # ── PERSONA ──────────────────────────────────────────────────────────────
    # The agent's name, tagline, and core personality
    "PERSONA": {
        "name": "Atlas",
        "tagline": "Your AI-Powered Travel Companion",
        "personality": (
            "You are Atlas, an expert AI travel planner with deep knowledge of "
            "global destinations, cultures, local cuisines, and travel logistics. "
            "You are enthusiastic, detail-oriented, and genuinely passionate about "
            "helping travelers create unforgettable journeys."
        ),
    },

    # ── TONE ─────────────────────────────────────────────────────────────────
    # How the agent communicates with users
    # Options: "friendly", "professional", "casual", "luxury", "adventurous"
    "TONE": {
        "style": "friendly",
        "use_emojis": True,
        "language_complexity": "accessible",   # accessible | technical | simple
        "encouragement": True,                  # Add motivating travel phrases
        "local_tips": True,                     # Include insider/local tips
    },

    # ── SPECIALIZATION ───────────────────────────────────────────────────────
    # Travel types the agent specializes in (set True to enable)
    "SPECIALIZATION": {
        "family_travel":    True,
        "solo_travel":      True,
        "adventure_travel": True,
        "luxury_travel":    True,
        "budget_travel":    True,
        "business_travel":  True,
        "weekend_getaways": True,
        "cultural_tours":   True,
        "eco_tourism":      True,
        "honeymoon":        True,
    },

    # ── SAFETY GUIDELINES ────────────────────────────────────────────────────
    # Safety and advisory behavior
    "SAFETY": {
        "include_visa_info":       True,
        "include_health_advisory": True,
        "include_safety_ratings":  True,
        "warn_high_risk_zones":    True,
        "suggest_travel_insurance":True,
        "emergency_contacts":      True,
        "vaccination_reminders":   True,
    },

    # ── RECOMMENDATION STYLE ─────────────────────────────────────────────────
    # How recommendations are structured
    "RECOMMENDATION_STYLE": {
        "itinerary_format":    "day_by_day",    # day_by_day | overview | flexible
        "budget_detail":       "itemized",      # itemized | summary | range
        "hotel_categories":    ["budget", "mid-range", "luxury"],
        "include_alternatives":True,            # Offer backup options
        "crowd_avoidance":     True,            # Suggest off-peak times
        "hidden_gems":         True,            # Include lesser-known spots
        "food_focus":          "local_cuisine", # local_cuisine | all | dietary_specific
        "transport_options":   ["flight", "train", "bus", "car", "ferry"],
    },

    # ── REGIONAL PREFERENCES ─────────────────────────────────────────────────
    # Focus regions (empty list = all regions covered)
    "REGIONS": {
        "preferred_regions": [],                # e.g. ["Europe", "Southeast Asia"]
        "excluded_regions":  [],                # e.g. ["Active conflict zones"]
        "currency_default":  "USD",             # Default currency for budgets
        "unit_system":       "metric",          # metric | imperial
        "language_support":  ["English"],       # Languages for destination info
    },

    # ── CONTENT RULES ────────────────────────────────────────────────────────
    # What the agent always/never does
    "CONTENT_RULES": {
        "always": [
            "Provide realistic budget estimates with currency conversions",
            "Include at least one free or low-cost activity per day",
            "Mention the best time of year to visit each destination",
            "Suggest local transportation options",
            "Include cultural etiquette tips",
            "Provide packing recommendations based on climate",
        ],
        "never": [
            "Recommend illegal activities",
            "Suggest traveling to active conflict zones without clear warnings",
            "Provide outdated visa information without citing verification needed",
            "Ignore accessibility needs when asked about group composition",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Application Setup
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "atlas-travel-secret-2024")
CORS(app)


@app.context_processor
def inject_user():
    return {"current_user": current_user()}

# ─────────────────────────────────────────────────────────────────────────────
# IBM Watsonx.ai Client Initialization
# ─────────────────────────────────────────────────────────────────────────────
def get_watsonx_model():
    """Initialize and return the IBM Watsonx.ai Granite model."""
    api_key    = os.getenv("IBM_API_KEY")
    project_id = os.getenv("IBM_PROJECT_ID")
    url        = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key or not project_id:
        return None

    try:
        credentials = Credentials(url=url, api_key=api_key)
        client      = APIClient(credentials)

        model = ModelInference(
            model_id   = "ibm/granite-3-8b-instruct",
            api_client = client,
            project_id = project_id,
            params     = {
                GenParams.MAX_NEW_TOKENS:   2048,
                GenParams.MIN_NEW_TOKENS:   50,
                GenParams.TEMPERATURE:      0.7,
                GenParams.TOP_P:            0.9,
                GenParams.TOP_K:            50,
                GenParams.REPETITION_PENALTY: 1.1,
            },
        )
        return model
    except Exception as e:
        print(f"[Watsonx] Init error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt Builder  (uses AGENT_CONFIG)
# ─────────────────────────────────────────────────────────────────────────────
def build_system_prompt():
    cfg   = AGENT_CONFIG
    persona = cfg["PERSONA"]
    tone    = cfg["TONE"]
    safety  = cfg["SAFETY"]
    style   = cfg["RECOMMENDATION_STYLE"]
    regions = cfg["REGIONS"]
    rules   = cfg["CONTENT_RULES"]

    emoji_instruction = (
        "Use relevant travel emojis sparingly to enhance readability."
        if tone["use_emojis"] else
        "Do not use emojis."
    )

    specializations = [k.replace("_", " ").title()
                       for k, v in cfg["SPECIALIZATION"].items() if v]
    safety_items    = [k.replace("_", " ") for k, v in safety.items() if v]
    always_rules    = "\n".join(f"  - {r}" for r in rules["always"])
    never_rules     = "\n".join(f"  - {r}" for r in rules["never"])
    preferred       = ", ".join(regions["preferred_regions"]) or "All global regions"
    transport       = ", ".join(style["transport_options"])

    return f"""You are {persona['name']}, {persona['tagline']}.

{persona['personality']}

COMMUNICATION STYLE:
- Tone: {tone['style']} and {tone['language_complexity']}
- {emoji_instruction}
- {"Include insider local tips and hidden gems." if tone['local_tips'] else ""}
- {"Encourage and motivate travelers." if tone['encouragement'] else ""}

TRAVEL SPECIALIZATIONS: {', '.join(specializations)}

ITINERARY FORMAT: {style['itinerary_format']} with {style['budget_detail']} budget breakdown
TRANSPORT OPTIONS: {transport}
FOOD FOCUS: {style['food_focus']}
CURRENCY: {regions['currency_default']} | UNITS: {regions['unit_system']}
REGIONAL FOCUS: {preferred}

SAFETY & ADVISORY (always include when relevant):
{', '.join(safety_items)}

YOU MUST ALWAYS:
{always_rules}

YOU MUST NEVER:
{never_rules}

When creating itineraries:
1. Start with a destination overview and best travel season
2. Provide a day-by-day schedule with morning/afternoon/evening activities
3. List estimated costs for accommodation, food, transport, and activities
4. Include hotel recommendations across budget tiers
5. Add local food must-tries and restaurant suggestions
6. Provide packing checklist based on climate and activities
7. Include visa requirements and travel advisories
8. Suggest contingency plans for weather or closures
9. Add cultural etiquette tips
10. End with money-saving tips specific to the destination

Format responses in clear markdown with headers, bullet points, and tables where helpful.
Always be specific with prices, times, and locations — avoid vague suggestions."""


# ─────────────────────────────────────────────────────────────────────────────
# Core AI Chat Function
# ─────────────────────────────────────────────────────────────────────────────
def chat_with_agent(user_message: str, conversation_history: list) -> str:
    """Send a message to IBM Granite and return the response."""
    model = get_watsonx_model()

    system_prompt = build_system_prompt()

    # Build conversation context (last 6 exchanges to stay within token limits)
    context_window = conversation_history[-12:] if len(conversation_history) > 12 else conversation_history
    history_text   = ""
    for msg in context_window:
        role    = "User" if msg["role"] == "user" else "Atlas"
        history_text += f"{role}: {msg['content']}\n"

    full_prompt = f"""{system_prompt}

CONVERSATION HISTORY:
{history_text}
User: {user_message}
Atlas:"""

    if model:
        try:
            response = model.generate_text(prompt=full_prompt)
            # Strip any repeated "Atlas:" prefix the model might add
            text = response.strip()
            if text.startswith("Atlas:"):
                text = text[6:].strip()
            return text
        except Exception as e:
            print(f"[Watsonx] Generation error: {e}")
            return _fallback_response(user_message)
    else:
        return _fallback_response(user_message)


def _fallback_response(user_message: str) -> str:
    """Intelligent fallback when Watsonx is unavailable."""
    msg     = user_message.lower()
    persona = AGENT_CONFIG["PERSONA"]

    # ── Greeting — use word-boundary check to avoid "hi" inside "this" ────────
    greeting_words = {"hello", "hey", "start"}
    msg_words      = set(re.findall(r"[a-z]+", msg))
    if msg_words & greeting_words or msg.strip() in ("hi", "hi!"):
        return (f"👋 Hello! I'm **{persona['name']}**, {persona['tagline']}. "
                "I'm here to help you plan your perfect trip! "
                "Tell me your dream destination or travel style and I'll craft a personalized itinerary for you.")

    # ── Travel-type style queries (from sidebar chips and quick prompts) ───────
    TRAVEL_TYPE_RESPONSES = {
        "family": (
            "👨‍👩‍👧‍👦 **Family Travel — Top Destinations & Tips**\n\n"
            "### 🏆 Best Family Destinations\n"
            "- 🇯🇵 **Tokyo, Japan** — Safe, clean, amazing theme parks (DisneySea, teamLab)\n"
            "- 🇸🇬 **Singapore** — Universal Studios, Gardens by the Bay, excellent food courts\n"
            "- 🇮🇹 **Rome, Italy** — History brought to life; gelato on every corner\n"
            "- 🇺🇸 **Orlando, USA** — Disney World, Universal, SeaWorld all in one city\n"
            "- 🇳🇿 **New Zealand** — Safe, stunning nature, Hobbiton, and outdoor adventures\n\n"
            "### ✅ Family Travel Tips\n"
            "- Book direct flights to minimize travel fatigue with kids\n"
            "- Choose hotels with pools, kids' clubs, and adjoining rooms\n"
            "- Plan no more than 2 major sights per day — rest time is essential\n"
            "- Pre-book theme parks and popular attractions to skip queues\n"
            "- Pack a day bag with snacks, wipes, and a small first-aid kit\n\n"
            "### 💰 Typical Family Budget (4 people, 7 days)\n"
            "- **Budget:** $3,000–5,000 | **Mid-range:** $6,000–10,000 | **Luxury:** $15,000+\n\n"
            "Tell me your destination and kids' ages for a custom family itinerary! 🌍"
        ),
        "solo": (
            "🧳 **Solo Travel — Top Destinations & Tips**\n\n"
            "### 🏆 Best Solo Destinations\n"
            "- 🇹🇭 **Bangkok, Thailand** — Incredibly social hostel scene, cheap, safe, easy to navigate\n"
            "- 🇵🇹 **Lisbon, Portugal** — Safe, walkable, great food, friendly locals\n"
            "- 🇯🇵 **Tokyo, Japan** — Solo-friendly culture, efficient transport, exciting at every turn\n"
            "- 🇨🇴 **Medellín, Colombia** — Thriving digital nomad hub, warm climate, low cost\n"
            "- 🇮🇸 **Reykjavik, Iceland** — Unique landscapes, very safe, easy solo road trips\n\n"
            "### ✅ Solo Travel Tips\n"
            "- Stay in social hostels to meet other travelers easily\n"
            "- Share your itinerary with someone you trust back home\n"
            "- Use eSIM cards for cheap local data from day one\n"
            "- Join free walking tours to meet people and learn the city\n"
            "- Keep digital and physical copies of all key documents\n\n"
            "### 💰 Solo Budget (1 person, 7 days)\n"
            "- **Budget:** $600–900 | **Mid-range:** $1,500–2,500 | **Luxury:** $5,000+\n\n"
            "Tell me where you want to go solo and I'll plan your trip! 🌍"
        ),
        "romantic": (
            "💑 **Romantic Getaways — Top Destinations & Tips**\n\n"
            "### 🏆 Most Romantic Destinations\n"
            "- 🇬🇷 **Santorini, Greece** — Iconic sunsets, cave hotels, caldera views\n"
            "- 🇲🇻 **Maldives** — Overwater bungalows, private beaches, crystal lagoons\n"
            "- 🇫🇷 **Paris, France** — The timeless city of love — art, wine, candlelit dinners\n"
            "- 🇮🇹 **Amalfi Coast, Italy** — Cliffside villages, fresh seafood, scenic boat trips\n"
            "- 🇧🇦 **Bali, Indonesia** — Private villas with pools, rice terrace dinners, spa retreats\n\n"
            "### ✅ Romance Travel Tips\n"
            "- Book a private villa or boutique hotel over large resorts\n"
            "- Arrange sunset dinner reservations in advance\n"
            "- Add a surprise experience — cooking class, couples spa, private boat tour\n"
            "- Travel in shoulder season for fewer crowds and better prices\n"
            "- Always carry a small gift or card for special moments\n\n"
            "### 💰 Couples Budget (2 people, 7 days)\n"
            "- **Budget:** $2,000–3,000 | **Mid-range:** $4,000–7,000 | **Luxury:** $12,000+\n\n"
            "Tell me your anniversary date or honeymoon dream for a custom plan! 💍"
        ),
        "adventure": (
            "🧗 **Adventure Travel — Top Destinations & Tips**\n\n"
            "### 🏆 Best Adventure Destinations\n"
            "- 🇳🇵 **Nepal** — Everest Base Camp trek, Annapurna Circuit, white-water rafting\n"
            "- 🇳🇿 **New Zealand** — Bungee jumping, skydiving, Milford Sound, Tongariro Crossing\n"
            "- 🇨🇷 **Costa Rica** — Zip-lining, volcano hikes, surfing, jungle wildlife\n"
            "- 🇿🇦 **South Africa** — Great White shark diving, Table Mountain, Drakensberg hiking\n"
            "- 🇵🇪 **Peru** — Inca Trail, Amazon jungle, sandboarding in Huacachina\n\n"
            "### ✅ Adventure Travel Tips\n"
            "- Always purchase specialist travel insurance covering activities\n"
            "- Acclimatize properly for high-altitude destinations\n"
            "- Book guided tours for technical hikes or extreme activities\n"
            "- Pack lightweight, moisture-wicking clothing and sturdy boots\n"
            "- Check local weather windows — timing is everything for adventure\n\n"
            "### 💰 Adventure Budget (1 person, 10 days)\n"
            "- **Budget:** $1,500–2,500 | **Mid-range:** $3,000–5,000 | **Luxury:** $8,000+\n\n"
            "Tell me your adventure style and fitness level for a custom plan! 🏔️"
        ),
        "business": (
            "💼 **Business Travel — Top Cities & Productivity Tips**\n\n"
            "### 🏆 Top Business Travel Destinations\n"
            "- 🇦🇪 **Dubai, UAE** — World-class conference facilities, direct flights everywhere\n"
            "- 🇸🇬 **Singapore** — Asia's financial hub, ultra-efficient, English-speaking\n"
            "- 🇺🇸 **New York City** — Global business capital; finance, tech, media\n"
            "- 🇬🇧 **London, UK** — Europe's top business city; excellent transport links\n"
            "- 🇯🇵 **Tokyo, Japan** — Advanced infrastructure, safe, Asia's largest economy\n\n"
            "### ✅ Business Travel Tips\n"
            "- Book hotels within walking distance of your venue to save time\n"
            "- Use airport lounges for a productive buffer before meetings\n"
            "- Keep a carry-on only policy for trips under 5 days\n"
            "- Use a VPN on hotel Wi-Fi to protect company data\n"
            "- Schedule one free evening per trip to experience the local culture\n\n"
            "### 🏨 Business Hotel Picks by Tier\n"
            "- **Economy:** Ibis, Hampton Inn ($80–120/night)\n"
            "- **Mid-range:** Marriott Courtyard, Novotel ($150–250/night)\n"
            "- **Luxury:** Four Seasons, Ritz-Carlton, Park Hyatt ($350–700/night)\n\n"
            "Tell me your destination and travel dates for a business itinerary! 🗓️"
        ),
        "luxury": (
            "✨ **Luxury Travel — Top Destinations & Experiences**\n\n"
            "### 🏆 Ultimate Luxury Destinations\n"
            "- 🇲🇻 **Maldives** — Private overwater villas from $1,000+/night; underwater restaurants\n"
            "- 🇫🇷 **French Riviera** — Monaco, Cannes, St-Tropez; superyachts and Michelin dining\n"
            "- 🇦🇪 **Dubai** — Burj Al Arab, private desert camps, helicopter sightseeing\n"
            "- 🇮🇹 **Tuscany, Italy** — Private villa rentals, wine estates, truffle hunts\n"
            "- 🇯🇵 **Kyoto Ryokan** — Traditional luxury inns, kaiseki dinners, private tea ceremonies\n\n"
            "### ✅ Luxury Travel Tips\n"
            "- Book a dedicated travel concierge or luxury travel agent\n"
            "- Use private transfer services — no taxis or rideshare\n"
            "- Look for shoulder-season deals at 5-star properties (30–40% savings)\n"
            "- Request early check-in / late check-out as a status perk\n"
            "- Pre-book Michelin-starred restaurants 2–3 months in advance\n\n"
            "### 💰 Typical Luxury Budget (2 people, 7 days)\n"
            "- **Entry Luxury:** $8,000–12,000 | **Ultra-Luxury:** $20,000–50,000+\n\n"
            "Tell me your luxury destination and I'll curate an exclusive itinerary! 🥂"
        ),
        "weekend": (
            "🏃 **Weekend Getaway — Best Quick Escapes**\n\n"
            "### 🏆 Perfect 2–3 Day Destinations\n"
            "- 🇦🇹 **Vienna, Austria** — Coffee houses, museums, opera — all walkable\n"
            "- 🇵🇹 **Porto, Portugal** — Wine cellars, azulejo tiles, Atlantic seafood\n"
            "- 🇯🇵 **Kyoto, Japan** — Bamboo groves, temples, geisha district in 48 hours\n"
            "- 🇲🇽 **Mexico City** — World-class food, art, and culture in 3 days\n"
            "- 🇦🇺 **Sydney, Australia** — Harbour Bridge, Bondi Beach, fish markets\n\n"
            "### ✅ Weekend Trip Tips\n"
            "- Fly Thursday evening or Friday morning to maximize time\n"
            "- Pre-book 2–3 key experiences to avoid wasting hours deciding\n"
            "- Stay centrally — location beats hotel size on short trips\n"
            "- Pack light: carry-on only saves hours at airports\n"
            "- Plan your return for Sunday evening, not late night\n\n"
            "### 💰 Weekend Budget (2 people, 3 days)\n"
            "- **Budget:** $400–700 | **Mid-range:** $800–1,500 | **Luxury:** $3,000+\n\n"
            "Tell me your home city and I'll suggest the best weekend escapes nearby! 🗺️"
        ),
    }

    # Match travel type keywords (word-level, handles "Budget Travel trip" etc.)
    TYPE_KEYWORDS = {
        "family":    ["family"],
        "solo":      ["solo"],
        "romantic":  ["romantic", "romance", "honeymoon", "couple"],
        "adventure": ["adventure"],
        "business":  ["business"],
        "luxury":    ["luxury"],
        "weekend":   ["weekend"],
    }
    for type_key, keywords in TYPE_KEYWORDS.items():
        if any(re.search(rf"\b{kw}\b", msg) for kw in keywords):
            return TRAVEL_TYPE_RESPONSES[type_key]

    # ── Itinerary / trip-planning requests — extract destination from prompt ──
    dest_match     = re.search(r"itinerary for ([A-Za-z ,\-]+?)[\.\n]", user_message, re.IGNORECASE)
    duration_match = re.search(r"(\d+)[- ]day", user_message, re.IGNORECASE)
    budget_match   = re.search(r"\$([0-9,]+)", user_message)

    if dest_match:
        dest     = dest_match.group(1).strip().rstrip(",")
        duration = duration_match.group(1) if duration_match else "7"
        budget   = f"${budget_match.group(1)}" if budget_match else "$2,000"
        return _sample_itinerary(dest, f"{duration} days", budget)

    # ── Named-destination shortcuts ───────────────────────────────────────────
    DEST_MAP = {
        ("paris", "france"):               ("Paris, France",        "5 days",  "$2,000"),
        ("tokyo", "japan"):                ("Tokyo, Japan",          "7 days",  "$3,000"),
        ("bali", "indonesia"):             ("Bali, Indonesia",       "7 days",  "$1,500"),
        ("new york", "nyc"):               ("New York City, USA",    "5 days",  "$2,500"),
        ("dubai", "uae"):                  ("Dubai, UAE",            "5 days",  "$3,000"),
        ("barcelona", "spain"):            ("Barcelona, Spain",      "5 days",  "$2,000"),
        ("bangkok", "thailand"):           ("Bangkok, Thailand",     "7 days",  "$1,200"),
        ("lisbon", "portugal"):            ("Lisbon, Portugal",      "5 days",  "$1,500"),
        ("santorini", "greece"):           ("Santorini, Greece",     "5 days",  "$2,500"),
        ("maldives",):                     ("The Maldives",          "7 days",  "$4,000"),
        ("kenya", "safari", "nairobi"):    ("Safari Kenya",          "10 days", "$5,000"),
        ("machu picchu", "peru", "cusco"): ("Machu Picchu, Peru",    "7 days",  "$2,000"),
    }
    for keywords, args in DEST_MAP.items():
        if any(k in msg for k in keywords):
            return _sample_itinerary(*args)

    # ── Topic-specific helpers ────────────────────────────────────────────────
    if any(w in msg for w in ["budget", "cheap", "affordable"]):
        return ("💰 **Budget Travel Tips:**\n\n"
                "- Book flights 6–8 weeks in advance for the best prices\n"
                "- Stay in hostels or guesthouses ($15–40/night)\n"
                "- Eat at local markets and street food stalls\n"
                "- Use public transportation instead of taxis\n"
                "- Travel during shoulder season (spring/fall)\n\n"
                "**Top Budget Destinations:** Bali, Thailand, Vietnam, Portugal, Mexico\n\n"
                "Tell me your budget and destination for a detailed plan! 🌍")

    if any(w in msg for w in ["weather", "climate", "temperature"]):
        return ("🌤️ **Weather & Climate Planning:**\n\n"
                "The best time to visit depends on your destination:\n"
                "- **Europe:** May–September for warm, sunny weather\n"
                "- **Southeast Asia:** November–April (dry season)\n"
                "- **Caribbean:** December–April (low hurricane risk)\n"
                "- **Australia:** September–November (spring)\n\n"
                "Share your destination and I'll give you a detailed climate breakdown! 🌏")

    if any(w in msg for w in ["visa", "entry", "passport", "requirements"]):
        return ("📋 **Visa & Entry Information:**\n\n"
                "Visa requirements vary by destination and passport nationality.\n\n"
                "**Common visa-free destinations (US passport):**\n"
                "- 🇪🇺 **Europe (Schengen):** 90 days visa-free\n"
                "- 🇯🇵 **Japan:** 90 days visa-free\n"
                "- 🇲🇽 **Mexico:** 180 days visa-free\n"
                "- 🇹🇭 **Thailand:** 60 days visa-exempt\n"
                "- 🇵🇹 **Portugal:** 90 days (Schengen)\n\n"
                "Tell me your destination and passport nationality for specific requirements! 🛂")

    if any(w in msg for w in ["packing", "pack", "luggage", "suitcase"]):
        return ("🧳 **Universal Packing Checklist:**\n\n"
                "**Documents:** Passport, visa copies, travel insurance, booking confirmations\n\n"
                "**Clothing:** Versatile layers, comfortable walking shoes, weather-appropriate outerwear\n\n"
                "**Electronics:** Phone charger, universal adapter, portable power bank, earphones\n\n"
                "**Health:** First-aid kit, prescription medications, sunscreen, insect repellent\n\n"
                "**Miscellaneous:** Reusable water bottle, day bag, local currency, guidebook\n\n"
                "Share your destination and trip length for a custom packing list! 🌍")

    # ── Generic catch-all ─────────────────────────────────────────────────────
    return (f"✈️ I'm **{persona['name']}**, your AI travel companion! "
            "I can help you with:\n\n"
            "- 📍 **Personalized Itineraries** — Day-by-day travel plans\n"
            "- 💰 **Budget Planning** — Cost estimates for any trip\n"
            "- 🏨 **Hotel Recommendations** — Budget to luxury options\n"
            "- 🗺️ **Destination Guides** — Top attractions & hidden gems\n"
            "- 🍜 **Food Recommendations** — Local cuisine must-tries\n"
            "- 🌤️ **Weather & Packing** — Climate-based packing lists\n"
            "- 📋 **Visa & Travel Advisories** — Entry requirements\n\n"
            "**Where would you like to go?** Tell me your destination, budget, travel dates, and group size! 🌍")


def _sample_itinerary(destination: str, duration: str, budget: str) -> str:
    # Parse duration number for day-range generation
    try:
        days = int(duration.split()[0])
    except (ValueError, IndexError):
        days = 7

    day_plans = [
        ("Arrival & Orientation",
         "Arrive at the airport, check into your hotel, and freshen up.",
         "Stroll through the city center and explore the nearest neighborhood.",
         "Welcome dinner at a highly-rated local restaurant — try the signature dish!"),
        ("Top Landmarks",
         "Visit the #1 landmark early to beat crowds (book tickets online the night before).",
         "Explore a historic district or open-air market for street food and souvenirs.",
         "Sunset viewpoint or rooftop bar with panoramic city views."),
        ("Culture & Local Life",
         "Museum or art gallery visit — allow 2–3 hours.",
         "Local cooking class or food tour through authentic neighborhoods.",
         "Traditional cultural performance or live music venue."),
        ("Nature & Adventure",
         "Day trip to a natural site — park, beach, mountain, or valley.",
         "Picnic lunch with scenic views; optional guided hike or water activity.",
         "Relaxed dinner back in the city; early rest for the next day."),
        ("Hidden Gems",
         "Explore a lesser-known neighborhood recommended by locals.",
         "Visit a local market, artisan workshop, or independent café.",
         "Sunset cruise, rooftop dinner, or night market exploration."),
        ("Leisure & Relaxation",
         "Spa morning or wellness activity (yoga, meditation, hot springs).",
         "Shopping district — mix of local boutiques and major retail.",
         "Farewell dinner at the destination's most iconic restaurant."),
        ("Day Trip",
         "Full-day excursion to a nearby town, island, or natural wonder.",
         "Lunch at a local eatery in the day-trip destination.",
         "Return by evening; light dinner at the hotel or nearby café."),
    ]

    day_sections = ""
    for i in range(1, days + 1):
        plan = day_plans[(i - 1) % len(day_plans)]
        label = "Arrival & Orientation" if i == 1 else (f"Departure Day" if i == days and days > 2 else plan[0])
        if i == days and days > 2:
            day_sections += (
                f"\n### 📅 Day {i} — Departure\n"
                f"- 🌅 **Morning:** Final breakfast; last-minute souvenir shopping\n"
                f"- 🏨 **Midday:** Hotel check-out; luggage storage if needed\n"
                f"- ✈️ **Afternoon/Evening:** Transfer to airport — safe travels!\n"
            )
        else:
            day_sections += (
                f"\n### 📅 Day {i} — {label}\n"
                f"- 🌅 **Morning:** {plan[1]}\n"
                f"- ☀️ **Afternoon:** {plan[2]}\n"
                f"- 🌙 **Evening:** {plan[3]}\n"
            )

    return (
        f"## ✈️ {destination} — {duration} Itinerary\n\n"
        f"> **Estimated Budget:** {budget} per person &nbsp;|&nbsp; "
        f"**Duration:** {duration} &nbsp;|&nbsp; **Style:** Flexible\n\n"
        f"---\n\n"
        f"### 🌍 Destination Overview\n"
        f"{destination} is a fantastic travel destination with a rich mix of culture, cuisine, "
        f"history, and natural beauty. This {duration} itinerary is designed to give you the "
        f"best balance of iconic sights and authentic local experiences.\n\n"
        f"---\n"
        f"{day_sections}\n"
        f"---\n\n"
        f"### 🏨 Hotel Recommendations\n\n"
        f"| Tier | Type | Est. Cost/Night |\n"
        f"|---|---|---|\n"
        f"| 💚 Budget | Hostel / Guesthouse | $20–50 |\n"
        f"| 💛 Mid-Range | Boutique / 3-star Hotel | $80–180 |\n"
        f"| 💜 Luxury | 5-star Resort / Design Hotel | $250–600+ |\n\n"
        f"### 💰 Budget Breakdown (Total Trip)\n\n"
        f"| Category | Estimated Cost |\n"
        f"|---|---|\n"
        f"| ✈️ Flights (round-trip) | $350–800 |\n"
        f"| 🏨 Accommodation ({days} nights, mid-range) | $800–1,500 |\n"
        f"| 🍜 Food & Dining | $300–600 |\n"
        f"| 🎯 Activities & Entrance Fees | $150–400 |\n"
        f"| 🚌 Local Transport | $100–200 |\n"
        f"| 📦 Miscellaneous | $50–150 |\n"
        f"| **💰 Total Estimate** | **{budget}** |\n\n"
        f"### 🍜 Must-Try Local Food\n"
        f"- Ask locals for the most popular street food spots\n"
        f"- Visit the main food market on Day 2 or 3\n"
        f"- Try the national dish and regional specialties\n"
        f"- Book a food tour for a guided culinary experience\n\n"
        f"### 🧳 Packing Essentials\n"
        f"- 📄 Passport, visa documents, travel insurance\n"
        f"- 👟 Comfortable walking shoes (you'll walk a lot!)\n"
        f"- 🔌 Universal power adapter\n"
        f"- 💊 Basic first-aid kit and any prescription meds\n"
        f"- 📱 Offline maps downloaded before arrival\n\n"
        f"### 💡 Money-Saving Tips\n"
        f"- Book flights 6–8 weeks in advance for best prices\n"
        f"- Use a no-foreign-fee credit card to avoid conversion charges\n"
        f"- Eat where locals eat — away from the main tourist squares\n"
        f"- Buy a local SIM card or eSIM on arrival for cheaper data\n"
        f"- Book popular attractions online to skip queues\n\n"
        f"---\n"
        f"> 🔑 *This is a sample itinerary generated in offline mode. "
        f"Configure your IBM Watsonx.ai API key for a fully AI-personalized plan "
        f"with real hotel names, restaurant picks, and live pricing!*"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Weather Helper
# ─────────────────────────────────────────────────────────────────────────────
def get_weather(city: str) -> dict:
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return travel_data.get_mock_weather(city)
    try:
        url  = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            d = resp.json()
            return {
                "city":        d["name"],
                "country":     d["sys"]["country"],
                "temp":        round(d["main"]["temp"]),
                "feels_like":  round(d["main"]["feels_like"]),
                "description": d["weather"][0]["description"].title(),
                "humidity":    d["main"]["humidity"],
                "wind_speed":  d["wind"]["speed"],
                "icon":        d["weather"][0]["icon"],
                "success":     True,
            }
    except Exception as e:
        print(f"[Weather] Error: {e}")
    return travel_data.get_mock_weather(city)


# ─────────────────────────────────────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    persona = AGENT_CONFIG["PERSONA"]
    destinations = travel_data.FEATURED_DESTINATIONS[:6]
    return render_template("index.html",
                           persona=persona,
                           destinations=destinations,
                           travel_types=travel_data.TRAVEL_TYPES)


@app.route("/login", methods=["GET", "POST"])
@app.route("/signin", methods=["GET", "POST"])
def login_page():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        ok, message = login_user(email, password)
        if ok:
            next_url = request.form.get("next") or request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        flash(message, "danger")

    return render_template("login.html", next_url=request.args.get("next"))


@app.route("/register", methods=["GET", "POST"])
@app.route("/signup", methods=["GET", "POST"])
def register_page():
    if current_user():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        ok, message = register_user(name, email, password)
        if ok:
            login_user(email, password)
            flash("Welcome! Your account has been created.", "success")
            return redirect(url_for("dashboard"))
        flash(message, "danger")

    return render_template("register.html")


@app.route("/logout")
def logout_page():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))


@app.route("/chat")
@login_required
def chat_page():
    persona = AGENT_CONFIG["PERSONA"]
    if "conversation" not in session:
        session["conversation"] = []
    return render_template("chat.html",
                           persona=persona,
                           quick_prompts=travel_data.QUICK_PROMPTS)


@app.route("/dashboard")
@login_required
def dashboard():
    persona      = AGENT_CONFIG["PERSONA"]
    destinations = travel_data.FEATURED_DESTINATIONS
    return render_template("dashboard.html",
                           persona=persona,
                           destinations=destinations,
                           stats=travel_data.DASHBOARD_STATS)


@app.route("/planner")
@login_required
def planner():
    persona = AGENT_CONFIG["PERSONA"]
    return render_template("planner.html",
                           persona=persona,
                           destinations=travel_data.FEATURED_DESTINATIONS,
                           travel_types=travel_data.TRAVEL_TYPES)


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    data    = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    if "conversation" not in session:
        session["conversation"] = []

    session["conversation"].append({"role": "user", "content": message})

    response = chat_with_agent(message, session["conversation"])

    session["conversation"].append({"role": "assistant", "content": response})
    session.modified = True

    return jsonify({"response": response, "status": "success"})


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def clear_chat():
    session["conversation"] = []
    session.modified = True
    return jsonify({"status": "cleared"})


@app.route("/api/itinerary", methods=["POST"])
@login_required
def generate_itinerary():
    data = request.json or {}
    destination   = data.get("destination", "")
    duration      = data.get("duration", "7")
    budget        = data.get("budget", "2000")
    travel_type   = data.get("travel_type", "leisure")
    group_size    = data.get("group_size", "2")
    interests     = data.get("interests", [])
    start_date    = data.get("start_date", "")
    special_req   = data.get("special_requirements", "").strip()
    include_sects = data.get("include", [])

    if not destination:
        return jsonify({"error": "Destination required"}), 400

    include_note = (
        f"Make sure to include sections for: {', '.join(include_sects)}."
        if include_sects else ""
    )
    special_note = (
        f"Special requirements: {special_req}"
        if special_req else ""
    )

    prompt = (
        f"Create a detailed {duration}-day travel itinerary for {destination}.\n"
        f"Travel Type: {travel_type} | Group Size: {group_size} people\n"
        f"Total Budget: ${budget} USD | Start Date: {start_date or 'flexible'}\n"
        f"Interests: {', '.join(interests) if interests else 'general sightseeing'}\n"
        + (f"{special_note}\n" if special_note else "")
        + (f"{include_note}\n" if include_note else "")
        + "\nProvide: day-by-day schedule, hotel recommendations, restaurant suggestions, "
        "transport options, estimated costs, packing list, and visa requirements."
    )

    itinerary = chat_with_agent(prompt, [])
    return jsonify({"itinerary": itinerary, "destination": destination, "status": "success"})


@app.route("/api/weather", methods=["GET"])
def api_weather():
    city = request.args.get("city", "Paris")
    weather = get_weather(city)
    return jsonify(weather)


@app.route("/api/destinations", methods=["GET"])
def api_destinations():
    region     = request.args.get("region", "")
    travel_type = request.args.get("type", "")
    budget     = request.args.get("budget", "")
    dests      = travel_data.FEATURED_DESTINATIONS

    if region:
        dests = [d for d in dests if d.get("region", "").lower() == region.lower()]
    if travel_type:
        dests = [d for d in dests if travel_type.lower() in [t.lower() for t in d.get("types", [])]]
    if budget:
        dests = [d for d in dests if d.get("budget_level", "") == budget]

    return jsonify({"destinations": dests, "count": len(dests)})


@app.route("/api/budget", methods=["POST"])
def calculate_budget():
    data        = request.json or {}
    destination = data.get("destination", "")
    duration    = int(data.get("duration", 7))
    travel_type = data.get("travel_type", "mid-range")
    group_size  = int(data.get("group_size", 2))

    dest_data = next(
        (d for d in travel_data.FEATURED_DESTINATIONS
         if destination.lower() in d["name"].lower()),
        None,
    )

    if dest_data:
        costs     = dest_data.get("avg_costs", {})
        tier      = travel_type if travel_type in costs else "mid-range"
        daily     = costs.get(tier, {})
        per_day   = sum(daily.values())
        total     = per_day * duration * group_size
        breakdown = {
            "accommodation": daily.get("accommodation", 80)  * duration,
            "food":          daily.get("food", 40)           * duration * group_size,
            "activities":    daily.get("activities", 30)     * duration * group_size,
            "transport":     daily.get("transport", 20)      * duration * group_size,
            "miscellaneous": daily.get("misc", 15)           * duration * group_size,
            "total":         total,
            "per_person":    total // group_size,
        }
    else:
        # Generic estimates
        tiers = {"budget": 60, "mid-range": 120, "luxury": 300}
        daily = tiers.get(travel_type, 120)
        breakdown = {
            "accommodation": int(daily * 0.40) * duration,
            "food":          int(daily * 0.25) * duration * group_size,
            "activities":    int(daily * 0.20) * duration * group_size,
            "transport":     int(daily * 0.10) * duration * group_size,
            "miscellaneous": int(daily * 0.05) * duration * group_size,
            "total":         daily * duration * group_size,
            "per_person":    daily * duration,
        }

    return jsonify({"budget": breakdown, "currency": AGENT_CONFIG["REGIONS"]["currency_default"]})


@app.route("/api/recommendations", methods=["POST"])
@login_required
def get_recommendations():
    data         = request.json or {}
    interests    = data.get("interests", [])
    budget       = data.get("budget", "mid-range")
    travel_type  = data.get("travel_type", "leisure")
    duration     = data.get("duration", "week")

    prompt = (
        f"Recommend 5 travel destinations for a {duration} trip.\n"
        f"Budget: {budget} | Travel Style: {travel_type}\n"
        f"Interests: {', '.join(interests) if interests else 'culture, food, nature'}\n\n"
        "For each destination provide: name, country, why it's perfect for this traveler, "
        "best time to visit, estimated cost per person, and 3 top activities."
    )
    recommendations = chat_with_agent(prompt, [])
    return jsonify({"recommendations": recommendations, "status": "success"})


@app.route("/api/packing-list", methods=["POST"])
@login_required
def get_packing_list():
    data        = request.json or {}
    destination = data.get("destination", "")
    duration    = data.get("duration", 7)
    activities  = data.get("activities", [])
    climate     = data.get("climate", "temperate")

    prompt = (
        f"Create a detailed packing checklist for {duration} days in {destination}.\n"
        f"Climate: {climate} | Activities: {', '.join(activities) if activities else 'general tourism'}\n\n"
        "Organize by category: Documents, Clothing, Toiletries, Electronics, "
        "Health & Medicine, Activities Gear, and Miscellaneous."
    )
    packing_list = chat_with_agent(prompt, [])
    return jsonify({"packing_list": packing_list, "status": "success"})


@app.route("/api/visa-info", methods=["POST"])
@login_required
def get_visa_info():
    data        = request.json or {}
    destination = data.get("destination", "")
    nationality = data.get("nationality", "US")

    prompt = (
        f"Provide visa and entry requirements for {nationality} passport holders traveling to {destination}.\n"
        "Include: visa type required, application process, costs, processing time, "
        "required documents, validity period, health requirements, and any travel advisories."
    )
    visa_info = chat_with_agent(prompt, [])
    return jsonify({"visa_info": visa_info, "status": "success"})


@app.route("/api/health", methods=["GET"])
def health_check():
    model_available = get_watsonx_model() is not None
    return jsonify({
        "status":          "healthy",
        "agent":           AGENT_CONFIG["PERSONA"]["name"],
        "model":           "ibm/granite-3-8b-instruct",
        "watsonx_status":  "connected" if model_available else "fallback_mode",
        "timestamp":       datetime.utcnow().isoformat(),
        "version":         "1.0.0",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    print(f"\n{'='*60}")
    print(f"  ✈️  Travel Planner Agent — {AGENT_CONFIG['PERSONA']['name']}")
    print(f"  🌍  {AGENT_CONFIG['PERSONA']['tagline']}")
    print(f"  🚀  Running on http://localhost:{port}")
    print(f"  🤖  Model: IBM Granite 3 8B Instruct")
    print(f"{'='*60}\n")
    app.run(debug=debug, host="0.0.0.0", port=port)
