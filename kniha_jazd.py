import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import requests
import random
import datetime
import csv
import math
import threading

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

# --- INICIALIZÁCIA A MIGRÁCIA SQLITE ---
def init_db():
    conn = sqlite3.connect("kniha_jazd.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS vozidla (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 spz TEXT, znacka TEXT, typ TEXT, druh TEXT,
                 phl TEXT, vin TEXT, vodic TEXT, norm_spotreba REAL, tacho REAL)''')
    # Migrácia: Bezpečné pridanie nových stĺpcov, ak existuje stará databáza
    try: c.execute("ALTER TABLE vozidla ADD COLUMN objem_nadrze REAL DEFAULT 50.0")
    except: pass
    try: c.execute("ALTER TABLE vozidla ADD COLUMN stav_nadrze REAL DEFAULT 0.0")
    except: pass
    
    conn.commit()
    conn.close()

class KnihaJazdApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Kniha Jázd PRO 12.0 - Complete Edition")
        self.root.geometry("1300x850")
        self.cache_gps = VELKA_DATABAZA.copy()
        
        init_db()
        
        self.notebook = ttk.Notebook(self.root)
        self.tab_generator = tk.Frame(self.notebook)
        self.tab_garaz = tk.Frame(self.notebook)
        self.notebook.add(self.tab_generator, text="Generátor Jázd")
        self.notebook.add(self.tab_garaz, text="Garáž (Vozidlá)")
        self.notebook.pack(expand=1, fill="both")

        self.setup_garaz_ui()
        self.setup_generator_ui()
        self.nacitaj_vozidla()

    # ==================== ZÁLOŽKA: GARÁŽ ====================
    def setup_garaz_ui(self):
        form = tk.LabelFrame(self.tab_garaz, text="Pridať / Upraviť Vozidlo", padx=10, pady=10)
        form.pack(fill="x", padx=10, pady=10)

        self.garaz_labels = [
            "ŠPZ / Názov:", "Značka:", "Typ/Model:", "Druh:", "PHL:", "VIN číslo:", 
            "Vodič:", "Norm. spotreba (l):", "Tachometer (Štart):", "Objem nádrže (l):", "Stav v nádrži (l):"
        ]
        self.garaz_entries = {}
        
        for i, lbl in enumerate(self.garaz_labels):
            tk.Label(form, text=lbl).grid(row=i//4, column=(i%4)*2, sticky="e", padx=5, pady=5)
            ent = tk.Entry(form, width=18)
            ent.grid(row=i//4, column=(i%4)*2+1, sticky="w", padx=5, pady=5)
            self.garaz_entries[lbl] = ent

        btn_frame = tk.Frame(form)
        btn_frame.grid(row=4, column=0, columnspan=8, pady=10)
        tk.Button(btn_frame, text="Pridať nové vozidlo", bg="#4CAF50", fg="white", command=self.pridat_vozidlo).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Upraviť vybrané", bg="#2196F3", fg="white", command=self.upravit_vozidlo).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Vymazať", bg="#f44336", fg="white", command=self.vymazat_vozidlo).pack(side="left", padx=10)

        self.tree_auta = ttk.Treeview(self.tab_garaz, columns=("id", "spz", "auto", "vodic", "tacho", "nadrz"), show="headings")
        for c, h, w in zip(self.tree_auta['columns'], ["ID", "ŠPZ", "Vozidlo", "Vodič", "Tachometer", "Nádrž (l)"], [30, 100, 250, 150, 100, 100]):
            self.tree_auta.heading(c, text=h); self.tree_auta.column(c, width=w)
        self.tree_auta.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Udalosť: Kliknutie na riadok načíta údaje do formulára
        self.tree_auta.bind("<<TreeviewSelect>>", self.nacitaj_do_formulara)

    def ziskaj_hodnoty_z_formulara(self):
        hodnoty = [self.garaz_entries[lbl].get().strip() for lbl in self.garaz_labels]
        if not hodnoty[0]: 
            messagebox.showerror("Chyba", "ŠPZ je povinná!")
            return None
        try:
            spotreba = float(hodnoty[7].replace(',', '.')) if hodnoty[7] else 0.0
            tacho = float(hodnoty[8].replace(',', '.')) if hodnoty[8] else 0.0
            objem = float(hodnoty[9].replace(',', '.')) if hodnoty[9] else 50.0
            stav = float(hodnoty[10].replace(',', '.')) if hodnoty[10] else 0.0
            return (*hodnoty[:7], spotreba, tacho, objem, stav)
        except: 
            messagebox.showerror("Chyba", "Spotreba, Tachometer a Nádrž musia byť čísla.")
            return None

    def pridat_vozidlo(self):
        data = self.ziskaj_hodnoty_z_formulara()
        if not data: return
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("INSERT INTO vozidla (spz, znacka, typ, druh, phl, vin, vodic, norm_spotreba, tacho, objem_nadrze, stav_nadrze) VALUES (?,?,?,?,?,?,?,?,?,?,?)", data)
        conn.commit(); conn.close()
        self.vycisti_formular(); self.nacitaj_vozidla()
        messagebox.showinfo("Úspech", "Nové vozidlo pridané.")

    def upravit_vozidlo(self):
        vybrane = self.tree_auta.selection()
        if not vybrane: return messagebox.showwarning("Upozornenie", "Najprv kliknite na vozidlo v tabuľke, ktoré chcete upraviť.")
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        data = self.ziskaj_hodnoty_z_formulara()
        if not data: return
        
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute('''UPDATE vozidla SET spz=?, znacka=?, typ=?, druh=?, phl=?, vin=?, vodic=?, 
                     norm_spotreba=?, tacho=?, objem_nadrze=?, stav_nadrze=? WHERE id=?''', (*data, v_id))
        conn.commit(); conn.close()
        self.vycisti_formular(); self.nacitaj_vozidla()
        messagebox.showinfo("Úspech", "Údaje vozidla boli zmenené.")

    def vymazat_vozidlo(self):
        vybrane = self.tree_auta.selection()
        if not vybrane: return
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("DELETE FROM vozidla WHERE id=?", (v_id,)); conn.commit(); conn.close()
        self.vycisti_formular(); self.nacitaj_vozidla()

    def nacitaj_do_formulara(self, event):
        vybrane = self.tree_auta.selection()
        if not vybrane: return
        v_id = self.tree_auta.item(vybrane[0])['values'][0]
        
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("SELECT spz, znacka, typ, druh, phl, vin, vodic, norm_spotreba, tacho, objem_nadrze, stav_nadrze FROM vozidla WHERE id=?", (v_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            for i, lbl in enumerate(self.garaz_labels):
                self.garaz_entries[lbl].delete(0, tk.END)
                self.garaz_entries[lbl].insert(0, str(row[i]))

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
            
        self.cb_vozidlo['values'] = zoznam_spz
        if zoznam_spz: self.cb_vozidlo.current(0); self.on_vozidlo_zmena(None)

    # ==================== ZÁLOŽKA: GENERÁTOR ====================
    def setup_generator_ui(self):
        top = tk.LabelFrame(self.tab_generator, text="Parametre Simulácie", padx=10, pady=10)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Aktívne vozidlo:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.cb_vozidlo = ttk.Combobox(top, width=30, state="readonly")
        self.cb_vozidlo.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        self.cb_vozidlo.bind("<<ComboboxSelected>>", self.on_vozidlo_zmena)

        tk.Label(top, text="Tachometer:").grid(row=0, column=3, sticky="e")
        self.ent_tacho = tk.Entry(top, width=10); self.ent_tacho.grid(row=0, column=4, padx=5)
        
        tk.Label(top, text="Stav nádrže:").grid(row=0, column=5, sticky="e")
        self.ent_nadrz = tk.Entry(top, width=10); self.ent_nadrz.grid(row=0, column=6, padx=5)

        tk.Label(top, text="Dátum od:").grid(row=1, column=0, sticky="w")
        self.ent_od = tk.Entry(top, width=12); self.ent_od.insert(0, "01.03.2025"); self.ent_od.grid(row=1, column=1, padx=5, pady=5)
        tk.Label(top, text="Dátum do:").grid(row=1, column=2, sticky="e")
        self.ent_do = tk.Entry(top, width=12); self.ent_do.insert(0, "05.03.2025"); self.ent_do.grid(row=1, column=3, padx=5, pady=5)

        tk.Label(top, text="Štart dňa:").grid(row=2, column=0, sticky="w")
        self.ent_start = tk.Entry(top, width=20); self.ent_start.insert(0, "Stará Turá"); self.ent_start.grid(row=2, column=1, padx=5, pady=5)
        tk.Label(top, text="Koncový bod:").grid(row=2, column=2, sticky="e")
        self.ent_koniec = tk.Entry(top, width=20); self.ent_koniec.insert(0, "Stará Turá"); self.ent_koniec.grid(row=2, column=3, padx=5, pady=5)
        tk.Label(top, text="Cieľové KM spolu:").grid(row=2, column=4, sticky="e")
        self.ent_total_km = tk.Entry(top, width=10); self.ent_total_km.insert(0, "130"); self.ent_total_km.grid(row=2, column=5, padx=5, pady=5)

        # Manuálne Tankovanie
        frame_tank = tk.LabelFrame(top, text="Bloček z čerpacej stanice (Voliteľné)", fg="#d32f2f")
        frame_tank.grid(row=3, column=0, columnspan=6, sticky="we", pady=10)
        
        tk.Label(frame_tank, text="Dátum:").grid(row=0, column=0, padx=5, pady=5)
        self.ent_tank_datum = tk.Entry(frame_tank, width=12); self.ent_tank_datum.grid(row=0, column=1, padx=5)
        tk.Label(frame_tank, text="Natankované litre:").grid(row=0, column=2, padx=5)
        self.ent_tank_litre = tk.Entry(frame_tank, width=10); self.ent_tank_litre.grid(row=0, column=3, padx=5)
        tk.Label(frame_tank, text="Cena (€/l):").grid(row=0, column=4, padx=5)
        self.ent_tank_cena = tk.Entry(frame_tank, width=10); self.ent_tank_cena.grid(row=0, column=5, padx=5)

        self.btn_gen = tk.Button(top, text="GENEROVAŤ", bg="#1976D2", fg="white", font=("Arial", 10, "bold"), command=self.spustit_vlakno)
        self.btn_gen.grid(row=0, column=7, rowspan=2, padx=10, sticky="nsew")
        self.btn_exp = tk.Button(top, text="EXPORT EXCEL", bg="#4CAF50", fg="white", command=self.export_csv)
        self.btn_exp.grid(row=2, column=7, rowspan=2, padx=10, sticky="nsew")

        # Rozšírená tabuľka
        self.tree = ttk.Treeview(self.tab_generator, columns=("d", "t", "tr", "km", "ts", "tc", "spotreba", "cerp", "cena", "zostatok"), show="headings")
        hlavicky = ["Dátum", "Čas", "Trasa", "KM", "Tacho(Š)", "Tacho(C)", "Spotreba", "Čerpané", "Cena/l", "Zostatok(l)"]
        sirky = [75, 90, 240, 50, 75, 75, 70, 70, 60, 80]
        for col, h, w in zip(self.tree['columns'], hlavicky, sirky):
            self.tree.heading(col, text=h); self.tree.column(col, width=w, anchor="center" if col not in ("tr") else "w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_vozidlo_zmena(self, event):
        vybrane = self.cb_vozidlo.get()
        if vybrane in self.auta_data:
            self.ent_tacho.delete(0, tk.END)
            self.ent_tacho.insert(0, str(self.auta_data[vybrane]["tacho"]))
            self.ent_nadrz.delete(0, tk.END)
            self.ent_nadrz.insert(0, str(self.auta_data[vybrane]["stav_nadrze"]))

    def get_coords(self, city):
        if city in self.cache_gps: return self.cache_gps[city]
        try:
            r = requests.get(f"https://nominatim.openstreetmap.org/search?q={city},+Slovakia&format=json&limit=1", headers={'User-Agent': 'KnihaJazdPro'}, timeout=5).json()
            if r:
                c = (float(r[0]['lon']), float(r[0]['lat'])); self.cache_gps[city] = c; return c
        except: pass
        return None

    def get_route(self, c1, c2):
        if c1 == c2: return 0.0, 0.0 
        l1, t1 = self.cache_gps[c1]; l2, t2 = self.cache_gps[c2]
        try:
            r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{l1},{t1};{l2},{t2}?overview=false", timeout=5).json()
            if r["code"] == "Ok": return r["routes"][0]["distance"]/1000.0, r["routes"][0]["duration"]/60.0
        except: pass
        return None, None

    def aktualizuj_ui_tabulku(self, hodnoty):
        self.tree.insert("", tk.END, values=hodnoty)

    def spustit_vlakno(self):
        if not self.cb_vozidlo.get(): return messagebox.showerror("Chyba", "Najprv pridajte a vyberte vozidlo v Garáži.")
        try:
            d_od = datetime.datetime.strptime(self.ent_od.get(), "%d.%m.%Y").date()
            d_do = datetime.datetime.strptime(self.ent_do.get(), "%d.%m.%Y").date()
            dni = (d_do - d_od).days + 1
            if dni <= 0: raise ValueError
            dt = float(self.ent_total_km.get().replace(',', '.')) / dni
            tacho = float(self.ent_tacho.get().replace(',', '.'))
            nadrz_start = float(self.ent_nadrz.get().replace(',', '.'))
            
            t_datum = self.ent_tank_datum.get().strip()
            t_litre = self.ent_tank_litre.get().strip().replace(',', '.')
            t_cena = self.ent_tank_cena.get().strip().replace(',', '.')
        except: return messagebox.showerror("Chyba", "Chybný formát dátumu alebo čísla.")

        for i in self.tree.get_children(): self.tree.delete(i)
        self.btn_gen.config(text="Beží...", state="disabled")
        auto_data = self.auta_data[self.cb_vozidlo.get()]
        auto_data["stav_nadrze"] = nadrz_start # Ak si to užívateľ ručne prepísal v GUI
        
        threading.Thread(target=self.vypocet_na_pozadi, args=(d_od, d_do, dt, tacho, self.ent_start.get().strip(), self.ent_koniec.get().strip(), auto_data, t_datum, t_litre, t_cena), daemon=True).start()

    # --- JADRO S MATEMATIKOU NÁDRŽE ---
    def vypocet_na_pozadi(self, d_od, d_do, denny_target, tacho, start_m, koniec_m, auto_data, t_datum, t_litre, t_cena):
        if not self.get_coords(start_m) or not self.get_coords(koniec_m):
            self.root.after(0, lambda: messagebox.showerror("Chyba", "Mesto sa nenašlo.")); self.root.after(0, lambda: self.btn_gen.config(text="GENEROVAŤ", state="normal")); return

        m_pool = list(VELKA_DATABAZA.keys())
        curr_d = d_od; spotreba_norm = auto_data["spotreba"]
        zvysena_spotreba = spotreba_norm * 1.17
        
        akt_nadrz = auto_data["stav_nadrze"]
        max_nadrz = auto_data["objem_nadrze"]
        tankovane_uz = False 

        # Sub-funkcia ktorá rieši matematiku tankovania pre každý riadok
        def zostav_riadok(datum_str, cas_str, trasa, km, start_t, ciel_t, spotr):
            nonlocal tankovane_uz, akt_nadrz
            c_litre = ""; c_eur = ""
            
            # Pripočítanie tankovania (ak sedí dátum)
            if t_datum and t_litre and not tankovane_uz and datum_str == t_datum:
                c_litre = t_litre
                c_eur = t_cena
                akt_nadrz += float(t_litre)
                if akt_nadrz > max_nadrz: akt_nadrz = max_nadrz # Nesmie pretiecť objem
                tankovane_uz = True
            
            # Odpočítanie spotreby
            akt_nadrz -= float(spotr)
            if akt_nadrz < 0: akt_nadrz = 0
            
            return (datum_str, cas_str, trasa, f"{km:.1f}", f"{start_t:.1f}", f"{ciel_t:.1f}", f"{spotr:.2f}", c_litre, c_eur, f"{akt_nadrz:.2f}")

        while curr_d <= d_do:
            zostatok_km = denny_target
            curr_m = start_m
            curr_time = datetime.datetime.combine(curr_d, datetime.time(8, 0))
            j_cislo = 0; den_str = curr_d.strftime("%d.%m.%Y")
            
            while j_cislo < 8 and zostatok_km > 2:
                d_home, t_home = self.get_route(curr_m, koniec_m)
                if d_home is None: d_home = 0
                
                if curr_m == koniec_m and zostatok_km <= 5:
                    odchod = curr_time.strftime("%H:%M")
                    curr_time += datetime.timedelta(minutes=int((zostatok_km/60)*60) if zostatok_km>0 else 1)
                    spotr = (zostatok_km / 100) * zvysena_spotreba
                    h = zostav_riadok(den_str, f"{odchod}-{curr_time.strftime('%H:%M')}", "Lokálne jazdy", zostatok_km, tacho, tacho+zostatok_km, spotr)
                    self.root.after(0, self.aktualizuj_ui_tabulku, h); tacho += zostatok_km; break 
                        
                if curr_m != koniec_m and (zostatok_km - d_home <= 15 or j_cislo >= 7):
                    if d_home > 0:
                        odchod = curr_time.strftime("%H:%M")
                        curr_time += datetime.timedelta(minutes=int(t_home))
                        spotr = (d_home / 100) * zvysena_spotreba
                        h = zostav_riadok(den_str, f"{odchod}-{curr_time.strftime('%H:%M')}", f"{curr_m} -> {koniec_m}", d_home, tacho, tacho+d_home, spotr)
                        self.root.after(0, self.aktualizuj_ui_tabulku, h)
                        tacho += d_home; zostatok_km -= d_home; curr_m = koniec_m
                        curr_time += datetime.timedelta(minutes=random.randint(15, 60))
                    j_cislo += 1; continue
                
                kand = []
                lc, tc = self.cache_gps[curr_m]; le, te = self.cache_gps[koniec_m]
                for c in m_pool:
                    if c == curr_m or (c == koniec_m and zostatok_km > 25): continue 
                    lx, tx = self.cache_gps[c]
                    odh = (vzdusna_vzdialenost(lc,tc,lx,tx) + vzdusna_vzdialenost(lx,tx,le,te)) * 1.3
                    if odh <= zostatok_km + 20: kand.append((c, odh))
                
                kand.sort(key=lambda x: abs((zostatok_km * 0.7) - x[1]))
                best_c = None; best_d = 0; best_t = 0
                
                for c, _ in kand[:8]:
                    d_t, t_t = self.get_route(curr_m, c); d_b, _ = self.get_route(c, koniec_m)
                    if d_t and d_b and (d_t + d_b <= zostatok_km + 10):
                        best_c = c; best_d = d_t; best_t = t_t; break 
                
                if not best_c and zostatok_km > 25:
                    for c, _ in sorted(kand, key=lambda x: x[1])[:5]:
                        d_t, t_t = self.get_route(curr_m, c); d_b, _ = self.get_route(c, koniec_m)
                        if d_t and d_b and (d_t + d_b <= zostatok_km + 30):
                            best_c = c; best_d = d_t; best_t = t_t; break
                
                if best_c:
                    odchod = curr_time.strftime("%H:%M")
                    curr_time += datetime.timedelta(minutes=int(best_t))
                    spotr = (best_d / 100) * zvysena_spotreba
                    h = zostav_riadok(den_str, f"{odchod}-{curr_time.strftime('%H:%M')}", f"{curr_m} -> {best_c}", best_d, tacho, tacho+best_d, spotr)
                    self.root.after(0, self.aktualizuj_ui_tabulku, h)
                    tacho += best_d; zostatok_km -= best_d; curr_m = best_c
                    curr_time += datetime.timedelta(minutes=random.randint(15, 60))
                else:
                    if curr_m != koniec_m:
                        odchod = curr_time.strftime("%H:%M")
                        curr_time += datetime.timedelta(minutes=int(t_home))
                        spotr = (d_home / 100) * zvysena_spotreba
                        h = zostav_riadok(den_str, f"{odchod}-{curr_time.strftime('%H:%M')}", f"{curr_m} -> {koniec_m}", d_home, tacho, tacho+d_home, spotr)
                        self.root.after(0, self.aktualizuj_ui_tabulku, h)
                        tacho += d_home; zostatok_km -= d_home; curr_m = koniec_m
                        curr_time += datetime.timedelta(minutes=random.randint(15, 60))
                    else:
                        if zostatok_km > 0:
                            odchod = curr_time.strftime("%H:%M")
                            curr_time += datetime.timedelta(minutes=int((zostatok_km/60)*60) if zostatok_km>0 else 5)
                            spotr = (zostatok_km / 100) * zvysena_spotreba
                            h = zostav_riadok(den_str, f"{odchod}-{curr_time.strftime('%H:%M')}", curr_m + " -> Jazdy po okolí", zostatok_km, tacho, tacho+zostatok_km, spotr)
                            self.root.after(0, self.aktualizuj_ui_tabulku, h)
                            tacho += zostatok_km; zostatok_km = 0
                        break
                j_cislo += 1
            curr_d += datetime.timedelta(days=1)
            
        # Aktualizácia tachometra a nádrže v databáze po dokončení !
        conn = sqlite3.connect("kniha_jazd.db"); c = conn.cursor()
        c.execute("UPDATE vozidla SET tacho=?, stav_nadrze=? WHERE id=?", (tacho, akt_nadrz, auto_data["id"]))
        conn.commit(); conn.close()
        
        self.root.after(0, self.nacitaj_vozidla)
        self.root.after(0, lambda: self.btn_gen.config(text="GENEROVAŤ", state="normal"))

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
                w.writerow(["PHL:", auto['phl'], "", "", "", "", ""])
                w.writerow([])
                
                w.writerow(["P.č.", "Dátum", "Čas", "Trasa", "Vodič", "Účel", "Km", "Tachometer", "Čerpané", "EUR/l", "Spotreba", "Zostatok v nádrži"])
                
                for index, row_id in enumerate(self.tree.get_children()):
                    val = self.tree.item(row_id)["values"]
                    w.writerow([
                        index + 1,        
                        val[0],           # Dátum
                        val[1],           # Čas
                        val[2],           # Trasa
                        auto['vodic'],    # Vodič
                        "Služobná cesta", # Účel
                        val[3],           # Km
                        val[5],           # Tachometer (Cieľ)
                        val[7],           # Čerpané (Litre)
                        val[8],           # EUR/l
                        val[6],           # Spotreba
                        val[9]            # Zostatok v nádrži (Už sa reálne vypisuje)
                    ])
            messagebox.showinfo("Úspech", "Kniha jázd bola uložená.")
        except Exception as e: messagebox.showerror("Chyba", f"Nepodarilo sa uložiť.\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = KnihaJazdApp(root)
    root.mainloop()