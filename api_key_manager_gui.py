#!/usr/bin/env python3
"""
API Key Manager PyQt Desktop Application

A simple desktop application to manage API key metadata in Supabase database.
The actual API keys remain stored in the configuration file for security.

Features:
- Add new API key names with provider selection
- View existing API keys and their status
- Simple table display with key statistics
- Direct connection to Supabase database

Requirements:
- PyQt5 or PyQt6
- supabase-py
- Configuration from todowa/config.py

Usage:
    python api_key_manager_gui.py
"""

import sys
import os
from typing import List, Dict, Any
from datetime import datetime

# Add the todowa directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
todowa_dir = os.path.dirname(current_dir)
sys.path.insert(0, todowa_dir)

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                                QTableWidget, QTableWidgetItem, QComboBox, 
                                QMessageBox, QGroupBox, QHeaderView, QTextEdit,
                                QSplitter, QFrame, QStatusBar)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt5.QtGui import QFont, QPalette
    PyQt_version = 5
except ImportError:
    try:
        from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                    QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                                    QTableWidget, QTableWidgetItem, QComboBox, 
                                    QMessageBox, QGroupBox, QHeaderView, QTextEdit,
                                    QSplitter, QFrame, QStatusBar)
        from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
        from PyQt6.QtGui import QFont, QPalette
        PyQt_version = 6
    except ImportError:
        print("Error: Neither PyQt5 nor PyQt6 is installed.")
        print("Please install one of them using:")
        print("  pip install PyQt5")
        print("  or")
        print("  pip install PyQt6")
        sys.exit(1)

try:
    from supabase import create_client, Client
    from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, get_named_api_keys
    from api_key_manager import ApiKeyManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the correct directory and have all dependencies installed.")
    sys.exit(1)


class ApiKeyStatsWorker(QThread):
    """Worker thread to fetch API key statistics without blocking the UI."""
    stats_ready = pyqtSignal(dict)
    
    def __init__(self, api_key_manager):
        super().__init__()
        self.api_key_manager = api_key_manager
        
    def run(self):
        try:
            # This runs in a separate thread
            import asyncio
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            async def fetch_stats():
                return await self.api_key_manager.get_statistics('gemini')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            stats = loop.run_until_complete(fetch_stats())
            loop.close()
            
            self.stats_ready.emit(stats)
        except Exception as e:
            self.stats_ready.emit({'error': str(e)})


class ApiKeyManagerGUI(QMainWindow):
    """Main GUI application for API key management."""
    
    def __init__(self):
        super().__init__()
        self.supabase = None
        self.api_key_manager = None
        self.stats_worker = None
        self.auto_refresh_timer = QTimer()
        
        self.init_database_connection()
        self.init_ui()
        self.load_data()
        
        # Set up auto-refresh
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        self.auto_refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def init_database_connection(self):
        """Initialize connection to Supabase database."""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            
            # Test the connection
            result = self.supabase.table('api_keys').select('count', count='exact').limit(1).execute()
            print(f"Database connection successful. Current API keys count: {result.count}")
            
            # Initialize API key manager
            named_keys = get_named_api_keys()
            self.api_key_manager = ApiKeyManager(self.supabase, named_keys)
            
        except Exception as e:
            QMessageBox.critical(self, "Database Connection Error", 
                               f"Failed to connect to Supabase database:\n{str(e)}")
            sys.exit(1)
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Todowa API Key Manager")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Todowa API Key Manager")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter if PyQt_version == 6 else Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Create splitter for layout
        splitter = QSplitter(Qt.Orientation.Horizontal if PyQt_version == 6 else Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Add API Key
        left_panel = self.create_add_key_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - API Keys Table and Statistics
        right_panel = self.create_table_and_stats_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Apply some basic styling
        self.apply_styling()
    
    def create_add_key_panel(self):
        """Create the panel for adding new API keys."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel if PyQt_version == 6 else QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Add Key Group
        add_group = QGroupBox("Add New API Key")
        add_layout = QVBoxLayout(add_group)
        
        # Key Name
        add_layout.addWidget(QLabel("API Key Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., gemini 6")
        add_layout.addWidget(self.name_input)
        
        # Provider (fixed to Gemini for now)
        add_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("gemini")
        # Could add more providers later:
        # self.provider_combo.addItems(["gemini", "openai", "anthropic"])
        add_layout.addWidget(self.provider_combo)
        
        # Add Button
        self.add_button = QPushButton("Add API Key")
        self.add_button.clicked.connect(self.add_api_key)
        add_layout.addWidget(self.add_button)
        
        # Instructions
        instructions = QTextEdit()
        instructions.setMaximumHeight(150)
        instructions.setPlainText(
            "Instructions:\n\n"
            "1. Enter a name for your API key (e.g., 'gemini 6')\n"
            "2. Select the provider (currently only Gemini)\n"
            "3. Click 'Add API Key' to register it in the database\n\n"
            "Note: The actual API key value should be added to config.py manually for security."
        )
        instructions.setReadOnly(True)
        add_layout.addWidget(instructions)
        
        layout.addWidget(add_group)
        layout.addStretch()
        
        return panel
    
    def create_table_and_stats_panel(self):
        """Create the panel with API keys table and statistics."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel if PyQt_version == 6 else QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_button = QPushButton("Refresh Data")
        refresh_button.clicked.connect(self.refresh_data)
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)
        
        # API Keys Table
        table_group = QGroupBox("API Keys")
        table_layout = QVBoxLayout(table_group)
        
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(6)
        self.keys_table.setHorizontalHeaderLabels([
            "Name", "Provider", "Status", "Success Rate", "Total Uses", "Last Failure"
        ])
        
        # Make table headers resize to content
        header = self.keys_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents if PyQt_version == 6 
                                   else QHeaderView.ResizeToContents)
        
        table_layout.addWidget(self.keys_table)
        layout.addWidget(table_group)
        
        # Statistics Group
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        layout.addWidget(stats_group)
        
        return panel
    
    def apply_styling(self):
        """Apply basic styling to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QLineEdit, QComboBox {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTableWidget {
                gridline-color: #ddd;
                background-color: white;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
    
    def add_api_key(self):
        """Add a new API key to the database."""
        name = self.name_input.text().strip()
        provider = self.provider_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, "Input Error", "Please enter a name for the API key.")
            return
        
        try:
            # Use asyncio to run the async method
            import asyncio
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                
            async def add_key():
                return await self.api_key_manager.add_key_to_database(name, provider)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(add_key())
            loop.close()
            
            if success:
                QMessageBox.information(self, "Success", f"API key '{name}' added successfully!")
                self.name_input.clear()
                self.load_data()  # Refresh the display
            else:
                QMessageBox.warning(self, "Error", f"Failed to add API key '{name}'. It may already exist.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error adding API key: {str(e)}")
    
    def load_data(self):
        """Load API keys data from database."""
        try:
            # Load keys table
            result = self.supabase.table('api_keys').select('*').eq('provider', 'gemini').order('created_at').execute()
            
            if result.data:
                self.populate_table(result.data)
                self.statusBar().showMessage(f"Loaded {len(result.data)} API keys")
            else:
                self.keys_table.setRowCount(0)
                self.statusBar().showMessage("No API keys found")
            
            # Load statistics asynchronously
            self.load_statistics()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading data: {str(e)}")
            self.statusBar().showMessage("Error loading data")
    
    def load_statistics(self):
        """Load statistics asynchronously."""
        if self.stats_worker and self.stats_worker.isRunning():
            return  # Already loading
        
        self.stats_worker = ApiKeyStatsWorker(self.api_key_manager)
        self.stats_worker.stats_ready.connect(self.update_statistics)
        self.stats_worker.start()
    
    def update_statistics(self, stats):
        """Update the statistics display."""
        if 'error' in stats:
            self.stats_text.setPlainText(f"Error loading statistics: {stats['error']}")
            return
        
        stats_text = f"""Overall Statistics:
Total Keys: {stats.get('total_keys', 0)}
Healthy Keys: {stats.get('healthy_keys', 0)}
Keys in Backoff: {stats.get('keys_in_backoff', 0)}
Total Uses: {stats.get('total_uses', 0)}
Average Success Rate: {stats.get('average_success_rate', 0):.1%}
Average Response Time: {stats.get('average_response_time_ms', 0):.1f}ms
"""
        self.stats_text.setPlainText(stats_text)
    
    def populate_table(self, keys_data):
        """Populate the table with API keys data."""
        self.keys_table.setRowCount(len(keys_data))
        
        for row, key_data in enumerate(keys_data):
            # Name
            self.keys_table.setItem(row, 0, QTableWidgetItem(key_data['name']))
            
            # Provider
            self.keys_table.setItem(row, 1, QTableWidgetItem(key_data['provider']))
            
            # Status
            status = "Active" if key_data['is_active'] else "Inactive"
            status_item = QTableWidgetItem(status)
            if key_data['is_active']:
                status_item.setBackground(Qt.GlobalColor.green if PyQt_version == 6 else Qt.green)
            else:
                status_item.setBackground(Qt.GlobalColor.red if PyQt_version == 6 else Qt.red)
            self.keys_table.setItem(row, 2, status_item)
            
            # For now, we'll show placeholders for success rate, total uses, and last failure
            # These will be populated when we have usage data
            self.keys_table.setItem(row, 3, QTableWidgetItem("N/A"))
            self.keys_table.setItem(row, 4, QTableWidgetItem("0"))
            self.keys_table.setItem(row, 5, QTableWidgetItem("Never"))
    
    def refresh_data(self):
        """Refresh all data."""
        self.load_data()
    
    def closeEvent(self, event):
        """Handle application close event."""
        if self.stats_worker and self.stats_worker.isRunning():
            self.stats_worker.quit()
            self.stats_worker.wait()
        event.accept()


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Todowa API Key Manager")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = ApiKeyManagerGUI()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
