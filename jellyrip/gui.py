"""Interface graphique JellyRip (Tkinter, inclus avec Python)."""

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import pipeline
from .config import load, save
from .disc import scan
from .runner import Cancelled, Runner


class JellyRipGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("JellyRip — DVD/CD vers Jellyfin")
        root.geometry("860x640")
        self.cfg = load()
        self.discs: list = []
        self.job_thread: threading.Thread | None = None
        self.runner: Runner | None = None
        self.log_queue: queue.Queue = queue.Queue()

        self._build_widgets()
        self.refresh_discs()
        root.after(100, self._drain_log)

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Button(top, text="Actualiser les lecteurs",
                   command=self.refresh_discs).pack(side="left")
        ttk.Label(top, text="Dossier de sortie :").pack(side="left", padx=(16, 4))
        ttk.Label(top, text=self.cfg["output_dir"], relief="groove",
                  width=40).pack(side="left")
        ttk.Button(top, text="Parcourir...",
                   command=self.choose_output).pack(side="left", padx=4)

        mid = ttk.LabelFrame(self.root, text="Disques détectés")
        mid.pack(fill="both", expand=True, **pad)
        self.disc_list = tk.Listbox(mid, height=6)
        self.disc_list.pack(fill="both", expand=True, padx=4, pady=4)

        mode = ttk.LabelFrame(self.root, text="Action")
        mode.pack(fill="x", **pad)
        self.mode = tk.StringVar(value="mp4")
        for value, label in (
            ("iso", "Sauvegarder en .iso (copie complète)"),
            ("mkv", "Extraire en .mkv (MakeMKV)"),
            ("mp4", "DVD → .mp4 optimisé Jellyfin"),
            ("mp3", "CD → .mp3 optimisé Jellyfin"),
        ):
            ttk.Radiobutton(mode, text=label, value=value,
                            variable=self.mode).pack(anchor="w")

        opts = ttk.LabelFrame(self.root, text="Qualité (image, son, GPU AMD)")
        opts.pack(fill="x", **pad)
        self.hw = tk.BooleanVar(value=self.cfg["hw_accel"])
        ttk.Checkbutton(opts, text="Accélération GPU (AMD VAAPI/AMF)",
                        variable=self.hw).grid(row=0, column=0, sticky="w")
        ttk.Label(opts, text="Codec :").grid(row=0, column=1, sticky="e")
        self.codec = tk.StringVar(value=self.cfg["video_codec"])
        ttk.Combobox(opts, textvariable=self.codec, state="readonly",
                     values=["h264", "hevc"], width=8).grid(row=0, column=2)
        ttk.Label(opts, text="Upscale :").grid(row=0, column=3, sticky="e")
        self.upscale = tk.StringVar(value=self.cfg["upscale_target"])
        ttk.Combobox(opts, textvariable=self.upscale, state="readonly",
                     values=["none", "1080", "2160"], width=8).grid(row=0, column=4)

        self.denoise = tk.BooleanVar(value=self.cfg["denoise"])
        ttk.Checkbutton(opts, text="Débruitage", variable=self.denoise
                        ).grid(row=1, column=0, sticky="w")
        self.sharpen = tk.BooleanVar(value=self.cfg["sharpen"])
        ttk.Checkbutton(opts, text="Netteté", variable=self.sharpen
                        ).grid(row=1, column=1, sticky="w")
        self.loudnorm = tk.BooleanVar(value=self.cfg["loudnorm"])
        ttk.Checkbutton(opts, text="Son normalisé (EBU R128)",
                        variable=self.loudnorm).grid(row=1, column=2, sticky="w")
        self.ai = tk.BooleanVar(value=self.cfg["ai_upscale"])
        ttk.Checkbutton(opts, text="Upscale IA (très long)",
                        variable=self.ai).grid(row=1, column=3, columnspan=2,
                                               sticky="w")

        meta = ttk.Frame(self.root)
        meta.pack(fill="x", **pad)
        ttk.Label(meta, text="Titre :").pack(side="left")
        self.title_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.title_var, width=32).pack(side="left",
                                                                   padx=4)
        ttk.Label(meta, text="Année :").pack(side="left")
        self.year_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.year_var, width=6).pack(side="left",
                                                                 padx=4)

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", **pad)
        self.start_btn = ttk.Button(actions, text="Lancer",
                                    command=self.start_job)
        self.start_btn.pack(side="left")
        ttk.Button(actions, text="Annuler", command=self.cancel_job
                   ).pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, length=300, maximum=100)
        self.progress.pack(side="left", padx=8, fill="x", expand=True)

        log_frame = ttk.LabelFrame(self.root, text="Journal")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=12, state="disabled",
                                wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def choose_output(self):
        directory = filedialog.askdirectory(initialdir=self.cfg["output_dir"])
        if directory:
            self.cfg["output_dir"] = directory
            save(self.cfg)
            self._refresh_output_label()

    def _refresh_output_label(self):
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("relief") == "groove":
                        child.config(text=self.cfg["output_dir"])

    def refresh_discs(self):
        self.discs = scan()
        self.disc_list.delete(0, tk.END)
        for disc in self.discs:
            self.disc_list.insert(tk.END, str(disc))
        if not self.discs:
            self.disc_list.insert(tk.END, "Aucun lecteur optique détecté")

    def _selected_disc(self):
        index = self.disc_list.curselection()
        if not index or not self.discs:
            messagebox.showwarning("JellyRip", "Sélectionnez d'abord un disque.")
            return None
        disc = self.discs[index[0]]
        if not disc.media:
            if not messagebox.askyesno(
                "JellyRip",
                f"Aucun disque détecté dans {disc.device}. Continuer quand même ?"
            ):
                return None
        return disc

    def start_job(self):
        if self.job_thread and self.job_thread.is_alive():
            messagebox.showwarning("JellyRip", "Un travail est déjà en cours.")
            return
        disc = self._selected_disc()
        if disc is None:
            return
        self._sync_cfg()
        save(self.cfg)
        mode = self.mode.get()
        title, year = self.title_var.get().strip(), self.year_var.get().strip()
        self.runner = Runner(log_cb=self.log_queue.put,
                             progress_cb=lambda p: self.log_queue.put(
                                 ("__progress__", p)))
        work = {
            "iso": lambda: pipeline.job_backup_iso(self.cfg, disc, self.runner,
                                                   title, year),
            "mkv": lambda: pipeline.job_rip_mkv(self.cfg, disc, self.runner),
            "mp4": lambda: pipeline.job_dvd_to_mp4(self.cfg, disc, self.runner,
                                                   title, year),
            "mp3": lambda: pipeline.job_cd_to_mp3(self.cfg, disc, self.runner),
        }[mode]

        def worker():
            try:
                result = work()
                self.log_queue.put(f"✔ Terminé : {result}")
            except Cancelled:
                self.log_queue.put("✖ Annulé")
            except Exception as exc:
                self.log_queue.put(f"✖ Erreur : {exc}")

        self.job_thread = threading.Thread(target=worker, daemon=True)
        self.job_thread.start()

    def cancel_job(self):
        if self.runner:
            self.runner.cancel()

    def _sync_cfg(self):
        self.cfg.update({
            "hw_accel": self.hw.get(),
            "video_codec": self.codec.get(),
            "upscale_target": self.upscale.get(),
            "denoise": self.denoise.get(),
            "sharpen": self.sharpen.get(),
            "loudnorm": self.loudnorm.get(),
            "ai_upscale": self.ai.get(),
        })

    def _drain_log(self):
        while not self.log_queue.empty():
            item = self.log_queue.get_nowait()
            if isinstance(item, tuple) and item[0] == "__progress__":
                self.progress["value"] = item[1]
                continue
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, str(item) + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(100, self._drain_log)


def run_gui():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass
    JellyRipGUI(root)
    root.mainloop()
