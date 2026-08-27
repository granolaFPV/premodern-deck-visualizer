/**
 * Modal Manager for Card Version, Foreign Language & Custom Image Selection
 * Supports:
 * - Premodern Era Filter (4ED -> SCG)
 * - Retro Border Only Filter (is:old / 1993/1997 frames)
 * - Placeholder Filter (Hide Scryfall "Localized version not available" placeholders)
 * - Real Scan badges
 * - Drag & Drop / File Upload of card photos
 * - Clipboard Paste (Ctrl+V)
 * - Direct Retailer Search (Hareruya, Google Images)
 * - Direct URL apply
 */

class CardVersionModal {
  constructor(onApplyCallback) {
    this.onApply = onApplyCallback;
    this.currentInstance = null;
    this.printings = [];
    this.selectedPrinting = null;
    this.activeLang = 'all';
    this.premodernOnly = true;
    this.retroBorderOnly = false;
    this.hidePlaceholders = false;

    this.initDOMElements();
    this.bindEvents();
  }

  initDOMElements() {
    this.modalEl = document.getElementById('versionModal');
    this.titleEl = document.getElementById('versionModalTitle');
    this.previewImg = document.getElementById('cardModalPreviewImg');
    this.foilBadge = document.getElementById('previewFoilBadge');
    this.nameEl = document.getElementById('cardModalName');
    this.printedNameEl = document.getElementById('cardModalPrintedName');
    this.setEl = document.getElementById('cardModalSet');
    this.langEl = document.getElementById('cardModalLang');
    this.yearEl = document.getElementById('cardModalYear');
    this.typeEl = document.getElementById('cardModalType');
    this.gridContainer = document.getElementById('printingsGrid');
    this.langContainer = document.getElementById('langPillContainer');

    // Filter elements
    this.premodernCheck = document.getElementById('checkPremodernOnly');
    this.retroBorderCheck = document.getElementById('checkRetroBorderOnly');
    this.hidePlaceholdersCheck = document.getElementById('checkHidePlaceholders');
    this.searchInput = document.getElementById('printingsSearchInput');
    this.foilCheck = document.getElementById('toggleFoilCheck');

    // Custom upload & URL elements
    this.customUrlInput = document.getElementById('customImgUrlInput');
    this.dropUploadZone = document.getElementById('dropUploadZone');
    this.cardFileInput = document.getElementById('cardFileInput');
    this.btnSearchHareruya = document.getElementById('btnSearchHareruya');
    this.btnSearchGoogle = document.getElementById('btnSearchGoogle');
    this.directImgUrlInput = document.getElementById('directImgUrlInput');
    this.btnApplyDirectUrl = document.getElementById('btnApplyDirectUrl');

    // Posca border alter elements
    this.poscaOverlay = document.getElementById('cardModalPoscaOverlay');
    this.poscaSwatchesContainer = document.getElementById('poscaSwatches');
    this.btnResetPosca = document.getElementById('btnResetPosca');
    this.poscaCustomColorInput = document.getElementById('poscaCustomColor');
    this.selectedPoscaColor = '';

    // Buttons
    this.closeBtn = document.getElementById('btnCloseVersion');
    this.cancelBtn = document.getElementById('btnCancelVersion');
    this.applySingleBtn = document.getElementById('btnApplySingle');
    this.applyAllBtn = document.getElementById('btnApplyAll');
    this.applyCustomUrlBtn = document.getElementById('btnApplyCustomUrl');

    // Mobile Navigation Tabs
    this.tabMobilePrintings = document.getElementById('tabMobilePrintings');
    this.tabMobileAlter = document.getElementById('tabMobileAlter');
  }

  bindEvents() {
    this.closeBtn.addEventListener('click', () => this.close());
    this.cancelBtn.addEventListener('click', () => this.close());

    // Mobile tabs
    this.tabMobilePrintings?.addEventListener('click', () => {
      this.modalEl.classList.remove('mobile-show-alter');
      this.tabMobilePrintings.classList.add('active');
      this.tabMobileAlter?.classList.remove('active');
    });

    this.tabMobileAlter?.addEventListener('click', () => {
      this.modalEl.classList.add('mobile-show-alter');
      this.tabMobileAlter.classList.add('active');
      this.tabMobilePrintings?.classList.remove('active');
    });

    // Language pills
    this.langContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.lang-pill');
      if (!btn) return;
      this.langContainer.querySelectorAll('.lang-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      this.activeLang = btn.dataset.lang;
      this.renderPrintingsList();
    });

    // Premodern filter toggle
    this.premodernCheck.addEventListener('change', (e) => {
      this.premodernOnly = e.target.checked;
      this.renderPrintingsList();
    });

    // Retro Border Only filter toggle
    this.retroBorderCheck.addEventListener('change', (e) => {
      this.retroBorderOnly = e.target.checked;
      this.renderPrintingsList();
    });

    // Hide Placeholders filter toggle
    this.hidePlaceholdersCheck.addEventListener('change', (e) => {
      this.hidePlaceholders = e.target.checked;
      this.renderPrintingsList();
    });

    // Search filter
    this.searchInput.addEventListener('input', () => {
      this.renderPrintingsList();
    });

    // Foil toggle
    this.foilCheck.addEventListener('change', (e) => {
      if (this.selectedPrinting) {
        this.selectedPrinting.is_foil = e.target.checked;
      }
      this.updatePreview();
    });

    // Custom URL buttons
    const handleCustomUrl = (url) => {
      url = url.trim();
      if (!url) return;
      if (!this.selectedPrinting) {
        this.selectedPrinting = { ...(this.currentInstance.card_data || {}) };
      }
      this.selectedPrinting.image_url = url;
      this.selectedPrinting.image_large = url;
      this.selectedPrinting.is_placeholder = false;
      this.selectedPrinting.image_status = 'highres_scan';
      this.selectedPrinting.source = 'Custom URL';
      this.updatePreview();

      // Submit to Community Scans Registry if it's a foreign card printing
      if (this.selectedPrinting.set && this.selectedPrinting.lang) {
        fetch('/api/submit-community-scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            card_name: this.currentInstance.name,
            set: this.selectedPrinting.set,
            collector_number: this.selectedPrinting.collector_number || '',
            lang: this.selectedPrinting.lang,
            image_url: url,
            printed_name: this.selectedPrinting.printed_name || this.currentInstance.name
          })
        }).catch(err => console.warn('Community scan submission error:', err));
      }
    };

    this.applyCustomUrlBtn.addEventListener('click', () => {
      handleCustomUrl(this.customUrlInput.value);
    });

    this.btnApplyDirectUrl.addEventListener('click', () => {
      handleCustomUrl(this.directImgUrlInput.value);
    });

    // Drag & Drop / File Upload
    this.dropUploadZone.addEventListener('click', () => {
      this.cardFileInput.click();
    });

    this.cardFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) this.handleFileUpload(file);
    });

    this.dropUploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      this.dropUploadZone.classList.add('drag-active');
    });

    this.dropUploadZone.addEventListener('dragleave', () => {
      this.dropUploadZone.classList.remove('drag-active');
    });

    this.dropUploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      this.dropUploadZone.classList.remove('drag-active');
      const file = e.dataTransfer.files[0];
      if (file) this.handleFileUpload(file);
    });

    // Global Paste (Ctrl+V / Cmd+V) while modal is open
    window.addEventListener('paste', (e) => {
      if (!this.modalEl.classList.contains('active')) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
          const file = items[i].getAsFile();
          if (file) {
            this.handleFileUpload(file);
            break;
          }
        }
      }
    });

    // Retailer Search Shortcuts
    this.btnSearchHareruya.addEventListener('click', () => {
      if (!this.currentInstance) return;
      const searchName = this.selectedPrinting?.printed_name || this.currentInstance.name;
      const url = `https://www.hareruyamtg.com/ja/products/search?str=${encodeURIComponent(searchName)}`;
      window.open(url, '_blank');
    });

    this.btnSearchGoogle.addEventListener('click', () => {
      if (!this.currentInstance) return;
      const searchName = this.selectedPrinting?.printed_name || this.currentInstance.name;
      const setCode = this.selectedPrinting?.set || '';
      const query = `${searchName} ${setCode} MTG card Japanese`;
      const url = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(query)}`;
      window.open(url, '_blank');
    });

    // Posca Swatches
    if (this.poscaSwatchesContainer) {
      this.poscaSwatchesContainer.addEventListener('click', (e) => {
        const swatch = e.target.closest('.posca-swatch');
        if (!swatch) return;
        this.poscaSwatchesContainer.querySelectorAll('.posca-swatch').forEach(s => s.classList.remove('active'));
        swatch.classList.add('active');
        this.selectedPoscaColor = swatch.dataset.color || '';
        if (this.selectedPrinting) {
          this.selectedPrinting.posca_border = this.selectedPoscaColor;
        }
        this.updatePreview();
      });
    }

    // Posca Custom Color Picker
    if (this.poscaCustomColorInput) {
      this.poscaCustomColorInput.addEventListener('input', (e) => {
        const color = e.target.value;
        this.poscaSwatchesContainer?.querySelectorAll('.posca-swatch').forEach(s => s.classList.remove('active'));
        this.selectedPoscaColor = color;
        if (this.selectedPrinting) {
          this.selectedPrinting.posca_border = this.selectedPoscaColor;
        }
        this.updatePreview();
      });
    }

    // Posca Reset Button
    if (this.btnResetPosca) {
      this.btnResetPosca.addEventListener('click', () => {
        this.selectedPoscaColor = '';
        if (this.selectedPrinting) {
          this.selectedPrinting.posca_border = '';
        }
        this.poscaSwatchesContainer?.querySelectorAll('.posca-swatch').forEach(s => {
          s.classList.toggle('active', !s.dataset.color);
        });
        this.updatePreview();
      });
    }

    // Apply Single
    this.applySingleBtn.addEventListener('click', () => {
      if (!this.currentInstance || !this.selectedPrinting) return;
      this.selectedPrinting.posca_border = this.selectedPoscaColor;
      this.onApply({
        instanceId: this.currentInstance.instance_id,
        cardName: this.currentInstance.name,
        cardData: this.selectedPrinting,
        applyToAll: false
      });
      this.close();
    });

    // Apply All
    this.applyAllBtn.addEventListener('click', () => {
      if (!this.currentInstance || !this.selectedPrinting) return;
      this.selectedPrinting.posca_border = this.selectedPoscaColor;
      this.onApply({
        instanceId: this.currentInstance.instance_id,
        cardName: this.currentInstance.name,
        cardData: this.selectedPrinting,
        applyToAll: true
      });
      this.close();
    });
  }

  handleFileUpload(file) {
    const reader = new FileReader();
    reader.onload = async (e) => {
      const dataUrl = e.target.result;
      
      // Update preview immediately with local data URL
      if (!this.selectedPrinting) {
        this.selectedPrinting = { ...(this.currentInstance.card_data || {}) };
      }
      this.selectedPrinting.image_url = dataUrl;
      this.selectedPrinting.image_large = dataUrl;
      this.selectedPrinting.is_placeholder = false;
      this.selectedPrinting.image_status = 'highres_scan';
      this.selectedPrinting.source = 'Uploaded Photo';
      this.updatePreview();

      // Also persist upload to server
      try {
        const resp = await fetch('/api/upload-card-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data_url: dataUrl,
            card_name: this.currentInstance.name
          })
        });
        const res = await resp.json();
        if (res.url) {
          this.selectedPrinting.image_url = res.url;
          this.selectedPrinting.image_large = res.url;

          // Also register with community registry if foreign
          if (this.selectedPrinting.set && this.selectedPrinting.lang) {
            fetch('/api/submit-community-scan', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                card_name: this.currentInstance.name,
                set: this.selectedPrinting.set,
                collector_number: this.selectedPrinting.collector_number || '',
                lang: this.selectedPrinting.lang,
                image_url: res.url,
                printed_name: this.selectedPrinting.printed_name || this.currentInstance.name
              })
            }).catch(err => console.warn('Community scan submission error:', err));
          }
        }
      } catch (err) {
        console.warn('Could not persist upload to server, using local data URL:', err);
      }
    };
    reader.readAsDataURL(file);
  }

  open(cardInstance) {
    this.currentInstance = cardInstance;
    this.currentCardName = cardInstance.name;
    this.printings = []; // Immediately wipe old card printings!
    this.selectedPrinting = { ...(cardInstance.card_data || {}) };
    this.selectedPoscaColor = cardInstance.posca_border || cardInstance.card_data?.posca_border || '';
    this.selectedPrinting.posca_border = this.selectedPoscaColor;
    this.titleEl.textContent = `Customize Version & Art — ${cardInstance.name}`;
    this.foilCheck.checked = Boolean(this.selectedPrinting.is_foil);
    this.customUrlInput.value = '';
    this.directImgUrlInput.value = '';
    this.searchInput.value = '';

    // Reset mobile tabs to Printings view
    this.modalEl.classList.remove('mobile-show-alter');
    this.tabMobilePrintings?.classList.add('active');
    this.tabMobileAlter?.classList.remove('active');

    // Sync Posca swatches active state
    if (this.poscaSwatchesContainer) {
      let matched = false;
      this.poscaSwatchesContainer.querySelectorAll('.posca-swatch').forEach(s => {
        const match = (s.dataset.color || '') === this.selectedPoscaColor;
        s.classList.toggle('active', match);
        if (match) matched = true;
      });
      if (!matched && this.selectedPoscaColor && this.poscaCustomColorInput) {
        this.poscaCustomColorInput.value = this.selectedPoscaColor;
      }
    }

    // Reset language pill to "All"
    this.activeLang = 'all';
    if (this.langContainer) {
      this.langContainer.querySelectorAll('.lang-pill').forEach(b => {
        b.classList.toggle('active', b.dataset.lang === 'all');
      });
    }

    this.gridContainer.innerHTML = `
      <div class="loading-printings">
        <span class="spinner">⏳</span> Fetching all printings and foreign editions for "${cardInstance.name}"...
      </div>
    `;

    this.updatePreview();
    this.modalEl.classList.add('active');

    // Fetch all printings and foreign languages from API with sequence token
    if (!this.fetchSeq) this.fetchSeq = 0;
    const seq = ++this.fetchSeq;
    this.fetchPrintings(cardInstance.name, seq);
  }

  close() {
    if (!this.fetchSeq) this.fetchSeq = 0;
    this.fetchSeq++;
    this.printings = [];
    this.currentInstance = null;
    this.currentCardName = null;
    this.modalEl.classList.remove('active');
  }

  updatePreview() {
    if (!this.selectedPrinting) return;
    const c = this.selectedPrinting;
    this.previewImg.src = c.image_large || c.image_url || '';
    this.nameEl.textContent = c.name || this.currentInstance?.name || '';
    this.printedNameEl.textContent = c.printed_name || c.name || '';
    this.setEl.textContent = (c.set_name || c.set || '???').toUpperCase();
    this.langEl.textContent = c.lang_name || c.lang?.toUpperCase() || 'EN';
    this.yearEl.textContent = c.released_at ? c.released_at.substring(0, 4) : '';
    this.typeEl.textContent = c.type_line || '';

    if (this.foilCheck.checked || c.is_foil) {
      this.foilBadge.classList.remove('hidden');
    } else {
      this.foilBadge.classList.add('hidden');
    }

    // Posca overlay preview
    if (this.poscaOverlay) {
      const pColor = c.posca_border !== undefined ? c.posca_border : this.selectedPoscaColor;
      if (pColor) {
        this.poscaOverlay.style.borderColor = pColor;
        this.poscaOverlay.classList.remove('hidden');
      } else {
        this.poscaOverlay.classList.add('hidden');
      }
    }
  }

  async fetchPrintings(cardName, seq) {
    try {
      const resp = await fetch(`/api/card-printings?name=${encodeURIComponent(cardName)}`);
      const data = await resp.json();

      // If user has switched to another card or closed the modal, discard stale response!
      if (seq !== this.fetchSeq || !this.currentInstance || this.currentInstance.name !== cardName) {
        return;
      }

      if (data.printings && data.printings.length > 0) {
        this.printings = data.printings;
        this.renderPrintingsList();
      } else {
        this.gridContainer.innerHTML = `<div class="no-printings">No printings found for "${cardName}".</div>`;
      }
    } catch (err) {
      if (seq !== this.fetchSeq) return;
      console.error('Error fetching printings:', err);
      this.gridContainer.innerHTML = `<div class="error-printings">Failed to fetch printings: ${err.message}</div>`;
    }
  }

  renderPrintingsList() {
    if (!this.printings || !this.printings.length) {
      this.gridContainer.innerHTML = `
        <div class="loading-printings">
          <span class="spinner">⏳</span> Fetching editions for "${this.currentCardName || 'card'}"...
        </div>
      `;
      return;
    }

    const searchTerm = this.searchInput.value.trim().toLowerCase();
    
    // Filter printings
    const filtered = this.printings.filter(p => {
      // 1. Language filter
      if (this.activeLang !== 'all') {
        const pl = (p.lang || '').toLowerCase();
        if (this.activeLang === 'zhs') {
          if (pl !== 'zhs' && pl !== 'zh-hans' && pl !== 'cn' && pl !== 'cs') return false;
        } else if (this.activeLang === 'zht') {
          if (pl !== 'zht' && pl !== 'zh-hant' && pl !== 'tw' && pl !== 'ct') return false;
        } else if (pl !== this.activeLang.toLowerCase()) {
          return false;
        }
      }
      // 2. Premodern era filter (4ED to SCG)
      if (this.premodernOnly && !p.is_premodern) {
        return false;
      }
      // 3. Retro Border filter (is:old / 1993/1997 frames)
      if (this.retroBorderOnly && !p.is_retro) {
        return false;
      }
      // 4. Hide Placeholders filter
      if (this.hidePlaceholders && p.is_placeholder) {
        return false;
      }
      // 5. Search term filter
      if (searchTerm) {
        if (searchTerm === 'frame:old') {
          if (!p.is_retro) return false;
        } else {
          const matchSet = (p.set || '').toLowerCase().includes(searchTerm);
          const matchSetName = (p.set_name || '').toLowerCase().includes(searchTerm);
          const matchPrinted = (p.printed_name || '').toLowerCase().includes(searchTerm);
          const matchLang = (p.lang_name || '').toLowerCase().includes(searchTerm);
          const matchFrame = searchTerm === 'retro' && p.is_retro;
          if (!matchSet && !matchSetName && !matchPrinted && !matchLang && !matchFrame) {
            return false;
          }
        }
      }
      return true;
    });

    if (filtered.length === 0) {
      this.gridContainer.innerHTML = `
        <div class="no-printings" style="grid-column: 1 / -1; padding: 20px; text-align: center; color: #555;">
          No printings match the selected filter combination.
          <br><small>Try unchecking "Premodern Era", "Retro Border (frame:old)", or "Hide Placeholders".</small>
        </div>
      `;
      return;
    }

    this.gridContainer.innerHTML = '';
    filtered.forEach(p => {
      const cardOption = document.createElement('div');
      cardOption.className = 'printing-card-option';
      
      const isCurrent = this.selectedPrinting && (
        (this.selectedPrinting.id && this.selectedPrinting.id === p.id) ||
        (this.selectedPrinting.set === p.set && this.selectedPrinting.collector_number === p.collector_number && this.selectedPrinting.lang === p.lang)
      );

      if (isCurrent) {
        cardOption.classList.add('selected');
      }

      // Build tag badges
      let tagBadges = '';
      if (p.is_placeholder) {
        tagBadges += '<span class="printing-tag tag-placeholder" title="Scryfall does not have a scanned image for this card and displays a placeholder banner">⚠️ Placeholder</span>';
      } else {
        tagBadges += '<span class="printing-tag tag-realscan" title="Real localized scan available">✅ Real Scan</span>';
      }

      if (p.is_retro) {
        tagBadges += '<span class="printing-tag tag-retro" title="Scryfall frame:old (1993/1997 vintage retro frame)">📜 frame:old</span>';
      }

      if (p.source && p.source !== 'Scryfall') {
        tagBadges += `<span class="printing-tag tag-source">${p.source}</span>`;
      }

      cardOption.innerHTML = `
        <div class="thumb-wrapper">
          <img class="printing-thumb-img" src="${p.image_url}" alt="${p.printed_name || p.name}" loading="lazy">
          ${p.is_placeholder ? '<div class="placeholder-overlay-hint">Scryfall Placeholder</div>' : ''}
        </div>
        <div class="printing-info">
          <div class="printing-set-row">
            <span>${p.set.toUpperCase()} #${p.collector_number || ''}</span>
            <span class="printing-lang-tag">${p.lang.toUpperCase()}</span>
          </div>
          <div class="printing-card-name" title="${p.printed_name || p.name}">
            ${p.printed_name || p.name}
          </div>
          <div class="printing-meta-tags">
            ${tagBadges}
          </div>
        </div>
      `;

      cardOption.addEventListener('click', () => {
        this.gridContainer.querySelectorAll('.printing-card-option').forEach(el => el.classList.remove('selected'));
        cardOption.classList.add('selected');
        
        const wasFoil = this.foilCheck.checked;
        const currentPosca = this.selectedPoscaColor;
        this.selectedPrinting = { ...p, is_foil: wasFoil, posca_border: currentPosca };
        this.updatePreview();
      });

      this.gridContainer.appendChild(cardOption);
    });
  }
}

window.CardVersionModal = CardVersionModal;
