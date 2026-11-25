import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import os
import LSC
import Roy
import SOTE 
import Taha
import Kornel_I_Radek as KornelRadek

class BaseSubTab(ttk.Frame):
    """Wspólne elementy: wybór nośnika, tryb przesunięcia, wynik."""

    def __init__(self, parent):
        super().__init__(parent, padding=10)
        self.columnconfigure(0, weight=1)
        self._row = 0

        self.carrier_label = ttk.Label(self, text="Nośnik (plik PDF)")
        self.carrier_label.grid(row=self._next(), column=0, sticky="w")
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


# ── LSC ───────────────────────────────────────────────────────────────────────

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


# ── Roy i Manasmita ───────────────────────────────────────────────────────────

class DocxSubTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.carrier_label.configure(text="Nośnik (plik DOCX)")

    def choose_carrier(self):
        path = filedialog.askopenfilename(filetypes=[("Word", "*.docx")])
        if path:
            self.carrier.delete(0, "end")
            self.carrier.insert(0, path)

    def get_carrier(self):
        carrier = self.carrier.get().strip()
        if not carrier:
            messagebox.showwarning("Brak pliku", "Wybierz plik DOCX.")
            return None
        return carrier


class RoyEncodeTab(DocxSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Wiadomość").grid(row=self._next(), column=0, sticky="w")
        self.message = tk.Text(self, height=3, wrap="word")
        self.message.grid(row=self._next(), column=0, sticky="ew", pady=(0, 8))
        ttk.Button(self, text="Zakoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result()

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        message = self.message.get("1.0", "end-1c")
        if not message:
            messagebox.showwarning("Brak wiadomości", "Wpisz wiadomość.")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".docx", filetypes=[("Word", "*.docx")])
        if not out:
            return
        try:
            Roy.encode(carrier, message, out)
            self.set_result(f"Zapisano: {out}")
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


class RoyDecodeTab(DocxSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Button(self, text="Odkoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result("Odczytana wiadomość")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        try:
            self.set_result(Roy.decode(carrier))
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


# ── Taha, Hammad i Selim ─────────────────────────────────────────────────────

class TextSubTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.carrier_label.configure(text="Nośnik (plik TXT UTF-8 z tekstem arabskim)")

    def choose_carrier(self):
        path = filedialog.askopenfilename(filetypes=[("Plik tekstowy UTF-8", "*.txt")])
        if path:
            self.carrier.delete(0, "end")
            self.carrier.insert(0, path)

    def get_carrier(self):
        carrier = self.carrier.get().strip()
        if not carrier:
            messagebox.showwarning("Brak pliku", "Wybierz plik TXT UTF-8.")
            return None
        return carrier


class TahaEncodeTab(TextSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Label(self, text="Wiadomość").grid(row=self._next(), column=0, sticky="w")
        self.message = tk.Text(self, height=3, wrap="word")
        self.message.grid(row=self._next(), column=0, sticky="ew", pady=(0, 8))
        ttk.Button(self, text="Zakoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result()

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        message = self.message.get("1.0", "end-1c")
        if not message:
            messagebox.showwarning("Brak wiadomości", "Wpisz wiadomość.")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[("Plik tekstowy UTF-8", "*.txt")])
        if not out:
            return
        try:
            Taha.encode(carrier, message, out)
            self.set_result(f"Zapisano: {out}")
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


class TahaDecodeTab(TextSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        ttk.Button(self, text="Odkoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result("Odczytana wiadomość")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        try:
            self.set_result(Taha.decode(carrier))
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))




class SOTEEncodeTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)

        ttk.Label(self, text="Wiadomość").grid(row=self._next(), column=0, sticky="w")
        self.message = tk.Text(self, height=3, wrap="word")
        self.message.grid(row=self._next(), column=0, sticky="ew", pady=(0, 8))

        ttk.Button(self, text="Zakoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result()

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        message = self.message.get("1.0", "end-1c")
        if not message:
            messagebox.showwarning("Brak wiadomości", "Wpisz wiadomość.")
            return
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        try:
            SOTE.encode(carrier, message, out)
            self.set_result(f"Zapisano: {out}")
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


class SOTEDecodeTab(BaseSubTab):
    def __init__(self, parent):
        super().__init__(parent)

        ttk.Button(self, text="Odkoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result("Odczytana wiadomość")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        try:
            self.set_result(SOTE.decode(carrier))
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))

# ── Kornel i Radek ────────────────────────────────────────────────────────────

class KRSubTab(BaseSubTab):
    FILETYPES = [("Word", "*.docx")]
    EXT = ".docx"
    TYPE_NAME = "DOCX"

    def __init__(self, parent):
        super().__init__(parent)
        self.carrier_label.configure(text=f"Nośnik (plik {self.TYPE_NAME})")

    def choose_carrier(self):
        path = filedialog.askopenfilename(filetypes=self.FILETYPES)
        if path:
            self.carrier.delete(0, "end")
            self.carrier.insert(0, path)

    def get_carrier(self):
        carrier = self.carrier.get().strip()
        if not carrier:
            messagebox.showwarning("Brak pliku", f"Wybierz plik {self.TYPE_NAME}.")
            return None
        return carrier

    def build_shift_bits(self):
        frame = ttk.Frame(self)
        frame.grid(row=self._next(), column=0, sticky="w", pady=(0, 8))
        ttk.Label(frame, text="Bity przesunięcia linii:").pack(side="left")
        self.shift_bits = ttk.Combobox(frame, values=[1, 2, 3, 4], width=3,
                                       state="readonly")
        self.shift_bits.set(3)
        self.shift_bits.pack(side="left", padx=6)


class KREncodeTab(KRSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        self._cap_key = None
        self._cap = None

        ttk.Label(self, text="Wiadomość").grid(row=self._next(), column=0, sticky="w")
        self.message = tk.Text(self, height=3, wrap="word")
        self.message.grid(row=self._next(), column=0, sticky="ew")

        # licznik: długość wiadomości / pojemność nośnika
        self.info = ttk.Label(self, text="")
        self.info.grid(row=self._next(), column=0, sticky="w", pady=(2, 8))

        self.build_shift_bits()
        ttk.Button(self, text="Zakoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result()

        # odświeżanie licznika
        self.message.bind("<<Modified>>", self._on_message_change)
        self.shift_bits.bind("<<ComboboxSelected>>", self.update_info)
        self.carrier.bind("<KeyRelease>", self.update_info)
        self.carrier.bind("<FocusOut>", self.update_info)
        self.update_info()

    def choose_carrier(self):
        super().choose_carrier()
        self.update_info()

    def _on_message_change(self, _event=None):
        self.message.edit_modified(False)
        self.update_info()

    def _message_bytes(self):
        return len(self.message.get("1.0", "end-1c").encode("utf-8"))

    def _capacity(self):
        """Pojemność nośnika w bajtach (zapamiętywana) lub None."""
        path = self.carrier.get().strip()
        if not path or not os.path.isfile(path):
            return None
        key = (path, os.path.getmtime(path), int(self.shift_bits.get()))
        if key != self._cap_key:
            try:
                self._cap = KornelRadek.capacity(path, key[2])
            except Exception:
                self._cap = None
            self._cap_key = key
        return self._cap

    def update_info(self, _event=None):
        length = self._message_bytes()
        cap = self._capacity()
        if cap is None:
            self.info.configure(text=f"Długość wiadomości: {length} B",
                                foreground="")
        else:
            too_long = length > cap
            self.info.configure(
                text=f"Długość wiadomości: {length} B / pojemność nośnika: {cap} B"
                     + ("  – za długa!" if too_long else ""),
                foreground="red" if too_long else "")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        message = self.message.get("1.0", "end-1c")
        if not message:
            messagebox.showwarning("Brak wiadomości", "Wpisz wiadomość.")
            return

        # sprawdzenie długości przed wyborem pliku wynikowego
        length = len(message.encode("utf-8"))
        cap = self._capacity()
        if cap is None:
            messagebox.showerror("Błąd", "Nie można odczytać pliku nośnika "
                                         "(czy to poprawny plik DOCX?).")
            return
        if length > cap:
            messagebox.showerror(
                "Za długa wiadomość",
                f"Wiadomość ma {length} B, a nośnik pomieści najwyżej {cap} B.\n\n"
                f"Skróć wiadomość, wybierz dłuższy dokument "
                f"lub zwiększ liczbę bitów przesunięcia.")
            return

        out = filedialog.asksaveasfilename(
            defaultextension=self.EXT, filetypes=self.FILETYPES)
        if not out:
            return
        try:
            KornelRadek.encode(carrier, message, out, int(self.shift_bits.get()))
            self.set_result(f"Zapisano: {out}\n"
                            f"Ukryto {length} B z {cap} B dostępnych.")
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))


class KRDecodeTab(KRSubTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.build_shift_bits()
        ttk.Button(self, text="Odkoduj", command=self.run).grid(
            row=self._next(), column=0, sticky="w")
        self.build_result("Odczytana wiadomość")

    def run(self):
        carrier = self.get_carrier()
        if carrier is None:
            return
        try:
            secret = KornelRadek.decode(carrier, int(self.shift_bits.get()))
            self.set_result(secret)
        except ValueError as e:
            messagebox.showerror("Błąd", str(e))
        except Exception as e:
            messagebox.showerror("Nieoczekiwany błąd", str(e))

# ── Struktura zakładek ────────────────────────────────────────────────────────

class MethodTab(ttk.Frame):
    def __init__(self, parent, encode_cls=EncodeTab, decode_cls=DecodeTab):
        super().__init__(parent)
        inner = ttk.Notebook(self)
        inner.pack(fill="both", expand=True)
        inner.add(encode_cls(inner), text="Kodowanie")
        inner.add(decode_cls(inner), text="Dekodowanie")


class RoyMethodTab(MethodTab):
    def __init__(self, parent):
        super().__init__(parent, RoyEncodeTab, RoyDecodeTab)


class SOTEMethodTab(MethodTab):
    def __init__(self, parent):
        super().__init__(parent, SOTEEncodeTab, SOTEDecodeTab)


class TahaMethodTab(MethodTab):
    def __init__(self, parent):
        super().__init__(parent, TahaEncodeTab, TahaDecodeTab)

class KRMethodTab(MethodTab):
    def __init__(self, parent):
        super().__init__(parent, KREncodeTab, KRDecodeTab)

# ── Pomoc (ikona + dymek) ─────────────────────────────────────────────────────

HELP_TEXTS = {
    "LSC": (
        "LSC – ukrywanie wiadomości w pliku PDF\n\n"
        "Kodowanie:\n"
        "1. Wybierz plik PDF (nośnik).\n"
        "2. Wpisz wiadomość (tylko znaki ASCII).\n"
        "3. Wybierz tryb przesunięcia (0 lub 1).\n"
        "4. Kliknij „Zakoduj” i wskaż miejsce zapisu.\n\n"
        "Dekodowanie:\n"
        "Wybierz PDF, ustaw ten sam tryb przesunięcia\n"
        "co przy kodowaniu i kliknij „Odkoduj”."
    ),
    "Roy i Manasmita": (
        "Roy i Manasmita – ukrywanie wiadomości w pliku DOCX\n\n"
        "Kodowanie:\n"
        "1. Wybierz plik DOCX (nośnik).\n"
        "2. Wpisz wiadomość.\n"
        "3. Kliknij „Zakoduj” i wskaż miejsce zapisu.\n\n"
        "Dekodowanie:\n"
        "Wybierz zakodowany plik DOCX i kliknij „Odkoduj”."
    ),
    "Spacje na końcu linii": (
        "Spacje na końcu linii – ukrywanie wiadomości w pliku PDF\n\n"
        "Kodowanie:\n"
        "1. Wybierz plik PDF (nośnik).\n"
        "2. Wpisz wiadomość.\n"
        "3. Kliknij „Zakoduj” i wskaż miejsce zapisu.\n\n"
        "Dekodowanie:\n"
        "Wybierz zakodowany plik PDF i kliknij „Odkoduj”."
    ),
    "Taha, Hammad i Selim": (
        "Taha, Hammad i Selim – arabski tekst UTF-8\n\n"
        "Kodowanie:\n"
        "1. Wybierz plik TXT UTF-8 zawierający tekst arabski.\n"
        "2. Wpisz wiadomość.\n"
        "3. Kliknij „Zakoduj” i wskaż plik wynikowy.\n\n"
        "Algorytm zapisuje bity przez Kashidę oraz trzy małe\n"
        "spacje Unicode między arabskimi wyrazami.\n\n"
        "Dekodowanie:\n"
        "Wybierz zakodowany plik TXT i kliknij „Odkoduj”."
    ),
        "Kornel i Radek": (
        "Kornel i Radek – ukrywanie wiadomości w pliku DOCX\n\n"
        "Kodowanie:\n"
        "1. Wybierz plik DOCX (nośnik).\n"
        "2. Wpisz wiadomość.\n"
        "3. Wybierz liczbę bitów przesunięcia linii (1–4).\n"
        "4. Kliknij „Zakoduj” i wskaż miejsce zapisu.\n\n"
        "Bity są zapisywane przez przesunięcie linii w górę/dół,\n"
        "wąskie spacje między słowami oraz spacje na końcu linii.\n\n"
        "Dekodowanie:\n"
        "Wybierz zakodowany plik DOCX, ustaw tę samą liczbę bitów\n"
        "przesunięcia co przy kodowaniu i kliknij „Odkoduj”."
    ),
}


class HelpIcon(tk.Label):
    """Ikona PNG w rogu okna; po najechaniu pokazuje dymek z pomocą."""

    def __init__(self, parent, image_path, get_text, max_size=28):
        self._get_text = get_text
        self._tip = None
        self._img = None

        try:
            img = tk.PhotoImage(file=image_path)
            factor = max(1, max(img.width(), img.height()) // max_size)
            self._img = img.subsample(factor, factor) if factor > 1 else img
            super().__init__(parent, image=self._img, cursor="question_arrow", bd=0)
        except tk.TclError:
            # brak pliku PNG -> awaryjnie zwykły znak zapytania
            super().__init__(parent, text="?", cursor="question_arrow",
                             font=("Segoe UI", 12, "bold"), width=2,
                             relief="solid", bd=1)

        self.bind("<Enter>", self._show)
        self.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self._tip:
            return
        self._tip = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        tk.Label(tw, text=self._get_text(), justify="left", anchor="w",
                 background="#ffffe0", relief="solid", borderwidth=1,
                 padx=10, pady=8).pack()
        tw.update_idletasks()
        # dymek wyrównany do prawej krawędzi ikony, tuż pod nią
        x = self.winfo_rootx() + self.winfo_width() - tw.winfo_reqwidth()
        y = self.winfo_rooty() + self.winfo_height() + 4
        tw.wm_geometry(f"+{max(x, 0)}+{y}")

    def _hide(self, _event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Aplikacja ─────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steganografia")
        self.geometry("820x600")

        self.notebook = notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        METHODS = {
            "LSC":                  MethodTab,
            "Roy i Manasmita":      RoyMethodTab,
            "Spacje na końcu linii": SOTEMethodTab,
            "Taha, Hammad i Selim": TahaMethodTab,
            "Kornel i Radek":        KRMethodTab,
        }
        for name, cls in METHODS.items():
            notebook.add(cls(notebook), text=name)

        # ikona pomocy w prawym górnym rogu
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help.png")
        self.help_icon = HelpIcon(self, icon_path, self._current_help, max_size=24)
        self.help_icon.place(relx=1.0, x=-12, y=10, anchor="ne")
        self.help_icon.lift()

    def _current_help(self):
        name = self.notebook.tab(self.notebook.select(), "text")
        return HELP_TEXTS.get(name, "Wybierz metodę i plik nośnika.")


if __name__ == "__main__":
    App().mainloop()
