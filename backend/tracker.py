import time
import re
import ctypes
import os

# Note: Requires `pip install pywin32 psutil`
try:
    import win32gui
    import win32process
    import win32api
    import psutil
except ImportError:
    pass

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint),
                ("dwTime", ctypes.c_uint)]

class ActivityTracker:
    """Tracks active window and detects idle state."""
    
    def __init__(self, idle_threshold=300):
        # 300 seconds (5 minutes) default idle threshold
        self.idle_threshold = idle_threshold
        
    def get_idle_time(self) -> float:
        """Returns the number of seconds since the user last interacted with the system."""
        try:
            lastInputInfo = LASTINPUTINFO()
            lastInputInfo.cbSize = ctypes.sizeof(lastInputInfo)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lastInputInfo)):
                millis = ctypes.windll.kernel32.GetTickCount() - lastInputInfo.dwTime
                return millis / 1000.0
            return 0.0
        except Exception:
            return 0.0

    def extract_domain(self, title: str, app: str) -> str:
        """Attempts to extract a domain from the window title, especially for browsers."""
        browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"]
        domain = ""
        
        if app.lower() in browsers:
            # We assume domains often appear in the title before a dash or a standard character
            # Simplistic approach since we can't reliably grab Chrome URL without an extension.
            # E.g. "GitHub - my-repo - Google Chrome"
            # Or "youtube - Google Search"
            # Let's use simple logic:
            
            # Remove common browser suffixes if present
            clean_title = title
            for suffix in [
                "- Google Chrome",
                "- Mozilla Firefox",
                "- Microsoft Edge",
                "- Brave",
                "- Opera",
            ]:
                clean_title = clean_title.replace(suffix, "")
            clean_title = clean_title.strip()
            
            # Simple keyword matching for popular domains
            lower_title = clean_title.lower()
            if "youtube" in lower_title: return "youtube.com"
            if "github" in lower_title: return "github.com"
            if "stack overflow" in lower_title: return "stackoverflow.com"
            if "google search" in lower_title: return "google.com"
            if "google drive" in lower_title or " drive " in lower_title: return "drive.google.com"
            if "google docs" in lower_title or " docs " in lower_title: return "docs.google.com"
            if "google sheets" in lower_title or " sheets " in lower_title: return "docs.google.com"
            if "google slides" in lower_title or " slides " in lower_title: return "docs.google.com"
            if "twitter" in lower_title or " x " in lower_title: return "twitter.com"
            if "reddit" in lower_title: return "reddit.com"
            if "chatgpt" in lower_title: return "chatgpt.com"
            if "facebook" in lower_title: return "facebook.com"
            if "instagram" in lower_title: return "instagram.com"
            if "linkedin" in lower_title: return "linkedin.com"
            if "pinterest" in lower_title: return "pinterest.com"
            if "whatsapp" in lower_title: return "web.whatsapp.com"
            if "telegram" in lower_title: return "web.telegram.org"
            if "twitch" in lower_title: return "twitch.tv"
            if "netflix" in lower_title: return "netflix.com"
            if "spotify" in lower_title: return "spotify.com"
            if "discord" in lower_title: return "discord.com"
            if "tiktok" in lower_title: return "tiktok.com"
            if "amazon" in lower_title and "prime" in lower_title: return "primevideo.com"
            
            # Or if it looks like a crude URL form:
            match = re.search(r'\b([a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})\b', clean_title)
            if match:
                domain = match.group(1)
                
        return domain

    def get_active_window(self):
        """Returns the current active app and title."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return "Unknown", "No Active Window", ""
                
            length = win32gui.GetWindowTextLength(hwnd)
            title = win32gui.GetWindowText(hwnd) if length > 0 else "Unknown Title"
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                app = process.name()
            except psutil.NoSuchProcess:
                app = "Unknown App"
                
            domain = self.extract_domain(title, app)
            
            return app, title, domain
            
        except Exception as e:
            print(f"Tracking error: {e}")
            return "Error", str(e), ""

    def get_current_state(self):
        """High-level function called in the loop."""
        idle_time = self.get_idle_time()
        
        # If user has been idle longer than threshold, override active window to IDLE
        if idle_time > self.idle_threshold:
            return "Idle", "User is away", "", idle_time
            
        app, title, domain = self.get_active_window()
        return app, title, domain, idle_time
