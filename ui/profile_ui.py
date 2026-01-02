"""
Gradio UI for user profile management.
Allows users to create and update their profiles with preferences.
"""

import gradio as gr
from app.database.user_repository import UserRepository
from app.database.models import Base
from app.database.connection import engine
from ui.constants import (
    CONTENT_PREFERENCE_CATEGORIES,
    CATEGORY_DISPLAY_NAMES,
    PREFERENCE_OPTIONS,
    EXPERTISE_LEVELS
)


def ensure_database_tables():
    """Ensure database tables exist before creating user."""
    Base.metadata.create_all(engine)


def map_display_to_category(display_name: str) -> str:
    """Map display name back to category value."""
    for cat, display in CATEGORY_DISPLAY_NAMES.items():
        if display == display_name:
            return cat
    # Fallback: if not found, try direct match
    return display_name if display_name in CONTENT_PREFERENCE_CATEGORIES else "others"


def map_preference_display_to_key(display_name: str) -> str:
    """Map preference display name back to key."""
    for key, display in PREFERENCE_OPTIONS.items():
        if display == display_name:
            return key
    return display_name


def save_profile(
    email: str,
    name: str,
    title: str,
    background: str,
    content_preferences: list,
    preferences: list,
    expertise_level: str
) -> tuple[str, str]:
    """
    Save or update user profile.
    
    Returns:
        Tuple of (status_message, profile_display)
    """
    if not email or not email.strip():
        return "❌ Error: Email is required.", ""
    
    if not name or not name.strip():
        return "❌ Error: Name is required.", ""
    
    # Validate email format (basic check)
    if "@" not in email or "." not in email.split("@")[1]:
        return "❌ Error: Please enter a valid email address.", ""
    
    try:
        # Ensure tables exist
        ensure_database_tables()
        
        user_repo = UserRepository()
        
        # Check if user exists
        existing_user = user_repo.get_user_by_email(email.strip())
        
        # Map display names back to category values
        category_values = [map_display_to_category(display) for display in content_preferences]
        
        # Map preference display names back to keys
        preference_keys = [map_preference_display_to_key(display) for display in preferences]
        preferences_dict = {key: key in preference_keys for key in PREFERENCE_OPTIONS.keys()}
        
        if existing_user:
            # Update existing user
            updated_user = user_repo.update_user(
            existing_user.id,
            name=name.strip(),
            title=title.strip() if title else None,
            background=background.strip() if background else None,
            content_preferences=category_values,
            preferences=preferences_dict,
            expertise_level=expertise_level
            )
            
            if updated_user:
                profile_display = format_profile_display(updated_user)
                return f"✅ Profile updated successfully for {email}!", profile_display
            else:
                return "❌ Error: Failed to update profile.", ""
        else:
            # Create new user
            new_user = user_repo.create_user(
                email=email.strip(),
                name=name.strip(),
                title=title.strip() if title else None,
                background=background.strip() if background else None,
                content_preferences=category_values,
                preferences=preferences_dict,
                expertise_level=expertise_level,
                is_active=True
            )
            
            profile_display = format_profile_display(new_user)
            return f"✅ Profile created successfully for {email}!", profile_display
            
    except ValueError as e:
        return f"❌ Error: {str(e)}", ""
    except Exception as e:
        return f"❌ Error: Failed to save profile. {str(e)}", ""


def load_profile(email: str) -> tuple[str, str, str, str, list, list, str]:
    """
    Load existing user profile by email.
    
    Returns:
        Tuple of (email, name, title, background, content_preferences, preferences, expertise_level)
    """
    if not email or not email.strip():
        return "", "", "", "", [], [], "Medium"
    
    try:
        ensure_database_tables()
        user_repo = UserRepository()
        user = user_repo.get_user_by_email(email.strip())
        
        if not user:
            return email.strip(), "", "", "", [], [], "Medium"
        
        # Convert preferences dict to list of selected keys, then to display names
        selected_preference_keys = [
            key for key, value in (user.preferences or {}).items() if value
        ]
        selected_preference_displays = [
            PREFERENCE_OPTIONS[key] for key in selected_preference_keys
        ]
        
        # Convert category values to display names
        category_displays = [
            CATEGORY_DISPLAY_NAMES.get(cat, cat) 
            for cat in (user.content_preferences or [])
        ]
        
        return (
            user.email,
            user.name,
            user.title or "",
            user.background or "",
            category_displays,
            selected_preference_displays,
            user.expertise_level or "Medium"
        )
    except Exception as e:
        return email.strip(), "", "", "", [], [], "Medium"


def format_profile_display(user) -> str:
    """Format user profile for display."""
    content_prefs = user.content_preferences or []
    prefs = user.preferences or {}
    
    lines = [
        f"**Email:** {user.email}",
        f"**Name:** {user.name}",
    ]
    
    if user.title:
        lines.append(f"**Title:** {user.title}")
    
    if user.background:
        lines.append(f"**Background:** {user.background}")
    
    lines.append(f"**Expertise Level:** {user.expertise_level}")
    
    if content_prefs:
        lines.append(f"\n**Content Preferences:**")
        for pref in content_prefs:
            display_name = CATEGORY_DISPLAY_NAMES.get(pref, pref)
            lines.append(f"  • {display_name}")
    
    if prefs:
        lines.append(f"\n**Preferences:**")
        for key, value in prefs.items():
            if value:
                display_name = PREFERENCE_OPTIONS.get(key, key)
                lines.append(f"  • {display_name}")
    
    lines.append(f"\n**Status:** {'Active' if user.is_active else 'Inactive'}")
    lines.append(f"**Created:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
    
    return "\n".join(lines)


def create_ui():
    """Create and return Gradio interface."""
    
    # Prepare content preference choices with display names
    content_choices = [
        CATEGORY_DISPLAY_NAMES.get(cat, cat) 
        for cat in CONTENT_PREFERENCE_CATEGORIES
    ]
    
    # Prepare preference choices
    preference_choices = list(PREFERENCE_OPTIONS.values())
    
    with gr.Blocks(title="AI Frontier - User Profile", theme=gr.themes.Soft()) as interface:
        gr.Markdown(
            """
            # 🤖 AI Frontier - User Profile Management
            
            Create or update your profile to receive personalized AI news digests.
            Your preferences help us curate the most relevant content for you.
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📝 Profile Information")
                
                email_input = gr.Textbox(
                    label="Email Address *",
                    placeholder="your.email@example.com",
                    info="Your email address (required)"
                )
                
                name_input = gr.Textbox(
                    label="Name *",
                    placeholder="Your Name",
                    info="Your full name (required)"
                )
                
                title_input = gr.Textbox(
                    label="Title/Role",
                    placeholder="e.g., AI Engineer, Researcher, Student",
                    info="Optional: Your professional title or role"
                )
                
                background_input = gr.Textbox(
                    label="Background",
                    placeholder="e.g., MSCS student at Duke University",
                    info="Optional: Brief background about yourself",
                    lines=2
                )
                
                expertise_dropdown = gr.Dropdown(
                    label="Expertise Level",
                    choices=EXPERTISE_LEVELS,
                    value="Medium",
                    info="Your level of expertise in AI/ML"
                )
                
                gr.Markdown("### 🎯 Content Preferences")
                gr.Markdown("Select the types of content you're interested in:")
                
                content_checkboxes = gr.CheckboxGroup(
                    label="Content Categories",
                    choices=content_choices,
                    info="Select one or more categories"
                )
                
                gr.Markdown("### ⚙️ Preferences")
                gr.Markdown("Customize your content preferences:")
                
                preference_checkboxes = gr.CheckboxGroup(
                    label="Content Preferences",
                    choices=preference_choices,
                    info="Select your preferences"
                )
                
                with gr.Row():
                    load_btn = gr.Button("📥 Load Profile", variant="secondary")
                    submit_btn = gr.Button("💾 Save Profile", variant="primary")
            
            with gr.Column(scale=1):
                gr.Markdown("### 👤 Current Profile")
                
                status_output = gr.Textbox(
                    label="Status",
                    interactive=False,
                    lines=2
                )
                
                profile_display = gr.Markdown(
                    label="Profile Details",
                    value="*No profile loaded. Enter an email and click 'Load Profile' or create a new profile.*"
                )
        
        # Event handlers
        load_btn.click(
            fn=load_profile,
            inputs=[email_input],
            outputs=[email_input, name_input, title_input, background_input, 
                    content_checkboxes, preference_checkboxes, expertise_dropdown]
        )
        
        submit_btn.click(
            fn=save_profile,
            inputs=[
                email_input,
                name_input,
                title_input,
                background_input,
                content_checkboxes,
                preference_checkboxes,
                expertise_dropdown
            ],
            outputs=[status_output, profile_display]
        )
        
        # Auto-load profile when email changes (optional)
        email_input.submit(
            fn=load_profile,
            inputs=[email_input],
            outputs=[email_input, name_input, title_input, background_input,
                    content_checkboxes, preference_checkboxes, expertise_dropdown]
        )
    
    return interface


def launch_ui(server_name="127.0.0.1", server_port=7860, share=False):
    """
    Launch the Gradio UI.
    
    Args:
        server_name: Server name (default: 127.0.0.1 for local)
        server_port: Port number (default: 7860)
        share: Whether to create a public link (default: False)
    """
    # Ensure database tables exist before launching
    ensure_database_tables()
    
    interface = create_ui()
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=share
    )


if __name__ == "__main__":
    launch_ui()
