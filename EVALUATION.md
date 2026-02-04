# Evaluering af Repository-skaber

**Repository:** KCD2 Potions Helper  
**Type:** Python desktop-applikation (Tkinter GUI + CLI)  
**Omfang:** ~1500 linjer kode, utility-værktøj til spil  
**Evalueret:** Februar 2026

> **Vigtig kontekst:** Dette er et personligt/community utility-projekt lavet i Python, ikke et frontend-fokuseret produkt. Evalueringen tager højde for projektets naturlige scope og formål.

---

## Scores

| Kategori | Score | Kontekst-justeret |
|----------|-------|-------------------|
| UI-implementering | 6/10 | Solid for projekttypen |
| UX-forståelse | 7/10 | God brugerforståelse |
| Design systemer | 5/10 | Passende for scope |
| Prototyping | N/A | Ikke relevant for projekttypen |
| Performance | 6/10 | Passende for datamængden |
| **Gennemsnit** | **6/10** | (ekskl. Prototyping) |

---

## 1. UI-implementering: 6/10

**Definition:** Evnen til at omsætte design og krav til fungerende, stabil og konsistent brugergrænseflade i kode.

### Styrker
- Velstruktureret klassebaseret arkitektur (`PotionGUI` klasse)
- God brug af Tkinter/ttk komponenter til formålet
- Custom styling system med centraliserede farver og fonts
- Avancerede UI-elementer: Treeviews med sortering, notebooks, paned windows, scrollable canvas
- Form-validering for numeriske inputs
- Kontekstmenuer og keyboard shortcuts (Delete, BackSpace)
- Markdown-lignende rendering i detail-panel
- Menu bar med logisk organisering

### Eksempler fra koden
```python
# Centraliseret styling - viser bevidsthed om konsistens
self.colors = {
    "bg": "#f4f4f6",
    "toolbar": "#e0e0e5", 
    "accent": "#4f6fa9",
    "warning": "#9c4d4d",
}

# Custom Treeview styling
style.configure("Modern.Treeview", font=base_font, rowheight=26)
style.map("Modern.Treeview",
    background=[("selected", self.colors["accent"])],
    foreground=[("selected", "white")],
)
```

### Noter (ikke detraktorer)
- Projektet bruger Tkinter (Python) fremfor web-teknologier - dette er et passende valg for et desktop utility-værktøj
- Ingen responsive web design - ikke relevant for desktop app
- Ingen ARIA/accessibility - ville være overkill for personligt værktøj

---

## 2. UX-forståelse: 7/10

**Definition:** Evnen til at forstå brugernes behov, adfærd og kontekst og omsætte det til brugbare og intuitive løsninger.

### Styrker
- **Klar og logisk brugerrejse:**
  1. Indtast inventory (med filter)
  2. Se craftable potions (med søg/sort)
  3. Planlæg brews (med quantity editing)
  4. Generer shopping list (buy vs sell)
- Auto-recompute giver øjeblikkelig feedback
- Søg/filter funktionalitet i alle relevante views
- Tabs organiserer information logisk
- Double-click til hurtig redigering
- Statusbar med kontekstuel feedback
- Attribution og link til original kilde

### Gode UX-beslutninger
```python
# Debouncing forhindrer irriterende genberegninger
AUTO_RECOMPUTE_DELAY = 400

# Shopping list med farvekodning
self.shop_tree.tag_configure("buy", foreground=self.colors["accent"])
self.shop_tree.tag_configure("sell", foreground="#7a5c2f")
```

### Målgruppe-forståelse
- Værktøjet løser et reelt problem for spillere
- Workflow matcher hvordan en spiller faktisk ville bruge det
- Integrerer eksterne data (Omricon's guide) på en brugervenlig måde

---

## 3. Design systemer: 5/10

**Definition:** Evnen til at arbejde struktureret med genanvendelige UI-komponenter og fælles visuelle og funktionelle standarder.

### Styrker
- Centraliseret styling i `_configure_style()` metode
- Konsistent font-familie gennem applikationen
- Farve-dictionary for genbrugelighed
- Named styles (`"Modern.Treeview"`, `"Section.TLabelframe"`)
- Struktureret layout-opbygning med separate metoder

### Passende for scope
```python
def _build_layout(self) -> None:
    self._build_left_pane()   # Inventory, Brew plan, Shopping list
    self._build_right_pane()  # Notebook, Details
```

### Noter (ikke detraktorer)
- Ingen separat komponentbibliotek - ville være overkill for én applikation
- Alt i én fil - acceptabelt for projektets størrelse
- Ingen design tokens dokumentation - ikke forventet for utility-projekt

---

## 4. Prototyping: Ikke evaluerbar / N/A

**Definition:** Evnen til hurtigt at visualisere og afprøve løsninger før endelig implementering.

### Hvorfor N/A
- Dette er et personligt utility-projekt, ikke et produkt med stakeholders
- Wireframes og mockups ville ikke give mening for dette scope
- Der er ingen indikation af at prototyping var en del af processen, men det ville heller ikke forventes

### Observationer (ikke scoret)
- README dokumenterer features godt
- CLI-version kan ses som en form for "prototype" eller alternativ interface
- Projektet viser evne til at gå fra idé til fungerende produkt

---

## 5. Performance: 6/10

**Definition:** Evnen til at sikre, at frontend løsningen er hurtig, responsiv og skalerbar også under belastning.

### Styrker
- **Debouncing implementeret korrekt:**
```python
def on_inventory_change(self, _event=None) -> None:
    if self._inv_debounce_after:
        self.after_cancel(self._inv_debounce_after)
    self._inv_debounce_after = self.after(AUTO_RECOMPUTE_DELAY, self._maybe_auto_recompute)
```
- Effektive datastrukturer (dictionaries for O(1) lookups)
- Normalisering af navne cached i lookup dict
- Ingen unødvendige genberegninger

### Passende for datamængden
- ~27 potions, ~30 ingredients - ingen tung optimering nødvendig
- Applikationen føles responsiv for sit formål
- Arkitekturen ville skalere rimeligt hvis datamængden voksede

### Noter (ikke detraktorer)
- Ingen virtualisering af lister - unødvendigt for denne datamængde
- Ingen caching til disk - ikke relevant for real-time beregninger
- Ingen bundling/minification - Python desktop app, ikke web

---

## Samlet Vurdering

### Kompetenceprofil

**Demonstrerede evner:**
- Struktureret kodeorganisering og OOP
- God forståelse for brugerworkflows
- Evne til at bygge funktionelle, brugervenlige værktøjer
- Bevidsthed om UI-konsistens og styling
- Grundlæggende performance-principper (debouncing)

### Kontekst-fair vurdering

Dette projekt viser en udvikler der kan:
1. Identificere et reelt brugerbehov
2. Designe en logisk løsning
3. Implementere den med god struktur
4. Tænke på brugeroplevelsen undervejs

**Scoreforklaring:** 
- Scores er justeret til at reflektere hvad der er rimeligt at forvente for projekttypen
- Elementer der ville være unaturlige for et Python utility-projekt (web frameworks, Figma prototypes, design system dokumentation) er noteret men ikke brugt som detraktorer
- Prototyping er markeret N/A da kategorien ikke giver mening i denne kontekst

### Finale scores

| Kategori | Score | Begrundelse |
|----------|-------|-------------|
| UI-implementering | **6/10** | Solid Tkinter implementation med god struktur |
| UX-forståelse | **7/10** | God brugerrejse og feedback-mekanismer |
| Design systemer | **5/10** | Passende konsistens for projektets scope |
| Prototyping | **N/A** | Ikke relevant for projekttypen |
| Performance | **6/10** | God praksis (debouncing) for datamængden |
| **Samlet** | **6/10** | Solidt utility-projekt med god UX-sans |
