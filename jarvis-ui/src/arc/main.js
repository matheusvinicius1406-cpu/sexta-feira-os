/**
 * ARC — the J.A.R.V.I.S. HUD.
 *
 * The reactor, the radial navigation, the annular sector, the boot sequence and
 * the command palette are the canonical ARC artifact, kept verbatim: this file
 * IS the design system's reference implementation, not a re-interpretation of it.
 * Canonical values live in docs/design-system/ (01-TOKENS §5 for the geometry,
 * 04-NAVEGACAO for the radial flow).
 *
 * What was deliberately NOT kept is the artifact's simulator — the canned
 * replies, the staged link failures and the random core load that made a static
 * mockup look alive. Those are replaced by `./kernel.js`, which reads the real
 * kernel. A HUD that invents its readings is a screensaver.
 *
 * The twelve modules are wired through `./modules.js` (what each sub-item reads)
 * and `./panel.js` (where it lands). `./live.js` owns the conversation, the
 * microphone and the camera, and it is what moves the reactor: `thinking` means
 * the kernel is thinking, `speaking` means audio is playing.
 */
import * as Kernel from './kernel.js'
import * as Panel from './panel.js'
import * as Live from './live.js'
import * as Api from './api.js'

(() => {
  "use strict";

  /* ═══════════════════════════════════════════════════════
     0 — TOKENS + MATH
     ═══════════════════════════════════════════════════════ */
  const C = {
    arc:      [ 46, 125, 255],
    plasma:   [ 53, 214, 255],
    ignition: [201, 244, 255],
    vital:    [ 46, 230, 168],
    caution:  [255, 178,  61],
    breach:   [255,  77, 106],
    steel:    [ 42,  58,  78],
  };
  /* Metal ramp — the reactor's chrome. Lit from upper-left.
     Pulled hard toward blue: this metal is not neutral steel, it is steel
     drowning in the light of what it contains. */
  const M = {
    deep:   [  5,  10,  22],
    shadow: [ 16,  30,  54],
    mid:    [ 45,  68, 104],
    light:  [110, 154, 208],
    spec:   [214, 236, 255],
  };

  const rgba = (c, a) => `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${a})`;
  const mix  = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  const TAU  = Math.PI * 2;
  const RAD  = Math.PI / 180;
  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const approach = (cur, tgt, rate, dt) => cur + (tgt - cur) * (1 - Math.exp(-rate * dt));

  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hasConic = typeof CanvasRenderingContext2D !== "undefined"
    && "createConicGradient" in CanvasRenderingContext2D.prototype;

  /* ═══════════════════════════════════════════════════════
     1 — MODULE GRAPH
     ═══════════════════════════════════════════════════════ */
  const MODULES = [
    { id: "ai",       label: "AI",       icon: "hex",    kids: ["Models","Prompts","Context","Tuning","Evals","Learning"] },
    { id: "memory",   label: "Memory",   icon: "layers", kids: ["Recent","Semantic","Episodic","Purge"] },
    { id: "agents",   label: "Agents",   icon: "nodes",  kids: ["Pulse","Proposals","Active","Queue","Registry","Logs","Spawn"] },
    { id: "files",    label: "Files",    icon: "folder", kids: ["Recent","Index","Vault","Sync","Journal","Habits"] },
    { id: "projects", label: "Projects", icon: "grid",   kids: ["Active","Archive","Tasks","Timeline","Decision"] },
    { id: "terminal", label: "Terminal", icon: "term",   kids: ["Shell","History","Jobs","SSH"] },
    { id: "browser",  label: "Browser",  icon: "globe",  kids: ["Tabs","Research","Capture","Marks"] },
    { id: "security", label: "Security", icon: "shield", kids: ["Keys","Audit","Perms","Threats"] },
    { id: "voice",    label: "Voice",    icon: "wave",   kids: ["Listen","Voices","Phrases","Latency","Radio"] },
    { id: "network",  label: "Network",  icon: "signal", kids: ["Nodes","Traffic","Devices","Actions","VPN"] },
    { id: "system",   label: "System",   icon: "chip",   kids: ["CPU","Memory","Disk","Power","Temp","Optimize","Time"] },
    { id: "settings", label: "Settings", icon: "gear",   kids: ["Core","Voice","Theme","About"] },
  ];

  /* ═══════════════════════════════════════════════════════
     2 — STATES
     Continuous targets the loop eases toward. Nothing snaps.
     ═══════════════════════════════════════════════════════ */
  const STATES = {
    idle:      { glow: 0.62, spin: 1.00, core: 1.00, tint: C.plasma,   text: "Standby",   chip: "idle" },
    listening: { glow: 1.00, spin: 1.45, core: 1.10, tint: C.plasma,   text: "Listening", chip: "listening" },
    thinking:  { glow: 0.84, spin: 3.60, core: 0.94, tint: C.arc,      text: "Thinking",  chip: "thinking" },
    speaking:  { glow: 1.00, spin: 1.20, core: 1.06, tint: C.ignition, text: "Speaking",  chip: "listening" },
    warning:   { glow: 0.78, spin: 0.82, core: 1.00, tint: C.caution,  text: "Warning",   chip: "warning" },
    error:     { glow: 0.92, spin: 0.28, core: 0.88, tint: C.breach,   text: "Fault",     chip: "error" },
    offline:   { glow: 0.14, spin: 0.12, core: 0.78, tint: C.steel,    text: "Offline",   chip: "offline" },
    sleep:     { glow: 0.09, spin: 0.06, core: 0.70, tint: C.steel,    text: "Sleep",     chip: "offline" },
  };

  const S = {
    name: "idle",
    glow: 0.62, spin: 1, core: 1, tint: [...C.plasma],
    depth: 0, open: 0, activeIdx: -1, hoverIdx: -1, hoverAmt: 0,
    wedgeAngle: 0, proximity: 0, ripples: [], surge: 0, t: 0,
  };

  /* ═══════════════════════════════════════════════════════
     3 — CANVAS
     ═══════════════════════════════════════════════════════ */
  const cv = document.getElementById("reactor");
  const ctx = cv.getContext("2d");
  let W = 0, H = 0, cx = 0, cy = 0, R = 78, dpr = 1;

  /* Geometry in multiples of R. The reactor body fills 0 → 1.58 R;
     the radial navigation layer starts beyond it at 1.78 R. */
  const G = {
    hot: 0.26, lens: 0.56, plateC: [0.60, 0.78], plateB: [0.84, 1.06],
    plateA: [1.12, 1.36], bezel: [1.38, 1.58],
    strut: [0.52, 1.34],
    wedgeIn: 1.78, wedgeOut: 3.05, orbit: 2.40, bound: 3.24,
  };

  function resize() {
    dpr = Math.min(devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    cv.width = Math.floor(W * dpr); cv.height = Math.floor(H * dpr);
    cv.style.width = W + "px"; cv.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cx = W / 2; cy = H / 2;
    R = clamp(Math.min(W, H) * 0.105, 52, 104);
    document.documentElement.style.setProperty("--coreOffset", (R * 1.92) + "px");
    seedParticles();
  }
  addEventListener("resize", resize);

  /* ═══════════════════════════════════════════════════════
     4 — PARTICLES
     ═══════════════════════════════════════════════════════ */
  let parts = [];
  function seedParticles() {
    const n = reduceMotion ? 0 : Math.round(clamp((W * H) / 28000, 26, 84));
    parts = Array.from({ length: n }, () => ({
      a: Math.random() * TAU,
      r: R * lerp(1.75, 5.2, Math.pow(Math.random(), 0.7)),
      sp: (Math.random() * 0.5 + 0.12) * (Math.random() < 0.5 ? -1 : 1),
      sz: Math.random() * 1.15 + 0.25,
      al: Math.random() * 0.4 + 0.08,
      ph: Math.random() * TAU,
    }));
  }

  /* ═══════════════════════════════════════════════════════
     5 — ICONS (unit-space paths, built once)
     ═══════════════════════════════════════════════════════ */
  function buildIcon(kind) {
    const p = new Path2D();
    const rect = (x, y, w, h) => p.rect(x, y, w, h);
    const line = (x1, y1, x2, y2) => { p.moveTo(x1, y1); p.lineTo(x2, y2); };
    const circ = (x, y, r) => { p.moveTo(x + r, y); p.arc(x, y, r, 0, TAU); };

    switch (kind) {
      case "hex":
        for (let i = 0; i < 6; i++) {
          const a = (i * 60 - 30) * RAD, x = Math.cos(a) * 0.5, y = Math.sin(a) * 0.5;
          i ? p.lineTo(x, y) : p.moveTo(x, y);
        }
        p.closePath(); circ(0, 0, 0.14); break;
      case "layers":
        line(-0.45, -0.22, 0.45, -0.22); line(-0.45, 0.02, 0.45, 0.02); line(-0.45, 0.26, 0.45, 0.26);
        break;
      case "nodes":
        circ(0, -0.32, 0.13); circ(-0.34, 0.26, 0.13); circ(0.34, 0.26, 0.13);
        line(-0.08, -0.20, -0.28, 0.14); line(0.08, -0.20, 0.28, 0.14); line(-0.20, 0.30, 0.20, 0.30);
        break;
      case "folder":
        p.moveTo(-0.45, 0.32); p.lineTo(-0.45, -0.24); p.lineTo(-0.10, -0.24);
        p.lineTo(-0.01, -0.10); p.lineTo(0.45, -0.10); p.lineTo(0.45, 0.32); p.closePath();
        break;
      case "grid":
        rect(-0.42, -0.42, 0.36, 0.36); rect(0.06, -0.42, 0.36, 0.36);
        rect(-0.42, 0.06, 0.36, 0.36); rect(0.06, 0.06, 0.36, 0.36);
        break;
      case "term":
        rect(-0.46, -0.36, 0.92, 0.72);
        line(-0.26, -0.12, -0.08, 0.02); line(-0.08, 0.02, -0.26, 0.16); line(0.02, 0.16, 0.26, 0.16);
        break;
      case "globe":
        circ(0, 0, 0.44); line(-0.44, 0, 0.44, 0);
        p.moveTo(0, -0.44); p.bezierCurveTo(0.28, -0.18, 0.28, 0.18, 0, 0.44);
        p.moveTo(0, -0.44); p.bezierCurveTo(-0.28, -0.18, -0.28, 0.18, 0, 0.44);
        break;
      case "shield":
        p.moveTo(0, -0.44); p.lineTo(0.38, -0.26); p.lineTo(0.38, 0.08);
        p.bezierCurveTo(0.38, 0.30, 0.18, 0.40, 0, 0.46);
        p.bezierCurveTo(-0.18, 0.40, -0.38, 0.30, -0.38, 0.08);
        p.lineTo(-0.38, -0.26); p.closePath();
        break;
      case "wave":
        [[-0.36,.12],[-0.18,.30],[0,.44],[0.18,.26],[0.36,.10]].forEach(([x,h]) => line(x,-h,x,h));
        break;
      case "signal":
        circ(0, 0.26, 0.07);
        for (let i = 1; i <= 3; i++) {
          const r = 0.15 + i * 0.13;
          p.moveTo(Math.cos(-0.75*Math.PI)*r, 0.26 + Math.sin(-0.75*Math.PI)*r);
          p.arc(0, 0.26, r, -0.75*Math.PI, -0.25*Math.PI);
        }
        break;
      case "chip":
        rect(-0.30, -0.30, 0.60, 0.60);
        [-0.16, 0, 0.16].forEach(o => {
          line(o, -0.30, o, -0.44); line(o, 0.30, o, 0.44);
          line(-0.30, o, -0.44, o); line(0.30, o, 0.44, o);
        });
        break;
      case "gear":
        circ(0, 0, 0.20);
        for (let i = 0; i < 8; i++) {
          const a = i * 45 * RAD;
          line(Math.cos(a)*0.30, Math.sin(a)*0.30, Math.cos(a)*0.45, Math.sin(a)*0.45);
        }
        break;
      default: circ(0, 0, 0.34);
    }
    return p;
  }
  const ICON_CACHE = {};
  const unitIcon = k => (ICON_CACHE[k] ||= buildIcon(k));

  /* ═══════════════════════════════════════════════════════
     6 — REACTOR PRIMITIVES
     ═══════════════════════════════════════════════════════ */

  /** Clip to an annulus and run a paint callback inside it. */
  function inAnnulus(rIn, rOut, paint) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, rOut, 0, TAU);
    ctx.arc(cx, cy, rIn, 0, TAU, true);
    ctx.clip("evenodd");
    paint();
    ctx.restore();
  }

  /**
   * Brushed-metal conic shading. Two specular highlights (a strong
   * one and a weaker opposite) rotating with `rotDeg` — this sweep is
   * what sells the chrome, far more than any static gradient.
   */
  function metalGradient(rotDeg, boost) {
    const b = boost === undefined ? 1 : boost;
    if (!hasConic) {
      const lg = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
      lg.addColorStop(0, rgba(M.light, 1)); lg.addColorStop(0.5, rgba(M.mid, 1));
      lg.addColorStop(1, rgba(M.shadow, 1));
      return lg;
    }
    const g = ctx.createConicGradient(rotDeg * RAD, cx, cy);
    const stop = (t, c, k) => g.addColorStop(t, rgba(k === undefined ? c : mix(c, M.spec, k * b), 1));
    stop(0.00, M.mid);      stop(0.06, M.light);
    stop(0.115, M.spec);    stop(0.17, M.light);
    stop(0.27, M.shadow);   stop(0.36, M.deep);
    stop(0.46, M.shadow);   stop(0.55, M.mid);
    stop(0.63, M.light);    stop(0.675, M.light, 0.55);
    stop(0.74, M.mid);      stop(0.84, M.shadow);
    stop(0.93, M.mid);      stop(1.00, M.mid);
    return g;
  }

  /** Solid metal band with rim light on both edges. */
  function metalBand(rIn, rOut, rotDeg, edgeAlpha) {
    inAnnulus(rIn, rOut, () => {
      ctx.fillStyle = metalGradient(rotDeg);
      ctx.fillRect(cx - rOut, cy - rOut, rOut * 2, rOut * 2);
    });
    ctx.lineWidth = 1;
    ctx.strokeStyle = rgba(M.spec, 0.20 * edgeAlpha);
    ctx.beginPath(); ctx.arc(cx, cy, rOut - 0.5, 0, TAU); ctx.stroke();
    ctx.strokeStyle = rgba(M.deep, 0.85);
    ctx.beginPath(); ctx.arc(cx, cy, rIn + 0.5, 0, TAU); ctx.stroke();
  }

  /**
   * A ring of beveled metal plates with glowing gaps between them.
   * The gaps are where the reactor's light escapes — the core visual
   * motif of the reference.
   */
  function plateRing(rIn, rOut, count, gapDeg, rotDeg, tint, glowA) {
    const step = 360 / count;
    const span = step - gapDeg;

    // Light escaping through the gaps, painted first so plates sit on top.
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    inAnnulus(rIn - 1, rOut + 1, () => {
      const g = ctx.createRadialGradient(cx, cy, rIn * 0.6, cx, cy, rOut * 1.1);
      g.addColorStop(0, rgba(mix(tint, C.ignition, 0.25), 0.74 * glowA));
      g.addColorStop(1, rgba(tint, 0.20 * glowA));
      ctx.fillStyle = g;
      ctx.fillRect(cx - rOut - 2, cy - rOut - 2, (rOut + 2) * 2, (rOut + 2) * 2);
    });
    ctx.restore();

    // All plates of a ring share one path: a single clip + single fill
    // instead of one per plate. At 36 plates a frame that is the
    // difference between 60fps and 30.
    const plates = new Path2D();
    for (let i = 0; i < count; i++) {
      const a0 = (rotDeg + i * step) * RAD;
      const a1 = a0 + span * RAD;
      plates.arc(cx, cy, rOut, a0, a1);
      plates.arc(cx, cy, rIn, a1, a0, true);
      plates.closePath();
    }

    ctx.save();
    ctx.clip(plates);
    ctx.fillStyle = metalGradient(rotDeg);   // one conic gradient per ring
    ctx.fillRect(cx - rOut, cy - rOut, rOut * 2, rOut * 2);
    ctx.restore();

    // Bevel: bright outer arc, dark inner arc — cheap strokes, no clipping.
    ctx.lineWidth = 1.4;
    for (let i = 0; i < count; i++) {
      const a0 = (rotDeg + i * step) * RAD;
      const a1 = a0 + span * RAD;
      ctx.strokeStyle = rgba(M.spec, 0.28);
      ctx.beginPath(); ctx.arc(cx, cy, rOut - 0.7, a0, a1); ctx.stroke();
      ctx.strokeStyle = rgba(M.deep, 0.9);
      ctx.beginPath(); ctx.arc(cx, cy, rIn + 0.7, a0, a1); ctx.stroke();
    }

    // Chromatic rim: each plate catches the colour of the light it caps.
    ctx.lineWidth = 0.9;
    ctx.strokeStyle = rgba(mix(M.light, tint, 0.55), 0.40);
    ctx.stroke(plates);
  }

  /** Radial struts — the reactor's coils. Tapered, metal, blue-capped. */
  function struts(count, rIn, rOut, rotDeg, tint, glowA) {
    const halfIn = 3.2 * (R / 78), halfOut = 6.4 * (R / 78);

    // One path for all struts — same single-clip economy as plateRing.
    const body = new Path2D();
    for (let i = 0; i < count; i++) {
      const a = (rotDeg + i * (360 / count)) * RAD;
      const ca = Math.cos(a), sa = Math.sin(a), px = -sa, py = ca;
      body.moveTo(cx + ca * rIn + px * halfIn,   cy + sa * rIn + py * halfIn);
      body.lineTo(cx + ca * rOut + px * halfOut, cy + sa * rOut + py * halfOut);
      body.lineTo(cx + ca * rOut - px * halfOut, cy + sa * rOut - py * halfOut);
      body.lineTo(cx + ca * rIn - px * halfIn,   cy + sa * rIn - py * halfIn);
      body.closePath();
    }
    ctx.save();
    ctx.clip(body);
    ctx.fillStyle = metalGradient(rotDeg * 0.6);
    ctx.fillRect(cx - rOut, cy - rOut, rOut * 2, rOut * 2);
    ctx.restore();

    ctx.lineWidth = 1;
    ctx.strokeStyle = rgba(M.spec, 0.20);
    ctx.stroke(body);

    // Energy travelling outward along each strut, phase-offset per coil.
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    for (let i = 0; i < count; i++) {
      const a = (rotDeg + i * (360 / count)) * RAD;
      const ca = Math.cos(a), sa = Math.sin(a);
      const phase = (S.t * 0.55 * S.spin + i / count) % 1;
      const pr = lerp(rIn, rOut, phase);
      const fade = Math.sin(phase * Math.PI);
      const ex = cx + ca * pr, ey = cy + sa * pr, er = halfOut * 3;
      const eg = ctx.createRadialGradient(ex, ey, 0, ex, ey, er);
      eg.addColorStop(0, rgba(tint, 0.7 * fade * glowA));
      eg.addColorStop(1, rgba(tint, 0));
      ctx.fillStyle = eg;
      ctx.beginPath(); ctx.arc(ex, ey, er, 0, TAU); ctx.fill();
    }
    ctx.restore();
  }

  /** Converging lens rings — the throat leading to the hot core. */
  function lens(rOut, tint, glowA, rotDeg) {
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    const layers = 7;
    for (let i = 0; i < layers; i++) {
      const t = i / (layers - 1);
      const r = rOut * lerp(1, 0.22, t);
      const a = lerp(0.15, 0.54, t) * glowA;
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU);
      ctx.fillStyle = rgba(mix(tint, C.ignition, t * 0.7), a * 0.34);
      ctx.fill();
      ctx.lineWidth = 1.1;
      ctx.strokeStyle = rgba(mix(tint, C.ignition, t), a);
      ctx.stroke();
    }
    // Slow iris blades over the lens
    ctx.lineWidth = 1;
    for (let i = 0; i < 6; i++) {
      const a0 = (rotDeg + i * 60) * RAD;
      ctx.beginPath();
      ctx.arc(cx, cy, rOut * 0.72, a0, a0 + 40 * RAD);
      ctx.strokeStyle = rgba(C.ignition, 0.20 * glowA);
      ctx.stroke();
    }
    ctx.restore();
  }

  /** The white-hot centre plus its bloom. */
  function hotCore(r, tint, glowA) {
    ctx.save();
    ctx.globalCompositeOperation = "lighter";

    const bloom = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 7);
    bloom.addColorStop(0.00, rgba(C.ignition, 0.80 * glowA));
    bloom.addColorStop(0.08, rgba(tint, 0.40 * glowA));
    bloom.addColorStop(0.30, rgba(C.arc, 0.13 * glowA));
    bloom.addColorStop(1.00, "rgba(0,0,0,0)");
    ctx.beginPath(); ctx.arc(cx, cy, r * 7, 0, TAU);
    ctx.fillStyle = bloom; ctx.fill();

    const hot = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    hot.addColorStop(0.00, rgba([255,255,255], 0.98 * clamp(glowA * 1.5, 0, 1)));
    hot.addColorStop(0.28, rgba([255,255,255], 0.80 * glowA));
    hot.addColorStop(0.58, rgba(C.ignition, 0.55 * glowA));
    hot.addColorStop(1.00, rgba(tint, 0.06 * glowA));
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU);
    ctx.fillStyle = hot; ctx.fill();

    // Anisotropic flare — a horizontal streak, as real bright optics produce.
    const fl = ctx.createLinearGradient(cx - r * 6, cy, cx + r * 6, cy);
    fl.addColorStop(0.0, "rgba(0,0,0,0)");
    fl.addColorStop(0.5, rgba(C.ignition, 0.16 * glowA));
    fl.addColorStop(1.0, "rgba(0,0,0,0)");
    ctx.fillStyle = fl;
    ctx.fillRect(cx - r * 6, cy - r * 0.10, r * 12, r * 0.20);

    ctx.restore();
  }

  /* ═══════════════════════════════════════════════════════
     7 — HUD PRIMITIVES
     ═══════════════════════════════════════════════════════ */
  function ring(r, w, col, alpha, dash) {
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU);
    ctx.lineWidth = w; ctx.strokeStyle = rgba(col, alpha);
    ctx.setLineDash(dash || []); ctx.stroke(); ctx.setLineDash([]);
  }

  function segRing(r, w, col, alpha, count, gapDeg, rotDeg) {
    const step = 360 / count, span = (step - gapDeg) * RAD;
    ctx.lineWidth = w; ctx.strokeStyle = rgba(col, alpha);
    for (let i = 0; i < count; i++) {
      const a0 = (rotDeg + i * step) * RAD;
      ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + span); ctx.stroke();
    }
  }

  function tickRing(r, len, col, alpha, count, rotDeg, everyN) {
    ctx.strokeStyle = rgba(col, alpha); ctx.lineWidth = 1;
    for (let i = 0; i < count; i++) {
      const a = (rotDeg + (360 / count) * i) * RAD;
      const l = (everyN && i % everyN === 0) ? len * 2.1 : len;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
      ctx.lineTo(cx + Math.cos(a) * (r + l), cy + Math.sin(a) * (r + l));
      ctx.stroke();
    }
  }

  /** The signature: an annular sector. */
  function wedge(a0, a1, rIn, rOut, col, fillA, strokeA) {
    ctx.beginPath();
    ctx.arc(cx, cy, rOut, a0, a1);
    ctx.arc(cx, cy, rIn, a1, a0, true);
    ctx.closePath();
    const g = ctx.createRadialGradient(cx, cy, rIn, cx, cy, rOut);
    g.addColorStop(0, rgba(col, fillA * 0.35));
    g.addColorStop(0.55, rgba(col, fillA));
    g.addColorStop(1, rgba(col, fillA * 0.72));
    ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = 1; ctx.strokeStyle = rgba(col, strokeA); ctx.stroke();
  }

  /* ═══════════════════════════════════════════════════════
     8 — RENDER
     ═══════════════════════════════════════════════════════ */
  const rot = { spec: 0, plateA: 0, plateB: 0, plateC: 0, bezel: 0, strut: 0, iris: 0, hud: 0, bound: 0 };

  function render(dt) {
    const tint = S.tint, g = S.glow, sp = S.spin;

    // Every assembly turns at its own rate and direction — this is what
    // reads as depth without any real 3D.
    rot.spec   += dt * 14.0 * lerp(0.35, 1, g);   // specular sweep, always alive
    rot.bezel  -= dt *  1.6 * sp;
    rot.plateA += dt *  4.2 * sp;
    rot.plateB -= dt *  6.8 * sp;
    rot.plateC += dt * 10.5 * sp;
    rot.strut  -= dt *  2.4 * sp;
    rot.iris   += dt *  3.0 * sp;
    rot.hud    += dt *  7.0 * sp;
    rot.bound  -= dt *  1.15 * sp;

    ctx.clearRect(0, 0, W, H);

    /* — Ambient nebula — */
    const breath = 0.5 + Math.sin(S.t * 0.55) * 0.5;
    const neb = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 6.4);
    neb.addColorStop(0.00, rgba(tint, 0.10 * g * (0.85 + breath * 0.3)));
    neb.addColorStop(0.24, rgba(C.arc, 0.055 * g));
    neb.addColorStop(0.58, rgba(C.arc, 0.016 * g));
    neb.addColorStop(1.00, "rgba(0,0,0,0)");
    ctx.fillStyle = neb; ctx.fillRect(0, 0, W, H);

    /* — Orbit field — */
    if (S.open > 0.01) {
      const fg = ctx.createRadialGradient(cx, cy, R * G.wedgeIn, cx, cy, R * G.bound);
      fg.addColorStop(0, rgba(C.arc, 0.030 * S.open));
      fg.addColorStop(1, rgba(C.arc, 0.004 * S.open));
      ctx.beginPath(); ctx.arc(cx, cy, R * G.bound, 0, TAU);
      ctx.fillStyle = fg; ctx.fill();
    }

    /* — Particles — */
    if (parts.length) {
      ctx.globalCompositeOperation = "lighter";
      for (const p of parts) {
        p.a += p.sp * dt * 0.09 * sp;
        const tw = 0.55 + Math.sin(S.t * 1.6 + p.ph) * 0.45;
        ctx.beginPath();
        ctx.arc(cx + Math.cos(p.a) * p.r, cy + Math.sin(p.a) * p.r, p.sz, 0, TAU);
        ctx.fillStyle = rgba(tint, p.al * tw * g * 0.7); ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
    }

    /* — Hover wedge, behind the icons — */
    if (S.hoverAmt > 0.01 && S.open > 0.1) {
      const n = currentItems().length;
      const span = (360 / n) * 0.86 * RAD;
      wedge(S.wedgeAngle - span / 2, S.wedgeAngle + span / 2,
            R * G.wedgeIn, R * G.wedgeOut,
            C.arc, 0.17 * S.hoverAmt * S.open, 0.46 * S.hoverAmt * S.open);
    }

    /* — HUD boundary — */
    if (S.open > 0.01) {
      ring(R * G.bound, 1, C.arc, 0.13 * S.open, [1, 7]);
      segRing(R * G.bound * 0.985, 1, tint, 0.20 * S.open, 3, 96, rot.bound);
    }

    drawOrbit();

    /* ── REACTOR ASSEMBLY, outside → in ────────────────── */
    const cs = S.core;

    // HUD instrument ring hugging the reactor
    tickRing(R * 1.66 * cs, R * 0.05, C.steel, 0.5 * (0.35 + g * 0.65), 72, rot.hud * -0.5, 6);
    segRing(R * 1.62 * cs, 1.2, tint, 0.22 * g, 5, 26, rot.hud);

    // Outer bezel
    metalBand(R * G.bezel[0] * cs, R * G.bezel[1] * cs, rot.spec + rot.bezel, 1);

    // Plate ring A — 12 large plates
    plateRing(R * G.plateA[0] * cs, R * G.plateA[1] * cs, 12, 4.5,
              rot.plateA, tint, g);

    // Struts under the inner plates
    struts(8, R * G.strut[0] * cs, R * G.strut[1] * cs, rot.strut, tint, g);

    // Plate ring B — 8 plates
    plateRing(R * G.plateB[0] * cs, R * G.plateB[1] * cs, 8, 6,
              rot.plateB, tint, g * 1.1);

    // Plate ring C — 16 fine plates
    plateRing(R * G.plateC[0] * cs, R * G.plateC[1] * cs, 16, 5,
              rot.plateC, tint, g * 1.2);

    // Lens throat + hot core
    lens(R * G.lens * cs, tint, g, rot.iris);
    hotCore(R * G.hot * cs * (1 + S.proximity * 0.10), tint, g);

    /* — Status arc, outside the bezel — */
    ctx.beginPath();
    ctx.lineWidth = 2; ctx.lineCap = "round";
    ctx.strokeStyle = rgba(tint, 0.5 + 0.4 * g);
    const arcA = 128 * RAD;
    const arcLen = lerp(30, 96, 0.5 + Math.sin(S.t * 0.42) * 0.5) * RAD;
    ctx.arc(cx, cy, R * 1.70 * cs, arcA, arcA + arcLen);
    ctx.stroke(); ctx.lineCap = "butt";

    /* — Surge shockwave on state change — */
    if (S.surge > 0.001) {
      const e = 1 - Math.pow(1 - S.surge, 3);
      ctx.save();
      ctx.globalCompositeOperation = "lighter";
      ring(R * lerp(1.3, 3.4, e), (1 - S.surge) * 2.4 + 0.4, tint, (1 - S.surge) * 0.42);
      ctx.restore();
    }

    /* — Click ripples — */
    for (let i = S.ripples.length - 1; i >= 0; i--) {
      const rp = S.ripples[i];
      rp.p += dt * 1.5;
      if (rp.p >= 1) { S.ripples.splice(i, 1); continue; }
      const e = 1 - Math.pow(1 - rp.p, 3);
      ring(R * (1.4 + e * 2.2), (1 - rp.p) * 2 + 0.3, C.ignition, (1 - rp.p) * 0.45);
    }
  }

  /* ═══════════════════════════════════════════════════════
     9 — ORBITAL ITEMS
     ═══════════════════════════════════════════════════════ */
  const labelEls = [];
  const labelHost = document.getElementById("labels");

  function currentItems() {
    if (S.depth === 2 && S.activeIdx >= 0) {
      const m = MODULES[S.activeIdx];
      return m.kids.map(k => ({ label: k, icon: m.icon }));
    }
    return MODULES.map(m => ({ label: m.label, icon: m.icon }));
  }
  const itemAngle = (i, n) => (-90 + (360 / n) * i) * RAD;

  function syncLabelPool(n) {
    while (labelEls.length < n) {
      const el = document.createElement("div");
      el.className = "mlabel"; labelHost.appendChild(el); labelEls.push(el);
    }
    labelEls.forEach((el, i) => { el.style.display = i < n ? "" : "none"; });
  }

  function drawOrbit() {
    const items = currentItems(), n = items.length;
    syncLabelPool(n);
    if (S.open <= 0.01) { labelEls.forEach(e => e.style.opacity = 0); return; }

    const orbitR = R * G.orbit;
    for (let i = 0; i < n; i++) {
      const stagger = clamp((S.open - (i / n) * 0.18) / 0.82, 0, 1);
      const e = 1 - Math.pow(1 - stagger, 3);
      if (e <= 0.001) { if (labelEls[i]) labelEls[i].style.opacity = 0; continue; }

      const a = itemAngle(i, n);
      const r = orbitR * e;
      const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
      const hov = S.hoverIdx === i ? S.hoverAmt : 0;
      const sz = R * 0.30 * lerp(0.55, 1, e) * lerp(1, 1.22, hov);
      const col = hov > 0.05 ? mix(C.arc, C.ignition, hov) : C.arc;
      const alpha = lerp(0.36, 1, hov) * e;

      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * R * 1.72, cy + Math.sin(a) * R * 1.72);
      ctx.lineTo(cx + Math.cos(a) * (r - sz * 0.9), cy + Math.sin(a) * (r - sz * 0.9));
      ctx.strokeStyle = rgba(C.arc, (0.05 + 0.20 * hov) * e);
      ctx.lineWidth = 1; ctx.stroke();

      const box = sz * 2;
      ctx.save();
      ctx.translate(x, y); ctx.scale(box, box);
      if (hov > 0.05) { ctx.shadowColor = rgba(C.plasma, 0.9); ctx.shadowBlur = 16 * hov; }
      ctx.strokeStyle = rgba(col, alpha);
      ctx.lineWidth = 1.15 / box; ctx.lineJoin = "round"; ctx.lineCap = "round";
      ctx.stroke(unitIcon(items[i].icon));
      ctx.restore();

      if (hov > 0.05) {
        ctx.beginPath(); ctx.arc(x, y, sz * 1.55, 0, TAU);
        ctx.strokeStyle = rgba(C.plasma, 0.30 * hov); ctx.lineWidth = 1; ctx.stroke();
      }

      const el = labelEls[i];
      if (el) {
        el.textContent = items[i].label;
        el.style.left = x + "px";
        el.style.top = (y + sz * 1.5) + "px";
        el.style.opacity = String(lerp(0.55, 1, hov) * e);
        el.classList.toggle("on", hov > 0.5);
      }
    }
  }

  /* ═══════════════════════════════════════════════════════
     10 — INPUT
     ═══════════════════════════════════════════════════════ */
  const cursorEl = document.getElementById("cursor");
  let mx = -999, my = -999, cursorScale = 1;

  addEventListener("pointermove", e => { mx = e.clientX; my = e.clientY; });
  addEventListener("pointerdown", e => { mx = e.clientX; my = e.clientY; onDown(e); });
  addEventListener("pointerleave", () => { mx = my = -999; });

  function hitTest() {
    if (S.open < 0.4) return -1;
    const dx = mx - cx, dy = my - cy, d = Math.hypot(dx, dy);
    if (d < R * G.wedgeIn || d > R * G.wedgeOut) return -1;
    const n = currentItems().length;
    const ang = Math.atan2(dy, dx) / RAD;
    let best = -1, bestDelta = 999;
    for (let i = 0; i < n; i++) {
      const target = -90 + (360 / n) * i;
      const delta = Math.abs((((ang - target + 180) % 360) + 360) % 360 - 180);
      if (delta < bestDelta) { bestDelta = delta; best = i; }
    }
    return bestDelta <= (360 / n) / 2 ? best : -1;
  }

  function onDown(e) {
    if (e.target.closest("#palette")) return;
    const d = Math.hypot(mx - cx, my - cy);

    if (d <= R * G.bezel[1] * 1.05) {
      S.ripples.push({ p: 0 });
      setDepth(S.depth === 0 ? 1 : S.depth === 2 ? 1 : 0);
      return;
    }
    const hit = hitTest();
    if (hit >= 0) {
      S.ripples.push({ p: 0 });
      if (S.depth === 1) {
        S.activeIdx = hit;
        setDepth(2);
        // Opening a module makes the assistant work — a real signal,
        // not a button press.
        Brain.observe("navigate", MODULES[hit].label);
      } else if (S.depth === 2) {
        const m = MODULES[S.activeIdx];
        // The sub-item used to raise a toast and nothing else. It now opens the
        // module's real reading from the kernel.
        Panel.open(m.id, m.label, m.kids[hit]);
      }
    }
  }

  function setDepth(d) {
    S.depth = d;
    document.body.dataset.depth = String(d);
    if (d === 0) S.activeIdx = -1;
    S.hoverIdx = -1;
    document.querySelectorAll("#rail .pip").forEach((p, i) => p.classList.toggle("on", i <= d));
    document.getElementById("crumb").textContent =
      d === 0 ? "Core" : d === 1 ? "Core · Modules" : `Core · ${MODULES[S.activeIdx].label}`;
  }

  /** True while the operator is typing, so shortcuts do not eat their text. */
  const typing = () => {
    const t = document.activeElement;
    return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA");
  };

  addEventListener("keydown", e => {
    if (e.key === "Escape") {
      if (pal.classList.contains("on")) { closePal(); return; }
      // Innermost surface first: a panel or the chat closes before the radial
      // navigation moves, or Escape would rip the whole view out from under
      // someone who only wanted to dismiss a reading.
      if (Panel.isOpen()) { Panel.close(); return; }
      if (Live.chatIsOpen()) { Live.closeChat(); return; }
      setDepth(Math.max(0, S.depth - 1));
      return;
    }
    if ((e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing())) {
      e.preventDefault(); openPal(); return;
    }
    if (typing()) return;

    // Hold V to talk. Held, not toggled: the microphone is open for exactly as
    // long as a key is down, so it cannot be left recording by accident.
    if (e.key.toLowerCase() === "v" && !e.repeat && !pal.classList.contains("on")) {
      e.preventDefault();
      Live.startListening();
      return;
    }
    if (e.key.toLowerCase() === "c" && !pal.classList.contains("on")) {
      e.preventDefault();
      Live.cameraIsOn() ? (Live.stopCamera(), toast("Câmera desligada")) : Live.look();
      return;
    }
    if (e.key === "Enter" && !pal.classList.contains("on")) {
      e.preventDefault(); Live.openChat(); return;
    }
    if (e.key === " " && !pal.classList.contains("on")) {
      e.preventDefault(); setDepth(S.depth === 0 ? 1 : 0);
    }
  });

  addEventListener("keyup", e => {
    if (e.key.toLowerCase() === "v" && Live.isListening()) {
      e.preventDefault();
      Live.stopListeningAndSend();
    }
  });

  // A page torn down with the microphone or camera still open would leave the
  // capture indicator lit with nothing behind it.
  addEventListener("pagehide", () => Live.releaseAll());

  /* ═══════════════════════════════════════════════════════
     11 — BRAIN
     The assistant's own lifecycle drives its state. Nothing here
     is a manual switch: states arrive because something happened
     (a wake word, a command, a background job, a link drop) or
     because a conversation is running its natural course.
     ═══════════════════════════════════════════════════════ */
  const chip = document.getElementById("statusChip");
  const chipText = document.getElementById("statusText");
  const voiceEl = document.getElementById("voice");
  const voiceCap = document.getElementById("voiceCap");
  const transcriptEl = document.getElementById("transcript");
  const linkOut = document.getElementById("linkOut");

  /**
   * The reactor's state machine.
   *
   * The mockup drove this from a timer: canned replies, staged link drops, a
   * conversation that played itself. None of that is here. State arrives from
   * two places only — what the kernel reports (Kernel.start, in boot) and what
   * the operator does. The reactor renders the consequence; it never invents
   * the cause.
   */
  const Brain = (() => {
    function apply(name) {
      if (!STATES[name] || S.name === name) return;
      S.name = name;
      const st = STATES[name];
      chipText.textContent = st.text;
      chip.dataset.state = st.chip;
      S.surge = 1;                                   // shockwave on every transition
      const voicing = name === "listening" || name === "speaking";
      voiceEl.classList.toggle("on", voicing);
      voiceCap.textContent = name === "speaking" ? "Responding" : "Listening";
      if (!voicing) transcriptEl.textContent = "";
      linkOut.textContent = Kernel.linkLabel();
    }

    return {
      start() { apply("idle"); },
      /** The only way the kernel moves the reactor. */
      set(name) { apply(name); },
      /** What the transcript line shows while a voice turn is open. */
      transcript(text) { transcriptEl.textContent = text || ""; },
      /** Operator signals. Navigating does not fake a thinking pass. */
      observe(kind, detail) {
        if (kind === "wake") {
          apply(S.name === "listening" ? "idle" : "listening");
        } else if (kind === "command" && detail) {
          toast(detail);
        }
      },
    };
  })();

  /**
   * Two things move the reactor and they must not fight.
   *
   * The /health poll reports the LINK (offline, warning, idle). `live.js`
   * reports ACTIVITY (listening, thinking, speaking). The poll fires every two
   * seconds, so without an arbiter a health tick landing mid-answer would wipe
   * `speaking` back to `idle` while audio was still playing — the reactor
   * would go quiet and the HUD would be lying about what it was doing.
   *
   * Activity wins while it lasts. A link fault still wins over activity, since
   * a dead kernel is the more important fact and nothing can be in flight.
   */
  const LINK_FAULTS = new Set(["offline", "error", "warning"]);
  let activity = null;       // what live.js says is happening, or null
  let linkState = "idle";    // what the last health poll reported

  function arbitrate() {
    if (LINK_FAULTS.has(linkState)) Brain.set(linkState);
    else Brain.set(activity ?? linkState);
  }

  function onLinkState(state) { linkState = state; arbitrate(); }
  function onActivity(state) {
    activity = state === "idle" ? null : state;
    arbitrate();
  }

  Live.configure({ onState: onActivity, onTranscript: (t) => Brain.transcript(t) });

  /* — Chat input — */
  const chatInput = document.getElementById("chatInput");
  chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      e.preventDefault();
      const text = chatInput.value;
      chatInput.value = "";
      Live.say(text);
    }
    if (e.key === "Escape") { e.preventDefault(); Live.closeChat(); }
  });

  /* — Waveform — */
  const wave = document.getElementById("wave");
  const bars = Array.from({ length: 34 }, () => {
    const i = document.createElement("i"); wave.appendChild(i); return i;
  });

  /* ═══════════════════════════════════════════════════════
     12 — COMMAND PALETTE
     ═══════════════════════════════════════════════════════ */
  const pal = document.getElementById("palette");
  const palInput = document.getElementById("palInput");
  const palList = document.getElementById("palList");

  /* Panel actions reuse the palette's own command pipeline: clicking an action
     button on a panel row runs the exact command typing it would have. One
     pipeline, one honesty — an action either resolves to a real command or it
     says so instead of pretending. */
  Panel.setActionRunner((cmd) => {
    const c = dynamicCommands(cmd);
    const first = c?.[0];
    if (first) {
      first.go();
    } else {
      toast(`sem ação para: ${cmd}`);
    }
  });
  const COMMANDS = MODULES.flatMap(m => [
    { t: m.label, s: "Module", go: () => { S.activeIdx = MODULES.indexOf(m); setDepth(2); } },
    ...m.kids.map(k => ({
      t: `${m.label} · ${k}`, s: "Action",
      go: () => { S.activeIdx = MODULES.indexOf(m); setDepth(2); Panel.open(m.id, m.label, k); },
    })),
  ]);

  /**
   * The cortex — the hand-built brain, zero LLM. Speech no dynamic command
   * matches goes here FIRST: the cortex parses it against its grammar, runs it
   * on the real engines and answers honestly. `falar <texto>` is spoken with
   * the active pack's voice. `understood=false` lists what it knows instead of
   * inventing a reply.
   */
  async function runCortex(text) {
    Panel.openCustom("Cortex", async () => {
      let r;
      try {
        r = await Api.cortexIntent(text);
      } catch (e) {
        return { rows: [{ k: "cortex", v: String(e.message ?? e) }] };
      }
      if (!r.understood) {
        return {
          rows: [{ k: "não entendi", v: `"${r.raw ?? text}" não casa com nenhuma intenção conhecida` }],
          note: `eu sei: ${(r.known ?? []).map(k => k.name).join(", ") || "nada ainda"}`,
        };
      }
      // "falar <texto>" devolve o texto a dizer — o áudio sobe com a voz do pack.
      if (r.verb === "falar" && r.response) Live.speak(r.response);
      const rows = [{ k: r.verb, v: r.response }];
      if (r.target) rows.push({ k: "alvo", v: r.target });
      return {
        rows,
        note: `cortex · ${r.trace?.[0] ?? "intenção determinística"} — sem LLM no caminho`,
      };
    });
  }

  /**
   * Typed input that is not a module name is still meant for the assistant.
   * These entries make the palette answer for it — `buscar X` reaches the web
   * through the kernel, the cortex decides what it can do, anything else is a
   * question for the brain. Without them, typing a real question would
   * silently match nothing.
   */
  function dynamicCommands(raw) {
    const q = raw.trim();
    if (!q) return [];

    // Colar música: um link de YouTube (vira video_id) ou uma URL de stream
    // direto vai direto ao POST /radio/play — o kernel extrai e toca.
    const paste = q.match(/^(?:colar|tocar\s+link)\s+(https?:\/\/\S+|www\.[^\s]+)/i);
    if (paste) {
      const raw = paste[1].trim();
      return [{
        t: `Tocar link: ${raw.slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const vid = youtubeId(raw);
          const r = vid
            ? await Api.radioPlay({ video_id: vid, name: vid })
            : await Api.radioPlay({ url: raw, name: raw });
          const t = r.playing ?? {};
          return {
            rows: [
              { k: "Tocando", v: t.title || (vid ? `YouTube ${vid}` : raw) },
              { k: "Artista", v: t.artist || "—" },
              { k: "Tipo", v: t.stream_type || (r.is_live ? "estação ao vivo" : "—") },
            ],
            note: r.is_live ? "estação ao vivo — fluxo contínuo" : undefined,
          };
        }),
      }];
    }

    // Rádio: tocar playlist e preset vêm ANTES do genérico `tocar <busca>`,
    // senão o regex genérico casa tudo e eles nunca disparam.
    const plPlay = q.match(/^tocar\s+playlist\s+(.+)/i);
    if (plPlay) {
      const name = plPlay[1].trim();
      return [{
        t: `Tocar playlist: ${name.slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPlaylistPlay(name);
          const t = r.playing;
          return { rows: [{ k: "tocando", v: t ? `${t.title}${t.artist ? ` — ${t.artist}` : ""}` : name }] };
        }),
      }];
    }
    const preset = q.match(/^tocar\s+preset\s+(\d+)$/i);
    if (preset) {
      return [{
        t: `Tocar preset ${preset[1]}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPlayPreset(parseInt(preset[1], 10));
          const t = r.playing;
          return { rows: [{ k: "preset", v: t ? `${t.title}${t.artist ? ` — ${t.artist}` : ""}` : "tocando" }] };
        }),
      }];
    }

    // Rádio: buscar e tocar (primeiro resultado), volume, pular.
    const play = q.match(/^tocar\s+(.+)/i);
    if (play) {
      return [{
        t: `Tocar: ${play[1].trim().slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioSearch(play[1].trim());
          const tracks = r.tracks ?? [];
          if (!tracks.length) return { rows: [{ k: "tocar", v: "nada encontrado" }] };
          const first = tracks[0];
          await Api.radioPlay(first.stream_url
            ? { url: first.stream_url, name: first.title }
            : { video_id: first.id, name: first.title });
          return {
            rows: tracks.slice(0, 8).map((t) => ({ k: t.title, v: `${t.artist ?? ""} · ${t.stream_type ?? ""}` })),
            note: `tocando: ${first.title}`,
          };
        }),
      }];
    }
    const volume = q.match(/^volume\s+(\d{1,3})$/i);
    if (volume) {
      const lvl = Math.max(0, Math.min(100, parseInt(volume[1], 10)));
      return [{
        t: `Volume ${lvl}%`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          await Api.radioVolume(lvl / 100);
          return { rows: [{ k: "volume", v: `${lvl}%` }] };
        }),
      }];
    }
    if (/^pular\s+faixa$/i.test(q)) {
      return [{
        t: "Pular faixa", s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioSkip();
          const t = r.track;
          return { rows: [{ k: "pulou", v: t ? `${t.title}${t.artist ? ` — ${t.artist}` : ""}` : "fim da fila" }] };
        }),
      }];
    }
    // Rádio extras: faixa anterior, limpar fila, busca só no YouTube,
    // enfileirar sem interromper, modos (embaralhar/repetir/adblock) e
    // playlists (salvar/listar/apagar).
    if (/^faixa\s+anterior$/i.test(q)) {
      return [{
        t: "Faixa anterior", s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPrevious();
          const t = r.track;
          return { rows: [{ k: "voltou para", v: t ? `${t.title}${t.artist ? ` — ${t.artist}` : ""}` : "nenhuma" }] };
        }),
      }];
    }
    if (/^limpar\s+fila$/i.test(q)) {
      return [{
        t: "Limpar fila", s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          await Api.radioQueueClear();
          return { rows: [{ k: "fila", v: "esvaziada" }] };
        }),
      }];
    }

    // Modos: embaralhar / repetir / adblock — toggles honestos (o kernel
    // devolve o estado novo; o painel mostra o que ficou).
    const shuffleQ = q.match(/^(?:não\s+)?embaralhar$/i);
    if (shuffleQ) {
      const want = !/^não/i.test(shuffleQ[0]);
      return [{
        t: `${want ? "Embaralhar" : "Não embaralhar"}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioToggleShuffle();
          return { rows: [{ k: "embaralhar", v: r.shuffle ? "ligado" : "desligado" }] };
        }),
      }];
    }
    const repeatQ = q.match(/^(?:não\s+)?repetir$/i);
    if (repeatQ) {
      const want = !/^não/i.test(repeatQ[0]);
      return [{
        t: `${want ? "Repetir" : "Não repetir"}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioToggleRepeat();
          return { rows: [{ k: "repetir", v: r.repeat ? "ligado" : "desligado" }] };
        }),
      }];
    }
    const adblockQ = q.match(/^adblock\s+(ligar|desligar)$/i);
    if (adblockQ) {
      return [{
        t: `Adblock ${adblockQ[1]}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioToggleAdblock();
          return { rows: [{ k: "adblock", v: r.ad_blocker_enabled ? "ligado" : "desligado" }] };
        }),
      }];
    }

    // Playlists: salvar a fila atual, listar, apagar.
    const plSave = q.match(/^salvar\s+playlist\s+(.+)/i);
    if (plSave) {
      const name = plSave[1].trim();
      return [{
        t: `Salvar playlist: ${name.slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPlaylistSave(name);
          return { rows: [{ k: "playlist", v: `${r.name} — ${r.count} faixa(s)` }] };
        }),
      }];
    }
    if (/^playlists$/i.test(q)) {
      return [{
        t: "Playlists salvas", s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPlaylists();
          const pls = r.playlists ?? [];
          return {
            rows: pls.length
              ? pls.map((p) => ({ k: p.name, v: `${p.count} faixa(s) · ${(p.titles ?? []).join(" / ")}` }))
              : [{ k: "playlists", v: "nenhuma salva — `salvar playlist <nome>` com uma fila tocando" }],
            note: "playlists são cópias da fila em memória — somem no reboot, como a fila",
          };
        }),
      }];
    }
    const plDel = q.match(/^apagar\s+playlist\s+(.+)/i);
    if (plDel) {
      const name = plDel[1].trim();
      return [{
        t: `Apagar playlist: ${name.slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioPlaylistDelete(name);
          return { rows: [{ k: "apagada", v: r.deleted }] };
        }),
      }];
    }
    const yt = q.match(/^buscar\s+m[úu]sica\s+(.+)/i);
    if (yt) {
      const term = yt[1].trim();
      return [{
        t: `Buscar música: ${term}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioYoutube(term);
          const tracks = r.tracks ?? [];
          return {
            rows: tracks.slice(0, 8).map((t) => ({
              k: t.title,
              v: `${t.artist ?? ""}${t.duration ? ` · ${Math.round(t.duration / 60)} min` : ""}`,
            })),
            note: tracks.length
              ? `${tracks.length} faixa(s) — tocar: “colar <link>” ou “adicionar à fila ${term}”`
              : "nada encontrado",
          };
        }),
      }];
    }
    const enq = q.match(/^adicionar\s+(?:à|a)\s+fila\s+(.+)/i);
    if (enq) {
      const term = enq[1].trim();
      return [{
        t: `Adicionar à fila: ${term}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Radio", async () => {
          const r = await Api.radioYoutube(term, 1);
          const t = (r.tracks ?? [])[0];
          if (!t) return { rows: [{ k: "fila", v: "nada encontrado" }] };
          const qa = await Api.radioQueueAdd({
            track_id: t.id, title: t.title, artist: t.artist ?? "",
            stream_url: t.stream_url ?? "", stream_type: t.stream_type ?? "youtube",
          });
          return {
            rows: [{ k: "fila", v: `${t.title}${t.artist ? ` — ${t.artist}` : ""}` }],
            note: qa.queue_length != null ? `posição ${qa.position ?? "?"} de ${qa.queue_length}` : undefined,
          };
        }),
      }];
    }

    // Voz: trocar o pacote ativo. Só oferece o que o kernel conhece — um
    // nome desconhecido devolveria Jarvis Classic por fallback, e o HUD não
    // inventa; ele diz que não achou e lista as opções reais.
    const voice = q.match(/^(?:usar\s+voz|voz)\s+(.+)/i);
    if (voice) {
      const want = voice[1].trim().toLowerCase();
      return [{
        t: `Usar voz: ${voice[1].trim().slice(0, 40)}`, s: "Voice",
        go: () => Panel.openCustom("Voice · Voices", async () => {
          const packs = await Api.voicePacks();
          const list = Array.isArray(packs) ? packs : (packs.packs ?? []);
          const hit = list.find((p) => {
            const key = String(p.key ?? "").toLowerCase();
            const name = String(p.name ?? "").toLowerCase();
            return key === want || name === want || (name && name.startsWith(want));
          });
          if (!hit) {
            const keys = list.map((p) => p.key ?? p.name).filter(Boolean).join(", ");
            return {
              rows: [{ k: "voz", v: "não encontrada" }],
              note: keys ? `disponíveis: ${keys}` : "nenhum pacote de voz instalado",
            };
          }
          const key = hit.key ?? hit.name;
          const p = await Api.voicePack(key);
          return {
            rows: [
              { k: "Voz", v: p.name ?? key },
              { k: "Descrição", v: p.description ?? "—" },
              { k: "Saudação", v: p.greeting ?? "—" },
              { k: "Fala", v: `${p.tts_voice ?? "—"} · ritmo ${p.tts_rate ?? "—"} · tom ${p.tts_pitch ?? "—"}` },
              ...(p.voice_profile ? [{ k: "Clonagem", v: p.voice_profile }] : []),
            ],
            note: "ativa a partir de agora — a voz TTS, a persona do chat e as respostas mudam juntas",
          };
        }),
      }];
    }

    // Falar: o Jarvis diz o texto com a voz do pack ativo, via TTS do kernel.
    const speak = q.match(/^falar\s+(.+)/i);
    if (speak) {
      const text = speak[1].trim();
      return [{
        t: `Falar: ${text.slice(0, 40)}`, s: "Voice",
        go: () => Live.speak(text),
      }];
    }

    // Sessão: o cofre e a postura de segurança exigem um token de dono de
    // verdade (nunca o bypass). Login guarda o JWT no navegador e toda
    // request passa a apresentá-lo.
    const lg = q.match(/^login\s+(\S+)\s+(\S+)/i);
    if (lg) {
      return [{
        t: `Entrar como ${lg[1]}`, s: "Security",
        go: () => Panel.openCustom("Security · Keys", async () => {
          const r = await Api.login(lg[1], lg[2]);
          Api.setToken(r.access_token);
          return {
            rows: [{ k: "sessão", v: `autenticado · dono ${(r.owner_id ?? "").slice(0, 8)}` }],
            note: "o token fica neste navegador até `sair`",
          };
        }),
      }];
    }
    if (/^sair$/i.test(q)) {
      return [{
        t: "Sair (esquecer token)", s: "Security",
        go: () => Panel.openCustom("Security · Keys", async () => {
          Api.setToken("");
          return { rows: [{ k: "sessão", v: "encerrada — token esquecido" }] };
        }),
      }];
    }

    // Actions: mandar um comando a um aparelho pareado.
    // `comandar <aparelho> <ação>` — seletor por nome ou tipo (celular, pc...).
    const cmd = q.match(/^comandar\s+(\S+)\s+(.+)/i);
    if (cmd) {
      return [{
        t: `Comandar ${cmd[1]} → ${cmd[2].trim().slice(0, 40)}`, s: "Network",
        go: () => Panel.openCustom("Network · Actions", async () => {
          const r = await Api.actionDispatch(cmd[1], cmd[2].trim());
          if (r.ok === false) {
            return { rows: [{ k: "comando", v: "não enviado" }], note: r.error ?? "dispositivo não encontrado" };
          }
          return {
            rows: [
              { k: "Dispositivo", v: r.device ?? cmd[1] },
              { k: "Comando", v: cmd[2].trim() },
              { k: "Status", v: r.status ?? "—" },
              { k: "Entrega", v: r.delivered ? "recebido ao vivo" : "na fila (corpo vai buscar)" },
            ],
            note: `id: ${(r.command_id ?? "").slice(0, 8)}`,
          };
        }),
      }];
    }

    // Capabilities: invocar uma capacidade do kernel com params livres
    // (chave=valor). O kernel resolve {param} e {segredo.X} no template.
    const call = q.match(/^chamar\s+(\S+?)(?:\s+(.+))?$/i);
    if (call) {
      const name = call[1];
      // chave=valor; um token sem "=" continua o valor anterior (espaços).
      const params = {};
      let cur = null;
      for (const tok of (call[2] ?? "").trim().split(/\s+/)) {
        const eq = tok.indexOf("=");
        if (eq > 0) { cur = tok.slice(0, eq); params[cur] = tok.slice(eq + 1); }
        else if (cur && tok) params[cur] += ` ${tok}`;
      }
      return [{
        t: `Chamar capability: ${name}`, s: "Security",
        go: () => Panel.openCustom("Security · Keys", async () => {
          const r = await Api.connectorCall(name, params);
          if (r.ok === false) {
            return { rows: [{ k: name, v: "não chamado" }], note: r.error ?? `HTTP ${r.status}` };
          }
          const d = r.data;
          const entries = d && typeof d === "object" && !Array.isArray(d)
            ? Object.entries(d)
            : [["resposta", Array.isArray(d) ? JSON.stringify(d) : String(d)]];
          return {
            rows: entries.slice(0, 12).map(([k, v]) => ({ k, v: typeof v === "object" ? JSON.stringify(v) : String(v) })),
            note: `HTTP ${r.status} · ${name}`,
          };
        }),
      }];
    }

    // Decision: o kernel escolhe o que focar agora (ranqueia metas abertas).
    if (/^decidir\s+foco$/i.test(q)) {
      return [{
        t: "Decidir o foco agora", s: "Projects",
        go: () => Panel.openCustom("Projects · Decision", async () => {
          const r = await Api.decideNext();
          if (!r.decision) {
            return { rows: [{ k: "foco", v: "nenhum" }], note: r.reason ?? "nenhum objetivo elegível" };
          }
          const d = r.decision;
          return {
            rows: [
              { k: "Foco", v: d.chosen_label ?? "—" },
              { k: "Porquê", v: d.rationale ?? "—" },
              { k: "Política", v: d.policy ?? "—" },
            ],
            note: (d.options ?? []).length ? `${d.options.length} opção(ões) avaliada(s)` : undefined,
          };
        }),
      }];
    }

    // Varredura completa: todos os probes numa lista de linhas de .env.
    // Lento por definição — ocupa a máquina por vários minutos.
    if (/^otimizar\s+completo$/i.test(q)) {
      return [{
        t: "Varredura completa de otimização (lento — vários minutos)", s: "System",
        go: () => Panel.openCustom("System · Optimize", async () => {
          const o = await Api.optimizeFull();
          return {
            rows: [
              ...(o.env ?? []).map((line) => ({ k: "env", v: line })),
              { k: "Contexto", v: o.context?.knee_tokens ? `${o.context.knee_tokens} tokens` : "—" },
              { k: "Threads", v: o.threads?.best ?? "—" },
              { k: "Batch", v: o.embedding_batch?.best ?? "—" },
              ...(o.models ?? []).slice(0, 4).map((m) => ({ k: m.name, v: `${m.size_gb ?? "?"} GB · ${m.quantization ?? "?"}` })),
            ],
            note: [...(o.findings ?? []), ...(o.notes ?? [])].slice(0, 5).join(" · ")
              || "nenhuma recomendação — o kernel só reporta; quem edita o .env é você",
          };
        }),
      }];
    }

    // Otimizador: cronometrar cada modelo de verdade (lento, explícito).
    if (/^(medir otimização|medir otimizacao|otimizar)$/i.test(q)) {
      return [{
        t: "Medir a inferência (lento — minutos em CPU)", s: "System",
        go: () => Panel.openCustom("System · Optimize", async () => {
          const o = await Api.optimizeProbe();
          const rows = (o.models ?? []).map((m) => ({
            k: m.name,
            v: m.error
              ? `erro: ${m.error}`
              : [
                  m.warm_reply_s != null ? `quente ${m.warm_reply_s}s` : null,
                  m.cold_load_s != null ? `frio ${m.cold_load_s}s` : null,
                  m.tokens_per_s != null ? `${m.tokens_per_s} tok/s` : null,
                ].filter(Boolean).join(" · ") || "—",
          }));
          return {
            rows,
            note: [...(o.findings ?? []), ...(o.actions ?? [])].join(" · ") || "nenhuma ação recomendada",
          };
        }),
      }];
    }

    // Pulse: rodar um ciclo do agente agora. O relatório do tick é o retorno.
    if (/^rodar\s+pulse$/i.test(q)) {
      return [{
        t: "Rodar ciclo do agente agora", s: "Agent",
        go: () => Panel.openCustom("Agents · Pulse", async () => {
          const r = await Api.pulseRun();
          return {
            rows: [
              { k: "Ciclo", v: r.reason ?? "executado" },
              { k: "Percebeu", v: String((r.noticed ?? []).length) },
              { k: "Executou", v: String((r.executed ?? []).length) },
              { k: "Propôs", v: String((r.proposed ?? []).length) },
              { k: "Pulou", v: String((r.skipped ?? []).length) },
            ],
            note: (r.skipped ?? []).join(" · ") || undefined,
          };
        }),
      }];
    }

    // Portão de confirmação: aprovar/recusar proposta pelo prefixo do id
    // (o painel Agents · Proposals mostra os 8 primeiros caracteres).
    const approve = q.match(/^aprovar\s+(\S+)/i);
    if (approve) {
      return [{
        t: `Aprovar proposta ${approve[1]}`, s: "Agent",
        go: () => Panel.openCustom("Agents · Proposals", async () => {
          const id = await resolveProposal(approve[1]);
          const p = await Api.approveProposal(id);
          return { rows: [{ k: p.title ?? id, v: `aprovada · ${p.status ?? "executada"}` }] };
        }),
      }];
    }
    const reject = q.match(/^recusar\s+(\S+)/i);
    if (reject) {
      return [{
        t: `Recusar proposta ${reject[1]}`, s: "Agent",
        go: () => Panel.openCustom("Agents · Proposals", async () => {
          const id = await resolveProposal(reject[1]);
          const p = await Api.rejectProposal(id);
          return { rows: [{ k: p.title ?? id, v: `recusada · ${p.status ?? "rejeitada"}` }] };
        }),
      }];
    }

    // Automações: rodar, ativar/desativar e instalar o catálogo embutido.
    const autoRun = q.match(/^rodar\s+automa[çc][ãa]o\s+(.+)/i);
    if (autoRun) {
      const slug = autoRun[1].trim();
      return [{
        t: `Rodar automação: ${slug}`, s: "Agent",
        go: () => Panel.openCustom("Agents · Queue", async () => {
          const r = await Api.runAutomation(slug);
          return {
            rows: [
              { k: "Workflow", v: r.workflow ?? slug },
              { k: "Status", v: r.status ?? "—" },
              { k: "Nós executados", v: String(r.nodes_executed ?? 0) },
              { k: "Duração", v: r.duration_ms != null ? `${r.duration_ms} ms` : "—" },
              ...(r.error ? [{ k: "erro", v: r.error }] : []),
            ],
            note: `execução ${String(r.execution_id ?? "").slice(0, 8)} — veja Agents · Queue`,
          };
        }),
      }];
    }
    const autoTgl = q.match(/^(ativar|desativar)\s+automa[çc][ãa]o\s+(\S+)/i);
    if (autoTgl) {
      const on = autoTgl[1].toLowerCase() === "ativar";
      const slug = autoTgl[2];
      return [{
        t: `${on ? "Ativar" : "Desativar"} automação: ${slug}`, s: "Agent",
        go: () => Panel.openCustom("Agents · Spawn", async () => {
          const r = await Api.automationEnable(slug, on);
          return { rows: [{ k: r.slug ?? slug, v: r.ativo ? "armada" : "desarmada" }] };
        }),
      }];
    }
    if (/^instalar\s+automa[çc][õo]es$/i.test(q)) {
      return [{
        t: "Instalar catálogo de automações", s: "Agent",
        go: () => Panel.openCustom("Agents · Spawn", async () => {
          const r = await Api.automationInstall();
          const list = Array.isArray(r.instaladas) ? r.instaladas : [];
          return {
            rows: list.slice(0, 12).map((s) => ({ k: String(s), v: "instalada" })),
            note: list.length ? `${r.total ?? list.length} no catálogo — as suas edições nunca são sobrescritas` : "catálogo já instalado",
          };
        }),
      }];
    }
    // Briefing: gerar agora e mostrar o resumo na hora.
    if (/^gerar\s+briefing$/i.test(q)) {
      return [{
        t: "Gerar briefing agora", s: "Projects",
        go: () => Panel.openCustom("Projects · Timeline", async () => {
          const b = await Api.generateBriefing();
          return {
            rows: String(b.summary ?? "").split("\n").filter(Boolean).map((l, i) => ({ k: `#${i + 1}`, v: l })),
            note: `briefing ${b.kind ?? "on_demand"} de ${when(b.created_at)}`,
          };
        }),
      }];
    }

    // Agenda: criar lembrete `lembrar <texto> em <n> <min|h|d>`, com
    // recorrência opcional `repetir a cada <n> <unidade>`. Checa ANTES do
    // recall de memória, que é o `lembrar X` sem tempo.
    const remind = parseReminder(q);
    if (remind) {
      return [{
        t: `Lembrete: ${remind.text} (${remind.in_minutes ?? remind.in_hours ?? remind.in_days} ${remind.recurrence_seconds ? ", repetindo" : ""})`, s: "Schedule",
        go: () => Panel.openCustom("Terminal · Jobs", async () => {
          const t = await Api.scheduleCreate(remind);
          return {
            rows: [{ k: t.text ?? "lembrete", v: `agendado · ${when(t.due_at)}` }],
            note: remind.recurrence_seconds ? `repete a cada ${Math.round(remind.recurrence_seconds / 60)} min` : undefined,
          };
        }),
      }];
    }
    // Diário, hábitos e timer — escritas rápidas, cada uma com o painel de destino.
    const note = q.match(/^anotar\s+(.+)/i);
    if (note) {
      return [{
        t: `Anotar no diário: ${note[1].trim().slice(0, 40)}`, s: "Files",
        go: () => Panel.openCustom("Files · Journal", async () => {
          const e = await Api.journalAdd(note[1].trim());
          return { rows: [{ k: "anotado", v: e.content }] };
        }),
      }];
    }
    const habit = q.match(/^marcar\s+hábito\s+(.+)/i);
    if (habit) {
      return [{
        t: `Marcar hábito: ${habit[1].trim().slice(0, 40)}`, s: "Files",
        go: () => Panel.openCustom("Files · Habits", async () => {
          const r = await Api.habitCheck(habit[1].trim());
          return { rows: [{ k: r.habit ?? "hábito", v: `streak ${r.streak ?? 0} dia(s)` }] };
        }),
      }];
    }
    const timerOn = q.match(/^iniciar\s+timer\s+(.+)/i);
    if (timerOn) {
      return [{
        t: `Iniciar timer: ${timerOn[1].trim().slice(0, 40)}`, s: "System",
        go: () => Panel.openCustom("System · Time", async () => {
          const e = await Api.timeStart(timerOn[1].trim());
          return { rows: [{ k: e.label ?? "timer", v: "aberto" }] };
        }),
      }];
    }
    if (/^parar\s+timer$/i.test(q)) {
      return [{
        t: "Parar timer", s: "System",
        go: () => Panel.openCustom("System · Time", async () => {
          const r = await Api.timeStop();
          const stopped = r?.stopped;
          return { rows: [{ k: "timer", v: stopped ? "parado" : "nenhum aberto" }] };
        }),
      }];
    }

    const cancel = q.match(/^cancelar\s+lembrete\s+(\S+)/i);
    if (cancel) {
      return [{
        t: `Cancelar lembrete ${cancel[1]}`, s: "Schedule",
        go: () => Panel.openCustom("Terminal · Jobs", async () => {
          const id = await resolveTask(cancel[1]);
          await Api.scheduleCancel(id);
          return { rows: [{ k: id, v: "cancelado" }] };
        }),
      }];
    }

    // Metas: criar, concluir, atualizar progresso e cancelar — resolvidas pelo
    // título (o painel Projects · Active mostra títulos, não ids).
    const goalNew = q.match(/^criar\s+meta\s+(.+)/i);
    if (goalNew) {
      return [{
        t: `Criar meta: ${goalNew[1].trim().slice(0, 40)}`, s: "Projects",
        go: () => Panel.openCustom("Projects · Active", async () => {
          const g = await Api.goalCreate(goalNew[1].trim());
          return { rows: [{ k: g.title ?? "meta", v: "criada" }], note: `id ${String(g.id).slice(0, 8)}` };
        }),
      }];
    }
    const goalDone = q.match(/^concluir\s+meta\s+(.+)/i);
    if (goalDone) {
      return [{
        t: `Concluir meta: ${goalDone[1].trim().slice(0, 40)}`, s: "Projects",
        go: () => Panel.openCustom("Projects · Active", async () => {
          const id = await resolveGoal(goalDone[1].trim());
          const g = await Api.goalComplete(id);
          return { rows: [{ k: g.title ?? id, v: `concluída · ${g.status ?? "done"}` }] };
        }),
      }];
    }
    const goalProg = q.match(/^progresso\s+meta\s+(.+?)\s+(\d{1,3})\s*%?$/i);
    if (goalProg) {
      const pct = Math.max(0, Math.min(100, parseInt(goalProg[2], 10)));
      return [{
        t: `Progresso da meta ${goalProg[1].trim().slice(0, 30)} → ${pct}%`, s: "Projects",
        go: () => Panel.openCustom("Projects · Active", async () => {
          const id = await resolveGoal(goalProg[1].trim());
          const g = await Api.goalProgress(id, pct / 100);
          return { rows: [{ k: g.title ?? id, v: `${Math.round((g.progress ?? 0) * 100)}%` }] };
        }),
      }];
    }
    const goalCancel = q.match(/^cancelar\s+meta\s+(.+)/i);
    if (goalCancel) {
      return [{
        t: `Cancelar meta: ${goalCancel[1].trim().slice(0, 40)}`, s: "Projects",
        go: () => Panel.openCustom("Projects · Active", async () => {
          const id = await resolveGoal(goalCancel[1].trim());
          await Api.goalCancel(id);
          return { rows: [{ k: id, v: "cancelada" }] };
        }),
      }];
    }

    // Vault Obsidian: importar/exportar (escrevem no seu disco — explícitos)
    // e ligar/desligar o watcher de auto-sync.
    const vaultIn = q.match(/^importar\s+vault\s+(.+)/i);
    if (vaultIn) {
      return [{
        t: `Importar vault: ${vaultIn[1].trim().slice(0, 40)}`, s: "Files",
        go: () => Panel.openCustom("Files · Sync", async () => {
          const r = await Api.obsidianImport(vaultIn[1].trim());
          return { rows: [{ k: "import", v: r.ok ? "concluído" : "falhou" }], note: r.message ?? "" };
        }),
      }];
    }
    const vaultOut = q.match(/^exportar\s+vault\s+(.+)/i);
    if (vaultOut) {
      return [{
        t: `Exportar vault: ${vaultOut[1].trim().slice(0, 40)}`, s: "Files",
        go: () => Panel.openCustom("Files · Sync", async () => {
          const r = await Api.obsidianExport(vaultOut[1].trim());
          return { rows: [{ k: "export", v: r.ok ? "concluído" : "falhou" }], note: r.message ?? "" };
        }),
      }];
    }
    const vaultWatch = q.match(/^observar\s+vault(?:\s+(.+))?$/i);
    if (vaultWatch) {
      const path = vaultWatch[1] ? vaultWatch[1].trim() : null;
      return [{
        t: `Observar vault${path ? `: ${path}` : ""}`, s: "Files",
        go: () => Panel.openCustom("Files · Sync", async () => {
          const r = await Api.obsidianWatch("start", path);
          return { rows: [{ k: "watcher", v: r.ok ? (r.message ?? "ligado") : "falhou" }], note: r.message ?? "" };
        }),
      }];
    }
    if (/^(?:parar\s+observação|parar\s+observacao)$/i.test(q)) {
      return [{
        t: "Parar observação do vault", s: "Files",
        go: () => Panel.openCustom("Files · Sync", async () => {
          const r = await Api.obsidianWatch("stop");
          return { rows: [{ k: "watcher", v: r.ok ? (r.message ?? "desligado") : "falhou" }], note: r.message ?? "" };
        }),
      }];
    }

    // Mundo: o kernel sabe o presente (fatos) e quem é o dono (perfil) —
    // curadoria soberana: o dono lê, define e esquece o que quiser.
    const profSet = q.match(/^definir\s+perfil\s+(\S+)\s+(.+)/i);
    if (profSet) {
      return [{
        t: `Definir perfil ${profSet[1]}`, s: "AI",
        go: () => Panel.openCustom("AI · Context", async () => {
          const a = await Api.worldSetProfile(profSet[1], profSet[2].trim());
          return { rows: [{ k: a.key, v: a.value }], note: "o kernel passa a saber isso sobre você" };
        }),
      }];
    }
    const profForget = q.match(/^esquecer\s+perfil\s+(\S+)/i);
    if (profForget) {
      return [{
        t: `Esquecer perfil ${profForget[1]}`, s: "AI",
        go: () => Panel.openCustom("AI · Context", async () => {
          const r = await Api.worldForgetProfile(profForget[1]);
          return { rows: [{ k: r.forgotten ?? profForget[1], v: "esquecido" }] };
        }),
      }];
    }
    const factSet = q.match(/^definir\s+fato\s+(\S+)\s+(.+)/i);
    if (factSet) {
      return [{
        t: `Definir fato ${factSet[1]}`, s: "AI",
        go: () => Panel.openCustom("AI · Context", async () => {
          const f = await Api.worldSetFact(factSet[1], factSet[2].trim());
          return { rows: [{ k: f.key, v: f.value }], note: "o kernel passa a saber isso sobre o mundo" };
        }),
      }];
    }
    const factForget = q.match(/^esquecer\s+fato\s+(\S+)/i);
    if (factForget) {
      return [{
        t: `Esquecer fato ${factForget[1]}`, s: "AI",
        go: () => Panel.openCustom("AI · Context", async () => {
          const r = await Api.worldForgetFact(factForget[1]);
          return { rows: [{ k: r.forgotten ?? factForget[1], v: "esquecido" }] };
        }),
      }];
    }

    // Memória: guardar um fato de propósito e esquecer pelo id/título.
    const keep = q.match(/^guardar\s+(.+)/i);
    if (keep) {
      return [{
        t: `Guardar: ${keep[1].trim().slice(0, 40)}`, s: "Memory",
        go: () => Panel.openCustom("Memory · Recent", async () => {
          const m = await Api.remember(keep[1].trim());
          return { rows: [{ k: m.title ?? "memória", v: m.content }], note: `id ${String(m.id).slice(0, 8)}` };
        }),
      }];
    }
    const forgetMem = q.match(/^esquecer\s+(.+)/i);
    if (forgetMem) {
      return [{
        t: `Esquecer: ${forgetMem[1].trim().slice(0, 40)}`, s: "Memory",
        go: () => Panel.openCustom("Memory · Purge", async () => {
          const id = await resolveMemory(forgetMem[1].trim());
          await Api.forget(id);
          return { rows: [{ k: id, v: "esquecido — ligações em cascata" }] };
        }),
      }];
    }

    // Dispositivos: revogar um corpo pareado pelo nome.
    const revoke = q.match(/^revogar\s+aparelho\s+(.+)/i);
    if (revoke) {
      return [{
        t: `Revogar aparelho: ${revoke[1].trim().slice(0, 40)}`, s: "Network",
        go: () => Panel.openCustom("Network · Devices", async () => {
          const id = await resolveDevice(revoke[1].trim());
          await Api.deviceRevoke(id);
          return { rows: [{ k: id, v: "revogado — o aparelho perde acesso" }] };
        }),
      }];
    }

    // Defesa ativa: armar/desarmar honeytokens pelo cofre. O valor-isca nunca
    // importa (é bait — o kernel nunca o devolve), então o HUD gera um.
    const arm = q.match(/^armar\s+honeypot\s+(.+)/i);
    if (arm) {
      const name = `honeypot.${arm[1].trim()}`;
      return [{
        t: `Armar honeytoken: ${name}`, s: "Security",
        go: () => Panel.openCustom("Security · Threats", async () => {
          await Api.setSecret(name, `sk-isca-${Math.random().toString(36).slice(2, 10)}`);
          return {
            rows: [{ k: name, v: "armado — quem o ler dispara um alerta de ameaça" }],
            note: "o valor-isca foi gerado na hora e nunca será devolvido",
          };
        }),
      }];
    }
    const disarm = q.match(/^desarmar\s+honeypot\s+(.+)/i);
    if (disarm) {
      const raw = disarm[1].trim();
      const name = raw.toLowerCase().startsWith("honeypot.") ? raw : `honeypot.${raw}`;
      return [{
        t: `Desarmar honeytoken: ${name}`, s: "Security",
        go: () => Panel.openCustom("Security · Threats", async () => {
          await Api.deleteSecret(name);
          return { rows: [{ k: name, v: "desarmado" }] };
        }),
      }];
    }

    // Browser: buscar e trazer o conteúdo do melhor resultado (a aba do kernel
    // vira `search_and_fetch` em Tabs). Checa ANTES do `buscar` simples.
    const fetch = q.match(/^buscar\s+e\s+trazer\s+(.+)/i);
    if (fetch) {
      const term = fetch[1].trim();
      return [{
        t: `Buscar e trazer: ${term}`, s: "Web",
        go: () => Panel.openCustom("Browser · Capture", async () => {
          const r = await Api.searchAndFetch(term);
          const top = r.top_content ?? {};
          return {
            rows: [
              { k: "Termo", v: term },
              { k: "Resultados", v: String((r.results ?? []).length) },
              { k: "Melhor resultado", v: top.title ?? top.url ?? "—" },
              { k: "Conteúdo", v: String(top.content ?? "").replace(/\s+/g, " ").slice(0, 140) || "—" },
            ],
            note: top.url ?? undefined,
          };
        }),
      }];
    }

    // Marcadores: links que valem guardar viram memórias de tipo bookmark.
    const mark = q.match(/^marcar\s+(https?:\/\/\S+)(?:\s+(.+))?$/i);
    if (mark) {
      const title = mark[2] ? mark[2].trim() : mark[1];
      return [{
        t: `Marcar: ${title.slice(0, 40)}`, s: "Browser",
        go: () => Panel.openCustom("Browser · Marks", async () => {
          const m = await Api.browserMarkAdd(mark[1], title);
          return {
            rows: [{ k: m.title ?? title, v: m.url }],
            note: `marcador ${String(m.id).slice(0, 8)} — vive em Memory (kind bookmark)`,
          };
        }),
      }];
    }
    const unmark = q.match(/^desmarcar\s+(.+)/i);
    if (unmark) {
      return [{
        t: `Desmarcar: ${unmark[1].trim().slice(0, 40)}`, s: "Browser",
        go: () => Panel.openCustom("Browser · Marks", async () => {
          const id = await resolveMark(unmark[1].trim());
          await Api.browserMarkDelete(id);
          return { rows: [{ k: id, v: "desmarcado — a memória foi esquecida" }] };
        }),
      }];
    }

    const search = q.match(/^buscar\s+(.+)/i);
    if (search) {
      const term = search[1];
      return [{
        t: `Buscar na web: ${term}`, s: "Web",
        go: () => Panel.openCustom("Browser · Research", async () => {
          const r = await Api.webSearch(term);
          return {
            rows: (r.results ?? []).slice(0, 8).map(x => ({ k: x.title ?? "—", v: x.url ?? x.href ?? "—" })),
            note: r.results?.length ? `${r.results.length} resultado(s) para "${term}"` : "nenhum resultado",
          };
        }),
      }];
    }
    // Regras declarativas do cortex: `avaliar regras` roda o motor contra o
    // mundo real e mostra as decisões com a trilha condição por condição;
    // `regras` lista a gramática de decisão carregada.
    if (/^avaliar regras$/i.test(q)) {
      return [{
        t: "Avaliar regras (cortex)", s: "Cortex",
        go: () => Panel.openCustom("Cortex · Regras", async () => {
          const r = await Api.cortexRulesEvaluate();
          const decs = r.decisions ?? [];
          const trail = r.trail ?? [];
          const rows = decs.length
            ? decs.map(d => ({ k: d.regra, v: d.acoes?.[0]?.valor ?? d.descricao }))
            : [{ k: "nenhuma regra disparou", v: "o mundo atual não casa com nenhuma condição" }];
          const top = trail.find(t => t.disparou);
          const why = top
            ? top.condicoes.map(c => `${c.detalhe}${c.passou ? " ✓" : " ✗"}`).join(" · ")
            : "nenhuma condição casou";
          return {
            rows,
            note: `${decs.length} de ${trail.length} regras · por que: ${why}`,
          };
        }),
      }];
    }
    if (/^regras$/i.test(q)) {
      return [{
        t: "Regras do cortex", s: "Cortex",
        go: () => Panel.openCustom("Cortex · Regras", async () => {
          const r = await Api.cortexRules();
          const rs = r.regras ?? [];
          return {
            rows: rs.map(g => ({ k: g.id, v: `${g.descricao} (p${g.prioridade}${g.auto ? " · auto" : ""})` })),
            note: `${rs.length} regras declarativas — condição → ação, com trilha do porquê`,
          };
        }),
      }];
    }

    // Regras → pulse: regras disparadas viram PROPOSTAS (source=cortex) com a
    // trilha anexada; aprova com 1 clique em Agents · Proposals.
    if (/^propor regras$/i.test(q)) {
      return [{
        t: "Propor regras (pulse)", s: "Cortex",
        go: () => Panel.openCustom("Cortex · Propostas", async () => {
          const r = await Api.cortexRegrasPropor();
          const criadas = r.propostas_criadas ?? [];
          const auto = r.auto_executadas ?? [];
          const rows = criadas.length
            ? (r.regras?.decisions ?? []).map(d => ({ k: d.regra, v: d.descricao }))
            : [{ k: "nenhuma regra disparou", v: "o mundo atual não gera proposta" }];
          return {
            rows,
            note: `${criadas.length} proposta(s) criada(s)${auto.length ? ` · ${auto.length} auto-executada(s)` : ""} — aprovar em Agents · Proposals (▶ executar)`,
          };
        }),
      }];
    }

    // Núcleo decisório: um ciclo único sem LLM — contexto → regras → metas
    // ranqueadas (DecisionEngine) → escolha determinística com rationale.
    if (/^decidir$/i.test(q)) {
      return [{
        t: "Decidir (núcleo)", s: "Cortex",
        go: () => Panel.openCustom("Cortex · Decisão", async () => {
          const r = await Api.cortexDecidir();
          const e = r.escolha ?? {};
          const rows = [{ k: e.tipo, v: e.descricao ?? "—" }];
          if (e.tipo === "foco" && r.foco) rows.push({ k: "foco", v: `${r.foco.label} (score ${r.foco.score})` });
          if (e.tipo === "regra" && e.alvo) rows.push({ k: "regra", v: e.alvo });
          if (e.tipo === "nenhuma" && r.foco) rows.push({ k: "foco possível", v: r.foco.label });
          const top = (r.regras?.trail ?? []).find(t => t.disparou);
          const why = top
            ? top.condicoes.map(c => `${c.detalhe}${c.passou ? " ✓" : " ✗"}`).join(" · ")
            : "nenhuma regra forte disparou";
          return {
            rows,
            note: `${e.rationale ?? ""} — ${r.regras?.dispararam ?? 0} de ${r.regras?.total ?? 0} regras (${why})`,
          };
        }),
      }];
    }

    return [
      { t: `Jarvis: ${q}`, s: "Cortex", go: () => runCortex(q) },
      { t: `Perguntar: ${q}`, s: "Chat", go: () => Live.say(q) },
      { t: `Lembrar: ${q}`, s: "Memory", go: () => Panel.openCustom("Memory · Semantic", async () => {
        const ms = await Api.recall(q);
        return {
          rows: ms.map(m => ({ k: m.kind ?? "fato", v: m.title || m.content })),
          note: ms.length ? `${ms.length} memória(s) para "${q}"` : "nada lembrado sobre isso",
        };
      }) },
    ];
  }

  /** Proposta pelo prefixo do id (o painel Agents · Proposals mostra 8 chars). */
  async function resolveProposal(prefix) {
    const ps = await Api.proposals();
    const hit = ps.find(p => String(p.id).toLowerCase().startsWith(prefix.toLowerCase()));
    if (!hit) throw new Error(`nenhuma proposta começa com "${prefix}"`);
    return hit.id;
  }

  /**
   * Extrai o id de 11 caracteres de um link do YouTube (watch, youtu.be,
   * shorts, live, embed, music.youtube). Retorna null para qualquer outra URL
   * — aí o kernel trata o link como stream direto de rádio.
   */
  function youtubeId(raw) {
    const m = String(raw).match(
      /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|shorts\/|live\/|embed\/)|youtu\.be\/)([\w-]{11})/
    );
    return m ? m[1] : null;
  }

  /** Memória pelo prefixo do id ou do título (o painel Memory · Recent mostra títulos). */
  async function resolveMemory(prefix) {
    const ms = await Api.memories();
    const hit = ms.find((m) =>
      String(m.id).toLowerCase().startsWith(prefix.toLowerCase())
      || String(m.title ?? "").toLowerCase().startsWith(prefix.toLowerCase())
    );
    if (!hit) throw new Error(`nenhuma memória começa com "${prefix}"`);
    return hit.id;
  }

  /** Meta pelo prefixo do título (o painel Projects · Active mostra títulos). */
  async function resolveGoal(prefix) {
    const gs = await Api.goals();
    const hit = gs.find((g) => String(g.title ?? "").toLowerCase().startsWith(prefix.toLowerCase()));
    if (!hit) throw new Error(`nenhuma meta começa com "${prefix}"`);
    return hit.id;
  }

  /** Marcador pelo prefixo do título ou da URL (o painel Browser · Marks mostra ambos). */
  async function resolveMark(prefix) {
    const ms = await Api.browserMarks();
    const hit = (ms.marks ?? []).find((m) =>
      String(m.title ?? "").toLowerCase().startsWith(prefix.toLowerCase())
      || String(m.url ?? "").toLowerCase().startsWith(prefix.toLowerCase())
    );
    if (!hit) throw new Error(`nenhum marcador começa com "${prefix}"`);
    return hit.id;
  }

  /** Aparelho pareado pelo prefixo do nome (o painel Network · Devices mostra nomes). */
  async function resolveDevice(prefix) {
    const ds = await Api.devices();
    const hit = ds.find((d) => String(d.name ?? "").toLowerCase().startsWith(prefix.toLowerCase()));
    if (!hit) throw new Error(`nenhum aparelho começa com "${prefix}"`);
    return hit.id;
  }

  /** Tarefa agendada pelo prefixo do id (o painel Terminal · Jobs mostra 8 chars). */
  async function resolveTask(prefix) {
    const ts = await Api.schedule();
    const hit = ts.find(t => String(t.id).toLowerCase().startsWith(prefix.toLowerCase()));
    if (!hit) throw new Error(`nenhuma tarefa agendada começa com "${prefix}"`);
    return hit.id;
  }

  /**
   * "lembrar <texto> em <n> <min|h|d>" (recorrência opcional "repetir a cada
   * <n> <unidade>") → corpo do POST /schedule. Retorna null se não casar.
   */
  function parseReminder(raw) {
    const m = raw.match(
      /^lembrar\s+(.+?)\s+em\s+(\d+(?:[.,]\d+)?)\s*(min|minutos?|h|horas?|d|dias?)(?:\s+repetir\s+a\s+cada\s+(\d+(?:[.,]\d+)?)\s*(min|minutos?|h|horas?|d|dias?))?\s*$/i
    );
    if (!m) return null;
    const toMinutes = (u) => (u.startsWith("min") ? 1 : u.startsWith("h") ? 60 : 1440);
    const n = parseFloat(m[2].replace(",", "."));
    const unit = m[3].toLowerCase();
    const body = { kind: "reminder", text: m[1].trim() };
    if (unit.startsWith("h")) body.in_hours = n;
    else if (unit.startsWith("d")) body.in_days = n;
    else body.in_minutes = n;
    if (m[4]) {
      const rn = parseFloat(m[4].replace(",", "."));
      body.recurrence_seconds = Math.round(rn * toMinutes(m[5].toLowerCase()) * 60);
    }
    return body;
  }

  function renderPal(q) {
    const query = (q || "").toLowerCase();
    const f = [
      ...dynamicCommands(q || ""),
      ...COMMANDS.filter(c => c.t.toLowerCase().includes(query)),
    ].slice(0, 24);
    palList.innerHTML = "";
    f.forEach((c, i) => {
      const el = document.createElement("div");
      el.className = "pal-item" + (i === 0 ? " sel" : "");
      const a = document.createElement("span"); a.textContent = c.t;
      const b = document.createElement("em");   b.textContent = c.s;
      el.append(a, b);
      el.addEventListener("click", () => { c.go(); closePal(); });
      palList.appendChild(el);
    });
  }
  function openPal() { pal.classList.add("on"); palInput.value = ""; renderPal(); setTimeout(() => palInput.focus(), 60); }
  function closePal() { pal.classList.remove("on"); palInput.blur(); }
  palInput.addEventListener("input", () => renderPal(palInput.value));
  palInput.addEventListener("keydown", e => {
    if (e.key === "Enter") { const f = palList.querySelector(".pal-item"); if (f) f.click(); }
  });
  pal.addEventListener("click", e => { if (e.target === pal) closePal(); });

  /* Falar o comando: o navegador transcreve (pt-BR) e o texto entra na paleta
     e executa sozinho — mesmo caminho do teclado, nada de clique extra. O
     texto que nenhum comando conhece vai para o cortex (o cérebro simbólico)
     decidir. */
  const palMic = document.getElementById("palMic");
  let palRec = null;
  palMic.addEventListener("click", () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast("este navegador não tem reconhecimento de fala — use Chrome"); return; }
    if (palRec) { palRec.cancelled = true; palRec.stop(); palRec = null; palMic.classList.remove("on"); return; }
    const rec = new SR();
    palRec = rec; rec.cancelled = false;
    palMic.classList.add("on");
    rec.lang = "pt-BR"; rec.interimResults = true; rec.continuous = false;
    rec.onresult = (ev) => {
      let interim = "", final = "";
      for (const res of ev.results) {
        if (res.isFinal) final += res[0].transcript;
        else interim += res[0].transcript;
      }
      palInput.value = (final || interim).trim();
      renderPal(palInput.value);
    };
    rec.onend = () => {
      palRec = null; palMic.classList.remove("on");
      if (rec.cancelled) return;
      const txt = palInput.value.trim();
      if (!txt) return;
      const f = palList.querySelector(".pal-item");
      if (f) f.click();   // roda o comando — ou o cortex decide por conta própria
    };
    rec.onerror = (e) => {
      palMic.classList.remove("on"); palRec = null;
      if (e.error !== "aborted") toast(`microfone: ${e.error}`);
    };
    rec.start();
  });

  /* ═══════════════════════════════════════════════════════
     13 — TOAST
     ═══════════════════════════════════════════════════════ */
  const toastEl = document.getElementById("toast");
  const toastText = document.getElementById("toastText");
  let toastTimer = 0;
  function toast(msg) {
    toastText.textContent = msg;
    toastEl.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("on"), 2600);
  }

  /* ═══════════════════════════════════════════════════════
     14 — TELEMETRY
     ═══════════════════════════════════════════════════════ */
  // Smoothed cost of one render pass, written by the loop below and read here.
  // Declared in this section, not with the loop: telemetry ticks once
  // immediately, before the loop's own declarations are reached.
  let frameMs = 0;
  const t0 = Date.now();
  function tickTelemetry() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    document.getElementById("clock").textContent = `${hh}:${mm}`;
    document.getElementById("dateOut").textContent =
      d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short" }).toUpperCase();

    const up = Math.floor((Date.now() - t0) / 1000);
    document.getElementById("uptimeOut").textContent =
      [Math.floor(up / 3600), Math.floor(up / 60) % 60, up % 60]
        .map(v => String(v).padStart(2, "0")).join(":");

    // Core load is the reactor's own render cost against a 60fps budget — a real
    // measurement of this HUD. The kernel exposes no CPU metric yet; when it
    // does, this is the one line that changes.
    document.getElementById("loadOut").textContent =
      frameMs > 0 ? clamp((frameMs / 16.67) * 100, 0, 999).toFixed(1).padStart(4, "0") + " %" : "—";

    // Latency is the measured round-trip to /api/v1/health. No link, no number.
    const lat = Kernel.snapshot.latencyMs;
    document.getElementById("latOut").textContent =
      lat === null ? "— — —" : String(lat).padStart(3, "0") + " MS";

    linkOut.textContent = Kernel.linkLabel();

    const h = d.getHours();
    document.getElementById("greetline").textContent =
      `Good ${h < 12 ? "morning" : h < 18 ? "afternoon" : "evening"}, Matheus`;
  }
  setInterval(tickTelemetry, 1000); tickTelemetry();

  /* ═══════════════════════════════════════════════════════
     15 — LOOP
     ═══════════════════════════════════════════════════════ */
  let last = performance.now();
  function frame(now) {
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now; S.t += dt;
    const frameStart = performance.now();

    const st = STATES[S.name];
    S.glow = approach(S.glow, st.glow, 3.2, dt);
    S.spin = approach(S.spin, st.spin, 2.6, dt);
    S.core = approach(S.core, st.core * (1 + S.proximity * 0.04), 4.0, dt);
    S.tint = S.tint.map((v, i) => approach(v, st.tint[i], 3.0, dt));
    S.open = approach(S.open, S.depth > 0 ? 1 : 0, 5.5, dt);
    if (S.surge > 0) S.surge = Math.max(0, S.surge - dt * 1.1);

    const dCore = Math.hypot(mx - cx, my - cy);
    const prox = clamp(1 - (dCore - R) / (R * 2.6), 0, 1);
    S.proximity = approach(S.proximity, isFinite(prox) ? prox : 0, 6, dt);

    const hit = hitTest();
    S.hoverIdx = hit;
    S.hoverAmt = approach(S.hoverAmt, hit >= 0 ? 1 : 0, 8, dt);
    if (hit >= 0) {
      const target = itemAngle(hit, currentItems().length);
      const diff = ((target - S.wedgeAngle + Math.PI * 3) % TAU) - Math.PI;
      S.wedgeAngle += diff * (1 - Math.exp(-11 * dt));
    }

    const overHot = dCore <= R * G.bezel[1] * 1.05 || hit >= 0;
    cursorScale = approach(cursorScale, overHot ? 1.5 : 1, 9, dt);
    cursorEl.style.transform = `translate(${mx}px, ${my}px) scale(${cursorScale.toFixed(3)})`;

    const amp = S.name === "listening" ? 1 : S.name === "speaking" ? 0.74 : 0;
    bars.forEach((b, i) => {
      const v = amp === 0 ? 3
        : 3 + Math.abs(Math.sin(S.t * 6.5 + i * 0.42) * Math.sin(S.t * 2.1 + i * 0.13)) * 26 * amp;
      b.style.height = v.toFixed(1) + "px";
      b.style.opacity = amp === 0 ? "0.15" : String(0.4 + (v / 29) * 0.6);
    });

    render(dt);
    // Smoothed, so the readout is legible instead of jittering every frame.
    frameMs = frameMs === 0 ? performance.now() - frameStart
                            : frameMs + ((performance.now() - frameStart) - frameMs) * 0.1;
    requestAnimationFrame(frame);
  }

  /* ═══════════════════════════════════════════════════════
     16 — BOOT
     ═══════════════════════════════════════════════════════ */
  const bootEl = document.getElementById("boot");
  const bootFill = document.getElementById("bootFill");
  const bootLog = document.getElementById("bootLog");
  const BOOT_STEPS = [
    "INITIALIZING", "REACTOR ONLINE", "MOUNTING MEMORY", "LINKING AGENTS",
    "CALIBRATING VOICE", "HANDSHAKE OK", "ARC READY",
  ];

  function boot() {
    resize();
    setDepth(0);
    requestAnimationFrame(frame);

    // From here on, the link is one of the two inputs the reactor answers to;
    // the other is live activity. `arbitrate` decides between them.
    Kernel.start(onLinkState);

    if (reduceMotion) { bootEl.classList.add("done"); Brain.start(); return; }
    let i = 0;
    const step = () => {
      bootLog.textContent = BOOT_STEPS[i];
      bootFill.style.width = ((i + 1) / BOOT_STEPS.length * 100) + "%";
      i++;
      if (i < BOOT_STEPS.length) setTimeout(step, 260);
      else setTimeout(() => {
        bootEl.classList.add("done");
        Brain.start();
        setTimeout(() => toast(
          Kernel.snapshot.connected
            ? "Enter fala · V escuta · C vê · Ctrl+K comanda"
            : "Kernel offline — suba o backend em 127.0.0.1:8000"), 900);
      }, 420);
    };
    setTimeout(step, 300);
  }

  boot();
})();
