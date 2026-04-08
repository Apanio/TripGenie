# TripGenie

# 🧞‍♂️ TripGenie - Generátor Knihy Jázd PRO

TripGenie je moderná a rýchla desktopová aplikácia napísaná v Pythone, ktorá slúži na automatizované generovanie knihy jázd pre firemné a súkromné vozidlá. Vďaka prepojeniu na mapové služby dokáže inteligentne vypočítať trasy, simulovať denné jazdy a exportovať hotové dáta priamo do Excelu.

## ✨ Hlavné funkcie

* **🚗 Virtuálna Garáž:** Kompletná evidencia vozidiel (ŠPZ, značka, VIN, objem nádrže, normovaná spotreba).
* **🗺️ Inteligentné trasy (OSRM & Nominatim):** Automatický výpočet reálnych dojazdových vzdialeností medzi slovenskými mestami. Aplikácia dynamicky hľadá ciele, aby naplnila tvoj požadovaný denný limit kilometrov.
* **⛽ Tankovanie a spotreba:** Realistický odpočet z nádrže podľa vypočítanej spotreby (+17 % pre mestskú prevádzku) s možnosťou manuálneho vloženia údajov za tankovanie (litre a cena).
* **📊 Export pre účtovníka:** Jedným kliknutím vygeneruješ prehľadný `.csv` súbor pripravený pre Excel alebo účtovný softvér.
* **🌗 Moderný UI dizajn:** Aplikácia využíva `CustomTkinter` a plne podporuje svetlý aj tmavý režim (Dark Mode) podľa nastavenia tvojho operačného systému.
* **🍏 Plná podpora pre macOS a Windows:** Aplikácia bezpečne izoluje databázu do vyhradeného používateľského priestoru pre bezproblémový beh na Macu bez pádov (TCC bypass).

---

## 🚀 Rýchly štart (Ako používať aplikáciu)

### 1. Pridanie vozidla (Záložka: Garáž)
Pred generovaním jázd musíš mať v systéme aspoň jedno vozidlo.
1. Prejdi do ľavého menu a klikni na **Garáž (Vozidlá)**.
2. Vyplň údaje (ŠPZ, normovanú spotrebu, počiatočný stav tachometra a aktuálny stav nádrže).
3. Klikni na **Pridať nové vozidlo**.

### 2. Parametre jázd (Záložka: Generátor Jázd)
1. Vyber si vozidlo z rozbaľovacieho zoznamu (tachometer a nádrž sa načítajú automaticky).
2. Nastav dátum od-do a vyber štartovacie a cieľové mesto.
3. Zadaj **Spolu KM** (koľko kilometrov chceš v danom období celkovo vygenerovať).
4. *(Voliteľné)* Ak chceš do knihy jázd pridať tankovanie, vyplň Dátum, Litre a Cenu.

### 3. Generovanie a Export
1. Klikni na **GENEROVAŤ**. Aplikácia na pozadí prepočíta súradnice a vytvorí logickú postupnosť jázd.
2. Skontroluj vygenerovanú tabuľku (časy odchodov/príchodov, zostatok v nádrži).
3. Klikni na **EXPORT EXCEL** a ulož si hotovú knihu jázd ako `.csv` súbor.

---

### 📂 Kde sa ukladajú dáta?
Aplikácia funguje plne offline (s výnimkou sťahovania GPS súradníc). Databáza kniha_jazd.db sa z bezpečnostných dôvodov na macOS ukladá do skrytého priečinka ~/.tripgenie, aby sa predišlo konfliktom s prístupovými právami. Pri Windows sa databáza ukladá na miesto odkiaľ sa spúšťa .exe

**Ak máš nápady na vylepšenie, neváhaj vytvoriť Pull Request alebo otvoriť Issue!**
#