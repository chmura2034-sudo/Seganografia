"""
Aplikacja do steganografii: każda metoda = osobna zakładka,
a w niej podzakładki Kodowanie / Dekodowanie.

Uruchomienie:  python stego_app.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import LSC   # <-- plik z funkcjami (LSC.py w tym samym folderze)


# ---------------------------------------------------------------
#  Podzakładki
# ---------------------------------------------------------------
class BaseSubTab(ttk.Frame):
    """Wspólne elementy: wybór nośnika, tryb przesunięcia, wynik."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.columnconfigure(0, weight=1)
        self._row = 0

        ttk.Label(self, text="Nośnik (plik PDF)").grid(row=self._next(), column=0, sticky="w")
        path_frame = ttk.Frame(self)
        path_frame.grid(row=self._next(), column=0, sticky="ew", pady=(0, 8))
        path_frame.columnconfigure(0, weight=1)
        self.carrier = ttk.Entry(path_frame)
        self.carrier.grid(row=0, column=0, sticky="ew")
        ttk.Button(path_frame, text="Wybierz…", command=self.choose_carrier).grid(
            row=0, column=1, padx=(6, 0))

    def _next(self):
        r = self._row
        self._row += 1
        return r

    def build_shift(self):
        frame = ttk.Frame(self)
        frame.grid(row=self._next(), column=0, sticky="w", pady=(0, 8))
        ttk.Label(frame, text="Tryb przesunięcia:").pack(side="left")
        self.shift = ttk.Combobox(frame, values=[0, 1], width=3, state="readonly")
        self.shift.current(0)
        self.shift.pack(side="left", padx=6)

    def build_result(self, label="Tekst wynikowy"):
        ttk.Label(self, text=label).grid(row=self._next(), column=0, sticky="w", pady=(8, 0))
        r = self._next()
        self.result = tk.Text(self, height=8, wrap="word")
        self.result.grid(row=r, column=0, sticky="nsew")
        self.rowconfigure(r, weight=1)

    def choose_carrier(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if path:
            self.carrier.delete(0, "end")
            self.carrier.insert(0, path)

    def set_result(self, text):
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)

    def get_carrier(self):
        carrier = self.carrier.get().strip()
        if not carrier:
            messagebox.showwarning("Brak pliku", "Wybierz plik PDF.")
            return None
        return carrier


class EncodeTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)

        ttk.Label(self, text="Wiadomość").grid(row=self._next(), column=0, sticky="w")
        self.message = tk.Text(self, height=3, wrap="word")
        self.message.grid(row=self._next(), column=0, sticky="ew", pady=(0, 8))

        self.build_shift()
        ttk.Button(self, text="Zakoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result()

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        message = self.message.get("1.0", "end").strip()
        if not message:
            messagebox.showwarning("Brak wiadomości", "Wpisz wiadomość.")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not out:
            return

        try:
            LSC.encode(carrier, message, int(self.shift.get()), out)
            self.set_result(f"Zapisano: {out}")
        except UnicodeEncodeError:
            messagebox.showerror("Błąd", "Wiadomość może zawierać tylko znaki ASCII.")
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


class DecodeTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)

        self.build_shift()
        ttk.Button(self, text="Odkoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result("Odczytana wiadomość")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        try:
            secret = LSC.decode(carrier, int(self.shift.get()))
            self.set_result(secret)
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


# ---------------------------------------------------------------
#  Zakładka metody = notebook z Kodowaniem i Dekodowaniem
# ---------------------------------------------------------------
class MethodTab(ttk.Frame):
    def __init__(self, parent, encode_cls=EncodeTab, decode_cls=DecodeTab):
        super().__init__(parent)
        inner = ttk.Notebook(self)
        inner.pack(fill="both", expand=True)
        inner.add(encode_cls(inner), text="Kodowanie")
        inner.add(decode_cls(inner), text="Dekodowanie")


# ---------------------------------------------------------------
#  Aplikacja
# ---------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steganografia")
        self.geometry("700x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # nazwa zakładki -> klasa zakładki; kolejne metody dopisujesz tutaj
        METHODS = {
            "LSC": MethodTab,
        }
        for name, cls in METHODS.items():
            notebook.add(cls(notebook), text=name)


if __name__ == "__main__":
    App().mainloop()