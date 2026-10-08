"""
Szkielet aplikacji: 6 zakładek, w każdej pola:
nośnik, wiadomość, tekst wynikowy.

Uruchomienie:  python stego_app.py
"""

import tkinter as tk
from tkinter import ttk


class Tab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.columnconfigure(0, weight=1)

        self.carrier = self._add_field("Nośnik", row=0, height=8)
        self.message = self._add_field("Wiadomość", row=2, height=3)
        self.result = self._add_field("Tekst wynikowy", row=4, height=8)

        for r in (1, 5):
            self.rowconfigure(r, weight=1)

    def _add_field(self, label, row, height):
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w")
        text = tk.Text(self, height=height, wrap="word")
        text.grid(row=row + 1, column=0, sticky="nsew", pady=(0, 8))
        return text


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steganografia")
        self.geometry("700x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tabs = []
        for i in range(1, 7):
            tab = Tab(notebook)
            notebook.add(tab, text=f"Zakładka {i}")
            self.tabs.append(tab)


if __name__ == "__main__":
    App().mainloop()