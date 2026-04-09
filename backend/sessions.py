import time

class SessionManager:
    """Consolidates raw tracker activity into sessions."""
    
    def __init__(self, classifier, idle_threshold: int = 300):
        self.classifier = classifier
        self.active_session = None
        self.deep_work_time = 0.0
        self.idle_threshold = idle_threshold
        self.category_resolver = None
        
    def _create_session(self, app, title, domain, timestamp, category):
        return {
            "app": app,
            "title": title,
            "domain": domain,
            "category": category,
            "start_time": timestamp,
            "last_active": timestamp,
            "duration": 0.0
        }

    def process_activity(self, app: str, title: str, domain: str, timestamp: float, idle_time: float):
        """Processes current active window, returning a finalised session dict if one closed."""
        if idle_time > self.idle_threshold: # Handled partially by Tracker mostly
            app = "Idle"
            title = "User is away"
            domain = ""
            
        completed_session = None
        
        # Check if the context changed
        if self.active_session:
            # Did the app or title change?
            if self.active_session["app"] != app or self.active_session["title"] != title:
                # The session is complete
                # Calculate final duration
                duration = timestamp - self.active_session["start_time"]
                self.active_session["duration"] = duration
                self.active_session["end_time"] = timestamp
                
                # Keep reference to return
                if duration >= 1.0: # Ignore flickers under 1 second
                    completed_session = self.active_session
                
                # Setup new session
                if self.category_resolver:
                    cat = self.category_resolver(app, title, domain)
                else:
                    cat = self.classifier.classify(app, title, domain)
                self.active_session = self._create_session(app, title, domain, timestamp, cat)
            else:
                # Same session, update last_active
                self.active_session["last_active"] = timestamp
        else:
            # First session ever
            if self.category_resolver:
                cat = self.category_resolver(app, title, domain)
            else:
                cat = self.classifier.classify(app, title, domain)
            self.active_session = self._create_session(app, title, domain, timestamp, cat)
            
        # Optional: Deep Work Calculation
        if completed_session:
            if completed_session["category"] in ["coding", "learning", "writing"]:
                self.deep_work_time += completed_session["duration"]
            else:
                # If they switched to entertainment, deep work breaks
                if completed_session["category"] == "entertainment":
                    self.deep_work_time = 0.0
            
        return completed_session

    def force_close_session(self, timestamp: float):
        """Forces the current session to end and returns it (e.g. on shutdown)."""
        if self.active_session:
            duration = timestamp - self.active_session["start_time"]
            self.active_session["duration"] = duration
            self.active_session["end_time"] = timestamp
            return self.active_session
        return None
