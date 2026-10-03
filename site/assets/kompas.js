"use strict";
/* ============================================================
   Financieel Vastgoedkompas – gedeelde schil
   Wordt door elke pagina geladen. Alles is defensief: een pagina
   zonder venster, zonder subnavigatie of zonder zoekveld moet het
   net zo goed doen.

   Klassiek script, geen module: vanaf file:// weigert de browser
   zowel ES-modules als fetch() op CORS.
   ============================================================ */

var KOMPAS = window.KOMPAS || {};
window.KOMPAS = KOMPAS;
KOMPAS.basis = KOMPAS.basis || "";

/* ------------------------------------------------------------
   Kleine helpers
   ------------------------------------------------------------ */
function $(sel, root) { return (root || document).querySelector(sel); }
function $$(sel, root) {
  return Array.prototype.slice.call((root || document).querySelectorAll(sel));
}

function esc(str) {
  return String(str == null ? "" : str).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function icon(n, maat, dikte) {
  var s = maat || 16;
  return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="' + (dikte || 1.7) + '" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><use href="#' + n + '"/></svg>';
}

/* Vaste kleur per rolcluster, in de VMV-familie. */
var CLUSTERKLEUR = {
  "RC-01": "#1f6fb2", "RC-02": "#3e9b62", "RC-03": "#12a3a0", "RC-04": "#b0566a",
  "RC-05": "#d98f2f", "RC-06": "#5a6fb8", "RC-07": "#9462a6", "RC-08": "#e2833c",
  "RC-09": "#57b6a4"
};
function clusterKleur(code) { return CLUSTERKLEUR[code] || "var(--vmv-grey-400)"; }

/* Opslag mag nooit de pagina slopen: in een privévenster gooit het. */
function bewaar(sleutel, waarde, sessie) {
  try {
    (sessie ? window.sessionStorage : window.localStorage)
      .setItem(sleutel, JSON.stringify(waarde));
  } catch (e) { /* stilte is hier het juiste gedrag */ }
}
function haal(sleutel, standaard, sessie) {
  try {
    var r = (sessie ? window.sessionStorage : window.localStorage).getItem(sleutel);
    return r ? JSON.parse(r) : standaard;
  } catch (e) { return standaard; }
}

/* ------------------------------------------------------------
   Meldingen
   ------------------------------------------------------------ */
function toast(bericht) {
  var host = $("#toasts");
  if (!host) {
    host = document.createElement("div");
    host.className = "toasts";
    host.id = "toasts";
    host.setAttribute("aria-live", "polite");
    document.body.appendChild(host);
  }
  var t = document.createElement("div");
  t.className = "toast";
  t.innerHTML = icon("i-info", 16) + "<span>" + esc(bericht) + "</span>";
  host.appendChild(t);
  window.setTimeout(function () {
    t.classList.add("toast--leaving");
    window.setTimeout(function () { if (t.parentNode) { t.parentNode.removeChild(t); } }, 220);
  }, 3600);
}

/* ------------------------------------------------------------
   Venster – alleen nog voor echte onderbrekingen, niet voor detail
   ------------------------------------------------------------ */
var modalBackdrop = $("#modal-backdrop");
var laatsteFocus = null;

function openModal(opts) {
  if (!modalBackdrop) { toast(opts.titel || ""); return; }
  laatsteFocus = document.activeElement;
  $("#modal-eyebrow").textContent = opts.eyebrow || "";
  $("#modal-titel").textContent = opts.titel || "";
  $("#modal-body").innerHTML = opts.body || "";
  $("#modal-foot").innerHTML = opts.foot ||
    '<button type="button" class="btn" data-action="close-modal">Sluiten</button>';
  modalBackdrop.hidden = false;
  document.body.style.overflow = "hidden";
  $("#modal-body").scrollTop = 0;
  ($("#modal-body button, #modal-body a, #modal-foot button") || $("#modal")).focus();
}

function closeModal() {
  if (!modalBackdrop) { return; }
  modalBackdrop.hidden = true;
  document.body.style.overflow = "";
  if (laatsteFocus && laatsteFocus.focus) { laatsteFocus.focus(); }
  laatsteFocus = null;
}

if (modalBackdrop) {
  modalBackdrop.addEventListener("mousedown", function (e) {
    if (e.target === modalBackdrop) { closeModal(); }
  });
}

document.addEventListener("keydown", function (e) {
  var paneel = $("#reflectiepaneel");
  if (e.key === "Escape") {
    if (modalBackdrop && !modalBackdrop.hidden) { closeModal(); return; }
    if (paneel && !paneel.hidden) { sluitPaneel(); }
    return;
  }
  if (e.key !== "Tab" || !modalBackdrop || modalBackdrop.hidden) { return; }
  var focusbaar = $$('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])', $("#modal"))
    .filter(function (el) { return el.offsetParent !== null; });
  if (!focusbaar.length) { return; }
  var eerste = focusbaar[0], laatste = focusbaar[focusbaar.length - 1];
  if (e.shiftKey && document.activeElement === eerste) { e.preventDefault(); laatste.focus(); }
  else if (!e.shiftKey && document.activeElement === laatste) { e.preventDefault(); eerste.focus(); }
});

/* ------------------------------------------------------------
   Reflectiepaneel
   ------------------------------------------------------------ */
function openPaneel() {
  var p = $("#reflectiepaneel");
  if (!p) { return; }
  p.hidden = false;
  $$('[data-action="open-reflection"]').forEach(function (b) {
    b.setAttribute("aria-expanded", "true");
  });
  var eerste = $("#reflectie-velden textarea");
  if (eerste) { eerste.focus(); }
}
function sluitPaneel() {
  var p = $("#reflectiepaneel");
  if (!p) { return; }
  p.hidden = true;
  $$('[data-action="open-reflection"]').forEach(function (b) {
    b.setAttribute("aria-expanded", "false");
  });
}

/* ------------------------------------------------------------
   Context: waar kwam de bezoeker vandaan?

   Dit is wat een pagina teruggeeft wat een modal gratis had — de
   gefilterde lijst stond daar immers achter. De index schrijft zijn
   filters weg, de detailpagina leest ze, toont de strip en markeert
   de chips die bij die situatie passen.
   ------------------------------------------------------------ */
var CTX_SLEUTEL = "kompas.context";

function zetContext(ctx) { bewaar(CTX_SLEUTEL, ctx, true); }
function leesContext() { return haal(CTX_SLEUTEL, null, true); }
function wisContext() {
  try { window.sessionStorage.removeItem(CTX_SLEUTEL); } catch (e) { /* niets */ }
}

function toonContextstrip() {
  var strip = $("#contextstrip");
  if (!strip) { return; }
  var ctx = leesContext();
  if (!ctx || !ctx.labels || !ctx.labels.length) { strip.hidden = true; return; }

  $("#contextstrip-labels").innerHTML = ctx.labels.map(function (l) {
    return '<span class="chip chip--teal">' + esc(l) + "</span>";
  }).join("");
  var terug = $("#contextstrip-terug");
  if (terug) {
    terug.href = KOMPAS.basis + "instrumenten.html" + (ctx.zoek || "");
  }
  strip.hidden = false;
  markeerContextchips(ctx);
}

/* Elke chip draagt data-ctx="groep:code". Past die bij de context,
   dan wordt het "past bij jou" in plaats van een feit op een rij. */
function markeerContextchips(ctx) {
  if (!ctx || !ctx.codes) { return; }
  var geraakt = 0;
  $$("[data-ctx]").forEach(function (el) {
    var paar = String(el.dataset.ctx).split(":");
    var lijst = ctx.codes[paar[0]];
    if (!lijst || lijst.indexOf(paar[1]) === -1) { return; }
    el.classList.add("mchip--context");
    el.classList.remove("mchip--primair");
    if (!$(".mchip__vink", el)) {
      el.insertAdjacentHTML("afterbegin",
        '<span class="mchip__vink">' + icon("i-check", 13, 2.4) + "</span>");
      el.insertAdjacentHTML("beforeend",
        '<span class="visually-hidden"> – past bij jouw situatie</span>');
    }
    geraakt += 1;
  });
  var noot = $("#contextnoot");
  if (noot) {
    noot.hidden = geraakt === 0;
    if (geraakt) {
      noot.textContent = geraakt === 1
        ? "Eén kenmerk hieronder is paars: dat past bij de situatie waarmee je zocht."
        : geraakt + " kenmerken hieronder zijn paars: die passen bij de situatie waarmee je zocht.";
    }
  }
}

/* ------------------------------------------------------------
   Mijn selectie – een plankje dat tussen pagina's blijft staan
   ------------------------------------------------------------ */
var SEL_SLEUTEL = "kompas.selectie";

function selectie() { return haal(SEL_SLEUTEL, [], false) || []; }

function wisselSelectie(code, naam) {
  var lijst = selectie();
  var i = lijst.indexOf(code);
  if (i === -1) {
    lijst.push(code);
    toast((naam || code) + " staat in je selectie.");
  } else {
    lijst.splice(i, 1);
    toast((naam || code) + " is uit je selectie gehaald.");
  }
  bewaar(SEL_SLEUTEL, lijst, false);
  verversSelectie();
}

function verversSelectie() {
  var lijst = selectie();
  var telling = $("#selectie-telling");
  if (telling) {
    telling.textContent = lijst.length ? String(lijst.length) : "";
    telling.setAttribute("data-leeg", lijst.length ? "nee" : "ja");
  }
  $$("[data-selectie]").forEach(function (b) {
    var aan = lijst.indexOf(b.dataset.selectie) !== -1;
    b.setAttribute("aria-pressed", aan ? "true" : "false");
    var label = $(".selectie-label", b);
    if (label) { label.textContent = aan ? "In je selectie" : "Zet in mijn selectie"; }
  });
}

/* ------------------------------------------------------------
   Ankernavigatie binnen een lange detailpagina
   ------------------------------------------------------------ */
function startSubnav() {
  var nav = $("#subnav");
  if (!nav || !window.IntersectionObserver) { return; }
  var links = $$(".subnav__link", nav);
  var doelen = links.map(function (l) {
    return document.getElementById(l.getAttribute("href").replace(/^.*#/, ""));
  });
  if (!doelen.filter(Boolean).length) { return; }

  var zichtbaar = {};
  var waarnemer = new IntersectionObserver(function (items) {
    items.forEach(function (it) { zichtbaar[it.target.id] = it.isIntersecting; });
    var actief = -1;
    doelen.forEach(function (d, i) {
      if (d && zichtbaar[d.id] && actief === -1) { actief = i; }
    });
    links.forEach(function (l, i) { l.classList.toggle("is-actief", i === actief); });
  }, { rootMargin: "-130px 0px -55% 0px" });

  doelen.forEach(function (d) { if (d) { waarnemer.observe(d); } });
}

/* ------------------------------------------------------------
   Zoeken in de bovenbalk: gaat naar de index met die zoekterm
   ------------------------------------------------------------ */
function startZoek() {
  var veld = $("#topzoek");
  if (!veld) { return; }
  var ga = function () {
    var t = veld.value.trim();
    window.location.href = KOMPAS.basis + "instrumenten.html" +
      (t ? "?zoek=" + encodeURIComponent(t) : "");
  };
  veld.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); ga(); }
  });
  var knop = $("#topzoek-knop");
  if (knop) { knop.addEventListener("click", ga); }
}

/* ------------------------------------------------------------
   Eén klikafhandelaar voor de hele schil
   ------------------------------------------------------------ */
document.addEventListener("click", function (e) {
  var sel = e.target.closest("[data-selectie]");
  if (sel) {
    e.preventDefault();
    wisselSelectie(sel.dataset.selectie, sel.dataset.selectienaam);
    return;
  }
  var melding = e.target.closest("[data-melding]");
  if (melding) { e.preventDefault(); toast(melding.dataset.melding); return; }

  var el = e.target.closest("[data-action]");
  if (!el) { return; }
  var a = el.dataset.action;
  if (a === "close-modal") { closeModal(); }
  else if (a === "open-reflection") { openPaneel(); }
  else if (a === "close-reflection") { sluitPaneel(); }
  else if (a === "print") { e.preventDefault(); window.print(); }
  else if (a === "wis-context") { wisContext(); var s = $("#contextstrip"); if (s) { s.hidden = true; } }
});

/* ------------------------------------------------------------
   Start
   ------------------------------------------------------------ */
toonContextstrip();
verversSelectie();
startSubnav();
startZoek();

/* ------------------------------------------------------------
   Reflectiepaneel – aantekeningen voor de werksessie
   ------------------------------------------------------------ */
var REFLECTIEVRAGEN = [
  "Waar zou jij op deze site beginnen?",
  "Welke informatie verwacht je als eerste te zien?",
  "Wat helpt je om een financiële keuze te maken?",
  "Wat voelt onnodig of te complex?",
  "Welke rol of welk perspectief ontbreekt?",
  "Wat wil je meenemen naar een volgende versie?"
];
var REFL_SLEUTEL = "kompas.reflecties";

function reflectieStatus(tekst) {
  var s = $("#reflectie-status");
  if (s) { s.textContent = tekst; }
}

function renderReflecties() {
  var host = $("#reflectie-velden");
  if (!host) { return; }
  var data = haal(REFL_SLEUTEL, {}, false) || {};
  host.innerHTML = REFLECTIEVRAGEN.map(function (v, i) {
    return '<div><label class="reflectielabel" for="refl-' + i + '">' +
      (i + 1) + ". " + esc(v) + "</label>" +
      '<textarea id="refl-' + i + '" data-refl="' + i + '" placeholder="Jouw notitie…">' +
      esc(data["v" + i] || "") + "</textarea></div>";
  }).join("");
  $$("textarea", host).forEach(function (ta) {
    ta.addEventListener("input", function () {
      var d = haal(REFL_SLEUTEL, {}, false) || {};
      d["v" + ta.dataset.refl] = ta.value;
      bewaar(REFL_SLEUTEL, d, false);
      reflectieStatus("Automatisch bewaard in deze browser.");
    });
  });
}

function reflectieTekst() {
  var data = haal(REFL_SLEUTEL, {}, false) || {};
  var regels = ["Reflectie op het Financieel Vastgoedkompas (conceptprototype)", ""];
  REFLECTIEVRAGEN.forEach(function (v, i) {
    regels.push((i + 1) + ". " + v);
    regels.push((data["v" + i] || "").trim() || "—");
    regels.push("");
  });
  return regels.join("\n");
}

function kopieerFallback(tekst) {
  var ta = document.createElement("textarea");
  ta.value = tekst;
  ta.setAttribute("readonly", "readonly");
  ta.style.position = "fixed"; ta.style.top = "50%"; ta.style.left = "50%";
  ta.style.width = "1px"; ta.style.height = "1px";
  document.body.appendChild(ta);
  ta.select();
  ta.setSelectionRange(0, tekst.length);
  reflectieStatus("Kopiëren via het klembord is hier niet beschikbaar. De tekst is geselecteerd: gebruik Ctrl+C of Cmd+C.");
  toast("Klembord niet beschikbaar. De tekst is geselecteerd, kopieer met Ctrl+C of Cmd+C.");
  window.setTimeout(function () { if (ta.parentNode) { ta.parentNode.removeChild(ta); } }, 6000);
}

document.addEventListener("click", function (e) {
  if (e.target.closest('[data-action="reflectie-kopieer"]')) {
    var tekst = reflectieTekst();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(tekst).then(function () {
        reflectieStatus("Reflecties gekopieerd naar het klembord.");
        toast("Reflecties gekopieerd naar het klembord.");
      }).catch(function () { kopieerFallback(tekst); });
    } else { kopieerFallback(tekst); }
  }
  if (e.target.closest('[data-action="reflectie-wis"]')) {
    REFLECTIEVRAGEN.forEach(function (v, i) {
      var ta = document.getElementById("refl-" + i);
      if (ta) { ta.value = ""; }
    });
    bewaar(REFL_SLEUTEL, {}, false);
    reflectieStatus("Alle reflecties zijn gewist.");
    toast("Alle reflecties zijn gewist.");
  }
});

/* ------------------------------------------------------------
   Mijn selectie in een venster
   ------------------------------------------------------------ */
function toonSelectie() {
  var lijst = selectie();
  if (!lijst.length) {
    openModal({
      eyebrow: "Mijn selectie",
      titel: "Je selectie is nog leeg",
      body: '<p class="small">Zet instrumenten in je selectie met de knop <strong>Zet in mijn selectie</strong> ' +
        "op een instrumentpagina of in de bibliotheek. Je selectie blijft in deze browser bewaard, " +
        "ook als je de site sluit.</p>" +
        '<p class="small"><a href="' + KOMPAS.basis + 'instrumenten.html">Naar de instrumentenbibliotheek</a></p>'
    });
    return;
  }
  var namen = (window.KOMPAS_NAMEN || {});
  openModal({
    eyebrow: "Mijn selectie",
    titel: lijst.length + (lijst.length === 1 ? " instrument" : " instrumenten"),
    body: '<ul class="linklist">' + lijst.map(function (c) {
      return '<li><a class="linklist__btn" href="' + KOMPAS.basis + "instrument/" + encodeURIComponent(c) + '.html">' +
        esc(namen[c] || c) +
        '<span class="linklist__meta">' + esc(c) + "</span>" +
        '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></a></li>";
    }).join("") + "</ul>",
    foot: '<button type="button" class="btn" data-action="close-modal">Sluiten</button>' +
      '<button type="button" class="btn btn--ghost" data-action="selectie-wis">' +
      icon("i-trash", 15, 1.8) + " Selectie wissen</button>"
  });
}

document.addEventListener("click", function (e) {
  if (e.target.closest('[data-action="open-selectie"]')) { toonSelectie(); }
  if (e.target.closest('[data-action="selectie-wis"]')) {
    bewaar(SEL_SLEUTEL, [], false);
    verversSelectie();
    closeModal();
    toast("Je selectie is gewist.");
  }
});

renderReflecties();
