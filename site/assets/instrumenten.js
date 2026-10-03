"use strict";
/* ============================================================
   Instrumentenbibliotheek

   Dezelfde filtermachinerie als in het prototype, met drie
   verschillen die het een website maken:

   1. De filters staan in de URL, dus een gefilterde lijst is te delen
      en de terugknop van de browser werkt.
   2. Een kaart is een link naar een echte pagina, geen knop die een
      venster opent.
   3. Bij het doorklikken gaat de zoeksituatie mee naar de
      detailpagina, zodat die kan zeggen wat bij jou past.
   ============================================================ */
(function () {
  var IX = window.KOMPAS_INDEX;
  if (!IX) { return; }

  var GROEPEN = IX.groepen;
  var filters = {};
  var open = {};
  var zoekterm = "";
  var toonAlles = false;
  var limiet = 24;
  var STAP = 24;

  GROEPEN.forEach(function (g) { filters[g.id] = []; open[g.id] = !!g.open; });

  /* ---------- URL in en uit ---------- */
  function uitUrl() {
    var p = new URLSearchParams(window.location.search);
    GROEPEN.forEach(function (g) {
      var w = p.get(g.id);
      if (w) { filters[g.id] = w.split(",").filter(Boolean); }
      if (filters[g.id].length) { open[g.id] = true; }
    });
    if (p.get("zoek")) { zoekterm = p.get("zoek"); }
    if (p.get("alles") === "1") { toonAlles = true; }
  }

  function naarUrl() {
    var p = new URLSearchParams();
    GROEPEN.forEach(function (g) {
      if (filters[g.id].length) { p.set(g.id, filters[g.id].join(",")); }
    });
    if (zoekterm) { p.set("zoek", zoekterm); }
    if (toonAlles) { p.set("alles", "1"); }
    var q = p.toString();
    window.history.replaceState(null, "", q ? "?" + q : window.location.pathname);
    bewaarZoeksituatie(q);
  }

  /* De detailpagina leest dit en kan dan zeggen wat bij jou past. */
  function bewaarZoeksituatie(q) {
    var labels = [];
    var codes = {};
    GROEPEN.forEach(function (g) {
      if (!filters[g.id].length) { return; }
      codes[g.id] = filters[g.id].slice();
      filters[g.id].forEach(function (c) {
        var o = optie(g.id, c);
        if (o) { labels.push(o.label); }
      });
    });
    if (zoekterm) { labels.push("“" + zoekterm + "”"); }
    if (!labels.length) {
      try { window.sessionStorage.removeItem("kompas.context"); } catch (e) { /* niets */ }
      return;
    }
    try {
      window.sessionStorage.setItem("kompas.context", JSON.stringify({
        labels: labels.slice(0, 6), codes: codes, zoek: q ? "?" + q : ""
      }));
    } catch (e) { /* niets */ }
  }

  function optie(groepId, code) {
    for (var i = 0; i < GROEPEN.length; i++) {
      if (GROEPEN[i].id !== groepId) { continue; }
      var o = GROEPEN[i].opties.filter(function (x) { return x.code === code; })[0];
      if (o) { return o; }
    }
    return null;
  }

  function groepTitel(id) {
    var g = GROEPEN.filter(function (x) { return x.id === id; })[0];
    return g ? g.titel : id;
  }

  /* ---------- Filteren en zoeken ---------- */
  function basis() {
    return IX.instrumenten.filter(function (i) {
      return toonAlles || i.v1 !== "nee";
    });
  }

  function matcht(i, negeer) {
    for (var n = 0; n < GROEPEN.length; n++) {
      var g = GROEPEN[n];
      if (g.id === negeer) { continue; }
      var gekozen = filters[g.id];
      if (!gekozen.length) { continue; }
      var heeft = i.kn[g.id] || [];
      var raak = gekozen.some(function (c) { return heeft.indexOf(c) !== -1; });
      if (!raak) { return false; }
    }
    return true;
  }

  function score(i, tekst) {
    var tokens = tekst.toLowerCase().split(/[^a-z0-9à-ÿ]+/).filter(function (t) {
      return t.length >= 3;
    });
    if (!tokens.length) { return 1; }
    var s = 0;
    tokens.forEach(function (t) { if (i.hooi.indexOf(t) !== -1) { s += 1; } });
    return s === tokens.length ? s + 1 : (s > 0 ? s : 0);
  }

  function resultaten() {
    var tekst = zoekterm.trim();
    return basis()
      .map(function (i) { return { i: i, s: score(i, tekst) }; })
      .filter(function (r) { return r.s > 0 && matcht(r.i); })
      .sort(function (a, b) {
        if (b.s !== a.s) { return b.s - a.s; }
        var pa = a.i.relevantie === "hoog" ? 0 : 1;
        var pb = b.i.relevantie === "hoog" ? 0 : 1;
        if (pa !== pb) { return pa - pb; }
        return a.i.naam.localeCompare(b.i.naam, "nl");
      })
      .map(function (r) { return r.i; });
  }

  /* ---------- Filterkolom ---------- */
  function renderFilters() {
    var host = document.getElementById("b-filters");
    host.innerHTML = GROEPEN.map(function (g) {
      var gekozen = filters[g.id];
      var uit = open[g.id];
      var opties = g.opties.map(function (o) {
        var aantal = basis().filter(function (i) {
          return (i.kn[g.id] || []).indexOf(o.code) !== -1 && matcht(i, g.id);
        }).length;
        var aan = gekozen.indexOf(o.code) !== -1;
        var klas = "check" + (o.diepte === 1 ? " check--genest" : o.diepte >= 2 ? " check--genest2" : "");
        return '<label class="' + klas + '">' +
          '<input type="checkbox" data-groep="' + esc(g.id) + '" value="' + esc(o.code) + '"' +
          (aan ? " checked" : "") + (aantal === 0 && !aan ? " disabled" : "") + ">" +
          "<span>" + esc(o.label) +
          (o.sub ? '<span class="fgroep__sub">' + esc(o.sub) + "</span>" : "") + "</span>" +
          '<span class="check__count">' + aantal + "</span></label>";
      }).join("");
      return '<div class="fgroep">' +
        '<button type="button" class="fgroep__knop" data-fgroep="' + esc(g.id) + '" ' +
        'aria-expanded="' + (uit ? "true" : "false") + '" aria-controls="fg-' + esc(g.id) + '">' +
        "<span>" + esc(g.titel) + "</span>" +
        (gekozen.length ? '<span class="filtergroup__count">' + gekozen.length + "</span>" : "") +
        '<span class="arrow">' + icon("i-chevron-down", 15, 2) + "</span></button>" +
        '<div class="fgroep__paneel" id="fg-' + esc(g.id) + '"' + (uit ? "" : " hidden") + ">" +
        opties + "</div></div>";
    }).join("");

    $$("#b-filters [data-fgroep]").forEach(function (k) {
      k.addEventListener("click", function () {
        open[k.dataset.fgroep] = !open[k.dataset.fgroep];
        renderFilters();
      });
    });
    $$("#b-filters input[type=checkbox]").forEach(function (cb) {
      cb.addEventListener("change", function () {
        var g = cb.dataset.groep;
        var i = filters[g].indexOf(cb.value);
        if (cb.checked && i === -1) { filters[g].push(cb.value); }
        if (!cb.checked && i !== -1) { filters[g].splice(i, 1); }
        limiet = STAP;
        render();
      });
    });
  }

  function renderChips() {
    var host = document.getElementById("b-chips");
    var chips = [];
    GROEPEN.forEach(function (g) {
      filters[g.id].forEach(function (c) {
        var o = optie(g.id, c);
        chips.push('<button type="button" class="filterchip" data-groep="' + esc(g.id) +
          '" data-code="' + esc(c) + '">' +
          '<span class="tiny muted">' + esc(g.titel) + "</span> " +
          esc(o ? o.label : c) + icon("i-close", 13, 2.2) + "</button>");
      });
    });
    if (zoekterm) {
      chips.push('<button type="button" class="filterchip" data-zoekwis="1">' +
        '<span class="tiny muted">Zoekterm</span> ' + esc(zoekterm) + icon("i-close", 13, 2.2) + "</button>");
    }
    host.innerHTML = chips.length
      ? chips.join("") + '<button type="button" class="btn btn--ghost btn--small" data-wis="1">Wis alles</button>'
      : "";
    $$("#b-chips .filterchip").forEach(function (c) {
      c.addEventListener("click", function () {
        if (c.dataset.zoekwis) {
          zoekterm = "";
          document.getElementById("b-zoek").value = "";
        } else {
          var lijst = filters[c.dataset.groep];
          var i = lijst.indexOf(c.dataset.code);
          if (i !== -1) { lijst.splice(i, 1); }
        }
        limiet = STAP;
        render();
      });
    });
  }

  /* Iemand die "Vastgoedregisseur" typt, zoekt zijn rol, niet een instrument. */
  function renderAliasnoot() {
    var host = document.getElementById("b-aliasnoot");
    var t = zoekterm.trim().toLowerCase();
    if (!host) { return; }
    if (t.length < 3) { host.innerHTML = ""; return; }
    var raak = IX.aliassen.filter(function (a) {
      return a.titel.toLowerCase().indexOf(t) !== -1;
    }).slice(0, 3);
    if (!raak.length || filters.rol.length) { host.innerHTML = ""; return; }
    host.innerHTML = '<div class="notice">' + icon("i-users", 16) +
      "<span>In het model heet die functie een rol. " +
      raak.map(function (a) {
        return '<button type="button" class="chip chip--teal" data-alias="' + esc(a.rol) + '">' +
          esc(a.titel) + " → " + esc(a.rolnaam) + "</button>";
      }).join(" ") + "</span></div>";
    $$("#b-aliasnoot [data-alias]").forEach(function (b) {
      b.addEventListener("click", function () {
        // De functietitel zelf staat niet in de instrumenten; die ruilen we
        // in voor het rolfilter, anders blijft het resultaat leeg.
        filters.rol = [b.dataset.alias];
        open.rol = true;
        zoekterm = "";
        document.getElementById("b-zoek").value = "";
        limiet = STAP;
        render();
      });
    });
  }

  /* ---------- Resultaten ---------- */
  function statusChip(i) {
    if (!i.status) { return ""; }
    var kl = { open: "chip--success", doorlopend: "chip--teal", verwacht: "chip--blue",
               gesloten: "chip--critical", onbekend: "chip--demo" }[i.status] || "";
    return '<span class="chip ' + kl + '">' + esc(i.status) + "</span>";
  }

  function renderResultaten() {
    var lijst = resultaten();
    var getoond = lijst.slice(0, limiet);
    var host = document.getElementById("b-resultaten");

    document.getElementById("b-telling").textContent =
      lijst.length === 1 ? "1 instrument" : lijst.length + " instrumenten";

    if (!lijst.length) {
      host.innerHTML = '<div class="empty">' + icon("i-search", 22, 1.6) +
        "<p><strong>Niets gevonden met deze combinatie.</strong></p>" +
        '<p class="small muted">Haal een filter weg, of zoek op een ander woord. ' +
        "Het model is concept v0.1; niet elke combinatie is al gevuld.</p>" +
        '<button type="button" class="btn btn--small" data-wis="1">Wis alle filters</button></div>';
      return;
    }

    host.innerHTML = getoond.map(function (i) {
      var fasen = (i.kn.fase || []).slice(0, 2);
      return '<a class="inst-card" href="instrument/' + encodeURIComponent(i.code) + '.html">' +
        '<div class="inst-card__top">' +
        '<span class="inst-card__icon">' + icon("i-doc", 17, 1.8) + "</span>" +
        '<span><span class="cardtitle">' + esc(i.naam) + "</span>" +
        '<span class="tiny muted">' + esc(i.type || "instrument") + "</span></span>" +
        statusChip(i) + "</div>" +
        '<p class="inst-card__desc">' + esc(i.vraag || i.omschrijving) + "</p>" +
        '<div class="inst-card__foot">' +
        fasen.map(function (f) { return '<span class="chip">' + esc(f) + "</span>"; }).join("") +
        (i.complexiteit ? '<span class="chip chip--blue">' + esc(i.complexiteit) + "</span>" : "") +
        '<span class="arrow" style="margin-left:auto;color:var(--vmv-grey-400)">' +
        icon("i-arrow-right", 16, 1.8) + "</span></div></a>";
    }).join("");

    if (lijst.length > limiet) {
      var rest = Math.min(STAP, lijst.length - limiet);
      host.insertAdjacentHTML("afterend",
        '<button type="button" class="btn btn--block" id="b-meer">Toon volgende ' + rest +
        " van " + (lijst.length - limiet) + "</button>");
      document.getElementById("b-meer").addEventListener("click", function () {
        limiet += STAP;
        render();
      });
    }
  }

  function renderZijkolom() {
    var themahost = document.getElementById("b-themachips");
    if (themahost) {
      themahost.innerHTML = IX.themas.map(function (t) {
        return '<span class="chip">' + esc(t.label) +
          '<span class="tiny muted">' + t.vragen.length + "</span></span>";
      }).join("");
    }

    var verdeling = {};
    IX.instrumenten.forEach(function (i) {
      var hg = i.hoofdgroep || "onbekend";
      verdeling[hg] = (verdeling[hg] || 0) + 1;
    });
    var host = document.getElementById("b-verdeling");
    if (host) {
      var max = Math.max.apply(null, Object.keys(verdeling).map(function (k) { return verdeling[k]; }));
      host.innerHTML = Object.keys(verdeling).sort(function (a, b) {
        return verdeling[b] - verdeling[a];
      }).map(function (hg) {
        return '<div style="margin-bottom:9px"><div class="tiny" style="display:flex;justify-content:space-between">' +
          "<span>" + esc(hg) + "</span><span class=\"muted\">" + verdeling[hg] + "</span></div>" +
          '<div style="height:6px;border-radius:3px;background:var(--vmv-grey-100);margin-top:3px">' +
          '<div style="height:6px;border-radius:3px;background:var(--vmv-teal);width:' +
          Math.round(verdeling[hg] / max * 100) + '%"></div></div></div>';
      }).join("");
    }

    var bhost = document.getElementById("b-beheerders");
    if (bhost) {
      var namen = Object.keys(IX.beheerders).sort(function (a, b) {
        return IX.beheerders[b].length - IX.beheerders[a].length;
      }).slice(0, 8);
      bhost.innerHTML = namen.map(function (o) {
        return '<li><button type="button" class="linklist__btn" data-beheerder="' + esc(o) + '">' +
          esc(o) + '<span class="linklist__meta">' + IX.beheerders[o].length +
          " instrumenten</span><span class=\"arrow\">" + icon("i-arrow-right", 16, 1.8) +
          "</span></button></li>";
      }).join("");
      $$("#b-beheerders [data-beheerder]").forEach(function (b) {
        b.addEventListener("click", function () {
          GROEPEN.forEach(function (g) { filters[g.id] = []; });
          zoekterm = b.dataset.beheerder;
          document.getElementById("b-zoek").value = zoekterm;
          limiet = STAP;
          render();
        });
      });
    }
  }

  function render() {
    renderFilters();
    renderChips();
    renderAliasnoot();
    renderResultaten();
    naarUrl();
  }

  /* ---------- Start ---------- */
  uitUrl();
  var veld = document.getElementById("b-zoek");
  veld.value = zoekterm;
  veld.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); zoekterm = veld.value; limiet = STAP; render(); }
  });
  document.getElementById("b-zoek-knop").addEventListener("click", function () {
    zoekterm = veld.value; limiet = STAP; render();
  });
  var alles = document.getElementById("b-toon-alles");
  alles.checked = toonAlles;
  alles.addEventListener("change", function () {
    toonAlles = alles.checked; limiet = STAP; render();
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest("[data-wis]")) { return; }
    GROEPEN.forEach(function (g) { filters[g.id] = []; });
    zoekterm = "";
    veld.value = "";
    limiet = STAP;
    render();
  });

  renderZijkolom();
  render();
}());
