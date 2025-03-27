# launch_gui.py
import flet as ft
import subprocess
import os
import sys
import webbrowser

# ✅ Resolve app path whether running from .py or frozen .exe
if getattr(sys, 'frozen', False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

APP_PATH = os.path.join(BASE_PATH, "streamlit_app.py")
WORK_DIR = BASE_PATH  # ✅ Use correct working directory for subprocess

def main(page: ft.Page):
    page.title = "Audit App Launcher"
    page.window_width = 400
    page.window_height = 300
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_resizable = False

    def launch_streamlit_app(e):
        try:
            subprocess.Popen(
                [
                    "C:\\Users\\colby\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
                    "-m", "streamlit", "run", APP_PATH
                ],
                cwd=WORK_DIR,
                shell=True,
                stdout=open(os.path.join(BASE_PATH, "streamlit_log.txt"), "w"),
                stderr=subprocess.STDOUT
            )

            # ✅ Write to log for confirmation
            with open(os.path.join(BASE_PATH, "launch_debug.txt"), "w") as f:
                f.write("✅ Streamlit launched from Flet GUI.\n")

            webbrowser.open("http://localhost:8501")

            page.snack_bar = ft.SnackBar(ft.Text("🚀 Streamlit app launching..."))
            page.snack_bar.open = True
            page.update()

        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error: {ex}"))
            page.snack_bar.open = True
            page.update()

    launch_button = ft.ElevatedButton("▶️ Launch Audit App", on_click=launch_streamlit_app)

    page.add(
        ft.Text("Audit Sampling App", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("Launch the Streamlit app with one click."),
        ft.Divider(),
        launch_button
    )

# 🚀 Launch the main Flet GUI
ft.app(target=main)
