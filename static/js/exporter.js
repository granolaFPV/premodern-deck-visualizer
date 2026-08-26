/**
 * High-Resolution Canvas Exporter for MTG Deck Visualizer
 * Renders complete physical playmat layout (Mainboard 6x10 + Sideboard Angled Fan)
 * to high-definition PNG.
 */

class DeckExporter {
  constructor() {
    this.modalEl = document.getElementById('exportModal');
    this.canvas = document.getElementById('exportCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.spinner = document.getElementById('exportSpinner');
    this.closeBtn = document.getElementById('btnCloseExport');
    this.cancelBtn = document.getElementById('btnCancelExport');
    this.downloadBtn = document.getElementById('btnDownloadImage');
    this.resInfo = document.getElementById('exportResolutionInfo');

    this.currentBlob = null;
    this.deckName = 'Premodern_Deck';

    this.bindEvents();
  }

  bindEvents() {
    this.closeBtn.addEventListener('click', () => this.close());
    this.cancelBtn.addEventListener('click', () => this.close());

    this.downloadBtn.addEventListener('click', () => {
      if (!this.currentBlob) return;
      const url = URL.createObjectURL(this.currentBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.deckName.replace(/\s+/g, '_')}_visual_deck.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  close() {
    this.modalEl.classList.remove('active');
  }

  getJitterFactors(jitterPercent = 45) {
    if (jitterPercent <= 100) {
      const m = jitterPercent / 45.0;
      return { rotMult: m * 0.75, dMult: m * 0.8, sbMult: m };
    }
    const excess = (jitterPercent - 100) / 250.0;
    return {
      rotMult: (100 / 45.0) * 0.75 + excess * 22.0,
      dMult: (100 / 45.0) * 0.8 + excess * 18.0,
      sbMult: (100 / 45.0) + excess * 10.0
    };
  }

  drawPoscaBorder(ctx, cardW, cardH, sleevePad, cardRadius, poscaColor) {
    const borderThick = 13; // Authentic ~3.5mm real card border in export resolution
    ctx.save();
    
    // Draw outer thick Posca acrylic border
    ctx.strokeStyle = poscaColor;
    ctx.lineWidth = borderThick;
    this.drawRoundedRect(
      ctx,
      -cardW / 2 + sleevePad + borderThick / 2,
      -cardH / 2 + sleevePad + borderThick / 2,
      cardW - (sleevePad * 2) - borderThick,
      cardH - (sleevePad * 2) - borderThick,
      Math.max(2, cardRadius - 2)
    );
    ctx.stroke();

    // Subtle matte acrylic paint sheen & inner black keyline
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.lineWidth = 1.2;
    this.drawRoundedRect(
      ctx,
      -cardW / 2 + sleevePad + borderThick,
      -cardH / 2 + sleevePad + borderThick,
      cardW - (sleevePad * 2) - (borderThick * 2),
      cardH - (sleevePad * 2) - (borderThick * 2),
      Math.max(1, cardRadius - borderThick / 2)
    );
    ctx.stroke();

    ctx.restore();
  }

  drawDistressWear(ctx, cardW, cardH, sleevePad, cardRadius, seedStr) {
    ctx.save();
    
    // Deterministic pseudo-random number generator for this card
    let hash = 0;
    const s = String(seedStr);
    for (let i = 0; i < s.length; i++) {
      hash = ((hash << 5) - hash) + s.charCodeAt(i);
      hash |= 0;
    }
    const rnd = () => {
      hash = (hash * 16807 + 12345) % 2147483647;
      return (Math.abs(hash) % 1000) / 1000.0;
    };

    const innerX = -cardW / 2 + sleevePad;
    const innerY = -cardH / 2 + sleevePad;
    const innerW = cardW - sleevePad * 2;
    const innerH = cardH - sleevePad * 2;

    // 1. Edge Whitening / Frayed Cardstock Core (Cardboard exposure along outer edges)
    ctx.fillStyle = 'rgba(240, 235, 220, 0.7)';
    // Top & Bottom edges
    for (let x = innerX + 6; x < innerX + innerW - 6; x += 10 + rnd() * 16) {
      const wearLen = 6 + rnd() * 16;
      const wearDepth = 1.2 + rnd() * 2.5;
      if (rnd() > 0.28) {
        ctx.fillRect(x, innerY, wearLen, wearDepth);
      }
      if (rnd() > 0.32) {
        ctx.fillRect(x, innerY + innerH - wearDepth, wearLen, wearDepth);
      }
    }
    // Left & Right edges
    for (let y = innerY + 6; y < innerY + innerH - 6; y += 10 + rnd() * 16) {
      const wearLen = 6 + rnd() * 16;
      const wearDepth = 1.2 + rnd() * 2.5;
      if (rnd() > 0.3) {
        ctx.fillRect(innerX, y, wearDepth, wearLen);
      }
      if (rnd() > 0.28) {
        ctx.fillRect(innerX + innerW - wearDepth, y, wearDepth, wearLen);
      }
    }

    // 2. Corner dings / whitening
    const corners = [
      [innerX, innerY],
      [innerX + innerW - 8, innerY],
      [innerX, innerY + innerH - 8],
      [innerX + innerW - 8, innerY + innerH - 8]
    ];
    ctx.fillStyle = 'rgba(255, 255, 255, 0.75)';
    corners.forEach(([cx, cy]) => {
      if (rnd() > 0.2) {
        ctx.beginPath();
        ctx.arc(cx + 4, cy + 4, 3 + rnd() * 4, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // 3. Playmat / Fingernail Scratches
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.24)';
    ctx.lineWidth = 0.8;
    const numScratches = Math.floor(2 + rnd() * 4);
    for (let i = 0; i < numScratches; i++) {
      const sx = innerX + 20 + rnd() * (innerW - 40);
      const sy = innerY + 25 + rnd() * (innerH - 50);
      const len = 18 + rnd() * 40;
      const angle = (rnd() - 0.5) * Math.PI * 0.85;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx + Math.cos(angle) * len, sy + Math.sin(angle) * len);
      ctx.stroke();
    }

    // 4. Subtle diagonal corner stress crease (simulates classic HP/DMG pocket bend)
    if (rnd() > 0.45) {
      const isTopRight = rnd() > 0.5;
      const creaseX = isTopRight ? innerX + innerW - 35 : innerX + 10;
      const creaseY = innerY + 14 + rnd() * 20;
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(creaseX, creaseY);
      ctx.lineTo(creaseX + 28, creaseY + 28);
      ctx.stroke();
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.beginPath();
      ctx.moveTo(creaseX + 1, creaseY + 1);
      ctx.lineTo(creaseX + 29, creaseY + 29);
      ctx.stroke();
    }

    // 5. Vintage cardstock patina / slight sepia fading
    ctx.fillStyle = 'rgba(100, 75, 30, 0.07)';
    this.drawRoundedRect(ctx, innerX, innerY, innerW, innerH, cardRadius);
    ctx.fill();

    ctx.restore();
  }

  async exportDeck(deckData, playmatStyle = 'heather', sleeveStyle = 'black', realismMultiplier = 1.0, isDistressed = false, jitterPercent = 45) {
    this.deckName = deckData.name || 'Premodern_Deck';
    this.modalEl.classList.add('active');
    this.spinner.classList.add('active');

    const jitterFactors = this.getJitterFactors(jitterPercent);

    // High resolution dimensions (Balanced photographic table framing)
    const W = 2000;
    const H = 2160;
    this.canvas.width = W;
    this.canvas.height = H;
    this.resInfo.textContent = `Resolution: ${W} × ${H} px • Clean Table Photo (No Watermarks)`;

    const ctx = this.ctx;

    // 1. Draw Playmat Background
    this.drawPlaymatBackground(ctx, W, H, playmatStyle);

    // 2. Collect ALL unique image URLs directly from mb.grid and sb.cards
    const imageCache = new Map();
    const uniqueUrls = new Set();

    const mb = deckData.mainboard;
    if (mb && mb.grid) {
      for (let r = 0; r < (mb.rows || 6); r++) {
        for (let c = 0; c < (mb.cols || 10); c++) {
          const cardInst = mb.grid[r][c];
          if (cardInst && cardInst.card_data) {
            const u = cardInst.card_data.image_large || cardInst.card_data.image_url;
            if (u) uniqueUrls.add(u);
          }
        }
      }
    }

    if (deckData.sideboard?.cards) {
      deckData.sideboard.cards.forEach(c => {
        if (c.card_data) {
          const u = c.card_data.image_large || c.card_data.image_url;
          if (u) uniqueUrls.add(u);
        }
      });
    }

    const loadPromises = Array.from(uniqueUrls).map(imgUrl => {
      return new Promise((resolve) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';

        // Scryfall CDN and local /static/ images already support CORS and are browser-cached
        const isDirectCors = imgUrl.startsWith('data:') || 
                             imgUrl.startsWith('/static/') || 
                             imgUrl.includes('cards.scryfall.io');

        const initialSrc = isDirectCors 
          ? imgUrl 
          : `/api/proxy-image?url=${encodeURIComponent(imgUrl)}`;

        img.src = initialSrc;
        img.onload = () => {
          imageCache.set(imgUrl, img);
          resolve(img);
        };
        img.onerror = () => {
          // Fallback: try proxy if direct failed, or try direct if proxy failed
          const fallback = new Image();
          fallback.crossOrigin = 'anonymous';
          fallback.src = isDirectCors 
            ? `/api/proxy-image?url=${encodeURIComponent(imgUrl)}` 
            : imgUrl;
          fallback.onload = () => {
            imageCache.set(imgUrl, fallback);
            resolve(fallback);
          };
          fallback.onerror = () => {
            console.warn('Could not load card image for export:', imgUrl);
            resolve(null);
          };
        };
      });
    });

    await Promise.all(loadPromises);

    // 3. Layout Dimensions — Cards basically touching, no headers, pure table photo
    const cardW = 180;
    const cardH = Math.round(cardW * (88 / 63)); // ~251px
    const gapX = 2; // Basically touching
    const gapY = 2; // Basically touching
    const sleevePad = 4;
    const sleeveRadius = 6;
    const cardRadius = 5;

    // Calculate canvas size so cards fit naturally with balanced playmat border
    const gridW = 10 * cardW + 9 * gapX; // 1818px
    const gridH = 6 * cardH + 5 * gapY;  // 1516px
    const sbGap = 50; // Clean space between mainboard and sideboard
    const sbRowStepY = 115;
    const sbHeight = 2 * sbRowStepY + cardH; // ~480px

    const startX = Math.round((W - gridW) / 2);
    const startY = 70;

    // 4. Draw Mainboard 6x10 Grid (Cards touching with natural sleeve edges)
    if (mb && mb.grid) {
      for (let r = 0; r < (mb.rows || 6); r++) {
        for (let c = 0; c < (mb.cols || 10); c++) {
          const cardInst = mb.grid[r][c];
          if (!cardInst) continue;

          const baseX = startX + c * (cardW + gapX);
          const baseY = startY + r * (cardH + gapY);

          // Jitter (Natural subtle misalignment up to 350% haphazard chaos)
          const rotDeg = (cardInst.jitter?.rotation || 0) * jitterFactors.rotMult;
          const dx = (cardInst.jitter?.dx || 0) * jitterFactors.dMult;
          const dy = (cardInst.jitter?.dy || 0) * jitterFactors.dMult;

          const cx = baseX + cardW / 2 + dx;
          const cy = baseY + cardH / 2 + dy;

          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate((rotDeg * Math.PI) / 180);

          // Diffuse card drop shadow on playmat
          ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
          ctx.shadowBlur = 10;
          ctx.shadowOffsetX = 1;
          ctx.shadowOffsetY = 4;

          // Outer Sleeve
          this.drawRoundedRect(ctx, -cardW / 2, -cardH / 2, cardW, cardH, sleeveRadius);
          if (sleeveStyle === 'gold') {
            ctx.fillStyle = '#c5a038';
          } else {
            ctx.fillStyle = '#0a0a0c'; // Black sleeve
          }
          ctx.fill();

          // Reset shadow for card image
          ctx.shadowColor = 'transparent';
          ctx.shadowBlur = 0;
          ctx.shadowOffsetX = 0;
          ctx.shadowOffsetY = 0;

          // Inner Card Image
          const imgUrl = cardInst.card_data?.image_large || cardInst.card_data?.image_url;
          const img = imageCache.get(imgUrl);
          if (img) {
            ctx.save();
            this.drawRoundedRect(
              ctx,
              -cardW / 2 + sleevePad,
              -cardH / 2 + sleevePad,
              cardW - sleevePad * 2,
              cardH - sleevePad * 2,
              cardRadius
            );
            ctx.clip();
            ctx.drawImage(
              img,
              -cardW / 2 + sleevePad,
              -cardH / 2 + sleevePad,
              cardW - sleevePad * 2,
              cardH - sleevePad * 2
            );
            ctx.restore();
          }

          // Posca Border Alter
          const poscaColor = cardInst.card_data?.posca_border || cardInst.posca_border;
          if (poscaColor) {
            this.drawPoscaBorder(ctx, cardW, cardH, sleevePad, cardRadius, poscaColor);
          }

          // Distressify Wear & Scuffs
          if (isDistressed) {
            this.drawDistressWear(ctx, cardW, cardH, sleevePad, cardRadius, cardInst.instance_id || `${r}_${c}`);
          }

          // Subtle specular sleeve edge highlight
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
          ctx.lineWidth = 1;
          this.drawRoundedRect(ctx, -cardW / 2, -cardH / 2, cardW, cardH, sleeveRadius);
          ctx.stroke();

          ctx.restore();
        }
      }
    }

    // 5. Draw Sideboard (Angled Fan Display directly below mainboard, no header)
    const sb = deckData.sideboard;
    if (sb && sb.cards && sb.cards.length > 0) {
      const sbStartY = startY + gridH + sbGap;


      const theta = 38 * (Math.PI / 180);
      // Rotated card bounding half-width: ~148.2px
      const halfProjW = (cardW * Math.cos(theta) + cardH * Math.sin(theta)) / 2;

      // 8 cards in top row, 7 in bottom row
      const minCx = startX + halfProjW;
      const maxCx = startX + gridW - halfProjW;
      const stepX = (maxCx - minCx) / 7; // ~217.4px
      const deltaY = 166; // Seamless zipper spacing: zero gap between rows!

      const row0Y = sbStartY + 155;
      const row1Y = row0Y + deltaY;

      sb.cards.forEach((cardInst) => {
        const r = cardInst.sb_row || 0;
        const col = cardInst.sb_col || 0;

        let cx, cy;
        if (r === 0) {
          cx = minCx + col * stepX;
          cy = row0Y;
        } else {
          // Zippered: nestled directly into the V-notch between top cards col and col + 1!
          cx = minCx + (col + 0.5) * stepX;
          cy = row1Y;
        }

        const baseAngle = -38.0;
        const angleDiff = ((cardInst.angle || baseAngle) - baseAngle) * jitterFactors.sbMult;
        const angle = baseAngle + angleDiff;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate((angle * Math.PI) / 180);

          // Deep cast shadow on adjacent cards and mat
          ctx.shadowColor = 'rgba(0, 0, 0, 0.65)';
          ctx.shadowBlur = 18;
          ctx.shadowOffsetX = 2;
          ctx.shadowOffsetY = 8;

          // Sleeve
          this.drawRoundedRect(ctx, -cardW / 2, -cardH / 2, cardW, cardH, sleeveRadius);
          ctx.fillStyle = sleeveStyle === 'gold' ? '#c5a038' : '#0a0a0c';
          ctx.fill();

          ctx.shadowColor = 'transparent';
          ctx.shadowBlur = 0;
          ctx.shadowOffsetX = 0;
          ctx.shadowOffsetY = 0;

          // Card Art
          const imgUrl = cardInst.card_data?.image_large || cardInst.card_data?.image_url;
          const img = imageCache.get(imgUrl);
          if (img) {
            ctx.save();
            this.drawRoundedRect(
              ctx,
              -cardW / 2 + sleevePad,
              -cardH / 2 + sleevePad,
              cardW - sleevePad * 2,
              cardH - sleevePad * 2,
              cardRadius
            );
            ctx.clip();
            ctx.drawImage(
              img,
              -cardW / 2 + sleevePad,
              -cardH / 2 + sleevePad,
              cardW - sleevePad * 2,
              cardH - sleevePad * 2
            );
            ctx.restore();
          }

          // Posca Border Alter
          const poscaColor = cardInst.card_data?.posca_border || cardInst.posca_border;
          if (poscaColor) {
            this.drawPoscaBorder(ctx, cardW, cardH, sleevePad, cardRadius, poscaColor);
          }

          // Distressify Wear & Scuffs
          if (isDistressed) {
            this.drawDistressWear(ctx, cardW, cardH, sleevePad, cardRadius, cardInst.instance_id || `sb_${col}`);
          }

          ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
          ctx.lineWidth = 1;
          this.drawRoundedRect(ctx, -cardW / 2, -cardH / 2, cardW, cardH, sleeveRadius);
          ctx.stroke();

          ctx.restore();
        });
    }

    // Complete Export Blob (No watermarks, no added text — authentic table photo)
    this.canvas.toBlob((blob) => {
      this.currentBlob = blob;
      this.spinner.classList.remove('active');
    }, 'image/png');
  }

  drawPlaymatBackground(ctx, W, H, style) {
    if (style === 'charcoal') {
      ctx.fillStyle = '#242528';
      ctx.fillRect(0, 0, W, H);
      return;
    }
    if (style === 'greenfelt') {
      ctx.fillStyle = '#174226';
      ctx.fillRect(0, 0, W, H);
      return;
    }
    if (style === 'wood') {
      ctx.fillStyle = '#3e2715';
      ctx.fillRect(0, 0, W, H);
      return;
    }

    // Default: Heather Grey Cloth (Matching photo!)
    ctx.fillStyle = '#555960';
    ctx.fillRect(0, 0, W, H);

    // Render cloth fiber noise pattern
    ctx.save();
    for (let x = 0; x < W; x += 8) {
      for (let y = 0; y < H; y += 8) {
        const rand = ((x * 17 + y * 31) % 100) / 100;
        if (rand > 0.6) {
          ctx.fillStyle = `rgba(255, 255, 255, ${0.02 + rand * 0.03})`;
          ctx.fillRect(x, y, 2, 2);
        } else if (rand < 0.3) {
          ctx.fillStyle = `rgba(0, 0, 0, ${0.03 + rand * 0.04})`;
          ctx.fillRect(x, y, 2, 2);
        }
      }
    }

    // Ambient vignette lighting
    const grad = ctx.createRadialGradient(W / 2, H / 2, 300, W / 2, H / 2, W * 0.7);
    grad.addColorStop(0, 'rgba(255, 255, 255, 0.04)');
    grad.addColorStop(1, 'rgba(0, 0, 0, 0.45)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    // Subtle mat stitch border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 4;
    ctx.strokeRect(20, 20, W - 40, H - 40);
    ctx.restore();
  }

  drawRoundedRect(ctx, x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }
}

window.DeckExporter = DeckExporter;
