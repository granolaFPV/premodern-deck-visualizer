/**
 * Visualizer Renderer for MTG Deck Layout
 * Handles 6x10 Mainboard Grid & Angled Sideboard Fan Display
 */

window.handleCardImgError = function(img) {
  if (!img) return;
  const attempts = parseInt(img.dataset.retries || '0', 10);
  if (attempts === 0) {
    img.dataset.retries = '1';
    const originalSrc = img.src;
    if (originalSrc && !originalSrc.includes('/api/proxy-image')) {
      img.src = '/api/proxy-image?url=' + encodeURIComponent(originalSrc);
      return;
    }
  } else if (attempts === 1) {
    img.dataset.retries = '2';
    setTimeout(() => {
      if (img) {
        const clean = img.src.replace('&r=1', '') + '&r=1';
        img.src = clean;
      }
    }, 500);
    return;
  }
  img.style.display = 'none';
  if (img.parentElement) {
    img.parentElement.classList.add('card-img-failed');
    if (!img.parentElement.querySelector('.failed-card-label')) {
      const label = document.createElement('div');
      label.className = 'failed-card-label';
      label.textContent = img.alt || 'Card';
      img.parentElement.appendChild(label);
    }
  }
};

class DeckVisualizer {
  constructor(containerEl, onCardClickCallback) {
    this.container = containerEl;
    this.onCardClick = onCardClickCallback;

    this.mainboardGridEl = document.getElementById('mainboardGrid');
    this.sideboardFanEl = document.getElementById('sideboardFan');
    this.playmatEl = document.getElementById('playmat');

    this.deckData = null;
    this.jitterPercent = 45;
    this.realismMultiplier = 1.0; // 0.0 (laser straight) to 7.7 (350% haphazard)
    this.isDistressed = false;
    this.currentPlaymat = 'heather';
    this.currentSleeve = 'black';

    this.selectedSwapCard = null; // For click-to-swap repositioning
  }

  setDeckData(data) {
    this.deckData = data;
    this.render();
  }

  getJitterFactors() {
    const val = this.jitterPercent !== undefined ? this.jitterPercent : 45;
    if (val <= 100) {
      const m = val / 45.0;
      return { rotMult: m, dMult: m, sbMult: m };
    }
    // Beyond 100% up to 350%: progressive haphazard chaos curve
    const excess = (val - 100) / 250.0; // 0.0 to 1.0
    return {
      rotMult: 2.22 + excess * 26.0,   // up to ~20 deg rotations!
      dMult: 2.22 + excess * 22.0,     // up to ~35px offset!
      sbMult: 2.22 + excess * 12.0     // wild sideboard wobble!
    };
  }

  setRealism(valPercent) {
    this.jitterPercent = valPercent;
    this.realismMultiplier = valPercent / 45.0;
    this.applyJitterStyles();
  }

  setDistressed(bool) {
    this.isDistressed = Boolean(bool);
    if (this.playmatEl) {
      this.playmatEl.classList.toggle('is-distressed', this.isDistressed);
    }
  }

  setPlaymat(style) {
    this.currentPlaymat = style;
    this.playmatEl.className = `playmat-surface ${style}`;
  }

  setSleeve(style) {
    this.currentSleeve = style;
    this.container.classList.remove('sleeve-black', 'sleeve-gold', 'sleeve-clear');
    this.container.classList.add(`sleeve-${style}`);
  }

  reJitter(seed = Date.now()) {
    if (!this.deckData) return;
    
    // Deterministic pseudo-random generator
    let s = seed % 2147483647;
    const nextRandom = () => {
      s = (s * 16807) % 2147483647;
      return (s - 1) / 2147483646;
    };

    // Re-jitter mainboard
    if (this.deckData.mainboard && this.deckData.mainboard.cards) {
      this.deckData.mainboard.cards.forEach(c => {
        c.jitter = {
          rotation: Math.round((nextRandom() - 0.5) * 1.4 * 100) / 100,
          dx: Math.round((nextRandom() - 0.5) * 3.0 * 10) / 10,
          dy: Math.round((nextRandom() - 0.5) * 3.0 * 10) / 10
        };
      });
    }

    // Re-jitter sideboard
    if (this.deckData.sideboard && this.deckData.sideboard.cards) {
      this.deckData.sideboard.cards.forEach(c => {
        const baseAngle = -38.0;
        const angleJitter = Math.round((nextRandom() - 0.5) * 2.5 * 10) / 10;
        c.angle = baseAngle + angleJitter;
      });
    }

    this.applyJitterStyles();
  }

  render() {
    const welcomeEl = document.getElementById('welcomeSplash');
    const mainSectionEl = document.getElementById('mainboardSection');
    const sbSectionEl = document.getElementById('sideboardSection');

    if (!this.deckData) {
      if (welcomeEl) welcomeEl.style.display = 'flex';
      if (mainSectionEl) mainSectionEl.style.display = 'none';
      if (sbSectionEl) sbSectionEl.style.display = 'none';
      return;
    }

    if (welcomeEl) welcomeEl.style.display = 'none';
    if (mainSectionEl) mainSectionEl.style.display = 'block';
    if (sbSectionEl) sbSectionEl.style.display = 'block';

    this.renderMainboard();
    this.renderSideboard();
    this.applyJitterStyles();
  }

  renderMainboard() {
    this.mainboardGridEl.innerHTML = '';
    const mb = this.deckData.mainboard;
    if (!mb || !mb.grid) return;

    const rows = mb.rows || 6;
    const cols = mb.cols || 10;

    // Set grid CSS
    this.mainboardGridEl.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    this.mainboardGridEl.style.gridTemplateRows = `repeat(${rows}, auto)`;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cardInst = mb.grid[r][c];
        const cardSlot = document.createElement('div');
        cardSlot.className = 'card-item';
        cardSlot.dataset.row = r;
        cardSlot.dataset.col = c;

        if (cardInst) {
          cardSlot.dataset.instanceId = cardInst.instance_id;
          if (cardInst.card_data?.is_foil) {
            cardSlot.classList.add('is-foil');
          }

          const cardData = cardInst.card_data || {};
          const imgSrc = cardData.image_url || '';
          const langDisplay = cardData.lang_name || cardData.lang?.toUpperCase() || 'EN';
          const poscaColor = cardData.posca_border || cardInst.posca_border || '';

          cardSlot.innerHTML = `
            <div class="card-sleeve">
              <img class="card-img" src="${imgSrc}" alt="${cardData.printed_name || cardInst.name}" loading="lazy" onerror="window.handleCardImgError(this)">
              ${poscaColor ? `<div class="posca-border-overlay" style="border-color: ${poscaColor};"></div>` : ''}
              <div class="card-distress-overlay"></div>
            </div>
            <div class="card-tooltip">
              <div class="tooltip-title">${cardData.printed_name || cardInst.name}</div>
              <div class="tooltip-sub">${(cardData.set || '???').toUpperCase()} #${cardData.collector_number || ''} • ${langDisplay}${poscaColor ? ' • 🖌️ Posca Alter' : ''}</div>
              <div style="color: #ffd700; font-size: 9px; margin-top: 2px;">Click to change art / border / version</div>
            </div>
          `;

          // Card Click Event
          cardSlot.addEventListener('click', (e) => {
            e.stopPropagation();
            if (this.onCardClick) {
              this.onCardClick(cardInst);
            }
          });
        } else {
          cardSlot.classList.add('empty-slot');
          cardSlot.innerHTML = `<div class="card-sleeve" style="background: rgba(0,0,0,0.15); border: 1px dashed rgba(255,255,255,0.2);"></div>`;
        }

        this.mainboardGridEl.appendChild(cardSlot);
      }
    }
  }

  renderSideboard() {
    this.sideboardFanEl.innerHTML = '';
    const sb = this.deckData.sideboard;
    if (!sb || !sb.cards || sb.cards.length === 0) return;

    // Group cards into rows (e.g. row 0 has 8 cards, row 1 has 7 cards)
    const numRows = sb.num_rows || 2;
    const rowCards = Array.from({ length: numRows }, () => []);

    sb.cards.forEach(c => {
      const r = c.sb_row || 0;
      if (r < numRows) {
        rowCards[r].push(c);
      }
    });

    const cardW = 104;
    const cardH = 145;
    const theta = 38 * (Math.PI / 180);
    // Rotated card bounding half-width: ~85.6px
    const halfProjW = (cardW * Math.cos(theta) + cardH * Math.sin(theta)) / 2;
    const mainboardW = 10 * cardW + 9 * 2; // 1058px

    // 8 cards in top row, 7 in bottom row
    const minCx = halfProjW;
    const maxCx = mainboardW - halfProjW;
    const stepX = (maxCx - minCx) / 7; // ~126.7px
    const deltaY = 96; // Seamless zipper spacing: zero gap between rows!

    const row0Y = 90;
    const row1Y = row0Y + deltaY;

    // Unified zipper container allowing seamless inter-row nesting
    const zipperContainer = document.createElement('div');
    zipperContainer.className = 'sb-zipper-container';

    sb.cards.forEach((cardInst) => {
      const r = cardInst.sb_row || 0;
      const col = cardInst.sb_col || 0;

      let cx, cy, zIdx;
      if (r === 0) {
        cx = minCx + col * stepX;
        cy = row0Y;
        zIdx = 10 + col;
      } else {
        // Zippered: nestled directly into the V-notch between top cards col and col + 1!
        cx = minCx + (col + 0.5) * stepX;
        cy = row1Y;
        zIdx = 20 + col;
      }

      const left = Math.round(cx - cardW / 2);
      const top = Math.round(cy - cardH / 2);

      const cardSlot = document.createElement('div');
      cardSlot.className = 'sb-card-item';
      cardSlot.dataset.instanceId = cardInst.instance_id;
      cardSlot.dataset.sbRow = r;
      cardSlot.dataset.sbCol = col;
      cardSlot.style.left = `${left}px`;
      cardSlot.style.top = `${top}px`;
      cardSlot.style.zIndex = zIdx;

      if (cardInst.card_data?.is_foil) {
        cardSlot.classList.add('is-foil');
      }

      const cardData = cardInst.card_data || {};
      const imgSrc = cardData.image_url || '';
      const langDisplay = cardData.lang_name || cardData.lang?.toUpperCase() || 'EN';
      const poscaColor = cardData.posca_border || cardInst.posca_border || '';

      cardSlot.innerHTML = `
        <div class="card-sleeve">
          <img class="card-img" src="${imgSrc}" alt="${cardData.printed_name || cardInst.name}" loading="lazy" onerror="window.handleCardImgError(this)">
          ${poscaColor ? `<div class="posca-border-overlay" style="border-color: ${poscaColor};"></div>` : ''}
          <div class="card-distress-overlay"></div>
        </div>
        <div class="card-tooltip">
          <div class="tooltip-title">${cardData.printed_name || cardInst.name}</div>
          <div class="tooltip-sub">${(cardData.set || '???').toUpperCase()} #${cardData.collector_number || ''} • ${langDisplay}${poscaColor ? ' • 🖌️ Posca Alter' : ''}</div>
          <div style="color: #ffd700; font-size: 9px; margin-top: 2px;">Click to change art / border / version</div>
        </div>
      `;

      cardSlot.addEventListener('click', (e) => {
        e.stopPropagation();
        if (this.onCardClick) {
          this.onCardClick(cardInst);
        }
      });

      zipperContainer.appendChild(cardSlot);
    });

    this.sideboardFanEl.appendChild(zipperContainer);
  }

  applyJitterStyles() {
    if (!this.deckData) return;

    const { rotMult, dMult, sbMult } = this.getJitterFactors();

    // 1. Mainboard Jitter
    const mbCards = this.mainboardGridEl.querySelectorAll('.card-item:not(.empty-slot)');
    mbCards.forEach(slot => {
      const r = parseInt(slot.dataset.row);
      const c = parseInt(slot.dataset.col);
      const cardInst = this.deckData.mainboard?.grid?.[r]?.[c];
      if (cardInst && cardInst.jitter) {
        const rot = cardInst.jitter.rotation * rotMult;
        const dx = cardInst.jitter.dx * dMult;
        const dy = cardInst.jitter.dy * dMult;
        slot.style.transform = `translate(${dx}px, ${dy}px) rotate(${rot}deg)`;
      } else {
        slot.style.transform = 'none';
      }
    });

    // 2. Sideboard Angled Fan
    const sbCards = this.sideboardFanEl.querySelectorAll('.sb-card-item');
    sbCards.forEach(slot => {
      const id = slot.dataset.instanceId;
      const cardInst = this.deckData.sideboard?.cards?.find(x => x.instance_id === id);
      if (cardInst) {
        const baseAngle = -38.0;
        const angleDiff = (cardInst.angle - baseAngle) * sbMult;
        const finalAngle = baseAngle + angleDiff;
        slot.style.transform = `rotate(${finalAngle}deg)`;
      }
    });
  }

  updateSingleCard(instanceId, newCardData) {
    if (!this.deckData) return;

    // Check mainboard grid
    let updated = false;
    const mb = this.deckData.mainboard;
    if (mb && mb.grid) {
      for (let r = 0; r < mb.rows; r++) {
        for (let c = 0; c < mb.cols; c++) {
          if (mb.grid[r][c] && mb.grid[r][c].instance_id === instanceId) {
            mb.grid[r][c].card_data = { ...newCardData };
            if (newCardData.posca_border !== undefined) {
              mb.grid[r][c].posca_border = newCardData.posca_border;
            }
            updated = true;
            break;
          }
        }
        if (updated) break;
      }
    }

    // Also update mainboard.cards list
    if (mb && mb.cards) {
      const match = mb.cards.find(x => x.instance_id === instanceId);
      if (match) {
        match.card_data = { ...newCardData };
        if (newCardData.posca_border !== undefined) {
          match.posca_border = newCardData.posca_border;
        }
        updated = true;
      }
    }

    // Check sideboard
    if (this.deckData.sideboard?.cards) {
      const c = this.deckData.sideboard.cards.find(x => x.instance_id === instanceId);
      if (c) {
        c.card_data = { ...newCardData };
        if (newCardData.posca_border !== undefined) {
          c.posca_border = newCardData.posca_border;
        }
        updated = true;
      }
    }

    if (updated) {
      this.render();
    }
  }

  updateAllCopies(cardName, newCardData) {
    if (!this.deckData) return;

    const lowerTarget = cardName.toLowerCase();

    // Update mainboard grid
    const mb = this.deckData.mainboard;
    if (mb && mb.grid) {
      for (let r = 0; r < mb.rows; r++) {
        for (let c = 0; c < mb.cols; c++) {
          if (mb.grid[r][c] && mb.grid[r][c].name.toLowerCase() === lowerTarget) {
            mb.grid[r][c].card_data = { ...newCardData };
            if (newCardData.posca_border !== undefined) {
              mb.grid[r][c].posca_border = newCardData.posca_border;
            }
          }
        }
      }
    }

    // Also update mainboard.cards list
    if (mb && mb.cards) {
      mb.cards.forEach(c => {
        if (c.name.toLowerCase() === lowerTarget) {
          c.card_data = { ...newCardData };
          if (newCardData.posca_border !== undefined) {
            c.posca_border = newCardData.posca_border;
          }
        }
      });
    }

    // Update sideboard
    if (this.deckData.sideboard?.cards) {
      this.deckData.sideboard.cards.forEach(c => {
        if (c.name.toLowerCase() === lowerTarget) {
          c.card_data = { ...newCardData };
          if (newCardData.posca_border !== undefined) {
            c.posca_border = newCardData.posca_border;
          }
        }
      });
    }

    this.render();
  }
}

window.DeckVisualizer = DeckVisualizer;
