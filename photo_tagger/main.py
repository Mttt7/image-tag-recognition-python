import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os

from database import init_db, add_photo, add_tags, get_all_tags, get_photos_by_tag, get_tags_for_photo, get_all_photos, delete_photo
from detector import detect_objects



class PhotoTaggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Tagger")
        self.root.geometry("1200x700")
        self.root.configure(bg="#1e1e2e")

        init_db()
        self.current_photos = []
        self.selected_photo = None
        self.photo_image = None
        self._preview_rotation = 0   # bieżący kąt obrotu podglądu

        self.build_ui()
        self.refresh_tags()
        self.show_all_photos()

    def build_ui(self):
        self.left_panel = tk.Frame(self.root, bg="#2a2a3e", width=200)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)
        self.left_panel.pack_propagate(False)

        tk.Label(self.left_panel, text="TAGI", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Arial", 12, "bold")).pack(pady=(15, 5))

        self.all_btn = tk.Button(self.left_panel, text="Wszystkie",
                                  bg="#45475a", fg="#cdd6f4", relief=tk.FLAT,
                                  font=("Arial", 10), cursor="hand2",
                                  command=self.show_all_photos)
        self.all_btn.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.tags_listbox = tk.Listbox(self.left_panel, bg="#313244", fg="#cdd6f4",
                                        selectbackground="#89b4fa", relief=tk.FLAT,
                                        font=("Arial", 10), borderwidth=0)
        self.tags_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.tags_listbox.bind("<<ListboxSelect>>", self.on_tag_select)

        self.add_btn = tk.Button(self.left_panel, text="+ Dodaj zdjecie",
                                  bg="#89b4fa", fg="#1e1e2e", relief=tk.FLAT,
                                  font=("Arial", 10, "bold"), cursor="hand2",
                                  command=self.add_photo)
        self.add_btn.pack(fill=tk.X, padx=10, pady=10)

        middle_frame = tk.Frame(self.root, bg="#1e1e2e")
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(middle_frame, text="GALERIA", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Arial", 12, "bold")).pack(pady=(5, 10))

        canvas_frame = tk.Frame(middle_frame, bg="#1e1e2e")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#181825", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.gallery_frame = tk.Frame(self.canvas, bg="#181825")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.gallery_frame, anchor="nw")

        self.gallery_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.progress = ttk.Progressbar(middle_frame, mode="indeterminate", length=300)
        self.progress.pack(pady=(0, 2))

        self.status_var = tk.StringVar(value="Gotowy")
        tk.Label(middle_frame, textvariable=self.status_var, bg="#1e1e2e",
                 fg="#6c7086", font=("Arial", 9)).pack(pady=2)

        self.right_panel = tk.Frame(self.root, bg="#2a2a3e", width=350)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        self.right_panel.pack_propagate(False)

        tk.Label(self.right_panel, text="PODGLAD", bg="#2a2a3e", fg="#cdd6f4",
                 font=("Arial", 12, "bold")).pack(pady=(15, 5))

        self.preview_label = tk.Label(self.right_panel, bg="#313244", text="Kliknij zdjecie",
                                       fg="#6c7086")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # --- Przyciski rotacji ---
        rotate_frame = tk.Frame(self.right_panel, bg="#2a2a3e")
        rotate_frame.pack(fill=tk.X, padx=10, pady=(0, 4))

        tk.Button(rotate_frame, text="↺  Obrót L", bg="#45475a", fg="#cdd6f4",
                  relief=tk.FLAT, font=("Arial", 9), cursor="hand2",
                  command=lambda: self._rotate_preview(-90)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))

        tk.Button(rotate_frame, text="Obrót P  ↻", bg="#45475a", fg="#cdd6f4",
                  relief=tk.FLAT, font=("Arial", 9), cursor="hand2",
                  command=lambda: self._rotate_preview(90)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        self.save_rotation_btn = tk.Button(self.right_panel, text="💾  Zapisz obrót do pliku",
                  bg="#313244", fg="#a6e3a1", relief=tk.FLAT, font=("Arial", 9),
                  cursor="hand2", command=self._save_rotation, state=tk.DISABLED)
        self.save_rotation_btn.pack(fill=tk.X, padx=10, pady=(0, 6))

        # --- Tagi ---
        tk.Label(self.right_panel, text="Wykryte obiekty:", bg="#2a2a3e",
                 fg="#cdd6f4", font=("Arial", 10, "bold")).pack(padx=10, anchor=tk.W)

        self.model_label = tk.Label(self.right_panel, text="", bg="#2a2a3e",
                                     fg="#89b4fa", font=("Arial", 8, "italic"))
        self.model_label.pack(padx=10, anchor=tk.W, pady=(0, 2))

        self.tags_text = tk.Text(self.right_panel, bg="#313244", fg="#cdd6f4",
                                  height=6, relief=tk.FLAT, font=("Arial", 10),
                                  state=tk.DISABLED)
        self.tags_text.pack(fill=tk.X, padx=10, pady=(0, 6))

        # --- Przycisk usuwania ---
        self.delete_btn = tk.Button(self.right_panel, text="🗑  Usuń zdjęcie z bazy",
                  bg="#313244", fg="#f38ba8", relief=tk.FLAT, font=("Arial", 9, "bold"),
                  cursor="hand2", command=self._delete_photo, state=tk.DISABLED)
        self.delete_btn.pack(fill=tk.X, padx=10, pady=(0, 10))

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def add_photo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Zdjecia", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if not path:
            return

        self.add_btn.config(state=tk.DISABLED, text="⏳ Analizuje...")
        self.status_var.set("🔍 Analizuję: {}...".format(os.path.basename(path)))
        self.progress.start(10)

        thread = threading.Thread(target=self._process_photo, args=(path,))
        thread.daemon = True
        thread.start()

    def _process_photo(self, path):
        try:
            tags, _ = detect_objects(path)
            photo_id = add_photo(path, model_used="CLIP ViT-B/32")
            add_tags(photo_id, tags)
            self.root.after(0, self._on_photo_processed, path, tags)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_photo_processed(self, path, tags):
        self.progress.stop()
        self.status_var.set("✅ Dodano! Wykryto: {}".format(", ".join(t["tag"] for t in tags)))
        self.add_btn.config(state=tk.NORMAL, text="+ Dodaj zdjecie")
        self.refresh_tags()
        self.show_all_photos()

    def _on_error(self, error):
        self.progress.stop()
        messagebox.showerror("Blad", "Nie udalo sie przetworzyc zdjecia:\n{}".format(error))
        self.add_btn.config(state=tk.NORMAL, text="+ Dodaj zdjecie")
        self.status_var.set("❌ Blad przetwarzania")

    def refresh_tags(self):
        self.tags_listbox.delete(0, tk.END)
        for tag in get_all_tags():
            self.tags_listbox.insert(tk.END, "  {}".format(tag))

    def on_tag_select(self, event):
        selection = self.tags_listbox.curselection()
        if not selection:
            return
        tag = self.tags_listbox.get(selection[0]).strip()
        photos = get_photos_by_tag(tag)
        self.display_photos(photos)
        self.status_var.set("Tag: {} ({} zdjec)".format(tag, len(photos)))

    def show_all_photos(self):
        photos = get_all_photos()
        self.display_photos(photos)
        self.status_var.set("Wszystkie zdjecia: {}".format(len(photos)))

    def display_photos(self, paths):
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        self.current_photos = []
        cols = 3

        for i, path in enumerate(paths):
            if not os.path.exists(path):
                continue
            try:
                img = Image.open(path)
                img.thumbnail((150, 150))
                photo = ImageTk.PhotoImage(img)
                self.current_photos.append(photo)

                row, col = divmod(i, cols)
                frame = tk.Frame(self.gallery_frame, bg="#181825", cursor="hand2")
                frame.grid(row=row, column=col, padx=5, pady=5)

                lbl = tk.Label(frame, image=photo, bg="#181825")
                lbl.pack()

                name_lbl = tk.Label(frame, text=os.path.basename(path)[:20],
                                     bg="#181825", fg="#6c7086", font=("Arial", 8))
                name_lbl.pack()

                lbl.bind("<Button-1>", lambda e, p=path: self.show_preview(p))
                frame.bind("<Button-1>", lambda e, p=path: self.show_preview(p))

            except Exception:
                pass

    def show_preview(self, path):
        """Wyświetla zdjęcie z bazy + tagi + model z DB."""
        self.selected_photo = path
        self._preview_rotation = 0
        self._render_preview()

        self.delete_btn.config(state=tk.NORMAL)
        self.save_rotation_btn.config(state=tk.DISABLED)

        tags, model_used = get_tags_for_photo(path)
        self.model_label.config(text="Model: {}".format(model_used) if model_used != "unknown" else "")

        self.tags_text.config(state=tk.NORMAL)
        self.tags_text.delete(1.0, tk.END)
        for t in tags:
            self.tags_text.insert(tk.END, "- {} ({:.0%})\n".format(t["tag"], t["confidence"]))
        self.tags_text.config(state=tk.DISABLED)

    def _render_preview(self):
        """Renderuje podgląd z aktualnym kątem obrotu."""
        if not self.selected_photo:
            return
        try:
            img = Image.open(self.selected_photo).convert("RGB")
            if self._preview_rotation != 0:
                img = img.rotate(-self._preview_rotation, expand=True)
            panel_w = max(self.right_panel.winfo_width() - 20, 300)
            img.thumbnail((panel_w, 300))
            photo = ImageTk.PhotoImage(img)
            self.photo_image = photo
            self.preview_label.config(image=photo, text="")
        except Exception:
            self.preview_label.config(image="", text="Błąd ładowania")

    def _rotate_preview(self, degrees):
        """Obraca podgląd o podany kąt (nie zapisuje do pliku)."""
        if not self.selected_photo:
            return
        self._preview_rotation = (self._preview_rotation + degrees) % 360
        self._render_preview()
        self.save_rotation_btn.config(
            state=tk.NORMAL if self._preview_rotation != 0 else tk.DISABLED
        )

    def _save_rotation(self):
        """Zapisuje obrót trwale do pliku na dysku."""
        if not self.selected_photo or self._preview_rotation == 0:
            return
        try:
            img = Image.open(self.selected_photo)
            img = img.rotate(-self._preview_rotation, expand=True)
            img.save(self.selected_photo)
            self._preview_rotation = 0
            self.save_rotation_btn.config(state=tk.DISABLED)
            self.status_var.set("✅ Obrót zapisany: {}".format(os.path.basename(self.selected_photo)))
            self.show_all_photos()
        except Exception as e:
            messagebox.showerror("Błąd", "Nie udało się zapisać obrotu:\n{}".format(e))

    def _delete_photo(self):
        if not self.selected_photo:
            return
        path = self.selected_photo
        name = os.path.basename(path)

        if not messagebox.askyesno("Usuń zdjęcie", "Usunąć '{}' z bazy?".format(name)):
            return

        delete_photo(path)
        self.status_var.set("🗑 Usunięto z bazy: {}".format(name))

        self.selected_photo = None
        self._preview_rotation = 0
        self.preview_label.config(image="", text="Kliknij zdjecie")
        self.photo_image = None
        self.delete_btn.config(state=tk.DISABLED)
        self.save_rotation_btn.config(state=tk.DISABLED)
        self.tags_text.config(state=tk.NORMAL)
        self.tags_text.delete(1.0, tk.END)
        self.tags_text.config(state=tk.DISABLED)
        self.refresh_tags()
        self.show_all_photos()


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoTaggerApp(root)
    root.mainloop()
