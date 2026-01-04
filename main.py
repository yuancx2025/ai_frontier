from app.daily_runner import run_daily_pipeline
import os
import sys


def main(hours: int = 24, top_n: int = 10):
    """Main entry point for Fargate tasks."""
    return run_daily_pipeline(hours=hours, top_n=top_n)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        # UI mode: Run Gradio UI (for local development)
        from app.ui.profile_ui import launch_ui
        print("🚀 Launching Gradio UI...")
        print("📝 Open your browser to: http://127.0.0.1:7860")
        launch_ui()
    else:
        # Pipeline mode: Run daily pipeline (default for scheduled tasks)
        hours = int(os.getenv("HOURS", "24"))
        top_n = int(os.getenv("TOP_N", "10"))
        
        # Allow override via command line args (for local testing)
        if len(sys.argv) > 1:
            hours = int(sys.argv[1])
        if len(sys.argv) > 2:
            top_n = int(sys.argv[2])

        try:
            result = main(hours=hours, top_n=top_n)
            ok = bool(result and result.get("success", False))
            sys.exit(0 if ok else 1)
        except Exception as e:
            print(f"Pipeline failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
