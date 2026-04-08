import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import sqlite3
import requests
import random
import datetime
import csv
import math
import threading
import webbrowser  

# --- NASTAVENIE TÉMY ---
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

# --- DATABÁZA MIEST ---
VELKA_DATABAZA = {
    "Bratislava":(17.1077,48.1486), "Košice":(21.2610,48.7163), "Prešov":(21.2393,48.9981),
    "Žilina":(18.7394,49.2231), "Nitra":(18.0845,48.3060), "Banská Bystrica":(19.1459,48.7333),
    "Trnava":(17.5875,48.3709), "Trenčín":(18.0443,48.8945), "Martin":(18.9239,49.0665),
    "Poprad":(20.2979,49.0506), "Prievidza":(18.6273,48.7719), "Zvolen":(19.1462,48.5772),
    "Považská Bystrica":(18.4485,49.1147), "Michalovce":(21.9195,48.7494), "Nové Zámky":(18.1619,47.9861),
    "Spišská Nová Ves":(20.5630,48.9446), "Komárno":(18.1226,47.7635), "Humenné":(21.9103,48.9372),
    "Levice":(18.6071,48.2156), "Piešťany":(17.8286,48.5917), "Ružomberok":(19.3034,49.0748),
    "Lučenec":(19.6631,48.3283), "Čadca":(18.7895,49.4350), "Dunajská Streda":(17.6186,47.9945),
    "Senica":(17.3667,48.6792), "Nové Mesto nad Váhom":(17.8305,48.7505), "Stará Turá":(17.6936,48.7769),
    "Myjava":(17.5684,48.7561), "Skalica":(17.2266,48.8449), "Malacky":(17.0219,48.4361)
}

def vzdusna_vzdialenost(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlon = math.radians(lon2 - lon1); dlat = math.radians(lat2 - lat1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

# --- DATABÁZA ---
def init_db():
    conn = sqlite3.connect("kniha_jazd.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vozidla (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 spz TEXT, znacka TEXT, typ TEXT, druh TEXT,
                 phl TEXT, vin TEXT, vodic TEXT, norm_spotreba REAL, tacho REAL)''')
    try: c.execute("ALTER TABLE vozidla ADD COLUMN objem_nadrze REAL DEFAULT 50.0")
    except: pass
    try: c.execute("ALTER TABLE vozidla ADD COLUMN stav_nadrze REAL DEFAULT 0.0")
    except: pass
    conn.commit(); conn.close()

class KnihaJazdApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TripGenie")
        self.geometry("1400x700")
        self.cache_gps = VELKA_DATABAZA.copy()
        
        init_db()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        
        self.frame_generator = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.frame_garaz = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")

        self.setup_generator_ui()
        self.setup_garaz_ui()

        self.aplikuj_styl_tabulky("Dark" if ctk.get_appearance_mode() == "Dark" else "Light")

        self.nacitaj_vozidla()
        self.zobraz_frame("generator")

        self.link_apanio = ctk.CTkLabel(
            self, 
            text="Apanio", 
            font=ctk.CTkFont(underline=True, weight="bold"), 
            text_color=("#1a73e8", "#5b9dd9"), 
            cursor="hand2"
        )
        self.link_apanio.place(relx=0.99, rely=0.99, anchor="se", x=-10, y=- -5)
        self.link_apanio.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Apanio?tab=repositories&q=&type=public&language=&sort="))

    # ==================== SIDEBAR ====================
    def setup_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TripGenie", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))

        self.btn_nav_gen = ctk.CTkButton(self.sidebar_frame, text="Generátor Jázd", command=lambda: self.zobraz_frame("generator"))
        self.btn_nav_gen.grid(row=1, column=0, padx=20, pady=10)

        self.btn_nav_garaz = ctk.CTkButton(self.sidebar_frame, text="Garáž (Vozidlá)", command=lambda: self.zobraz_frame("garaz"))
        self.btn_nav_garaz.grid(row=2, column=0, padx=20, pady=10)

        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Vzhľad (Režim):", anchor="w")
        self.theme_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.theme_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Dark", "Light"], command=self.zmenit_temu)
        self.theme_menu.grid(row=6, column=0, padx=20, pady=(10, 20))

    def zobraz_frame(self, name):
        if name == "generator":
            self.frame_garaz.grid_forget()
            self.frame_generator.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        else:
            self.frame_generator.grid_forget()
            self.frame_garaz.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def zmenit_temu(self, novy_vzhlad: str):
        ctk.set_appearance_mode(novy_vzhlad)
        self.aplikuj_styl_tabulky(novy_vzhlad)

    def aplikuj_styl_tabulky(self, rezim):
        style = ttk.Style()
        style.theme_use("default")
        if rezim == "Dark" or (rezim == "System" and ctk.get_appearance_mode() == "Dark"):
            bg_color = "#2b2b2b"; fg_color = "white"; field_bg = "#2b2b2b"
            head_bg = "#1f538d"; head_fg = "white"; sel_bg = "#14375e"
        else:
            bg_color = "white"; fg_color = "black"; field_bg = "white"
            head_bg = "#3a7ebf"; head_fg = "white"; sel_bg = "#b3d4f0"

        style.configure("Treeview", background=bg_color, foreground=fg_color, rowheight=30, fieldbackground=field_bg, borderwidth=0, font=("Arial", 11))
        style.map('Treeview', background=[('selected', sel_bg)])
        style.configure("Treeview.Heading", background=head_bg, foreground=head_fg, relief="flat", font=("Arial", 12, "bold"))
        style.map("Treeview.Heading", background=[('active', head_bg)])

    # ==================== ZÁLOŽKA: GARÁŽ ====================
    def setup_garaz_ui(self):
        self.frame_garaz.grid_columnconfigure(0, weight=1)
        self.frame_garaz.grid_rowconfigure(2, weight=1)

        card_form = ctk.CTkFrame(self.frame_garaz)
        card_form.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(card_form, text="Pridať / Upraviť Vozidlo", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, columnspan=8, pady=(10,20), sticky="w", padx=20)

        self.garaz_labels = [
            "ŠPZ / Názov:", "Značka:", "Typ/Model:", "Druh:", "PHL:", "VIN číslo:", 
            "Vodič:", "Norm. spotreba (l):", "Tachometer (Štart):", "Objem nádrže (l):", "Stav v nádrži (l):"
        ]
        self.garaz_entries = {}
        for i, lbl in enumerate(self.garaz_labels):
            ctk.CTkLabel(card_form, text=lbl).grid(row=(i//4)+1, column=(i%4)*2, sticky="e", padx=10, pady=10)
            ent = ctk.CTkEntry(card_form, width=150)
            ent.grid(row=(i//4)+1, column=(i%4)*2+1, sticky="w", padx=10, pady=10)
            self.garaz_entries[lbl] = ent

        btn_frame = ctk.CTkFrame(self.frame_garaz, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="Pridať nové vozidlo", command=self.pridat_vozidlo, fg_color="#28a745", hover_color="#218838").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Uložiť zmeny", command=self.upravit_vozidlo).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Vymazať", command=self.vymazat_vozidlo, fg_color="#dc3545", hover_color="#c82333").pack(side="left", padx=10)

        tree_frame = ctk.CTkFrame(self.frame_garaz)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        self.tree_auta = ttk.Treeview(tree_frame, columns=("id", "spz", "auto", "vodic", "tacho", "nadrz"), show="headings")
        for c, h, w in zip(self.tree_auta['columns'], ["ID", "ŠPZ", "Vozidlo", "Vodič", "Tachometer", "Nádrž (l)"], [50, 100, 250, 150, 100, 100]):
            self.tree_auta.heading(c, text=h); self.tree_auta.column(c, width=w)
        self.tree_auta.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree_auta.bind("<<TreeviewSelect>>", self.nacitaj_do_formulara)

    def ziskaj_hodnoty_z_formulara(self):
        hodnoty = [self.garaz_entries[lbl].get().strip() for lbl in self.garaz_labels]
        if not hodnoty[0]: return messagebox.showerror("Chyba", "ŠPZ je povinná!")
        try:
            return (*hodnoty[:7], float(hodnoty[7].replace(',','.') or 0), float(hodnoty[8].replace(',','.') or 0), float(hodnoty[9].replace(',','.') or 50), float(hodnoty[10].replace(',','.') or 0))
        except: return messagebox.showerror("Chyba", "Polia musia obsahovať čísla.")

    def pridat_vozidlo(self):
        data = self.ziskaj_hodnoty_z_formulara()
        if not data: return
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("INSERT INTO vozidla (spz, znacka, typ, druh, phl, vin, vodic, norm_spotreba, tacho, objem_nadrze, stav_nadrze) VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
        conn.commit(); conn.close(); self.vycisti_formular(); self.nacitaj_vozidla()

    def upravit_vozidlo(self):
        vybrane = self.tree_auta.selection()
        if not vybrane: return messagebox.showwarning("Upozornenie", "Kliknite na vozidlo v tabuľke.")
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        data = self.ziskaj_hodnoty_z_formulara()
        if not data: return
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute('''UPDATE vozidla SET spz=?, znacka=?, typ=?, druh=?, phl=?, vin=?, vodic=?, 
                     norm_spotreba=?, tacho=?, objem_nadrze=?, stav_nadrze=? WHERE id=?''', (*data, v_id))
        conn.commit(); conn.close(); self.vycisti_formular(); self.nacitaj_vozidla()

    def vymazat_vozidlo(self):
        vybrane = self.tree_auta.selection()
        if not vybrane: return
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("DELETE FROM vozidla WHERE id=?", (v_id,)); conn.commit(); conn.close(); self.vycisti_formular(); self.nacitaj_vozidla()

    def nacitaj_do_formulara(self, event):
        vybrane = self.tree_auta.selection()
        if not vybrane: return
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("SELECT spz, znacka, typ, druh, phl, vin, vodic, norm_spotreba, tacho, objem_nadrze, stav_nadrze FROM vozidla WHERE id=?", (v_id,))
        row = c.fetchone(); conn.close()
        if row:
            for i, lbl in enumerate(self.garaz_labels):
                self.garaz_entries[lbl].delete(0, tk.END); self.garaz_entries[lbl].insert(0, str(row[i]))

    def vycisti_formular(self):
        for ent in self.garaz_entries.values(): ent.delete(0, tk.END)

    def nacitaj_vozidla(self):
        for i in self.tree_auta.get_children(): self.tree_auta.delete(i)
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("SELECT id, spz, znacka, typ, druh, phl, vin, vodic, norm_spotreba, tacho, objem_nadrze, stav_nadrze FROM vozidla")
        auta = c.fetchall(); conn.close()
        zoznam_spz = []
        self.auta_data = {}
        for a in auta:
            self.tree_auta.insert("", tk.END, values=(a[0], a[1], f"{a[2]} {a[3]}", a[7], f"{a[9]:.1f} km", f"{a[11]:.1f} l"))
            nazov = f"{a[1]} ({a[2]} {a[3]})"
            zoznam_spz.append(nazov)
            self.auta_data[nazov] = {
                "id": a[0], "znacka": a[2], "typ": a[3], "druh": a[4], "phl": a[5], 
                "vin": a[6], "vodic": a[7], "spotreba": a[8], "tacho": a[9], 
                "objem_nadrze": a[10], "stav_nadrze": a[11]
            }
        
        self.cb_vozidlo.configure(values=zoznam_spz)
        if zoznam_spz: self.cb_vozidlo.set(zoznam_spz[0]); self.on_vozidlo_zmena(None)

    # ==================== ZÁLOŽKA: GENERÁTOR ====================
    def setup_generator_ui(self):
        self.frame_generator.grid_columnconfigure(0, weight=1)
        self.frame_generator.grid_rowconfigure(1, weight=1)

        top_cards_frame = ctk.CTkFrame(self.frame_generator, fg_color="transparent")
        top_cards_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # KARTA 1: Vozidlo
        card_car = ctk.CTkFrame(top_cards_frame)
        card_car.grid(row=0, column=0, sticky="nsew", padx=5)
        ctk.CTkLabel(card_car, text="Vozidlo a Stav", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        ctk.CTkLabel(card_car, text="Aktívne vozidlo:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.cb_vozidlo = ctk.CTkComboBox(card_car, command=self.on_vozidlo_zmena)
        self.cb_vozidlo.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(card_car, text="Tachometer:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.ent_tacho = ctk.CTkEntry(card_car, width=120)
        self.ent_tacho.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        ctk.CTkLabel(card_car, text="Nádrž:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.ent_nadrz = ctk.CTkEntry(card_car, width=120)
        self.ent_nadrz.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # KARTA 2: Trasa a Dátumy
        card_route = ctk.CTkFrame(top_cards_frame)
        card_route.grid(row=0, column=1, sticky="nsew", padx=5)
        ctk.CTkLabel(card_route, text="Parametre Trasy", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, pady=10)
        
        # --- ZÍSKANIE DNEŠNÉHO DÁTUMU ---
        dnes = datetime.date.today().strftime("%d.%m.%Y")
        
        ctk.CTkLabel(card_route, text="Dátum od:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.ent_od = ctk.CTkEntry(card_route, width=100)
        self.ent_od.insert(0, dnes) 
        self.ent_od.grid(row=1, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(card_route, text="Dátum do:").grid(row=1, column=2, padx=10, pady=5, sticky="e")
        self.ent_do = ctk.CTkEntry(card_route, width=100)
        self.ent_do.insert(0, dnes) 
        self.ent_do.grid(row=1, column=3, pady=5, sticky="w")

        ctk.CTkLabel(card_route, text="Štart:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.ent_start = ctk.CTkEntry(card_route, width=100); self.ent_start.insert(0, "Stará Turá"); self.ent_start.grid(row=2, column=1, pady=5, sticky="w")
        ctk.CTkLabel(card_route, text="Cieľ:").grid(row=2, column=2, padx=10, pady=5, sticky="e")
        self.ent_koniec = ctk.CTkEntry(card_route, width=100); self.ent_koniec.insert(0, "Stará Turá"); self.ent_koniec.grid(row=2, column=3, pady=5, sticky="w")
        
        ctk.CTkLabel(card_route, text="Spolu KM:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.ent_total_km = ctk.CTkEntry(card_route, width=100); self.ent_total_km.insert(0, "130"); self.ent_total_km.grid(row=3, column=1, pady=5, sticky="w")

        # KARTA 3: Tankovanie & Akcie
        card_actions = ctk.CTkFrame(top_cards_frame)
        card_actions.grid(row=0, column=2, sticky="nsew", padx=5)
        ctk.CTkLabel(card_actions, text="Tankovanie & Spustenie", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        tank_frame = ctk.CTkFrame(card_actions, fg_color="transparent")
        tank_frame.grid(row=1, column=0, columnspan=2, pady=5)
        self.ent_tank_datum = ctk.CTkEntry(tank_frame, width=90, placeholder_text="Dátum"); self.ent_tank_datum.grid(row=0, column=0, padx=2)
        self.ent_tank_litre = ctk.CTkEntry(tank_frame, width=60, placeholder_text="Litre"); self.ent_tank_litre.grid(row=0, column=1, padx=2)
        self.ent_tank_cena = ctk.CTkEntry(tank_frame, width=60, placeholder_text="€/l"); self.ent_tank_cena.grid(row=0, column=2, padx=2)

        self.btn_gen = ctk.CTkButton(card_actions, text="GENEROVAŤ", command=self.spustit_vlakno, height=40, font=ctk.CTkFont(weight="bold", size=14))
        self.btn_gen.grid(row=2, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="ew")
        
        self.btn_exp = ctk.CTkButton(card_actions, text="EXPORT EXCEL", command=self.export_csv, fg_color="#28a745", hover_color="#218838")
        self.btn_exp.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        # Rozšírená tabuľka
        tree_frame = ctk.CTkFrame(self.frame_generator)
        tree_frame.grid(row=1, column=0, sticky="nsew", pady=10)
        self.tree = ttk.Treeview(tree_frame, columns=("d", "t", "tr", "km", "ts", "tc", "spotreba", "cerp", "cena", "zostatok"), show="headings")
        hlavicky = ["Dátum", "Čas", "Trasa", "KM", "Tacho(Š)", "Tacho(C)", "Spotreba", "Čerpané", "Cena/l", "Zostatok(l)"]
        sirky = [80, 100, 300, 60, 90, 90, 80, 80, 70, 90]
        for col, h, w in zip(self.tree['columns'], hlavicky, sirky):
            self.tree.heading(col, text=h); self.tree.column(col, width=w, anchor="center" if col not in ("tr") else "w")
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

    def on_vozidlo_zmena(self, vybrane):
        if hasattr(self, 'auta_data') and vybrane in self.auta_data:
            self.ent_tacho.delete(0, tk.END)
            self.ent_tacho.insert(0, str(self.auta_data[vybrane]["tacho"]))
            self.ent_nadrz.delete(0, tk.END)
            self.ent_nadrz.insert(0, str(self.auta_data[vybrane]["stav_nadrze"]))

    # ==================== VYLEPŠENÉ VYHĽADÁVANIE MIEST ====================
    def get_coords(self, city):
        if city in self.cache_gps: 
            return self.cache_gps[city]
            
        city_clean = city.strip()
        
        for q in [f"{city_clean}, Slovakia", city_clean]:
            try:
                url = "https://nominatim.openstreetmap.org/search"
                params = {'q': q, 'format': 'json', 'limit': 1}
                headers = {'User-Agent': 'KnihaJazdPro_SVK/1.5'}
                r = requests.get(url, params=params, headers=headers, timeout=10)
                r.raise_for_status() 
                data = r.json()
                if data:
                    c = (float(data[0]['lon']), float(data[0]['lat']))
                    self.cache_gps[city] = c
                    return c
            except Exception:
                continue
                
        return None

    def get_route(self, c1, c2):
        if c1 == c2: return 0.0, 0.0 
        if c1 not in self.cache_gps or c2 not in self.cache_gps: return None, None
        l1, t1 = self.cache_gps[c1]; l2, t2 = self.cache_gps[c2]
        try:
            r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{l1},{t1};{l2},{t2}?overview=false", timeout=5).json()
            if r["code"] == "Ok": return r["routes"][0]["distance"]/1000.0, r["routes"][0]["duration"]/60.0
        except: pass
        return None, None

    def aktualizuj_ui_tabulku(self, hodnoty):
        self.tree.insert("", tk.END, values=hodnoty)

    def spustit_vlakno(self):
        # 1. BEZPEČNOSTNÁ POISTKA: Skontroluje, či je v databáze nejaké auto
        if not hasattr(self, 'auta_data') or len(self.auta_data) == 0:
            return messagebox.showwarning("Prázdna Garáž", "Pred generovaním jázd musíte mať v Garáži pridané aspoň jedno vozidlo!")
            
        if not self.cb_vozidlo.get(): 
            return messagebox.showwarning("Chyba", "Vyberte vozidlo z Garáže.")
            
        try:
            d_od = datetime.datetime.strptime(self.ent_od.get(), "%d.%m.%Y").date()
            d_do = datetime.datetime.strptime(self.ent_do.get(), "%d.%m.%Y").date()
            dni = (d_do - d_od).days + 1
            if dni <= 0: raise ValueError
            dt = float(self.ent_total_km.get().replace(',', '.')) / dni
            tacho = float(self.ent_tacho.get().replace(',', '.'))
            nadrz_start = float(self.ent_nadrz.get().replace(',', '.'))
            
            t_datum_str = self.ent_tank_datum.get().strip()
            t_datum = None
            if t_datum_str:
                parts = t_datum_str.split('.')
                t_datum = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
                
            t_litre_str = self.ent_tank_litre.get().strip().replace(',', '.')
            t_litre = float(t_litre_str) if t_litre_str else 0.0
            t_cena = self.ent_tank_cena.get().strip().replace(',', '.')
            
        except Exception as e: 
            return messagebox.showerror("Chyba formátu", "Chybný formát dátumu (DD.MM.YYYY) alebo čísla pri tankovaní.")

        for i in self.tree.get_children(): self.tree.delete(i)
        self.btn_gen.configure(text="Beží...", state="disabled")
        auto_data = self.auta_data[self.cb_vozidlo.get()]
        auto_data["stav_nadrze"] = nadrz_start
        
        threading.Thread(target=self.vypocet_na_pozadi, args=(d_od, d_do, dt, tacho, self.ent_start.get().strip(), self.ent_koniec.get().strip(), auto_data, t_datum, t_litre, t_cena), daemon=True).start()

    def vypocet_na_pozadi(self, d_od, d_do, denny_target, tacho, start_m, koniec_m, auto_data, t_datum, t_litre, t_cena):
        c_start = self.get_coords(start_m)
        c_koniec = self.get_coords(koniec_m)
        
        if not c_start:
            self.after(0, lambda: messagebox.showerror("Chyba hľadania", f"Súradnice pre mesto ŠTART sa nenašli:\n'{start_m}'\nSkontrolujte preklep."))
            self.after(0, lambda: self.btn_gen.configure(text="GENEROVAŤ", state="normal"))
            return
            
        if not c_koniec:
            self.after(0, lambda: messagebox.showerror("Chyba hľadania", f"Súradnice pre mesto CIEĽ sa nenašli:\n'{koniec_m}'\nSkontrolujte preklep."))
            self.after(0, lambda: self.btn_gen.configure(text="GENEROVAŤ", state="normal"))
            return

        m_pool = list(VELKA_DATABAZA.keys())
        curr_d = d_od; spotreba_norm = auto_data["spotreba"]
        zvysena_spotreba = spotreba_norm * 1.17
        
        akt_nadrz = auto_data["stav_nadrze"]
        max_nadrz = auto_data["objem_nadrze"]
        tankovane_uz = False 

        def zostav_riadok(datum_str, cas_str, trasa, km, start_t, ciel_t, spotr):
            nonlocal tankovane_uz, akt_nadrz
            c_litre = ""; c_eur = ""
            if t_datum and t_litre > 0 and not tankovane_uz and curr_d == t_datum:
                c_litre = f"{t_litre:.2f}"; c_eur = t_cena
                akt_nadrz += t_litre
                if akt_nadrz > max_nadrz: akt_nadrz = max_nadrz 
                tankovane_uz = True
            akt_nadrz -= float(spotr)
            if akt_nadrz < 0: akt_nadrz = 0
            return (datum_str, cas_str, trasa, f"{km:.1f}", f"{start_t:.1f}", f"{ciel_t:.1f}", f"{spotr:.2f}", c_litre, c_eur, f"{akt_nadrz:.2f}")

        while curr_d <= d_do:
            zostatok_km = denny_target; curr_m = start_m
            curr_time = datetime.datetime.combine(curr_d, datetime.time(8, 0))
            j_cislo = 0; den_str = curr_d.strftime("%d.%m.%Y")
            
            while zostatok_km > 0.1:
                d_home, t_home = self.get_route(curr_m, koniec_m)
                if d_home is None: d_home = 0
                
                if j_cislo >= 6:
                    jazda_dist = zostatok_km
                    label = f"{curr_m} -> {koniec_m}" if curr_m != koniec_m else f"{curr_m} -> {curr_m}"
                    t_dur = int((jazda_dist/50)*60) or 5
                    spotr = (jazda_dist / 100) * zvysena_spotreba
                    odchod = curr_time.strftime("%H:%M"); curr_time += datetime.timedelta(minutes=t_dur); prichod = curr_time.strftime("%H:%M")
                    h = zostav_riadok(den_str, f"{odchod}-{prichod}", label, jazda_dist, tacho, tacho+jazda_dist, spotr)
                    self.after(0, self.aktualizuj_ui_tabulku, h); tacho += jazda_dist; zostatok_km = 0; break

                if curr_m == koniec_m and zostatok_km <= 30:
                    jazda_dist = zostatok_km
                    t_dur = int((jazda_dist/50)*60) or 5
                    spotr = (jazda_dist / 100) * zvysena_spotreba
                    odchod = curr_time.strftime("%H:%M"); curr_time += datetime.timedelta(minutes=t_dur); prichod = curr_time.strftime("%H:%M")
                    h = zostav_riadok(den_str, f"{odchod}-{prichod}", f"{curr_m} -> {curr_m}", jazda_dist, tacho, tacho+jazda_dist, spotr)
                    self.after(0, self.aktualizuj_ui_tabulku, h); tacho += jazda_dist; zostatok_km = 0; break

                if curr_m != koniec_m and zostatok_km <= d_home + 5:
                    jazda_dist = min(d_home, zostatok_km)
                    t_dur = int(t_home or (jazda_dist/50)*60) or 10
                    spotr = (jazda_dist / 100) * zvysena_spotreba
                    odchod = curr_time.strftime("%H:%M"); curr_time += datetime.timedelta(minutes=t_dur); prichod = curr_time.strftime("%H:%M")
                    h = zostav_riadok(den_str, f"{odchod}-{prichod}", f"{curr_m} -> {koniec_m}", jazda_dist, tacho, tacho+jazda_dist, spotr)
                    self.after(0, self.aktualizuj_ui_tabulku, h)
                    tacho += jazda_dist; zostatok_km -= jazda_dist; curr_m = koniec_m
                    curr_time += datetime.timedelta(minutes=random.randint(15, 30)); j_cislo += 1; continue

                kand = []
                lc, tc = self.cache_gps[curr_m]; le, te = self.cache_gps[koniec_m]
                for c in m_pool:
                    if c in (curr_m, koniec_m): continue 
                    lx, tx = self.cache_gps[c]
                    odh = (vzdusna_vzdialenost(lc,tc,lx,tx) + vzdusna_vzdialenost(lx,tx,le,te)) * 1.3
                    if odh <= zostatok_km: kand.append((c, odh))
                    
                kand.sort(key=lambda x: x[1], reverse=True)
                best_c, best_d, best_t = None, 0, 0
                for c, _ in kand[:6]:
                    d_t, t_t = self.get_route(curr_m, c); d_b, _ = self.get_route(c, koniec_m)
                    if d_t and d_b and (d_t + d_b <= zostatok_km):
                        best_c, best_d, best_t = c, d_t, t_t; break 
                        
                if not best_c:
                    best_c = curr_m
                    best_d = max(1.0, zostatok_km) if curr_m == koniec_m else max(1.0, (zostatok_km - d_home) / 2)
                    best_t = (best_d / 40) * 60
                    
                jazda_dist = best_d; t_dur = int(best_t or 10); spotr = (jazda_dist / 100) * zvysena_spotreba
                odchod = curr_time.strftime("%H:%M"); curr_time += datetime.timedelta(minutes=t_dur); prichod = curr_time.strftime("%H:%M")
                h = zostav_riadok(den_str, f"{odchod}-{prichod}", f"{curr_m} -> {best_c}", jazda_dist, tacho, tacho+jazda_dist, spotr)
                self.after(0, self.aktualizuj_ui_tabulku, h)
                
                tacho += jazda_dist; zostatok_km -= jazda_dist; curr_m = best_c
                curr_time += datetime.timedelta(minutes=random.randint(15, 45)); j_cislo += 1
                
            curr_d += datetime.timedelta(days=1)
            
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("UPDATE vozidla SET tacho=?, stav_nadrze=? WHERE id=?", (tacho, akt_nadrz, auto_data["id"]))
        conn.commit(); conn.close()
        
        self.after(0, self.nacitaj_vozidla)
        self.after(0, lambda: self.btn_gen.configure(text="GENEROVAŤ", state="normal"))

    # --- EXPORT ---
    def export_csv(self):
        if not self.cb_vozidlo.get(): return messagebox.showerror("Chyba", "Vyberte vozidlo.")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Excel", "*.csv")])
        if not path: return
        auto = self.auta_data[self.cb_vozidlo.get()]
        zvysena_spotreba = auto['spotreba'] * 1.17
        try:
            with open(path, mode='w', encoding='utf-8-sig', newline='') as f:
                w = csv.writer(f, delimiter=';')
                w.writerow(["Vozidlo:", auto['znacka'], "", "Druh:", auto['druh'], "Normovaná spotreba:", f"{auto['spotreba']}"])
                w.writerow(["Typ:", auto['typ'], "", "VIN Číslo:", auto['vin'], "Zvýšená spotreba:", f"{zvysena_spotreba:.2f}"])
                w.writerow(["PHL:", auto['phl'], "", "", "", "", ""]); w.writerow([])
                w.writerow(["P.č.", "Dátum", "Čas", "Trasa", "Vodič", "Účel", "Km", "Tachometer", "Čerpané", "EUR/l", "Spotreba", "Zostatok v nádrži"])
                for index, row_id in enumerate(self.tree.get_children()):
                    val = self.tree.item(row_id)["values"]
                    w.writerow([index + 1, val[0], val[1], val[2], auto['vodic'], "Služobná cesta", val[3], val[5], val[7], val[8], val[6], val[9]])
            messagebox.showinfo("Úspech", "Kniha jázd bola uložená.")
        except Exception as e: messagebox.showerror("Chyba", f"Nepodarilo sa uložiť.\n{e}")

if __name__ == "__main__":
    app = KnihaJazdApp()
    app.mainloop()