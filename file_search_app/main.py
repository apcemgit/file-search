"""
Entry point for the Advanced File Search Pro application.
"""
import tkinter as tk
from .ui import FileSearchApp

def main():
    """Creates the root window and starts the application."""
    root = tk.Tk()
    app = FileSearchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
