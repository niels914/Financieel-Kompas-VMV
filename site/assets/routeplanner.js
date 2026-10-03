/* ============================================================
   Archetype C2 – Routeplanner door rollen
   ============================================================ */
var C2 = { gutter: 192, x0: 196, kolom: 97, kopHoog: 100, rij0: 130, rijStap: 43, onder: 520 };
var c2Cluster = null;   // gekozen rolcluster
var c2Moment = null;    // gekozen beslismoment

function c2KolomX(i) { return C2.x0 + i * C2.kolom; }
function c2Midden(i) { return C2.x0 + i * C2.kolom + C2.kolom / 2; }
function c2RijY(i) { return C2.rij0 + i * C2.rijStap; }

var c2Fasen = [], c2Clusters = [], c2Actief = {}, c2Betrokken = {};

function c2Bouw() {
  /* Fasen in modelvolgorde, eerst portefeuille dan object. */
  c2Fasen = sorteer(tab("procesniveau")).reduce(function (acc, n) {
    sorteer(tab("procesfase")).filter(function (f) { return f.procesniveau_id === n.code; })
      .forEach(function (f) { acc.push(f); });
    return acc;
  }, []);
  c2Clusters = sorteer(tab("rolcluster"));

  /* Welke clusters zitten bij welk beslismoment aan tafel, en in welke fase
     is een cluster daarmee actief? */
  tab("beslismoment_rol").forEach(function (br) {
    var r = rec("rol", br.rol_id);
    var b = rec("beslismoment", br.beslismoment_id);
    if (!r || !b || !r.rolcluster_id) { return; }
    (c2Betrokken[b.beslismoment_code] = c2Betrokken[b.beslismoment_code] || {});
    (c2Betrokken[b.beslismoment_code][r.rolcluster_id] =
      c2Betrokken[b.beslismoment_code][r.rolcluster_id] || []).push(br);
    (c2Actief[r.rolcluster_id] = c2Actief[r.rolcluster_id] || {})[b.procesfase_id] = true;
  });
}

function c2ClusterRij(code) {
  for (var i = 0; i < c2Clusters.length; i++) { if (c2Clusters[i].code === code) { return i; } }
  return -1;
}
function c2FaseKolom(code) {
  for (var i = 0; i < c2Fasen.length; i++) { if (c2Fasen[i].fase_code === code) { return i; } }
  return -1;
}

function c2Wrap(tekst, max) {
  /* Lange samenstellingen als "investeringsbesluit" passen in geen enkele
     kolom; die breken we af met een koppelteken. */
  var woorden = [];
  String(tekst).split(/\s+/).forEach(function (w) {
    /* Bij 12 tekens valt de breuk bij deze Nederlandse samenstellingen
       precies op de voeg: portefeuille-strategie, investerings-besluit. */
    while (w.length > max) {
      var knip = Math.min(12, max - 1);
      woorden.push(w.slice(0, knip) + "-");
      w = w.slice(knip);
    }
    woorden.push(w);
  });
  var regels = [], nu = "";
  woorden.forEach(function (w) {
    if (!nu.length) { nu = w; }
    else if (nu.slice(-1) === "-") { regels.push(nu); nu = w; }
    else if ((nu + " " + w).length <= max) { nu += " " + w; }
    else { regels.push(nu); nu = w; }
  });
  if (nu.length) { regels.push(nu); }
  return regels.slice(0, 3);
}

function renderC2Kaart() {
  var breed = C2.x0 + c2Fasen.length * C2.kolom + 12;

  /* Niveaubanden boven de kolommen: portefeuille en object zijn twee
     losse processen, ook al staan ze hier op één rij. */
  var banden = "";
  var niveaus = sorteer(tab("procesniveau")).filter(function (n) {
    return c2Fasen.some(function (f) { return f.procesniveau_id === n.code; });
  });
  niveaus.forEach(function (n) {
    var idx = c2Fasen.map(function (f, i) { return f.procesniveau_id === n.code ? i : -1; })
      .filter(function (i) { return i >= 0; });
    if (!idx.length) { return; }
    var van = c2KolomX(Math.min.apply(null, idx)) + 3;
    var tot = c2KolomX(Math.max.apply(null, idx)) + C2.kolom - 3;
    var kleur = n.code === "PORT" ? "var(--vmv-teal-dark)" : "var(--c2-violet)";
    banden += '<rect class="c2-niveaubalk" x="' + van + '" y="10" width="' + (tot - van) + '" height="24" fill="' + kleur + '"/>' +
      '<text class="c2-niveaukop" x="' + ((van + tot) / 2) + '" y="27">' + esc(n.naam.toUpperCase()) + "</text>";
  });

  var kolommen = c2Fasen.map(function (f, i) {
    var regels = c2Wrap(f.naam, 15).map(function (t, j) {
      return '<text class="c2-fasekop" x="' + c2Midden(i) + '" y="' + (76 + j * 11) + '">' + esc(t) + "</text>";
    }).join("");
    return '<g class="c2-vakgroep" data-fase="' + f.fase_code + '" role="button" tabindex="0" ' +
      'aria-label="Fase ' + esc(f.fase_code) + ": " + esc(f.naam) + '">' +
      '<rect class="c2-vak' + (i % 2 ? " c2-vak--om" : "") + '" x="' + c2KolomX(i) + '" y="' + C2.kopHoog +
      '" width="' + C2.kolom + '" height="' + (C2.onder - C2.kopHoog) + '"/>' +
      '<text class="c2-fasecode" x="' + c2Midden(i) + '" y="56">' + esc(f.fase_code) + "</text>" +
      regels + "</g>";
  }).join("");

  var namen = c2Clusters.map(function (c, i) {
    var n = Object.keys(c2Actief[c.code] || {}).length;
    return '<text class="c2-clusternaam" x="' + (C2.gutter - 14) + '" y="' + (c2RijY(i) + 1) + '" text-anchor="end">' +
      esc(c.naam) + "</text>" +
      '<text class="c2-clustertelling" x="' + (C2.gutter - 14) + '" y="' + (c2RijY(i) + 14) + '" text-anchor="end">' +
      n + " van " + c2Fasen.length + " fasen</text>";
  }).join("");

  var lijnen = c2Clusters.map(function (c, ri) {
    var kolomIdx = c2Fasen.map(function (f, i) {
      return (c2Actief[c.code] || {})[f.fase_code] ? i : -1;
    }).filter(function (i) { return i >= 0; });
    if (!kolomIdx.length) { return ""; }
    var y = c2RijY(ri), kleur = clusterKleur(c.code);
    var gedimd = c2Cluster && c2Cluster !== c.code;
    var x1 = c2Midden(Math.min.apply(null, kolomIdx));
    var x2 = c2Midden(Math.max.apply(null, kolomIdx));
    var stations = kolomIdx.map(function (i) {
      return '<g class="c2-halte" data-cluster="' + c.code + '" data-fase="' + c2Fasen[i].fase_code + '" ' +
        'role="button" tabindex="' + (gedimd ? "-1" : "0") + '" aria-label="' + esc(c.naam) + " in fase " +
        esc(c2Fasen[i].naam) + '">' +
        '<circle class="c2-halte__punt" cx="' + c2Midden(i) + '" cy="' + y + '" r="6.5" stroke="' + kleur + '"/></g>';
    }).join("");
    return '<g class="c2-lijngroep' + (gedimd ? " is-dimmed" : "") + '" data-rol="' + c.code + '">' +
      '<path class="c2-lijn" d="M' + x1 + " " + y + " L" + x2 + " " + y + '" stroke="' + kleur + '" stroke-width="4.5"/>' +
      stations + "</g>";
  }).join("");

  var ruiten = c2Fasen.map(function (f, fi) {
    var lijst = tab("beslismoment").filter(function (b) { return b.procesfase_id === f.fase_code; });
    var offsets = lijst.length === 1 ? [0] : (lijst.length === 2 ? [-24, 24] : [-30, 0, 30]);
    return lijst.map(function (b, k) {
      var clusters = Object.keys(c2Betrokken[b.beslismoment_code] || {});
      var rijen = clusters.map(c2ClusterRij).filter(function (n) { return n >= 0; });
      if (!rijen.length) { return ""; }
      var x = c2Midden(fi) + (offsets[k] || 0);
      var yTop = c2RijY(Math.min.apply(null, rijen));
      var yBot = c2RijY(Math.max.apply(null, rijen));
      var yMid = (yTop + yBot) / 2;
      var r = b.formaliteitsniveau === "bestuurlijk" ? 12 : (b.formaliteitsniveau === "formeel" ? 11 : 9);
      var stippen = rijen.map(function (n) {
        return '<circle class="c2-knoopstip" cx="' + x + '" cy="' + c2RijY(n) + '" r="3.2"/>';
      }).join("");
      return '<g class="c2-knoopgroep' + (c2Moment === b.beslismoment_code ? " is-selected" : "") +
        '" data-moment="' + b.beslismoment_code + '" role="button" tabindex="0" ' +
        'aria-label="Beslismoment ' + esc(b.naam) + ", fase " + esc(f.naam) + '">' +
        '<path class="c2-koppellijn" d="M' + x + " " + yTop + " L" + x + " " + yBot + '"/>' + stippen +
        '<path class="c2-ruit" d="M' + x + " " + (yMid - r) + " L" + (x + r) + " " + yMid +
        " L" + x + " " + (yMid + r) + " L" + (x - r) + " " + yMid + ' Z"/></g>';
    }).join("");
  }).join("");

  $("#c2-map").innerHTML =
    '<svg viewBox="0 0 ' + breed + ' 560" role="img" aria-label="Rasterkaart met negen rolclusters door twaalf procesfasen, met zestien beslismomenten als ruiten">' +
    banden + kolommen + namen + lijnen + ruiten + "</svg>";

  $$("#c2-map .c2-vakgroep").forEach(function (g) {
    var klik = function () { kiesC2Fase(g.dataset.fase); };
    g.addEventListener("click", klik);
    g.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") { e.preventDefault(); klik(); }
    });
  });
  $$("#c2-map .c2-halte").forEach(function (g) {
    g.addEventListener("click", function (e) { e.stopPropagation(); kiesC2Cluster(g.dataset.cluster); });
    g.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
        e.preventDefault(); e.stopPropagation(); kiesC2Cluster(g.dataset.cluster);
      }
    });
  });
  $$("#c2-map .c2-knoopgroep").forEach(function (g) {
    var klik = function () { kiesC2Moment(g.dataset.moment); };
    g.addEventListener("click", klik);
    g.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") { e.preventDefault(); klik(); }
    });
  });

  $("#c2-status").textContent = c2Cluster
    ? "Lijn: " + naam("rolcluster", c2Cluster)
    : "Alle negen clusters zichtbaar";
}

function renderC2Clusters() {
  $("#c2-clusters").innerHTML = c2Clusters.map(function (c) {
    var rollen = tab("rol").filter(function (r) { return r.rolcluster_id === c.code; });
    var prim = rollen.filter(function (r) { return r.primaire_gebruiker_v1 === "ja"; }).length;
    return '<button type="button" class="c2-rol" data-cluster="' + c.code + '" style="--rol:' + clusterKleur(c.code) +
      '" aria-pressed="' + (c2Cluster === c.code) + '">' +
      '<span class="c2-rol__dot" aria-hidden="true"></span>' +
      '<span><span class="c2-rol__naam">' + esc(c.naam) + "</span>" +
      '<span class="c2-rol__vraag">' + rollen.length + " rollen" +
      (prim ? " · " + prim + " in versie 1" : "") + "</span></span></button>";
  }).join("");
  $$("#c2-clusters .c2-rol").forEach(function (b) {
    b.addEventListener("click", function () { kiesC2Cluster(b.dataset.cluster); });
  });
}

function renderC2Momenten() {
  $("#c2-momentenlijst").innerHTML = tab("beslismoment").map(function (b) {
    var n = Object.keys(c2Betrokken[b.beslismoment_code] || {}).length;
    return '<li><button type="button" class="linklist__btn" data-moment="' + b.beslismoment_code + '">' +
      esc(b.naam) +
      '<span class="linklist__meta">' + esc(b.fase_code || b.procesfase_id) + " · " + esc(naam("procesfase", b.procesfase_id)) +
      " · " + esc(b.formaliteitsniveau || "") + " · " + n + " clusters</span>" +
      '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></button></li>";
  }).join("");
  $$("#c2-momentenlijst [data-moment]").forEach(function (b) {
    b.addEventListener("click", function () { kiesC2Moment(b.dataset.moment); });
  });
}

function c2Markeer() {
  $$("#c2-clusters .c2-rol").forEach(function (b) {
    b.setAttribute("aria-pressed", b.dataset.cluster === c2Cluster ? "true" : "false");
  });
}

/* De keuze in de URL zetten maakt hem deelbaar, zonder de terugknop vol te
   gooien met elke klik op de kaart. */
function c2Adres() {
  var h = c2Moment || c2Cluster || "";
  window.history.replaceState(null, "", h ? "#" + h : window.location.pathname);
}
function kiesC2Cluster(code) {
  c2Cluster = (c2Cluster === code) ? null : code;
  c2Moment = null;
  renderC2Kaart();
  c2Markeer();
  renderC2Detail();
  c2Adres();
}
function kiesC2Moment(code) {
  c2Moment = (c2Moment === code) ? null : code;
  renderC2Kaart();
  renderC2Detail();
  c2Adres();
}
function kiesC2Fase(code) {
  var lijst = tab("beslismoment").filter(function (b) { return b.procesfase_id === code; });
  if (lijst.length) { kiesC2Moment(lijst[0].beslismoment_code); }
  else { toast("In fase " + naam("procesfase", code) + " staat geen beslismoment in het model."); }
}

function renderC2Detail() {
  var host = $("#c2-detail");

  if (c2Moment) { host.innerHTML = c2MomentBlad(rec("beslismoment", c2Moment)); }
  else if (c2Cluster) { host.innerHTML = c2ClusterBlad(rec("rolcluster", c2Cluster)); }
  else {
    host.innerHTML = '<p class="small muted">Nog niets gekozen. Klik links op een rolcluster, in de kaart op een lijn, een fasekolom of een ruit.</p>' +
      '<hr class="divider"><span class="label">Het model in cijfers</span><ul class="small" style="margin:0">' +
      "<li>" + tab("rol").length + " rollen in " + tab("rolcluster").length + " clusters</li>" +
      "<li>" + tab("procesfase").length + " procesfasen op " + tab("procesniveau").length + " niveaus</li>" +
      "<li>" + tab("beslismoment").length + " beslismomenten</li>" +
      "<li>" + tab("beslismoment_rol").length + " rolbetrokkenheden</li>" +
      "<li>" + tab("informatieoverdracht").length + " informatieoverdrachten</li></ul>";
    return;
  }

  $$("#c2-detail [data-moment]").forEach(function (b) {
    b.addEventListener("click", function () { kiesC2Moment(b.dataset.moment); });
  });
  $$("#c2-detail [data-cluster]").forEach(function (b) {
    b.addEventListener("click", function () { kiesC2Cluster(b.dataset.cluster); });
  });
}

function c2ClusterBlad(c) {
  var rollen = tab("rol").filter(function (r) { return r.rolcluster_id === c.code; });
  var momenten = tab("beslismoment").filter(function (b) {
    return (c2Betrokken[b.beslismoment_code] || {})[c.code];
  });
  /* Instrumenten die voor rollen uit dit cluster hoog scoren. */
  var score = {};
  rollen.forEach(function (r) {
    bij("instrument_rol", "rol_id", r.rol_code).forEach(function (ir) {
      score[ir.instrument_id] = (score[ir.instrument_id] || 0) + (ir.relevantie === "hoog" ? 2 : 1);
    });
  });
  var top = Object.keys(score).sort(function (a, b) { return score[b] - score[a]; }).slice(0, 6);

  return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">' +
    '<span class="c2-rol__dot" style="background:' + clusterKleur(c.code) + '" aria-hidden="true"></span>' +
    '<h3 style="font-size:1.02rem">' + esc(c.naam) + "</h3></div>" +
    '<p class="small muted">' + rollen.length + " rollen, actief in " +
    Object.keys(c2Actief[c.code] || {}).length + " van de " + c2Fasen.length + " fasen.</p>" +
    '<hr class="divider">' +
    '<span class="label">Rollen in dit cluster</span><div style="margin-bottom:14px">' +
    rollen.map(function (r) {
      return '<div class="rolregel"><span class="rolregel__spoor" style="background:' + clusterKleur(c.code) + '"></span>' +
        "<span><strong>" + esc(r.naam) + "</strong>" +
        (r.primaire_gebruiker_v1 === "ja" ? ' <span class="chip chip--teal">versie 1</span>' : "") +
        (r.externe_rol === "ja" ? ' <span class="chip">extern</span>' : "") +
        '<span class="d-waarom">' + esc(r.primaire_verantwoordelijkheid || "") + "</span>" +
        (r.informatie_detailniveau ? '<span class="d-waarom">informatieniveau: ' + esc(r.informatie_detailniveau) + "</span>" : "") +
        "</span></div>";
    }).join("") + "</div>" +
    '<span class="label">Aan tafel bij</span>' +
    (momenten.length ? '<ul class="linklist" style="margin-bottom:14px">' + momenten.map(function (b) {
      var typen = (c2Betrokken[b.beslismoment_code][c.code] || [])
        .map(function (br) { return br.betrokkenheidstype; })
        .filter(function (v, i, a) { return v && a.indexOf(v) === i; });
      return '<li><button type="button" class="linklist__btn" data-moment="' + b.beslismoment_code + '">' + esc(b.naam) +
        '<span class="linklist__meta">' + esc(b.procesfase_id) + " · " + esc(typen.join(", ") || "betrokken") + "</span>" +
        '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></button></li>";
    }).join("") + "</ul>" : '<p class="small muted" style="margin-bottom:14px">Dit cluster staat bij geen enkel beslismoment in het model.</p>') +
    '<span class="label">Instrumenten voor dit cluster</span>' +
    (top.length ? '<ul class="linklist">' + top.map(function (code) {
      return '<li><a class="linklist__btn" href="' + instrumentUrl(code) + '">' +
        esc(naam("instrument", code)) +
        '<span class="linklist__meta">' + esc(naam("instrumenttype", (rec("instrument", code) || {}).primaire_instrumenttype_id)) + "</span>" +
        '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></a></li>";
    }).join("") + "</ul>" : '<p class="small muted">Geen instrumenten gekoppeld.</p>');
}

function c2MomentBlad(b) {
  if (!b) { return '<p class="small muted">Beslismoment niet gevonden.</p>'; }
  var code = b.beslismoment_code;
  var rollen = bij("beslismoment_rol", "beslismoment_id", code);
  var info = bij("beslismoment_informatiebehoefte", "beslismoment_id", code);
  var vragen = bij("beslismoment_financiele_vraag", "beslismoment_id", code);
  var producten = bij("beslismoment_beslisproduct", "beslismoment_id", code);
  var hps = bij("beslismoment_handelingsperspectief", "beslismoment_id", code);
  var knels = bij("beslismoment_knelpunt", "beslismoment_id", code);
  var instrs = bij("instrument_beslismoment", "beslismoment_id", code);
  var overdrachten = bij("informatieoverdracht", "beslismoment_id", code);

  function rolRegel(br) {
    var r = rec("rol", br.rol_id);
    return '<div class="rolregel"><span class="rolregel__spoor" style="background:' + rolKleur(br.rol_id) + '"></span>' +
      "<span><strong>" + esc(r ? r.naam : br.rol_id) + "</strong>" +
      '<span class="d-waarom">' + esc(br.betrokkenheidstype || "betrokken") + "</span></span></div>";
  }

  return '<div class="chip-row" style="margin-bottom:10px">' +
    '<span class="chip chip--purple">' + esc(code) + "</span>" +
    '<span class="chip chip--teal">' + esc(b.procesfase_id) + " · " + esc(naam("procesfase", b.procesfase_id)) + "</span>" +
    (b.formaliteitsniveau ? '<span class="chip">' + esc(b.formaliteitsniveau) + "</span>" : "") + "</div>" +
    '<h3 style="font-size:1.02rem;margin-bottom:8px">' + esc(b.naam) + "</h3>" +
    '<span class="c2-panel__vraag" style="--rol:var(--c2-violet)">' + esc(b.centrale_vraag || "") + "</span>" +
    '<a class="btn btn--block btn--primary" style="margin-top:12px" href="' + momentUrl(code) + '">' +
    "Hele pagina over dit beslismoment " + icon("i-arrow-right", 15, 1.9) + "</a>" +
    '<hr class="divider">' +
    '<dl class="deflist" style="margin-bottom:14px">' +
    (b.besluittype_id ? "<div><dt>Besluittype</dt><dd>" + esc(naam("besluittype", b.besluittype_id)) + "</dd></div>" : "") +
    (b.verwacht_besluit ? "<div><dt>Verwacht besluit</dt><dd>" + esc(b.verwacht_besluit) + "</dd></div>" : "") +
    (b.benodigde_input_samenvatting ? "<div><dt>Input</dt><dd>" + esc(b.benodigde_input_samenvatting) + "</dd></div>" : "") +
    (b.verwachte_output ? "<div><dt>Output</dt><dd>" + esc(b.verwachte_output) + "</dd></div>" : "") +
    (b.volgende_stap ? "<div><dt>Volgende stap</dt><dd>" + esc(b.volgende_stap) + "</dd></div>" : "") +
    "</dl>" +
    '<span class="label">Wie zit hier aan tafel (' + rollen.length + ")</span>" +
    '<div style="margin-bottom:14px">' + rollen.map(rolRegel).join("") + "</div>" +
    (overdrachten.length ? '<span class="label">Informatieoverdracht</span><div style="margin-bottom:14px">' +
      overdrachten.map(function (o) {
        return '<div class="overdracht"><span><strong>' + esc(naam("rol", o.van_rol_id)) + "</strong></span>" +
          '<span class="overdracht__pijl">' + icon("i-arrow-right", 15, 2) + "</span>" +
          "<span><strong>" + esc(naam("rol", o.naar_rol_id)) + "</strong></span>" +
          '<span class="overdracht__risico">' + esc(naam("beslisproduct", o.beslisproduct_id)) +
          (o.vereist_formaat ? " · " + esc(o.vereist_formaat) : "") +
          (o.overdrachtsrisico ? " · risico: " + esc(o.overdrachtsrisico) : "") + "</span></div>";
      }).join("") + "</div>" : "") +
    (vragen.length ? '<span class="label">Financiële vragen</span><ul class="small" style="margin:0 0 14px">' +
      vragen.map(function (v) {
        var fv = rec("financiele_vraag", v.financiele_vraag_id);
        return '<li><a href="' + vraagUrl(v.financiele_vraag_id) + '">' +
          esc(fv ? fv.vraagtekst : v.financiele_vraag_id) + "</a>" +
          (v.prioriteit ? ' <span class="chip chip--demo">' + esc(v.prioriteit) + "</span>" : "") + "</li>";
      }).join("") + "</ul>" : "") +
    (info.length ? '<span class="label">Benodigde informatie</span><ul class="small" style="margin:0 0 14px">' +
      info.map(function (x) {
        var ib = rec("informatiebehoefte", x.informatiebehoefte_id);
        return "<li>" + esc(ib ? ib.naam : x.informatiebehoefte_id) +
          (x.prioriteit ? ' <span class="chip chip--demo">' + esc(x.prioriteit) + "</span>" : "") +
          (ib && ib.vaak_ontbrekend === "ja" ? ' <span class="chip chip--warning">ontbreekt vaak</span>' : "") + "</li>";
      }).join("") + "</ul>" : "") +
    (hps.length ? '<span class="label">Handelingsperspectief</span><div style="margin-bottom:14px">' +
      hps.map(function (h) {
        var hp = rec("handelingsperspectief", h.handelingsperspectief_id);
        if (!hp) { return ""; }
        return '<div class="notice notice--purple small" style="margin-bottom:6px"><span>' +
          "<strong>" + esc(hp.titel) + ".</strong> " + esc(hp.aanbevolen_actie || hp.samenvatting || "") +
          (hp.waarschuwing ? '<span class="d-waarom" style="margin-top:4px">Let op: ' + esc(hp.waarschuwing) + "</span>" : "") +
          "</span></div>";
      }).join("") + "</div>" : "") +
    (knels.length ? '<span class="label">Knelpunten</span><ul class="small" style="margin:0 0 14px">' +
      knels.map(function (k) {
        var kp = rec("knelpunt", k.knelpunt_id);
        return "<li>" + esc(kp ? kp.naam : k.knelpunt_id) +
          (k.impact ? ' <span class="chip chip--warning">impact ' + esc(k.impact) + "</span>" : "") + "</li>";
      }).join("") + "</ul>" : "") +
    (producten.length ? '<span class="label">Beslisproducten</span><div class="chip-row" style="margin-bottom:14px">' +
      producten.map(function (p) {
        return '<span class="chip">' + esc(naam("beslisproduct", p.beslisproduct_id)) + "</span>";
      }).join("") + "</div>" : "") +
    (instrs.length ? '<span class="label">Instrumenten hier</span><ul class="linklist">' +
      instrs.map(function (x) {
        return '<li><a class="linklist__btn" href="' + instrumentUrl(x.instrument_id) + '">' +
          esc(naam("instrument", x.instrument_id)) +
          '<span class="linklist__meta">' + esc(x.ondersteuningsfunctie || "ondersteunt") + "</span>" +
          '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></a></li>";
      }).join("") + "</ul>" : "");
}

function renderC2() {
  renderC2Kaart();
  renderC2Clusters();
  renderC2Momenten();
  renderC2Detail();
}

$('[data-action="c2-alle"]').addEventListener("click", function () {
  c2Cluster = null; c2Moment = null;
  renderC2Kaart(); c2Markeer(); renderC2Detail();
  toast("Alle negen clusters zijn weer zichtbaar.");
});

/* Een beslismoment is deelbaar: routeplanner.html#BM-O4-01 opent het meteen. */
function c2UitHash() {
  var h = window.location.hash.replace("#", "");
  if (h && rec("beslismoment", h)) { kiesC2Moment(h); return true; }
  if (h && rec("rolcluster", h)) { kiesC2Cluster(h); return true; }
  return false;
}
window.addEventListener("hashchange", c2UitHash);

c2Bouw();
renderC2();
c2UitHash();
