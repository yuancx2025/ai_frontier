from app.daily_runner import run_daily_pipeline


def main(hours: int = 24, top_n: int = 10):
    return run_daily_pipeline(hours=hours, top_n=top_n)


if __name__ == "__main__":
    import sys

    # Check if UI mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        from app.ui.profile_ui import launch_ui
        print("🚀 Launching Gradio UI...")
        print("📝 Open your browser to: http://127.0.0.1:7860")
        launch_ui()
    else:
        # Run daily pipeline
        hours = 24
        top_n = 10

        if len(sys.argv) > 1:
            hours = int(sys.argv[1])
        if len(sys.argv) > 2:
            top_n = int(sys.argv[2])

        result = main(hours=hours, top_n=top_n)
        exit(0 if result["success"] else 1)
