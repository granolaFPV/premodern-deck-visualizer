/**
 * Main Application Orchestrator for MTG Premodern Deck Visualizer '98
 */

const EXAMPLE_1_TEXT = `3 Cabal Therapy (WC03) we62sb
3 Cursed Scroll (WC98) br281
4 Dark Ritual (MMQ) 129
2 Diabolic Edict (TMP) 128
4 Duress (USG) 132
2 Graveborn Muse (LGN) 73
4 Hypnotic Specter (PTC) gb142
4 Mishra's Factory (4ED) 361
3 Nantuko Shade (TOR) 74
4 Ravenous Rats (INV) 120
2 Smother (ONS) 170
1 Snuff Out (MMQ) 162
1 Spawning Pool (ULG) 142
16 Swamp (ONS) 341
3 Wasteland (WC98) br330
4 Withered Wretch (LGN) 86

SIDEBOARD:
1 Diabolic Edict (TMP) 128
3 Dystopia (ALL) 47
4 Engineered Plague (ULG) 51
2 Gloom (3ED) 113
2 Masticore (WC99) kb143b
1 Perish (TMP) 147
2 Tormod's Crypt (DRK) 112`;

const EXAMPLE_2_MOXFIELD_URL = 'https://moxfield.com/decks/B4yfAeSNVHWZJdrAZrcAKg';

const EXAMPLE_2_TEXT = `2 Fact or Fiction (INV) 57
2 Exclude (INV) 56
2 Repulse (INV) 70
2 Prohibit (INV) 67
2 Dominate (NEM) 31
2 Impulse (WC97) jk34
2 Mana Leak (STH) 36
2 Grim Lavamancer (DMR) 324
4 Accumulated Knowledge (NEM) 26
4 Faerie Conclave (ULG) 139
4 Counterspell (4ED) 65
4 Lightning Bolt (3ED) 162
4 Fire // Ice (APC) 128
4 Shivan Reef (APC) 142
1 Morphling (USG) 85
1 Lat-Nam's Legacy (ALL) 30a
7 Island (MIR) 338
5 Mountain (MIR) 344
3 Mishra's Factory (RIN) 172
3 Prophetic Bolt (APC) 116

SIDEBOARD:
2 Tormod's Crypt (CHR) 109
2 Pyroblast (ICE) 213
2 Pyroclasm (ICE) 214
2 Blue Elemental Blast (3ED) 49
1 Teferi's Response (INV) 78
1 Red Elemental Blast (4ED) 218
1 Phyrexian Furnace (WTH) 155
1 Hydroblast (ICE) 72
3 Annul (USG) 59`;

const EXAMPLE_MOXFIELD_URL = EXAMPLE_2_MOXFIELD_URL;

class App {
  constructor() {
    this.currentDeck = null;
    this.currentZoom = 1.0;

    this.initComponents();
    this.bindUIEvents();

    // Start with a clean playmat and the welcome splash prompt
    this.visualizer.render();
  }

  initComponents() {
    // 1. Visualizer
    this.visualizer = new DeckVisualizer(
      document.getElementById('playmat'),
      (cardInst) => this.onCardClicked(cardInst)
    );

    // 2. Card Version & Art Picker Modal
    this.versionModal = new CardVersionModal(({ instanceId, cardName, cardData, applyToAll }) => {
      if (this.currentDeck?.main_groups) {
        for (const g of this.currentDeck.main_groups) {
          if (g.name === cardName) {
            g.card_data = { ...g.card_data, ...cardData };
          }
        }
      }
      if (applyToAll) {
        this.visualizer.updateAllCopies(cardName, cardData);
        this.setStatus(`Updated all copies of "${cardName}" to ${cardData.set?.toUpperCase()} (${cardData.lang_name || cardData.lang})`);
      } else {
        this.visualizer.updateSingleCard(instanceId, cardData);
        this.setStatus(`Updated card "${cardName}" to ${cardData.set?.toUpperCase()} (${cardData.lang_name || cardData.lang})`);
      }
    });

    // 3. Exporter
    this.exporter = new DeckExporter();
  }

  bindUIEvents() {
    // Import Modal elements
    const importModal = document.getElementById('importModal');
    const btnOpenImport = document.getElementById('btnOpenImport');
    const btnOpenMoxfield = document.getElementById('btnOpenMoxfield');
    const btnCloseImport = document.getElementById('btnCloseImport');
    const btnCancelImport = document.getElementById('btnCancelImport');
    const btnSubmitImport = document.getElementById('btnSubmitImport');

    const tabText = document.getElementById('tabText');
    const tabUrl = document.getElementById('tabUrl');
    const contentTabText = document.getElementById('contentTabText');
    const contentTabUrl = document.getElementById('contentTabUrl');

    const deckTextInput = document.getElementById('deckTextInput');
    const moxfieldUrlInput = document.getElementById('moxfieldUrlInput');

    const presetEx1 = document.getElementById('presetEx1');
    const presetEx2 = document.getElementById('presetEx2');
    const presetTopDeck = document.getElementById('presetTopDeck');

    // Menu Bar items
    document.getElementById('menuItemNew')?.addEventListener('click', () => openImport(false));
    document.getElementById('menuItemMoxfield')?.addEventListener('click', () => openImport(true));
    document.getElementById('menuItemEx1')?.addEventListener('click', () => {
      this.loadDeck({ text: EXAMPLE_1_TEXT, name: 'Moneyball Black' });
    });
    document.getElementById('menuItemEx2')?.addEventListener('click', () => {
      this.loadDeck({ moxfield_url: EXAMPLE_2_MOXFIELD_URL, name: 'UR Counterburn' });
    });

    const openImport = (isUrl = false) => {
      importModal.classList.add('active');
      if (isUrl) {
        tabUrl.click();
      } else {
        tabText.click();
      }
    };

    btnOpenImport.addEventListener('click', () => openImport(false));
    btnOpenMoxfield.addEventListener('click', () => openImport(true));
    btnCloseImport.addEventListener('click', () => importModal.classList.remove('active'));
    btnCancelImport.addEventListener('click', () => importModal.classList.remove('active'));

    // Welcome Splash button
    document.getElementById('btnWelcomeImport')?.addEventListener('click', () => openImport(false));

    // Tabs
    tabText.addEventListener('click', () => {
      tabText.classList.add('active');
      tabUrl.classList.remove('active');
      contentTabText.classList.add('active');
      contentTabUrl.classList.remove('active');
    });

    tabUrl.addEventListener('click', () => {
      tabUrl.classList.add('active');
      tabText.classList.remove('active');
      contentTabUrl.classList.add('active');
      contentTabText.classList.remove('active');
    });

    // Presets
    presetEx1?.addEventListener('click', () => {
      tabText.click();
      deckTextInput.value = EXAMPLE_1_TEXT;
    });

    presetEx2?.addEventListener('click', () => {
      tabUrl.click();
      moxfieldUrlInput.value = EXAMPLE_2_MOXFIELD_URL;
    });

    presetTopDeck?.addEventListener('click', () => {
      tabUrl.click();
      moxfieldUrlInput.value = 'https://topdeck.gg/deck/TopDeckInvi24/@zrob';
    });

    // Submit Import
    btnSubmitImport.addEventListener('click', () => {
      const isUrlTab = tabUrl.classList.contains('active');
      if (isUrlTab) {
        const url = moxfieldUrlInput.value.trim();
        if (!url) {
          alert('Please enter a deck URL (TopDeck.gg, Moxfield, Archidekt, MTGGoldfish, MTGTop8, Cube Cobra, etc.).');
          return;
        }
        importModal.classList.remove('active');
        this.loadDeck({ url: url, moxfield_url: url });
      } else {
        const text = deckTextInput.value.trim();
        if (!text) {
          alert('Please paste a deck list.');
          return;
        }
        importModal.classList.remove('active');
        this.loadDeck({ text });
      }
    });

    // Playmat selector
    const playmatSelect = document.getElementById('playmatSelect');
    playmatSelect.addEventListener('change', (e) => {
      const mat = e.target.value;
      this.visualizer.setPlaymat(mat);
      document.querySelectorAll('.mat-opt-btn').forEach(b => b.classList.toggle('active', b.dataset.mat === mat));
    });

    document.querySelectorAll('.mat-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const mat = btn.dataset.mat;
        playmatSelect.value = mat;
        this.visualizer.setPlaymat(mat);
        document.querySelectorAll('.mat-opt-btn').forEach(b => b.classList.toggle('active', b.dataset.mat === mat));
      });
    });

    // Sleeve selector
    const sleeveSelect = document.getElementById('sleeveSelect');
    sleeveSelect.addEventListener('change', (e) => {
      this.visualizer.setSleeve(e.target.value);
    });

    document.querySelectorAll('.sleeve-opt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const slv = btn.dataset.sleeve;
        sleeveSelect.value = slv;
        this.visualizer.setSleeve(slv);
        document.querySelectorAll('.sleeve-opt-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Jitter slider & button
    const realismSlider = document.getElementById('realismSlider');
    const realismVal = document.getElementById('realismVal');
    realismSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value);
      if (val > 250) {
        realismVal.textContent = `${val}% 🤪`;
      } else if (val > 100) {
        realismVal.textContent = `${val}% 💥`;
      } else {
        realismVal.textContent = `${val}%`;
      }
      this.visualizer.setRealism(val);
      if (val > 100) {
        this.setStatus(`Jitter at ${val}%: cards placed haphazardly for the lulz!`);
      }
    });

    document.getElementById('btnReJitter').addEventListener('click', () => {
      this.visualizer.reJitter();
      this.setStatus('Table alignment re-randomized.');
    });

    // Distressify toggle button
    const btnDistressify = document.getElementById('btnDistressify');
    if (btnDistressify) {
      btnDistressify.addEventListener('click', () => {
        const nextState = !this.visualizer.isDistressed;
        btnDistressify.classList.toggle('active', nextState);
        this.visualizer.setDistressed(nextState);
        if (nextState) {
          this.setStatus('Distressify ON: Simulating vintage Heavily Played & Damaged cards with edge wear, scuffs, and aging.');
        } else {
          this.setStatus('Distressify OFF: Clean card condition restored.');
        }
      });
    }

    // Export button
    const btnExport = document.getElementById('btnExport');
    const menuExportPng = document.getElementById('menuExportPng');
    const triggerExport = () => {
      if (!this.currentDeck) return;
      this.exporter.exportDeck(
        this.currentDeck,
        playmatSelect.value,
        sleeveSelect.value,
        this.visualizer.realismMultiplier,
        this.visualizer.isDistressed,
        this.visualizer.jitterPercent
      );
    };
    btnExport.addEventListener('click', triggerExport);
    menuExportPng?.addEventListener('click', triggerExport);

    // Zoom controls
    const playmatEl = document.getElementById('playmat');
    const setZoom = (scale) => {
      this.currentZoom = Math.max(0.4, Math.min(1.6, scale));
      playmatEl.style.transform = `scale(${this.currentZoom})`;
      playmatEl.style.transformOrigin = 'top center';
    };

    document.getElementById('zoomInBtn')?.addEventListener('click', () => setZoom(this.currentZoom + 0.15));
    document.getElementById('zoomOutBtn')?.addEventListener('click', () => setZoom(this.currentZoom - 0.15));
    document.getElementById('zoomResetBtn')?.addEventListener('click', () => setZoom(1.0));

    // About Premodern dialog
    document.getElementById('menuAboutPremodern')?.addEventListener('click', () => {
      alert(
        "About the Premodern MTG Format:\n\n" +
        "Premodern is a nostalgic community-driven constructed format consisting exclusively of cards printed from Fourth Edition (April 1995) through Scourge (May 2003).\n\n" +
        "This visualizer prioritizes the exact authentic retro art from this golden era, respects explicit set/collector codes, and lets you customize each physical card to foreign languages (like Japanese) with one click!"
      );
    });
  }

  onCardClicked(cardInstance) {
    this.versionModal.open(cardInstance);
  }

  async loadDeck(payload) {
    const loader = document.getElementById('appLoader');
    const statusText = document.getElementById('loadingStatusText');
    loader.classList.add('active');
    const isUrl = Boolean(payload.url || payload.moxfield_url);
    statusText.textContent = isUrl 
      ? 'Fetching deck data from URL...' 
      : 'Resolving Premodern printings with Scryfall...';

    const timer1 = setTimeout(() => {
      if (loader.classList.contains('active')) {
        statusText.textContent = 'Resolving authentic Premodern printings with Scryfall...';
      }
    }, 2500);

    const timer2 = setTimeout(() => {
      if (loader.classList.contains('active')) {
        statusText.textContent = 'Packing deck into photographic table layout...';
      }
    }, 6500);

    this.setStatus('Loading and packing deck into visual grid...');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 40000);

    try {
      const resp = await fetch('/api/parse-deck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!resp.ok) {
        let errMsg = `HTTP ${resp.status}`;
        try {
          const errData = await resp.json();
          if (errData && errData.error) errMsg = errData.error;
        } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await resp.json();
      if (data.error) {
        throw new Error(data.error);
      }

      this.currentDeck = data;
      this.visualizer.setDeckData(data);

      const mainCount = data.total_main || 0;
      const sbCount = data.total_sb || 0;
      document.getElementById('statusCounts').textContent = `Main: ${mainCount}/60 • Sideboard: ${sbCount}/15`;
      this.setStatus(`Visual grid rendered: ${data.name || 'Deck'} (${mainCount} Main, ${sbCount} SB) • Click any card to customize`);
    } catch (err) {
      console.error('Failed to load deck:', err);
      const isAbort = err.name === 'AbortError';
      const msg = isAbort ? 'Request timed out after 40 seconds. Please try again.' : err.message;
      alert(`Error loading deck: ${msg}`);
      this.setStatus(`Error: ${msg}`);
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timeoutId);
      loader.classList.remove('active');
    }
  }

  setStatus(msg) {
    const el = document.getElementById('statusMessage');
    if (el) el.textContent = msg;
  }
}

// Launch app on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
