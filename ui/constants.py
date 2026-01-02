"""
Constants for UI components - predefined choices for user preferences.
"""

from app.agent.curator_digest_agent import VALID_CATEGORIES, CATEGORY_DESCRIPTIONS

# Content preference categories (9 categories matching ContentCategory enum)
CONTENT_PREFERENCE_CATEGORIES = VALID_CATEGORIES

# Category descriptions for display in UI
CATEGORY_DISPLAY_NAMES = {
    "technique": "Technique - New methods, algorithms, or technical approaches",
    "research": "Research - Research papers, academic work, or scientific findings",
    "education": "Education - Educational content, tutorials, or learning materials",
    "announcement": "Announcement - Product launches, company news, or official announcements",
    "analysis": "Analysis - Deep dives, detailed analysis, or investigative pieces",
    "tutorial": "Tutorial - How-to guides, step-by-step instructions, or walkthroughs",
    "opinion": "Opinion - Opinion pieces, editorials, or personal perspectives",
    "news": "News - General news updates or current events",
    "others": "Others - Content that doesn't fit into the above categories"
}

# Preference options with display labels
PREFERENCE_OPTIONS = {
    "prefer_practical": "Prefer practical applications",
    "prefer_technical_depth": "Prefer technical depth",
    "prefer_research_breakthroughs": "Prefer research breakthroughs",
    "prefer_production_focus": "Prefer production focus",
    "avoid_marketing_hype": "Avoid marketing hype"
}

# Expertise levels
EXPERTISE_LEVELS = ["Beginner", "Medium", "Advanced"]
