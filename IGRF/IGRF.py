import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import numpy as np
import datetime
import os
import sys
from scipy import interpolate

def resource_path(relative_path):
    """ Mendapatkan path absolut ke resource, berfungsi untuk dev dan PyInstaller """
    try:
        # PyInstaller membuat folder sementara dan menyimpan path di _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- IMPORT MODULE ---
try:
    import igrf_utils as iut
except ImportError:
    messagebox.showerror("System Error", "Critical component 'igrf_utils.py' missing.\nEnsure environment is configured correctly.")
    sys.exit()

class ArcGISProIGRF:
    def __init__(self, root):
        self.root = root
        self.root.title("IGRF-14 Geospatial Calculator")
        self.root.geometry("1200x700")
        
        # --- THEME DEFINITIONS ---
        self.current_theme = "dark" # Default start
        
        self.themes = {
            "dark": {
                "bg_main": "#1E1E1E",       # Main Background
                "bg_panel": "#2B2B2B",      # Sidebar/Ribbon
                "accent": "#007AC2",        # ArcGIS Blue
                "text": "#F0F0F0",          # White text
                "text_dim": "#AAAAAA",      # Dimmed Text
                "entry_bg": "#3F3F3F",
                "entry_fg": "#FFFFFF",
                "tree_bg": "#1E1E1E",
                "tree_fg": "#F0F0F0",
                "tree_head": "#323232",
                "icon_mode": "☀️ Light Mode"
            },
            "light": {
                "bg_main": "#FFFFFF",       # White Background
                "bg_panel": "#F3F3F3",      # Light Gray Ribbon
                "accent": "#005E94",        # Darker Blue for contrast
                "text": "#151515",          # Black text
                "text_dim": "#555555",      # Dimmed Text
                "entry_bg": "#FFFFFF",
                "entry_fg": "#000000",
                "tree_bg": "#FFFFFF",
                "tree_fg": "#000000",
                "tree_head": "#E0E0E0",
                "icon_mode": "🌙 Dark Mode"
            }
        }

        # --- DATA VARIABLES ---
        self.filepath = ""
        self.df = None
        self.igrf_data = None 

        # --- UI INITIALIZATION ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Widgets containers (untuk update warna nanti)
        self.containers = {} 
        self.labels = []
        self.buttons = []

        self.create_ribbon()
        self.create_sidebar()
        self.create_main_view()
        self.create_status_bar()

        # Apply Initial Theme
        self.apply_theme("dark")

        # Load Coefficients silently
        self.load_igrf_coefficients()

    def apply_theme(self, theme_name):
        """Menerapkan warna berdasarkan tema yang dipilih"""
        colors = self.themes[theme_name]
        self.current_theme = theme_name

        # 1. Update Root & Frames
        self.root.configure(bg=colors["bg_main"])
        for widget in self.containers.values():
            widget.configure(bg=colors["bg_panel"] if "sidebar" in str(widget) or "ribbon" in str(widget) else colors["bg_main"])

        # 2. Update Specific Widgets (Labels)
        for lbl in self.labels:
            # Cek apakah label judul atau label biasa
            bg_color = colors["bg_panel"] if lbl in self.panel_labels else colors["bg_main"]
            # Accent headers
            fg_color = colors["accent"] if lbl in self.accent_labels else colors["text"]
            if lbl in self.dim_labels: fg_color = colors["text_dim"]
            
            lbl.configure(bg=bg_color, fg=fg_color)

        # 3. Update Entries
        self.entry_date.configure(bg=colors["entry_bg"], fg=colors["entry_fg"], insertbackground=colors["text"])

        # 4. Update TTK Styles
        self.style.configure("TFrame", background=colors["bg_panel"])
        self.style.configure("TLabel", background=colors["bg_panel"], foreground=colors["text"])
        
        # Normal Buttons
        self.style.configure("TButton", 
                             background="#CCCCCC" if theme_name == "light" else "#333333", 
                             foreground="black" if theme_name == "light" else "white", 
                             borderwidth=0, 
                             font=("Segoe UI", 9))
        
        # Accent Buttons (Blue)
        self.style.configure("Accent.TButton", background=colors["accent"], foreground="white")
        self.style.map("Accent.TButton", background=[('active', "#00497A")])
        
        # Danger/Reset Buttons
        self.style.configure("Danger.TButton", background="#D32F2F", foreground="white")
        self.style.map("Danger.TButton", background=[('active', "#B71C1C")])

        # Treeview (Table)
        self.style.configure("Treeview", 
                             background=colors["tree_bg"], 
                             fieldbackground=colors["tree_bg"], 
                             foreground=colors["tree_fg"],
                             borderwidth=0)
        self.style.configure("Treeview.Heading", 
                             background=colors["tree_head"], 
                             foreground=colors["text"], 
                             relief="flat",
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview.Heading", background=[('active', colors["accent"])])

        # 5. Update Toggle Button Text
        self.btn_theme.configure(text=colors["icon_mode"])

        # 6. Update Chart/Table Frame Backgrounds
        self.tree_frame.configure(bg=colors["bg_main"])

    def toggle_theme(self):
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)

    def create_ribbon(self):
        """Top Header Area"""
        ribbon = tk.Frame(self.root, height=50)
        ribbon.pack(fill="x", side="top")
        self.containers["ribbon"] = ribbon
        
        # Title
        lbl_title = tk.Label(ribbon, text="Geomagnetic Analysis / IGRF-14 Tool", font=("Segoe UI", 12, "bold"), padx=15, pady=10)
        lbl_title.pack(side="left")
        
        # Register label for theming
        self.labels.append(lbl_title)
        self.panel_labels = [lbl_title] # Group special labels
        self.accent_labels = []
        self.dim_labels = []

        # Theme Toggle Button
        self.btn_theme = tk.Button(ribbon, text="Mode", command=self.toggle_theme, 
                                   bd=0, bg=self.themes["dark"]["bg_panel"], fg=self.themes["dark"]["text"], 
                                   font=("Segoe UI", 9), cursor="hand2", padx=10)
        self.btn_theme.pack(side="right", fill="y", padx=0)

    def create_sidebar(self):
        """Left Control Panel"""
        sidebar = tk.Frame(self.root, width=300)
        sidebar.pack(fill="y", side="left", padx=(0, 1), pady=(1, 0))
        sidebar.pack_propagate(False)
        self.containers["sidebar"] = sidebar

        # --- Helper to create section headers ---
        def create_header(text):
            lbl = tk.Label(sidebar, text=text, font=("Segoe UI", 8, "bold"), anchor="w")
            lbl.pack(fill="x", padx=15, pady=(20, 5))
            self.labels.append(lbl)
            self.panel_labels.append(lbl)
            self.accent_labels.append(lbl) # Make these accent colored

        # Section 1: Data Source
        create_header("DATA SOURCE")

        self.btn_load = ttk.Button(sidebar, text="Import Excel Table (.xlsx)", command=self.load_file, cursor="hand2")
        self.btn_load.pack(fill="x", padx=15, pady=5)

        self.lbl_file_status = tk.Label(sidebar, text="No file loaded", font=("Segoe UI", 8), anchor="w")
        self.lbl_file_status.pack(fill="x", padx=15, pady=0)
        self.labels.append(self.lbl_file_status)
        self.panel_labels.append(self.lbl_file_status)
        self.dim_labels.append(self.lbl_file_status)

        # Section 2: Parameters
        create_header("PARAMETERS")

        lbl_date = tk.Label(sidebar, text="Survey Date (YYYY-MM-DD):", anchor="w")
        lbl_date.pack(fill="x", padx=15)
        self.labels.append(lbl_date)
        self.panel_labels.append(lbl_date)

        self.entry_date = tk.Entry(sidebar, relief="flat", font=("Segoe UI", 10))
        self.entry_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.entry_date.pack(fill="x", padx=15, pady=5, ipady=3)

        # Section 3: Processing
        create_header("PROCESSING")

        self.btn_calc = ttk.Button(sidebar, text="Run Analysis", style="Accent.TButton", command=self.calculate_igrf, state="disabled", cursor="hand2")
        self.btn_calc.pack(fill="x", padx=15, pady=5, ipady=5)

        self.btn_export = ttk.Button(sidebar, text="Export Result", command=self.export_file, state="disabled", cursor="hand2")
        self.btn_export.pack(fill="x", padx=15, pady=5)

        # Section 4: Utilities (Reset)
        tk.Frame(sidebar, height=30, bg=self.themes["dark"]["bg_panel"]).pack() # Spacer
        
        self.btn_reset = ttk.Button(sidebar, text="Reset Application", style="Danger.TButton", command=self.reset_app, cursor="hand2")
        self.btn_reset.pack(side="bottom", fill="x", padx=15, pady=20)

    def create_main_view(self):
        """Right Data Table"""
        self.tree_frame = tk.Frame(self.root)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbars
        scroll_y = ttk.Scrollbar(self.tree_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(self.tree_frame, orient="horizontal")

        self.tree = ttk.Treeview(self.tree_frame, yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set, selectmode="browse")
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)

        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

    def create_status_bar(self):
        """Bottom Status Bar"""
        self.status_bar = tk.Label(self.root, text="Ready", font=("Segoe UI", 9), anchor="w", padx=10, bg=self.themes["dark"]["accent"], fg="white")
        self.status_bar.pack(side="bottom", fill="x")

    def update_status(self, message, is_error=False):
        color = "#D32F2F" if is_error else self.themes[self.current_theme]["accent"]
        self.status_bar.config(text=message, bg=color)
        self.root.update_idletasks()

    # --- LOGIC UTILITIES ---

    def reset_app(self):
        """Fungsi Reset Aplikasi"""
        if self.df is not None:
            confirm = messagebox.askyesno("Reset Application", "Are you sure you want to clear all data and reset?")
            if not confirm:
                return

        # 1. Clear Variables
        self.df = None
        self.filepath = ""
        
        # 2. Clear UI
        self.tree.delete(*self.tree.get_children())
        self.lbl_file_status.config(text="No file loaded")
        
        # 3. Reset Inputs
        self.entry_date.delete(0, tk.END)
        self.entry_date.insert(0, datetime.date.today().strftime("%Y-%m-%d"))

        # 4. Disable Buttons
        self.btn_calc.config(state="disabled")
        self.btn_export.config(state="disabled")
        
        # 5. Status
        self.update_status("Application Reset successfully.")

    def load_igrf_coefficients(self):
        shc_path = resource_path(os.path.join("SHC_files", "IGRF14.SHC"))
        if not os.path.exists(shc_path):
            shc_path = "IGRF14.SHC"
        
        if not os.path.exists(shc_path):
            self.update_status("Error: IGRF14.SHC not found in SHC_files folder.", True)
            return

        try:
            self.igrf_data = iut.load_shcfile(shc_path, None)
            self.update_status("System Ready. IGRF-14 Model Loaded.")
        except Exception as e:
            self.update_status(f"Model Load Error: {e}", True)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if file_path:
            try:
                self.df = pd.read_excel(file_path)
                self.df.columns = [str(col).upper().strip() for col in self.df.columns]
                
                wajib = ['LATITUDE', 'LONGITUDE', 'Z']
                if not all(col in self.df.columns for col in wajib):
                    messagebox.showerror("Schema Error", f"Input table must contain columns:\n{', '.join(wajib)}")
                    return

                self.filepath = file_path
                self.lbl_file_status.config(text=os.path.basename(file_path))
                
                if self.igrf_data:
                    self.btn_calc.config(state="normal")
                
                self.preview_data()
                self.update_status(f"Loaded: {os.path.basename(file_path)} - {len(self.df)} features.")
            except Exception as e:
                self.update_status(f"File Error: {e}", True)

    def preview_data(self):
        self.tree.delete(*self.tree.get_children())
        cols = list(self.df.columns)
        self.tree["columns"] = cols
        self.tree["show"] = "headings"
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, minwidth=50)
        
        for index, row in self.df.head(100).iterrows():
            self.tree.insert("", "end", values=list(row))

    def date_to_decimal_year(self, date_obj):
        start_of_year = datetime.date(date_obj.year, 1, 1)
        days_in_year = 366 if (date_obj.year % 4 == 0 and (date_obj.year % 100 != 0 or date_obj.year % 400 == 0)) else 365
        day_of_year = (date_obj - start_of_year).days
        return date_obj.year + (day_of_year / days_in_year)

    def geodetic_to_geocentric(self, lat, lon, alt_km):
        a = 6378.137
        f = 1/298.257223563
        b = a * (1 - f)
        e2 = 1 - (b/a)**2
        
        lat_rad = np.radians(lat)
        clat = np.cos(lat_rad)
        slat = np.sin(lat_rad)
        
        N = a / np.sqrt(1 - e2 * slat**2)
        X = (N + alt_km) * clat * np.cos(np.radians(lon))
        Y = (N + alt_km) * clat * np.sin(np.radians(lon))
        Z = (N * (1 - e2) + alt_km) * slat
        
        r = np.sqrt(X**2 + Y**2 + Z**2)
        lat_geocentric = np.arcsin(Z / r)
        colat_rad = (np.pi / 2) - lat_geocentric
        
        psi = lat_geocentric
        phi = lat_rad
        cd = np.cos(phi - psi)
        sd = np.sin(phi - psi)
        
        return r, colat_rad, sd, cd

    def calculate_igrf(self):
        if self.df is None or self.igrf_data is None:
            return

        self.update_status("Processing... Please wait.")
        self.root.update()

        try:
            date_str = self.entry_date.get()
            survey_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            decimal_year = self.date_to_decimal_year(survey_date)
            
            f = interpolate.interp1d(self.igrf_data.time, self.igrf_data.coeffs, fill_value='extrapolate')
            coeffs = f(decimal_year)

            list_dec, list_inc, list_total = [], [], []

            for index, row in self.df.iterrows():
                lat = float(row['LATITUDE'])
                lon = float(row['LONGITUDE'])
                alt_m = float(row['Z'])
                alt_km = alt_m / 1000.0 

                r, colat_rad, sd, cd = self.geodetic_to_geocentric(lat, lon, alt_km)

                colat_deg = np.degrees(colat_rad)
                lon_deg = lon 

                Br, Bt, Bp = iut.synth_values(coeffs.T, r, colat_deg, lon_deg, self.igrf_data.parameters['nmax'])

                X = -Bt
                Y = Bp
                Z = -Br
                
                t = X
                X = X * cd + Z * sd
                Z = Z * cd - t * sd

                dec, hoz, inc, eff = iut.xyz2dhif(X, Y, Z)

                list_dec.append(round(dec, 4))
                list_inc.append(round(inc, 4))
                list_total.append(round(eff, 2))

            self.df['IGRF14_DEC'] = list_dec
            self.df['IGRF14_INC'] = list_inc
            self.df['IGRF14_TOTAL'] = list_total

            self.preview_data()
            self.btn_export.config(state="normal")
            self.btn_reset.config(state="normal")
            
            msg = f"Analysis successfully completed.\nFeatures Processed: {len(self.df)}\nSample Total Field (row 1): {list_total[0]} nT"
            messagebox.showinfo("Analysis Complete", msg)
            self.update_status("Analysis completed successfully.")

        except Exception as e:
            print(e)
            messagebox.showerror("Processing Error", str(e))
            self.update_status("Analysis Failed.", True)

    def export_file(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel Files", "*.xlsx")])
        if save_path:
            try:
                self.df.to_excel(save_path, index=False)
                messagebox.showinfo("Export", f"Data exported successfully to:\n{save_path}")
                self.update_status(f"Exported to {os.path.basename(save_path)}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ArcGISProIGRF(root)
    root.mainloop()