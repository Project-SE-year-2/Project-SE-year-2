import sys
from PyQt5.QtWidgets import QApplication

# Import the main scaffold window
from src.main_window import MainWindow

def main():
    """
    Main entry point for the PyQt5 desktop application.
    Initializes the application loop and displays the MainWindow.
    """
    # Initialize the core application event loop
    app = QApplication(sys.argv)
    
    # Instantiate and display the main interface
    window = MainWindow()
    window.showMaximized()
    
    # Execute the application and wait for the user to close the window
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()