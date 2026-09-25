from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from geosort.settings import _auto_detect_exiftool, _exiftool_works, load_settings, save_settings

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class GeoSortGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Geo-Photosort")
        self.geometry("780x680")
        self.minsize(700, 560)

        self.output_queue: "queue.Queue[str]" = queue.Queue()

        self._build_widgets()
        self.after(100, self._poll_output_queue)
        self.after(200, self._check_exiftool)

    # ---------- UI Aufbau ----------
    def _build_widgets(self):
        pad = {"padx": 12, "pady": 6}

        ctk.CTkLabel(self, text="Geo-Photosort", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(14, 0)
        )
        ctk.CTkLabel(self, text="Fotos & Videos automatisch nach Ort sortieren", text_color="gray60").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10)
        )

        ctk.CTkLabel(self, text="Quellordner:").grid(row=2, column=0, sticky="w", **pad)
        self.source_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.source_var, width=420).grid(row=2, column=1, sticky="ew", **pad)
        ctk.CTkButton(self, text="Durchsuchen...", width=110, command=self._browse_source).grid(row=2, column=2, **pad)

        ctk.CTkLabel(self, text="Zielordner:").grid(row=3, column=0, sticky="w", **pad)
        self.output_var = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.output_var, width=420).grid(row=3, column=1, sticky="ew", **pad)
        ctk.CTkButton(self, text="Durchsuchen...", width=110, command=self._browse_output).grid(row=3, column=2, **pad)

        ctk.CTkLabel(self, text="Modus:").grid(row=4, column=0, sticky="w", **pad)
        self.mode_var = ctk.StringVar(value="copy")
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.grid(row=4, column=1, columnspan=2, sticky="w", **pad)
        ctk.CTkRadioButton(mode_frame, text="Kopieren (Originale bleiben erhalten)", variable=self.mode_var, value="copy").pack(
            side="left", padx=(0, 20)
        )
        ctk.CTkRadioButton(mode_frame, text="Verschieben", variable=self.mode_var, value="move").pack(side="left")

        ctk.CTkLabel(self, text="Bubble-Radius (km):").grid(row=5, column=0, sticky="w", **pad)
        self.bubble_var = ctk.StringVar(value="20")
        ctk.CTkEntry(self, textvariable=self.bubble_var, width=100).grid(row=5, column=1, sticky="w", **pad)

        ctk.CTkLabel(self, text="Sprache der Ortsnamen:").grid(row=6, column=0, sticky="w", **pad)
        self.lang_var = ctk.StringVar(value="de")
        ctk.CTkEntry(self, textvariable=self.lang_var, width=100).grid(row=6, column=1, sticky="w", **pad)

        self.tags_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self,
            text="Ort zusaetzlich in die Dateien schreiben (durchsuchbar in Explorer/Fotos-Apps/Lightroom)",
            variable=self.tags_var,
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=8, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 6))
        self.scan_btn = ctk.CTkButton(btn_frame, text="Scan (Vorschau)", command=self._on_scan, width=160)
        self.scan_btn.pack(side="left", padx=(0, 10))
        self.run_btn = ctk.CTkButton(
            btn_frame, text="Jetzt ausfuehren", command=self._on_run, width=160,
            fg_color="#b5451b", hover_color="#8f3714",
        )
        self.run_btn.pack(side="left", padx=(0, 10))
        self.open_btn = ctk.CTkButton(btn_frame, text="Ordner oeffnen", command=self._open_output, width=140, state="disabled")
        self.open_btn.pack(side="left")

        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.grid(row=9, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 6))

        self.status_var = ctk.StringVar(value="Bereit.")
        ctk.CTkLabel(self, textvariable=self.status_var, text_color="gray60").grid(
            row=10, column=0, columnspan=3, sticky="w", padx=12
        )

        self.log_box = ctk.CTkTextbox(self, width=700, height=260, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.grid(row=11, column=0, columnspan=3, sticky="nsew", padx=12, pady=(6, 12))
        self.log_box.configure(state="disabled")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(11, weight=1)

    # ---------- exiftool ----------
    def _check_exiftool(self):
        settings = load_settings()
        saved = settings.get("exiftool_path")
        if saved and _exiftool_works(saved):
            return
        detected = _auto_detect_exiftool()
        if detected and _exiftool_works(detected):
            settings["exiftool_path"] = detected
            save_settings(settings)
            return
        self._ask_exiftool_path(settings)

    def _ask_exiftool_path(self, settings: dict):
        messagebox.showinfo(
            "exiftool wird benoetigt",
            "exiftool wurde nicht gefunden.\n\n"
            "Installation: winget install -e --id OliverBetz.ExifTool\n"
            "(oder Download von https://exiftool.org)\n\n"
            "Im naechsten Dialog bitte die exiftool.exe auswaehlen.",
        )
        while True:
            path = filedialog.askopenfilename(
                title="exiftool.exe auswaehlen",
                filetypes=[("exiftool", "exiftool*.exe"), ("Alle Dateien", "*.*")],
            )
            if not path:
                messagebox.showwarning("Abgebrochen", "Ohne exiftool kann Geo-Photosort keine Fotos/Videos lesen.")
                return
            if _exiftool_works(path):
                settings["exiftool_path"] = path
                save_settings(settings)
                messagebox.showinfo("Gespeichert", "exiftool-Pfad wurde gespeichert.")
                return
            messagebox.showerror("Ungueltig", "Das ist keine funktionierende exiftool.exe. Bitte erneut versuchen.")

    # ---------- Ordner-Dialoge ----------
    def _browse_source(self):
        path = filedialog.askdirectory(title="Quellordner waehlen")
        if path:
            self.source_var.set(path)
            if not self.output_var.get():
                self.output_var.set(str(Path(path) / "GeoSort"))

    def _browse_output(self):
        path = filedialog.askdirectory(title="Zielordner waehlen")
        if path:
            self.output_var.set(path)

    def _open_output(self):
        out = self.output_var.get()
        if out and Path(out).is_dir():
            os.startfile(out)

    # ---------- Validierung ----------
    def _build_command(self, dry_run: bool) -> Optional[list]:
        source = self.source_var.get().strip()
        if not source or not Path(source).is_dir():
            messagebox.showerror("Fehler", "Bitte einen gueltigen Quellordner waehlen.")
            return None
        output = self.output_var.get().strip() or str(Path(source) / "GeoSort")
        try:
            bubble_km = float(self.bubble_var.get().strip() or "20")
        except ValueError:
            messagebox.showerror("Fehler", "Bubble-Radius muss eine Zahl sein.")
            return None

        cmd = [
            sys.executable, "-m", "geosort",
            "--source", source,
            "--output", output,
            "--bubble-km", str(bubble_km),
            "--mode", self.mode_var.get(),
            "--language", self.lang_var.get().strip() or "de",
        ]
        if self.tags_var.get():
            cmd.append("--write-location-tags")
        if dry_run:
            cmd.append("--dry-run")
        return cmd

    # ---------- Ausfuehrung ----------
    def _on_scan(self):
        cmd = self._build_command(dry_run=True)
        if cmd:
            self._run_command(cmd, label="Scan laeuft ...")

    def _on_run(self):
        mode_txt = "verschoben" if self.mode_var.get() == "move" else "kopiert"
        if not messagebox.askyesno(
            "Wirklich ausfuehren?",
            f"Dateien werden jetzt wirklich {mode_txt}.\n\n"
            f"Quelle: {self.source_var.get()}\nZiel: {self.output_var.get()}\n\nFortfahren?",
        ):
            return
        cmd = self._build_command(dry_run=False)
        if cmd:
            self._run_command(cmd, label="Sortierung laeuft ...")

    def _run_command(self, cmd: list, label: str):
        self._set_running(True, label)
        self._clear_log()
        self.open_btn.configure(state="disabled")

        def worker():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                while True:
                    chunk = proc.stdout.read(256)
                    if not chunk:
                        break
                    self.output_queue.put(chunk)
                proc.wait()
                self.output_queue.put(f"\n__DONE__{proc.returncode}\n")
            except Exception as e:
                self.output_queue.put(f"\nFehler: {e}\n__DONE__1\n")

        threading.Thread(target=worker, daemon=True).start()

    def _set_running(self, running: bool, label: str = ""):
        state = "disabled" if running else "normal"
        self.scan_btn.configure(state=state)
        self.run_btn.configure(state=state)
        if running:
            self.progress.start()
            self.status_var.set(label)
        else:
            self.progress.stop()

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _append_log(self, text: str):
        text = text.replace("\r", "\n")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_output_queue(self):
        try:
            while True:
                chunk = self.output_queue.get_nowait()
                if "__DONE__" in chunk:
                    before, _, rest = chunk.partition("__DONE__")
                    if before:
                        self._append_log(before)
                    code = rest.strip() or "0"
                    self._set_running(False)
                    if code == "0":
                        self.status_var.set("Fertig.")
                        self.open_btn.configure(state="normal")
                    else:
                        self.status_var.set("Fehler - siehe Log unten.")
                else:
                    self._append_log(chunk)
        except queue.Empty:
            pass
        self.after(100, self._poll_output_queue)


def main():
    app = GeoSortGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
