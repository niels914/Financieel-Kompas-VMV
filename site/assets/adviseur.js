/* ============================================================
   Archetype D – Persoonlijke adviseur
   ============================================================ */
var dAntwoord = {};
var dStap = 0;

var dStappen = [
  { id: "opgave", kort: "Opgave", vraag: "Wat is je opgave?",
    toelichting: "Waar wil je antwoord op? Dit bepaalt welke instrumenten later in beeld komen." },
  { id: "vastgoed", kort: "Vastgoed", vraag: "Om welk vastgoed gaat het, en wie is de eigenaar?",
    toelichting: "Objecttype en eigenaartype bepalen welke regelingen überhaupt van toepassing zijn." },
  { id: "fase", kort: "Fase", vraag: "In welke fase zit je?",
    toelichting: "Portefeuille en object zijn twee aparte processen met elk hun eigen fasen." },
  { id: "rol", kort: "Rol", vraag: "Wat is jouw rol?",
    toelichting: "Je rol bepaalt welke informatie je nodig hebt en bij welke besluiten je aan tafel zit." },
  { id: "knelpunt", kort: "Knelpunt", vraag: "Waar loop je tegenaan?",
    toelichting: "Het knelpunt kleurt het handelingsperspectief dat je straks krijgt." }
];

function dKlaar() { return dStap >= dStappen.length; }

function dOptieKnop(groep, code, titel, sub, extra) {
  return '<button type="button" class="d-optie" data-dgroep="' + groep + '" data-dcode="' + esc(code) +
    '" aria-pressed="' + (dAntwoord[groep] === code) + '">' +
    '<span><span class="d-optie__naam">' + esc(titel) + "</span>" +
    (sub ? '<span class="d-optie__sub">' + esc(sub) + "</span>" : "") + "</span>" +
    "<span>" + (extra || "") + "</span></button>";
}

function renderDStappenbalk() {
  $("#d-stappenbalk").innerHTML = dStappen.map(function (s, i) {
    var klaar = !!dAntwoord[s.id] || (s.id === "vastgoed" && dAntwoord.objecttype && dAntwoord.eigenaar);
    var klasse = klaar ? "is-klaar" : (i === dStap ? "is-nu" : "");
    return '<span class="d-stap ' + klasse + '">' + (klaar ? icon("i-check", 12, 2.4) : (i + 1) + ".") +
      " " + esc(s.kort) + "</span>";
  }).join("");
  var gedaan = dStappen.filter(function (s) {
    return s.id === "vastgoed" ? (dAntwoord.objecttype && dAntwoord.eigenaar) : !!dAntwoord[s.id];
  }).length;
  $("#d-voortgang").textContent = gedaan + " van " + dStappen.length + " beantwoord";
}

function renderDVraag() {
  var host = $("#d-vraag");
  if (dKlaar()) { host.innerHTML = ""; return; }
  var s = dStappen[dStap];
  var inhoud = "";

  if (s.id === "opgave") {
    inhoud = '<div class="d-opties">' + sorteer(tab("opgave")).map(function (o) {
      return dOptieKnop("opgave", o.opgave_code, o.naam, o.korte_omschrijving,
        '<span class="chip chip--demo">' + esc(o.niveau_default || "") + "</span>");
    }).join("") + "</div>";

  } else if (s.id === "vastgoed") {
    var objecten = sorteer(tab("objecttype")).filter(function (o) {
      return o.parent_objecttype_id;   /* hoofdcategorie zelf overslaan */
    });
    inhoud = '<span class="label">Objecttype</span><div class="d-opties d-opties--twee" style="margin-bottom:18px">' +
      objecten.map(function (o) {
        return dOptieKnop("objecttype", o.objecttype_code, o.naam, naam("objecttype", o.parent_objecttype_id));
      }).join("") + "</div>" +
      '<span class="label">Eigenaartype</span><div class="d-opties">' +
      sorteer(tab("eigenaartype")).map(function (e) {
        return dOptieKnop("eigenaar", e.code, e.naam, null,
          e.primaire_scope_v1 === "ja" ? '<span class="chip chip--teal">versie 1</span>' : "");
      }).join("") + "</div>";

  } else if (s.id === "fase") {
    inhoud = sorteer(tab("procesniveau")).map(function (n) {
      var fasen = sorteer(tab("procesfase")).filter(function (f) { return f.procesniveau_id === n.code; });
      if (!fasen.length) { return ""; }
      return '<span class="label">' + esc(n.naam) + "</span>" +
        '<div class="d-opties" style="margin-bottom:18px">' + fasen.map(function (f) {
          return dOptieKnop("fase", f.fase_code, f.fase_code + " · " + f.naam, f.centrale_vraag);
        }).join("") + "</div>";
    }).join("");

  } else if (s.id === "rol") {
    inhoud = sorteer(tab("rolcluster")).map(function (c) {
      var rollen = tab("rol").filter(function (r) { return r.rolcluster_id === c.code; });
      if (!rollen.length) { return ""; }
      return '<span class="label"><span style="display:inline-block;width:12px;height:4px;border-radius:2px;background:' +
        clusterKleur(c.code) + ';margin-right:6px"></span>' + esc(c.naam) + "</span>" +
        '<div class="d-opties d-opties--twee" style="margin-bottom:18px">' + rollen.map(function (r) {
          return dOptieKnop("rol", r.rol_code, r.naam, r.primaire_verantwoordelijkheid,
            r.primaire_gebruiker_v1 === "ja" ? '<span class="chip chip--teal">versie 1</span>' : "");
        }).join("") + "</div>";
    }).join("");

  } else if (s.id === "knelpunt") {
    inhoud = '<div class="d-opties">' + tab("knelpunt").map(function (k) {
      return dOptieKnop("knelpunt", k.code, k.naam, k.omschrijving,
        '<span class="chip chip--warning">' + esc(k.ernst || "") + "</span>");
    }).join("") + "</div>";
  }

  host.innerHTML = '<div class="qcard"><div class="qcard__head">' +
    '<span class="qcard__num" aria-hidden="true">' + (dStap + 1) + "</span>" +
    '<h3 style="font-size:.98rem">' + esc(s.vraag) + "</h3>" +
    '<span class="chip chip--demo" style="margin-left:auto">stap ' + (dStap + 1) + " van " + dStappen.length + "</span></div>" +
    '<p class="small muted" style="margin-bottom:14px">' + esc(s.toelichting) + "</p>" +
    inhoud +
    (dStap > 0 ? '<button type="button" class="btn btn--ghost btn--small" style="margin-top:14px" data-dterug="1">Vorige vraag</button>' : "") +
    "</div>";

  $$("#d-vraag [data-dgroep]").forEach(function (b) {
    b.addEventListener("click", function () {
      dAntwoord[b.dataset.dgroep] = b.dataset.dcode;
      var s2 = dStappen[dStap];
      var compleet = s2.id === "vastgoed" ? (dAntwoord.objecttype && dAntwoord.eigenaar) : true;
      if (compleet) { dStap += 1; }
      renderD();
    });
  });
  var terug = $("#d-vraag [data-dterug]");
  if (terug) {
    terug.addEventListener("click", function () { dStap = Math.max(0, dStap - 1); renderD(); });
  }
}

/* Het beslismoment dat bij de gekozen fase en rol hoort. */
function dBeslismoment() {
  var inFase = tab("beslismoment").filter(function (b) { return b.procesfase_id === dAntwoord.fase; });
  if (!inFase.length) { return null; }
  var metRol = inFase.filter(function (b) {
    return bij("beslismoment_rol", "beslismoment_id", b.beslismoment_code)
      .some(function (br) { return br.rol_id === dAntwoord.rol; });
  });
  return (metRol[0] || inFase[0]);
}

/* Transparante instrumentmatch: tel treffers per dimensie, gewogen op
   relevantie, en onthoud waaróm een instrument matcht. */
var D_DIM = [
  { sleutel: "opgave", kenmerk: "opgave", label: "je opgave", gewicht: 3 },
  { sleutel: "rol", kenmerk: "rol", label: "je rol", gewicht: 3 },
  { sleutel: "fase", kenmerk: "fase", label: "je fase", gewicht: 3 },
  { sleutel: "objecttype", kenmerk: "objecttype", label: "dit objecttype", gewicht: 1 },
  { sleutel: "eigenaar", kenmerk: "eigenaar", label: "dit eigenaartype", gewicht: 1 }
];

function dMatches(moment) {
  var uit = [];
  bBasis().forEach(function (i) {
    var kn = KENMERK[i.instrument_code] || {};
    var score = 0, waarom = [];
    D_DIM.forEach(function (d) {
      var gekozen = dAntwoord[d.sleutel];
      if (gekozen && (kn[d.kenmerk] || []).indexOf(gekozen) !== -1) {
        score += d.gewicht; waarom.push(d.label);
      }
    });
    if (moment && (kn.moment || []).indexOf(moment.beslismoment_code) !== -1) {
      score += 4; waarom.push("dit beslismoment");
    }
    if (i.relevantie_v1 === "hoog") { score += 1; }
    if (score >= 4) { uit.push({ i: i, score: score, waarom: waarom }); }
  });
  return uit.sort(function (a, b) { return b.score - a.score; }).slice(0, 8);
}

function renderDResultaat() {
  var host = $("#d-resultaat");
  if (!dKlaar()) { host.innerHTML = ""; return; }

  var b = dBeslismoment();
  var treffers = dMatches(b);
  var vastgesteld = [
    naam("opgave", dAntwoord.opgave),
    naam("objecttype", dAntwoord.objecttype),
    naam("eigenaartype", dAntwoord.eigenaar),
    dAntwoord.fase + " · " + naam("procesfase", dAntwoord.fase),
    naam("rol", dAntwoord.rol),
    naam("knelpunt", dAntwoord.knelpunt)
  ];

  var info = b ? bij("beslismoment_informatiebehoefte", "beslismoment_id", b.beslismoment_code) : [];
  var vragen = b ? bij("beslismoment_financiele_vraag", "beslismoment_id", b.beslismoment_code) : [];
  var hps = b ? bij("beslismoment_handelingsperspectief", "beslismoment_id", b.beslismoment_code) : [];
  var rollen = b ? bij("beslismoment_rol", "beslismoment_id", b.beslismoment_code) : [];

  host.innerHTML = '<div class="result card" style="margin-top:16px">' +
    '<div class="card__head"><h3>Eerste denkrichting voor jouw situatie</h3>' +
    '<span class="chip chip--success" style="margin-left:auto">' + icon("i-check", 13, 2.2) + " Intake compleet</span></div>" +
    '<div class="card__body">' +

    '<span class="label">Vastgesteld</span><ul class="checklist" style="margin-bottom:18px">' +
    vastgesteld.map(function (v) {
      return '<li class="done"><span class="mark" aria-hidden="true">' + icon("i-check", 12, 2.4) + "</span>" + esc(v) + "</li>";
    }).join("") + "</ul>" +

    (b ? '<span class="label">Het beslismoment dat nu voorligt</span>' +
      '<div class="notice notice--purple" style="margin-bottom:18px"><span>' +
      "<strong>" + esc(b.naam) + "</strong>" +
      '<span class="d-waarom" style="margin-top:4px">' + esc(b.centrale_vraag || "") + "</span>" +
      '<span class="d-waarom">' + esc(b.formaliteitsniveau || "") + " · verwacht besluit: " + esc(b.verwacht_besluit || "onbekend") + "</span>" +
      "</span></div>"
      : '<div class="notice notice--neutral" style="margin-bottom:18px"><span>In deze fase staat nog geen beslismoment in het model.</span></div>') +

    '<div class="result__grid">' +

    "<div>" + (vragen.length ? '<span class="label">Financiële vragen</span><ul class="small" style="margin:0">' +
      vragen.map(function (v) {
        var fv = rec("financiele_vraag", v.financiele_vraag_id);
        return "<li>" + esc(fv ? fv.vraagtekst : v.financiele_vraag_id) + "</li>";
      }).join("") + "</ul>" : "") + "</div>" +

    "<div>" + (info.length ? '<span class="label">Informatie die je nodig hebt</span><ul class="small" style="margin:0">' +
      info.map(function (x) {
        var ib = rec("informatiebehoefte", x.informatiebehoefte_id);
        return "<li>" + esc(ib ? ib.naam : x.informatiebehoefte_id) +
          (ib && ib.vaak_ontbrekend === "ja" ? ' <span class="chip chip--warning">ontbreekt vaak</span>' : "") + "</li>";
      }).join("") + "</ul>" : "") + "</div>" +

    "<div>" + (rollen.length ? '<span class="label">Wie zit er aan tafel</span><ul class="small" style="margin:0">' +
      rollen.slice(0, 8).map(function (br) {
        return "<li>" + esc(naam("rol", br.rol_id)) + " <span class=\"muted\">(" + esc(br.betrokkenheidstype || "betrokken") + ")</span></li>";
      }).join("") + "</ul>" : "") + "</div>" +

    "</div>" +

    (hps.length ? '<hr class="divider"><span class="label">Handelingsperspectief</span>' +
      hps.map(function (h) {
        var hp = rec("handelingsperspectief", h.handelingsperspectief_id);
        if (!hp) { return ""; }
        return '<div class="notice small" style="margin-bottom:8px"><span>' +
          "<strong>" + esc(hp.titel) + ".</strong> " + esc(hp.aanbevolen_actie || "") +
          (hp.verwacht_resultaat ? '<span class="d-waarom" style="margin-top:4px">Resultaat: ' + esc(hp.verwacht_resultaat) + "</span>" : "") +
          (hp.waarschuwing ? '<span class="d-waarom">Let op: ' + esc(hp.waarschuwing) + "</span>" : "") +
          "</span></div>";
      }).join("") : "") +

    '<hr class="divider"><span class="label">Instrumenten die hier passen</span>' +
    (treffers.length ? '<ul class="linklist">' + treffers.map(function (t) {
      return '<li><a class="linklist__btn" href="' + instrumentUrl(t.i.instrument_code) + '">' +
        "<span>" + esc(t.i.naam_kort || t.i.naam_officieel) +
        ' <span class="d-match">' + t.score + " punten</span></span>" +
        '<span class="linklist__meta">past bij ' + esc(t.waarom.join(", ") || "je situatie") + "</span>" +
        '<span class="arrow">' + icon("i-arrow-right", 16, 1.8) + "</span></a></li>";
    }).join("") + "</ul>"
      : '<p class="small muted">Geen instrument scoort hoog genoeg op deze combinatie. Dat is in het model een reële uitkomst: niet elke situatie heeft een passend instrument.</p>') +

    '<div class="notice notice--purple small" style="margin-top:16px"><span>' + icon("i-info", 16) + "</span>" +
    "<span>Dit is een eerste navigatievoorstel, geen formeel financieel advies. De koppelingen waarop deze uitkomst berust zijn dummy.</span></div>" +

    '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px">' +
    (b ? '<a class="btn btn--primary" href="' + momentUrl(b.beslismoment_code) +
      '">Alles over dit beslismoment ' + icon("i-arrow-right", 15, 1.9) + "</a>" +
      '<a class="btn" href="' + KOMPAS.basis + "routeplanner.html#" + esc(b.beslismoment_code) +
      '">Dit moment in de routeplanner</a>' : "") +
    '<a class="btn" href="' + dBibliotheekUrl() + '">Zoek verder in de bibliotheek</a>' +
    '<button type="button" class="btn btn--ghost" data-action="d-reset">Opnieuw beginnen</button>' +
    "</div></div></div>";

  dBewaarZoeksituatie();
}

/* De intake is een zoeksituatie. Die gaat mee naar de detailpagina's, zodat
   die kunnen zeggen welke kenmerken bij jou passen. */
function dBibliotheekUrl() {
  var p = [];
  if (dAntwoord.opgave) { p.push("opgave=" + encodeURIComponent(dAntwoord.opgave)); }
  if (dAntwoord.rol) { p.push("rol=" + encodeURIComponent(dAntwoord.rol)); }
  if (dAntwoord.fase) { p.push("fase=" + encodeURIComponent(dAntwoord.fase)); }
  return KOMPAS.basis + "instrumenten.html" + (p.length ? "?" + p.join("&") : "");
}

function dBewaarZoeksituatie() {
  var codes = {};
  var labels = [];
  var paren = [["opgave", "opgave", "opgave"], ["rol", "rol", "rol"],
               ["fase", "fase", "procesfase"], ["objecttype", "objecttype", "objecttype"],
               ["eigenaar", "eigenaar", "eigenaartype"]];
  paren.forEach(function (x) {
    var w = dAntwoord[x[0]];
    if (!w) { return; }
    codes[x[1]] = [w];
    labels.push(naam(x[2], w));
  });
  var b = dBeslismoment();
  if (b) { codes.moment = [b.beslismoment_code]; }
  if (!labels.length) { return; }
  try {
    window.sessionStorage.setItem("kompas.context", JSON.stringify({
      labels: labels, codes: codes,
      zoek: dBibliotheekUrl().indexOf("?") !== -1
        ? dBibliotheekUrl().slice(dBibliotheekUrl().indexOf("?")) : ""
    }));
  } catch (e) { /* niets */ }
}

function renderDProfiel() {
  var regels = [
    ["Opgave", dAntwoord.opgave && naam("opgave", dAntwoord.opgave)],
    ["Objecttype", dAntwoord.objecttype && naam("objecttype", dAntwoord.objecttype)],
    ["Eigenaar", dAntwoord.eigenaar && naam("eigenaartype", dAntwoord.eigenaar)],
    ["Fase", dAntwoord.fase && (dAntwoord.fase + " · " + naam("procesfase", dAntwoord.fase))],
    ["Rol", dAntwoord.rol && naam("rol", dAntwoord.rol)],
    ["Knelpunt", dAntwoord.knelpunt && naam("knelpunt", dAntwoord.knelpunt)]
  ];
  $("#d-profiel").innerHTML = regels.map(function (r) {
    return "<div><dt>" + esc(r[0]) + "</dt><dd>" +
      (r[1] ? esc(r[1]) : '<span class="muted">nog niet gekozen</span>') + "</dd></div>";
  }).join("");
}

function renderDZijpaneel() {
  var host = $("#d-zijpaneel");
  if (!dKlaar()) {
    var resterend = bBasis().filter(function (i) {
      var kn = KENMERK[i.instrument_code] || {};
      return D_DIM.every(function (d) {
        var g = dAntwoord[d.sleutel];
        return !g || (kn[d.kenmerk] || []).indexOf(g) !== -1;
      });
    }).length;
    host.innerHTML = '<p class="small muted">Elke keuze maakt het beeld scherper. Na vijf vragen zie je het beslismoment dat voorligt, de informatie die je daarvoor nodig hebt en de instrumenten die passen.</p>' +
      '<hr class="divider"><span class="label">Nu nog in beeld</span>' +
      '<p style="font-size:1.6rem;font-weight:600;color:var(--vmv-purple);line-height:1.1;margin:0">' + resterend + "</p>" +
      '<p class="small muted">van de ' + bBasis().length + " instrumenten passen bij je keuzes tot nu toe.</p>";
    return;
  }
  var b = dBeslismoment();
  host.innerHTML = '<span class="label">Route door het model</span>' +
    '<ol class="steplist" style="margin-bottom:14px">' +
    "<li>" + esc(naam("opgave", dAntwoord.opgave)) + "</li>" +
    "<li>" + esc(dAntwoord.fase + " · " + naam("procesfase", dAntwoord.fase)) + "</li>" +
    "<li>" + (b ? esc(b.naam) : "geen beslismoment in deze fase") + "</li>" +
    "<li>" + esc(naam("rol", dAntwoord.rol)) + "</li>" +
    "</ol>" +
    '<p class="small muted">Dit is de hoofdroute uit het datamodel: van opgave via procesfase naar het beslismoment, en pas daarna naar rol, informatie en instrumenten.</p>';
}

function renderD() {
  renderDStappenbalk();
  renderDVraag();
  renderDResultaat();
  renderDProfiel();
  renderDZijpaneel();
}

document.addEventListener("click", function (e) {
  if (!e.target.closest('[data-action="d-reset"]')) { return; }
  dAntwoord = {}; dStap = 0;
  renderD();
  toast("De intake is opnieuw gestart.");
});

renderD();
