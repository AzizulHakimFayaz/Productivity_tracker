# FocusIO (AI-Powered Productivity Tracker)

> An intelligent, desktop-based productivity application built to monitor computer usage, track daily activity sessions, and autonomously categorize tasks using AI-powered insights.

## Table of Contents
- [About the Project](#about-the-project)
- [Key Features](#key-features)
- [Technologies Used](#technologies-used)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## About the Project
FocusIO provides a seamless way to stay on top of your daily productivity. By deeply integrating into your desktop environment, it monitors active window transitions and app usage durations, granting you powerful structural insights. It removes the hassle of manual categorization by using local, on-machine AI (FastEmbed & ONNX Runtime) to classify applications and tasks, ensuring your privacy remains intact.

## Key Features
- **🧠 Local AI-Based Activity Classification:** Employs FastEmbed and ONNX models directly on your device to automatically sort and categorize daily app usage—no data is sent to the cloud.
- **⏱️ Detailed Time Tracking:** Precise and granular time tracking of active windows, reducing idle time from the equation for a realistic view of how you spend your day.
- **📊 Rize-Style Interactive Timeline:** Features an intuitive, interactive timeline grid that visualizes your day in chunks, alongside hover-based navigation.
- **🔍 Activity Explorer:** An in-depth view into your tasks. Use "Apps" inspection popups to view and audit specific application data for any given hour.
- **💻 Completely Local & Private:** All data, including AI models and tracking histories (SQLite), are stored seamlessly on your local machine.

## Technologies Used
- **Language:** Python
- **GUI Framework:** PyQt6, PyQt6-Charts
- **Local AI:** FastEmbed, ONNX Runtime
- **Database:** SQLite
- **System Monitoring:** `pywin32`, `psutil`
- **Packaging:** PyInstaller

## Project Architecture
The application is logically structured as follows:
- **`ui/`**: Contains page modules (Dashboard, Analytics, Settings, Planner, etc.) built with PyQt6.
- **`widgets/`**: Reusable custom components like the Timeline frontend interface.
- **`backend/`**: The core logic including the AI classifier and app usage tracking systems.
- **`classifier_data/`**: Local caching for FastEmbed models.
- **`styles/`**: Custom styles for giving the application a modern look.

## Getting Started

### Prerequisites
Make sure you have Python 3.9+ installed on your system. You also need a Windows environment for pywin32 to operate effectively.

### Installation
1. Clone the repository or download the source code:
   ```bash
   # If using git
   git clone https://github.com/AzizulHakimFayaz/Productivity_tracker.git
   cd Productivity_tracker
   ```
2. Install the required python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Usage
- **Start the Tracker:** Ensure the application is running in the background. It will automatically detect active window changes and capture your productive hours.
- **Navigate Metrics:** Use the **Dashboard** to view real-time productivity points and the **Analytics Component** to see how time accumulates across your working hours.
- **Inspect Specific Hours:** Utilize the interactive timeline feature by hovering over hour segments. Click to see specific apps used within that timeframe.
- **Categorization Settings:** Modify application classifications as needed. The built-in AI handles unseen apps out of the box.

## Contributing
Contributions are always welcome! If you'd like to improve FocusIO:
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
Distributed under the MIT License. See `LICENSE` for more information.
