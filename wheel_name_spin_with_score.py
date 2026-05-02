#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog, ttk, simpledialog
import random
import json
import os
import sys
import math
import csv
from datetime import datetime

# ---------------------------------------------------------------------------
# APP SETTINGS — change these to customize the app
# ---------------------------------------------------------------------------
SCHOOL_NAME = r"\(^ω^\ ) Wheel Spinner with Score System ( /^ω^)/"   # title shown on main menu
MAX_BACKUPS = 5   # how many backup saves to keep per class — old ones get auto-deleted

# Always resolve file paths relative to where THIS script file lives.
# This prevents data loss when launching from taskbar vs file manager vs terminal.
# sys.argv[0] = path to this script file
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))


class ClassroomWheel:
    def __init__(self, master):
        self.root = master
        self.root.title("Wheel Spinner with Score System By : Yosef Setiawan")
        self.root.geometry("1400x900")   # default window size — change if needed
        self.root.configure(bg="#1a1a1a")   # dark background color

        # F11 toggles fullscreen — useful for classroom projector use
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.is_fullscreen = False

        # --- Core data ---
        self.students   = {}    # dict of {student_name: score} — main data store
        self.attendance = {}    # dict of {student_name: True/False} — False = excluded from wheel
        self.history    = []    # list of last 5 winner names shown above scoreboard
        self.filename   = ""    # full path to the currently open .json class file
        self.sort_mode  = "name"   # "name" = alphabetical, "score" = highest first

        self.current_student = None   # whoever the wheel last landed on — used by point buttons
        self.angle           = 0      # current wheel rotation in degrees
        self.is_spinning     = False  # True while wheel is animating — blocks double-spins
        self.temp_removed    = []     # placeholder for future "skip this round" feature
        self.center_face     = "(´･ω･`)"   # emoji shown in wheel center — changes while spinning

        self.show_main_menu()   # start by showing the class selection screen

    # =========================================================================
    # MAIN MENU — shown on startup and when switching classes
    # =========================================================================
    def show_main_menu(self):
        """Clear everything and show the class selection screen."""
        # Destroy all existing widgets so we can rebuild the screen fresh
        for widget in self.root.winfo_children():
            widget.destroy()

        # Center the menu frame in the middle of the window
        menu_frame = tk.Frame(self.root, bg="#1a1a1a")
        menu_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Title and author label
        tk.Label(menu_frame, text=SCHOOL_NAME,
                 font=("Arial", 28, "bold"), fg="#00d2ff", bg="#1a1a1a").pack(pady=20)
        tk.Label(menu_frame, text="By : Yosef Setiawan",
                 font=("Arial", 12), fg="#555", bg="#1a1a1a").pack()

        list_frame = tk.Frame(menu_frame, bg="#1a1a1a")
        list_frame.pack(pady=20)

        # Scan BASE_DIR for all .json files — each one is a class profile
        json_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.json')]

        for file in json_files:
            row = tk.Frame(list_frame, bg="#1a1a1a", pady=2)
            row.pack(fill=tk.X)
            clean_name = file.replace('.json', '')   # show name without .json extension

            # Open button — loads this class
            tk.Button(row, text=f"📂 {clean_name}", width=25, bg="#333", fg="white",
                      font=("Arial", 11),
                      command=self._make_launch_handler(file)).pack(side=tk.LEFT, padx=5)
            # Rename button
            tk.Button(row, text="✏️", bg="#444", fg="white",
                      command=self._make_rename_handler(file)).pack(side=tk.LEFT)
            # Delete button — red background as warning
            tk.Button(row, text="🗑️", bg="#600", fg="white",
                      command=self._make_delete_handler(file)).pack(side=tk.LEFT, padx=5)

        tk.Label(menu_frame, text="---", fg="#333", bg="#1a1a1a").pack(pady=10)
        tk.Button(menu_frame, text="➕ Create New Class Profile",
                  font=("Arial", 12, "bold"), bg="#2e7d32", fg="white", width=30,
                  command=self.create_new_class).pack(pady=5)

    # --- Handler factories ---
    # WHY FACTORIES? Python closures inside loops capture the variable by reference,
    # not by value. Without factories, every button would end up calling the handler
    # with the LAST value of 'file' in the loop, not their own filename.
    # By wrapping in a function, each button gets its own private copy.
    def _make_launch_handler(self, filename):
        def handler(): self.launch_class(filename)
        return handler

    def _make_rename_handler(self, filename):
        def handler(): self.rename_class_file(filename)
        return handler

    def _make_delete_handler(self, filename):
        def handler(): self.delete_class_file(filename)
        return handler

    def create_new_class(self):
        """Ask for a class name and create a new empty .json file for it."""
        new_name = simpledialog.askstring("New Class", "Enter name for the new class:")
        if new_name:
            # Replace spaces with underscores for safe filenames
            filename = os.path.join(BASE_DIR, f"{new_name.replace(' ', '_')}.json")
            self.students   = {"Sample Student": 0}   # start with one placeholder student
            self.attendance = {"Sample Student": True}
            self.filename   = filename
            self.save_data()           # write the file immediately
            self.show_main_menu()      # refresh menu to show the new file

    def rename_class_file(self, old_file):
        """Rename a class .json file on disk."""
        new_name = simpledialog.askstring("Rename", f"Enter new name for {old_file}:")
        if new_name:
            old_path = os.path.join(BASE_DIR, old_file)
            new_path = os.path.join(BASE_DIR, f"{new_name.replace(' ', '_')}.json")
            try:
                os.rename(old_path, new_path)   # rename the actual file on disk
                self.show_main_menu()            # refresh to show new name
            except Exception as e:
                messagebox.showerror("Error", f"Could not rename: {e}")

    def delete_class_file(self, filename):
        """Delete a class file after user confirms."""
        if messagebox.askyesno("Confirm Delete", f"Delete {filename}?"):
            os.remove(os.path.join(BASE_DIR, filename))   # permanently delete from disk
            self.show_main_menu()   # refresh menu

    # =========================================================================
    # LOAD / SAVE
    # =========================================================================
    def launch_class(self, filename):
        """Load a class file from disk and switch to the main app UI."""
        self.filename = os.path.join(BASE_DIR, filename)
        self.load_data(filename)
        # Destroy all menu widgets before building the app UI
        for widget in self.root.winfo_children():
            widget.destroy()
        self.setup_ui()
        self.update_scoreboard()
        self.draw_wheel()

    def load_data(self, path):
        """
        Load student data from a JSON file.
        Supports two formats:
          - New format: {"students": {name: score, ...}, "attendance": {name: bool, ...}}
          - Old format: just {name: score, ...} (backwards compatible)
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "students" in data:
                    # New format with separate attendance data
                    self.students   = data["students"]
                    self.attendance = data.get("attendance",
                                               {n: True for n in self.students})
                else:
                    # Old format — just scores, mark everyone as present
                    self.students   = data
                    self.attendance = {n: True for n in self.students}
        except FileNotFoundError:
            messagebox.showerror("Error", f"File not found: {path}")
            self.students = {}
            self.attendance = {}
        except json.JSONDecodeError:
            messagebox.showerror("Error", f"File is corrupted: {path}")
            self.students = {}
            self.attendance = {}

    def save_data(self):
        """
        Save student data to the main .json file AND create a timestamped backup.
        Backups go in a /backups subfolder next to the script.
        Old backups beyond MAX_BACKUPS are automatically deleted.
        """
        if not self.filename:
            return   # nothing to save if no file is loaded

        data = {"students": self.students, "attendance": self.attendance}

        # Write the main file
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Create backup folder if it doesn't exist yet
        backup_dir = os.path.join(BASE_DIR, "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # Backup filename includes timestamp so they sort chronologically
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(self.filename).replace('.json', '')
        backup_name = os.path.join(backup_dir, f"{base_name}_{timestamp}.json")

        with open(backup_name, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Prune old backups — find all backups for this class, sorted oldest first
        existing = sorted([
            f for f in os.listdir(backup_dir)
            if f.startswith(base_name + "_") and f.endswith(".json")
        ])
        # Delete from the front (oldest) until we're at or below MAX_BACKUPS
        while len(existing) > MAX_BACKUPS:
            os.remove(os.path.join(backup_dir, existing.pop(0)))

    # =========================================================================
    # UI SETUP — builds the entire main app layout
    # =========================================================================
    def setup_ui(self):
        """
        Build the 3-panel layout:
          LEFT  — student name editor, sort buttons, export, activity log
          MIDDLE — spinning wheel canvas
          RIGHT  — result label, spin/skip, point buttons, manual score, scoreboard
        """

        # --- TOP HEADER BAR ---
        header = tk.Frame(self.root, bg="#333", height=60)
        header.pack(side=tk.TOP, fill=tk.X)
        # Show class name in header (clean up filename formatting)
        clean_name = os.path.basename(self.filename).replace('.json', '').replace('_', ' ')
        tk.Label(header, text=clean_name,
                 font=("Arial", 20, "bold"), fg="#00d2ff", bg="#333").pack(
                     side=tk.LEFT, padx=20, pady=10)
        tk.Button(header, text="🏠 Home / Switch Class", bg="#444", fg="white",
                  command=self.show_main_menu).pack(side=tk.RIGHT, padx=20)

        # --- LEFT PANEL ---
        left_frame = tk.Frame(self.root, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, padx=15, pady=10, fill=tk.Y)

        # Small label showing which file is open — useful for debugging
        tk.Label(left_frame,
                 text=f"file open: {os.path.basename(self.filename)}",
                 fg="#aaa", bg="#1a1a1a", font=("Arial", 8)).pack(pady=5)

        tk.Label(left_frame, text="Edit Student Names:",
                 fg="white", bg="#1a1a1a").pack(pady=(10, 0))

        # Multi-line text box — one student name per line
        self.name_input = scrolledtext.ScrolledText(left_frame, width=25, height=8,
                                                     font=("Arial", 10))
        self.name_input.pack(pady=5)
        self.name_input.insert(tk.END, "\n".join(self.students.keys()))   # populate with current names

        # Save button — reads the text box and syncs it to self.students
        tk.Button(left_frame, text="💾 Update Names & Save",
                  command=self.sync_students, bg="#555", fg="white").pack(fill=tk.X)

        # Sort mode buttons
        tk.Label(left_frame, text="Sort by: ",
                 fg="#00d2ff", bg="#1a1a1a", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        sort_btn_frame = tk.Frame(left_frame, bg="#1a1a1a")
        sort_btn_frame.pack(fill=tk.X)
        tk.Button(sort_btn_frame, text="🔠 Name", width=10,
                  command=lambda: self.set_sort("name")).pack(side=tk.LEFT, padx=2)
        tk.Button(sort_btn_frame, text="📊️ Score", width=10,
                  command=lambda: self.set_sort("score")).pack(side=tk.RIGHT, padx=2)

        tk.Button(left_frame, text="🔀 Shuffle List",
                  command=self.shuffle_list).pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="📤 Export CSV",
                  command=self.export_csv, bg="#2e7d32", fg="white").pack(fill=tk.X, pady=2)
        tk.Button(left_frame, text="🗑️ Reset Scores",
                  command=self.reset_points, bg="#c62828", fg="white").pack(fill=tk.X, pady=2)

        # Activity log — green text on black, like a terminal
        # Shows spin events, winners, score changes in real time
        self.log_box = scrolledtext.ScrolledText(left_frame, width=25, height=10,
                                                  font=("Courier", 9), bg="#000", fg="#0f0")
        self.log_box.pack(pady=10)

        # --- MIDDLE PANEL: spinning wheel + manual score below ---
        mid_frame = tk.Frame(self.root, bg="#1a1a1a")
        mid_frame.pack(side=tk.LEFT, expand=True)

        # Canvas is packed first and fixed size — nothing below affects its position
        self.canvas = tk.Canvas(mid_frame, width=500, height=500,
                                bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack()

        # ── MANUAL SCORE BY NAME — sits below the wheel, doesn't move it ────
        # Apply a score to ANY student by typing their name.
        # Will NOT create new students — shows error if name not found.
        # Name matching is case-insensitive (e.g. "budi" matches "Budi").
        manual_frame = tk.Frame(mid_frame, bg="#1a1a1a")
        manual_frame.pack(pady=(5, 0))

        tk.Label(manual_frame, text="Manual Score by Name:",
                 fg="#00d2ff", bg="#1a1a1a",
                 font=("Arial", 10, "bold")).pack()

        # Name + score fields side by side in one row
        fields_row = tk.Frame(manual_frame, bg="#1a1a1a")
        fields_row.pack(pady=4)

        tk.Label(fields_row, text="Name:", fg="#aaa", bg="#1a1a1a",
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 3))
        self.manual_name_var = tk.StringVar()   # holds the typed student name
        tk.Entry(fields_row, textvariable=self.manual_name_var,
                 width=16, bg="#333", fg="white",
                 insertbackground="white",
                 font=("Arial", 11)).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(fields_row, text="Score:", fg="#aaa", bg="#1a1a1a",
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=(0, 3))
        self.manual_score_var = tk.StringVar()   # holds the typed score amount
        tk.Entry(fields_row, textvariable=self.manual_score_var,
                 width=6, bg="#333", fg="white",
                 insertbackground="white",
                 font=("Arial", 11), justify="center").pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(fields_row, text="✅ Apply",
                  bg="#1565c0", fg="white", font=("Arial", 10, "bold"),
                  command=self.apply_manual_score).pack(side=tk.LEFT)

        tk.Label(manual_frame, text="(error if student name not found)",
                 fg="#555", bg="#1a1a1a", font=("Arial", 8)).pack()
        # ─────────────────────────────────────────────────────────────────────

        # --- RIGHT PANEL ---
        right_frame = tk.Frame(self.root, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, padx=15, pady=10, fill=tk.BOTH)

        # Big result label — shows selected student name after spin
        self.result_label = tk.Label(right_frame, text="Lets get this party started",
                                     font=("Arial", 32, "bold"), fg="yellow", bg="#1a1a1a")
        self.result_label.pack(pady=10)

        # Spin and Skip buttons side by side
        spin_btn_frame = tk.Frame(right_frame, bg="#1a1a1a")
        spin_btn_frame.pack()
        tk.Button(spin_btn_frame, text="Spin (*ω*)",
                  font=("Arial", 14, "bold"), bg="#d32f2f", fg="white",
                  width=8, command=self.start_spin).pack(side=tk.LEFT, padx=5)
        tk.Button(spin_btn_frame, text="Skip ( • ̀ω•́ )✧",
                  font=("Arial", 14), bg="#555", fg="white",
                  command=self.skip_student).pack(side=tk.LEFT)

        # Fixed point buttons — applies to current_student (whoever the wheel selected)
        tk.Label(right_frame, text="( ´･ω･) Adjust Points (・ω・｀)",
                 fg="#00d2ff", bg="#1a1a1a", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        pts_frame = tk.Frame(right_frame, bg="#1a1a1a")
        pts_frame.pack(pady=5)
        tk.Button(pts_frame, text="+1", width=5,
                  command=lambda: self.modify_points(1)).pack(side=tk.LEFT, padx=2)
        tk.Button(pts_frame, text="+3", width=5,
                  command=lambda: self.modify_points(3)).pack(side=tk.LEFT, padx=2)
        tk.Button(pts_frame, text="+5", width=5,
                  command=lambda: self.modify_points(5)).pack(side=tk.LEFT, padx=2)
        tk.Button(pts_frame, text="-1", width=5,
                  command=lambda: self.modify_points(-1)).pack(side=tk.LEFT, padx=2)

        # ── QUICK SCORE (wheel-selected student) ─────────────────────────────
        # Type any number and hit Apply — goes to whoever the wheel last picked.
        # Useful when +1/+3/+5 aren't enough (e.g. bonus points for a big answer).
        tk.Label(right_frame, text="Quick Score (selected student):",
                 fg="#00d2ff", bg="#1a1a1a", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        quick_frame = tk.Frame(right_frame, bg="#1a1a1a")
        quick_frame.pack(pady=2)
        self.quick_score_var = tk.StringVar()   # holds the text in the entry box
        tk.Entry(quick_frame, textvariable=self.quick_score_var,
                 width=8, bg="#333", fg="white",
                 insertbackground="white",   # cursor color inside entry box
                 font=("Arial", 12), justify="center").pack(side=tk.LEFT, padx=5)
        tk.Button(quick_frame, text="✅ Apply",
                  bg="#1565c0", fg="white", font=("Arial", 10, "bold"),
                  command=self.apply_quick_score).pack(side=tk.LEFT, padx=5)
        tk.Label(right_frame, text="(applies to wheel-selected student)",
                 fg="#555", bg="#1a1a1a", font=("Arial", 8)).pack()

        # Recent winner history — shows last 5 names separated by arrows
        self.history_label = tk.Label(right_frame, text="No winners yet",
                                       fg="#888", bg="#1a1a1a", font=("Arial", 10))
        self.history_label.pack(pady=10)

        # Search box — filters scoreboard in real time as you type
        search_frame = tk.Frame(right_frame, bg="#1a1a1a")
        search_frame.pack(fill=tk.X, pady=(0, 5))
        self.search_var = tk.StringVar()
        # trace_add fires the callback every time the text changes
        self.search_var.trace_add("write", lambda *args: self.update_scoreboard())
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg="#333", fg="white",
                 insertbackground="white").pack(fill=tk.X)

        # Scrollable scoreboard using a Canvas + Scrollbar combo
        # (Tkinter doesn't have a native scrollable frame, so this is the standard workaround)
        self.score_container = tk.Frame(right_frame, bg="#222")
        self.score_container.pack(fill=tk.BOTH, expand=True)
        self.canvas_score = tk.Canvas(self.score_container, bg="#222", highlightthickness=0)
        self.scrollbar    = ttk.Scrollbar(self.score_container, orient="vertical",
                                           command=self.canvas_score.yview)
        self.scrollable_frame = tk.Frame(self.canvas_score, bg="#222")
        # Recalculate scroll area whenever the inner frame resizes
        self.scrollable_frame.bind("<Configure>",
            lambda e: self.canvas_score.configure(
                scrollregion=self.canvas_score.bbox("all")))
        self.canvas_score.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_score.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_score.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    # =========================================================================
    # SCORE ENTRY METHODS
    # =========================================================================
    def apply_quick_score(self):
        """
        Apply a typed score amount to whoever the wheel currently selected.
        Reads from self.quick_score_var (the entry box next to the Apply button).
        Clears the box after applying.
        """
        if not self.current_student:
            messagebox.showwarning("No Student Selected",
                                   "Spin the wheel first to select a student!")
            return

        raw = self.quick_score_var.get().strip()   # read and clean whitespace
        if not raw:
            messagebox.showwarning("Empty Input", "Please type a number first.")
            return

        try:
            amount = int(raw)   # int() will raise ValueError if it's not a whole number
        except ValueError:
            messagebox.showerror("Invalid Input",
                                 f"'{raw}' is not a valid number.\nUse whole numbers only.")
            return

        self.modify_points(amount)        # apply to current_student
        self.quick_score_var.set("")      # clear the box
        self.log_event(f"Quick: {'+' if amount >= 0 else ''}{amount} → {self.current_student}")

    def apply_manual_score(self):
        """
        Apply a typed score to any student by name.
        - Reads name from self.manual_name_var
        - Reads amount from self.manual_score_var
        - Case-insensitive name match (loops through self.students to find it)
        - If name not found: shows error, does NOTHING (no new student created)
        - Score floor = 0 (can't go negative)
        - Clears both fields after success
        - Shows a confirmation popup with the new score
        """
        raw_name  = self.manual_name_var.get().strip()
        raw_score = self.manual_score_var.get().strip()

        # Validate name field first
        if not raw_name:
            messagebox.showwarning("No Name", "Please type a student name.")
            return

        # Case-insensitive lookup — loop through actual names in the dict
        matched_name = None
        for name in self.students:
            if name.lower() == raw_name.lower():
                matched_name = name   # use the original casing from the dict
                break

        if matched_name is None:
            # Name not found — show error and stop, don't create new student
            messagebox.showerror("Student Not Found",
                                 f"'{raw_name}' does not exist in this class.\n"
                                 f"Check the spelling and try again.")
            return

        # Validate score field
        if not raw_score:
            messagebox.showwarning("No Score", "Please type a score amount.")
            return

        try:
            amount = int(raw_score)
        except ValueError:
            messagebox.showerror("Invalid Score",
                                 f"'{raw_score}' is not a valid number.\n"
                                 f"Use whole numbers only (e.g. 10, -5)")
            return

        # Apply score — max(0, ...) prevents score going below zero
        self.students[matched_name] = max(0, self.students[matched_name] + amount)
        self.save_data()
        self.update_scoreboard()
        self.draw_wheel()   # wheel slice sizes update since they're score-weighted

        # Clear both entry boxes so they're ready for next use
        self.manual_name_var.set("")
        self.manual_score_var.set("")

        # Log and confirm
        self.log_event(f"Manual: {'+' if amount >= 0 else ''}{amount} → {matched_name}")
        messagebox.showinfo("Applied",
                            f"{'+' if amount >= 0 else ''}{amount} pts → {matched_name}\n"
                            f"New score: {self.students[matched_name]}")

    # =========================================================================
    # WHEEL LOGIC
    # =========================================================================
    def get_karma_weights(self):
        """
        Return (names, weights) for active students only.
        Karma weighting: lower score = bigger wheel slice = more likely to be picked.
        Formula: weight = 1 / (score + 1)
          - score 0  → weight 1.0   (full size)
          - score 9  → weight 0.1   (smaller slice)
          - score 99 → weight 0.01  (tiny slice)
        Students unchecked in attendance or in temp_removed are excluded.
        """
        active_names = [n for n in self.students.keys()
                        if self.attendance.get(n, True) and n not in self.temp_removed]
        weights = [1.0 / (self.students[n] + 1) for n in active_names]
        return active_names, weights

    def _hsl_color(self, hue):
        """
        Convert a hue (0.0–1.0) to a hex color string like '#ff8800'.
        Used to give each wheel slice a distinct color.
        colorsys.hls_to_rgb(hue, lightness, saturation)
        """
        import colorsys
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.75)   # tweak 0.45/0.75 to change brightness/saturation
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def draw_wheel(self, flash_idx=None):
        """
        Draw the full wheel on the canvas.
        flash_idx: index of slice to draw white (used for winner flash animation).
        Slice size is proportional to each student's karma weight.
        """
        self.canvas.delete("all")   # clear previous drawing
        active_names, weights = self.get_karma_weights()
        if not active_names:
            return   # nothing to draw

        total_w    = sum(weights)
        curr_angle = self.angle   # start drawing from current rotation

        # Evenly spaced hues so adjacent slices look different
        n      = len(active_names)
        colors = [self._hsl_color(i / n) for i in range(n)]

        for i, (name, w) in enumerate(zip(active_names, weights)):
            extent = (w / total_w) * 360   # this slice's arc in degrees
            color  = "#fff" if i == flash_idx else colors[i]   # white if flashing

            # Draw the slice arc (20,20,480,480 = bounding box of the wheel circle)
            self.canvas.create_arc(20, 20, 480, 480,
                                   start=curr_angle, extent=extent,
                                   fill=color, outline="white", width=2)

            # Place name label in the middle of the slice
            # math.radians converts degrees to radians for cos/sin
            rad    = math.radians(curr_angle + extent / 2)
            tx, ty = 250 + 175 * math.cos(rad), 250 - 175 * math.sin(rad)
            self.canvas.create_text(tx, ty, text=name[:10],   # truncate to 10 chars
                                    fill="white" if i != flash_idx else "black",
                                    font=("Arial", 8, "bold"),
                                    angle=int(curr_angle + extent / 2))   # rotate text with slice
            curr_angle += extent   # advance to next slice

        # Center circle (covers slice wedge tips)
        self.canvas.create_oval(210, 210, 290, 290,
                                fill="#1a1a1a", outline="white", width=2)
        self.canvas.create_text(250, 250, text=self.center_face,
                                fill="#00d2ff", font=("Arial", 14, "bold"))

        # Fixed red pointer triangle on the right — points at the winner
        self.canvas.create_polygon(460, 250, 500, 230, 500, 270, fill="#ff1744")

    def start_spin(self):
        """Start spinning with random speed and duration."""
        if self.is_spinning:
            return   # prevent double-spin if button clicked while already spinning

        try:
            varied_speed = random.uniform(1, 300)   # pixels per frame at start — change range to adjust feel
            dur          = random.uniform(1, 3)      # spin duration in seconds — change range to adjust
            # Friction: how fast it slows down. Derived from duration so longer spins decelerate slower.
            # 1 - (1 / (dur * 12)) means higher dur = friction closer to 1 = slower deceleration
            self.friction    = 1 - (1 / (dur * 12))
            self.is_spinning = True
            self.log_event(f"Spd {varied_speed:.1f} | Dur {dur:.1f}s")
            self.animate_spin(varied_speed)
        except Exception as e:
            messagebox.showerror("Spin Error", str(e))

    def animate_spin(self, speed):
        """
        Recursive animation — called every 20ms via root.after().
        Multiplies speed by friction each frame to simulate deceleration.
        Stops when speed drops below 0.5 to avoid infinite crawl.
        Changes center face expression based on current speed.
        """
        if speed > 0.5:   # still spinning — continue animation
            self.angle = (self.angle + speed) % 360   # advance wheel rotation
            # Face changes based on speed — fun visual feedback
            if speed > 200:   self.center_face = "(X_X)"
            elif speed > 150: self.center_face = "(@_@)"
            elif speed > 100: self.center_face = "(°ロ°)"
            elif speed > 50:  self.center_face = "(°o°)"
            elif speed > 10:  self.center_face = "(·_·)"
            else:             self.center_face = "(´･ω･`)"
            self.draw_wheel()
            # Schedule next frame — 20ms delay = ~50fps animation
            # speed * friction makes it slower each frame
            self.root.after(20, lambda: self.animate_spin(speed * self.friction))
        else:
            # Wheel stopped
            self.is_spinning = False
            self.center_face = "(๑˃ᴗ˂)ﻭ"   # happy face when done
            self.draw_wheel()
            self.determine_winner()

    def determine_winner(self):
        """
        Figure out which slice is under the pointer (right side of wheel).
        The pointer is fixed at the 3 o'clock position (angle 0).
        We check which slice covers that position given the current rotation.
        """
        active_names, weights = self.get_karma_weights()
        if not active_names:
            return

        total_w = sum(weights)
        # The pointer is at angle 0 (right). Given wheel rotation, find which slice is there.
        target     = (360 - (self.angle % 360)) % 360   # convert wheel angle to pointer-relative angle
        curr_w_sum = 0
        winner_idx = 0

        for i, w in enumerate(weights):
            extent = (w / total_w) * 360
            if curr_w_sum <= target < curr_w_sum + extent:
                winner_idx = i
                break
            curr_w_sum += extent

        self.current_student = active_names[winner_idx]
        self.result_label.config(text=self.current_student)   # show name in big label
        self.update_history(self.current_student)
        self.flash_winner(winner_idx, 0)   # start flash animation

    def skip_student(self):
        """Skip the current student — no points, no log entry for score, just clears selection."""
        if self.current_student:
            self.log_event(f"Skipped: {self.current_student}")
            self.result_label.config(text="NO RESULT")
            self.current_student = None
            self.draw_wheel()

    def update_history(self, name):
        """Add winner to recent history list and update the history label."""
        self.history.insert(0, name)       # newest at front
        self.history = self.history[:5]    # keep only last 5
        self.history_label.config(text=" ← ".join(self.history))
        self.log_event(f"Winner: {name}")

    def flash_winner(self, idx, count):
        """
        Flash the winning slice white 3 times by alternating flash_idx on/off.
        count goes 0–5 (6 frames), alternating between flash and normal.
        root.after(200, ...) = 200ms between each flash frame.
        """
        if count < 6:
            self.draw_wheel(flash_idx=idx if count % 2 == 0 else None)
            self.root.after(200, lambda: self.flash_winner(idx, count + 1))

    # =========================================================================
    # SCORE MANAGEMENT
    # =========================================================================
    def modify_points(self, amount):
        """
        Add or subtract points from self.current_student.
        Score floor is 0 — max(0, ...) prevents going negative.
        Saves data and refreshes scoreboard and wheel after each change.
        """
        if self.current_student:
            self.students[self.current_student] = max(
                0, self.students[self.current_student] + amount)
            self.save_data()
            self.update_scoreboard()
            self.draw_wheel()   # redraw since karma weights change with scores

    def set_sort(self, mode):
        """Switch scoreboard sort mode and refresh. mode = 'name' or 'score'."""
        self.sort_mode = mode
        self.update_scoreboard()

    def update_scoreboard(self):
        """
        Rebuild the scrollable scoreboard from scratch.
        Destroys all existing rows and recreates them.
        Applies search filter and current sort mode.
        Each row has: attendance checkbox | name | score | badge emoji
        """
        # Clear existing rows
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().lower()   # empty string = show all

        # Sort by score descending or name alphabetically
        if self.sort_mode == "score":
            items = sorted(self.students.items(), key=lambda x: x[1], reverse=True)
        else:
            items = sorted(self.students.items())   # default alphabetical

        for name, score in items:
            # Skip if search is active and name doesn't contain the query
            if search_query and search_query not in name.lower():
                continue

            frame = tk.Frame(self.scrollable_frame, bg="#222")
            frame.pack(fill=tk.X, padx=5, pady=2)

            # Attendance checkbox — uncheck to remove student from wheel without deleting
            var = tk.BooleanVar(value=self.attendance.get(name, True))
            tk.Checkbutton(frame, variable=var, bg="#222",
                           command=self._make_attendance_handler(name, var)).pack(side=tk.LEFT)

            # Badge emoji based on score milestones — change thresholds here to customize
            badge = ("💎" if score >= 50 else
                     "🥇" if score >= 30 else
                     "🥈" if score >= 20 else
                     "🥉" if score >= 10 else "")

            # Fixed-width Courier font keeps columns aligned
            # name[:12] truncates long names, :<12 left-pads to 12 chars
            tk.Label(frame,
                     text=f"{name[:12]:<12} | {score:3}pts {badge}",
                     fg="white", bg="#222", font=("Courier", 10)).pack(side=tk.LEFT)

    def _make_attendance_handler(self, name, var):
        """
        Factory for attendance checkbox callbacks.
        Same closure-fix reason as _make_launch_handler — each checkbox needs
        its own captured 'name' and 'var', not the loop's last value.
        """
        def handler(): self.toggle_attendance(name, var)
        return handler

    def toggle_attendance(self, name, var):
        """Update attendance dict and redraw wheel to reflect the change."""
        self.attendance[name] = var.get()   # True = present, False = absent/excluded
        self.draw_wheel()   # wheel slices update immediately

    def sync_students(self):
        """
        Read the name text box and sync it to self.students.
        - Names in the box but NOT in self.students → added with score 0
        - Names in BOTH → existing score kept (not reset)
        - Names in self.students but NOT in the box → removed
        Then saves and refreshes everything.
        """
        raw       = self.name_input.get("1.0", tk.END).splitlines()   # get all lines
        new_names = [n.strip() for n in raw if n.strip()]              # ignore blank lines

        # dict comprehension: keeps existing scores, defaults new names to 0
        self.students   = {n: self.students.get(n, 0) for n in new_names}
        self.attendance = {n: self.attendance.get(n, True) for n in new_names}
        self.save_data()
        self.update_scoreboard()
        self.draw_wheel()

    def log_event(self, msg):
        """Append a timestamped line to the activity log. Auto-scrolls to bottom."""
        self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M')}] {msg}\n")
        self.log_box.see(tk.END)   # scroll to bottom so latest entry is visible

    def export_csv(self):
        """Export the current scoreboard as a CSV file. Opens a save dialog."""
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            with open(path, 'w', newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Score"])   # header row
                for n, s in self.students.items():
                    writer.writerow([n, s])
            messagebox.showinfo("Success", "Exported!")

    def reset_points(self):
        """Reset all student scores to 0 after confirmation dialog."""
        if messagebox.askyesno("Confirm", "Reset all scores?"):
            for n in self.students:
                self.students[n] = 0   # set every score to zero
            self.save_data()
            self.update_scoreboard()
            self.draw_wheel()

    def shuffle_list(self):
        """Randomly shuffle the order of students in the scoreboard and wheel."""
        items = list(self.students.items())
        random.shuffle(items)
        self.students = dict(items)   # rebuild dict in shuffled order
        self.update_scoreboard()
        self.draw_wheel()

    def toggle_fullscreen(self, _e=None):
        """Toggle fullscreen on/off. Bound to F11 key."""
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app  = ClassroomWheel(root)
    root.mainloop()   # starts the tkinter event loop — runs until window is closed