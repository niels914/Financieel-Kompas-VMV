"use strict";
/* ============================================================
   Datatoegang over KOMPAS_MODEL

   Dezelfde vorm als de Python-laag in de generator: het model
   verwijst op leesbare codes (ROL-003, P1, I-001), niet op UUID's.
   Alle opzoekingen zijn gememoïseerd.

   Alleen de routeplanner en de adviseur laden dit; de detailpagina's
   hebben hun inhoud al ingebakken.
   ============================================================ */
var DB = window.KOMPAS_MODEL || {};

var SLEUTEL = {
  opgave: "opgave_code", procesniveau: "code", procesfase: "fase_code",
  beslismoment: "beslismoment_code", besluittype: "code", rol: "rol_code",
  rolcluster: "code", eigenaartype: "code", objecttype: "objecttype_code",
  financiele_vraag: "vraag_code", financieel_thema: "thema_code",
  informatiebehoefte: "informatie_code", informatietype: "code",
  beslisproduct: "code", handelingsperspectief: "code", knelpunt: "code",
  instrument: "instrument_code", instrumenttype: "code", digitale_vorm: "code",
  organisatie: "naam", organisatietype: "code", bron: "titel", brontype: "code",
  financiele_route: "route_code", effecttype: "code", voorwaardetype: "code",
  werkingsgebied: "naam", pc_moment: "code", instrument_relatietype: "code"
};

function tab(naam) { return DB[naam] || []; }

var _idx = {};
function index(tabel) {
  if (!_idx[tabel]) {
    var sl = SLEUTEL[tabel] || tabel + "_code";
    var m = {};
    tab(tabel).forEach(function (r) { if (r[sl] != null) { m[String(r[sl])] = r; } });
    _idx[tabel] = m;
  }
  return _idx[tabel];
}
function rec(tabel, code) { return code == null ? null : (index(tabel)[String(code)] || null); }
function naam(tabel, code) {
  var r = rec(tabel, code);
  if (!r) { return String(code); }
  return r.naam || r.naam_kort || r.naam_officieel || r.titel || r.vraagtekst || String(code);
}

var _grp = {};
function bij(tabel, veld, code) {
  var pot = tabel + "|" + veld;
  if (!_grp[pot]) {
    var g = {};
    tab(tabel).forEach(function (r) {
      if (r[veld] == null) { return; }
      var k = String(r[veld]);
      (g[k] = g[k] || []).push(r);
    });
    _grp[pot] = g;
  }
  return _grp[pot][String(code)] || [];
}

function sorteer(lijst, veld) {
  return lijst.slice().sort(function (a, b) {
    var sa = a.sort_order == null ? 9999 : Number(a.sort_order);
    var sb = b.sort_order == null ? 9999 : Number(b.sort_order);
    if (sa !== sb) { return sa - sb; }
    var na = String(a[veld || "naam"] || a.titel || "");
    var nb = String(b[veld || "naam"] || b.titel || "");
    return na.localeCompare(nb, "nl");
  });
}

function rolKleur(rolCode) {
  var r = rec("rol", rolCode);
  return r ? clusterKleur(r.rolcluster_id) : "var(--vmv-grey-400)";
}

/* Links naar de echte pagina's; de basis verschilt per maplaag. */
function instrumentUrl(code) {
  return KOMPAS.basis + "instrument/" + encodeURIComponent(code) + ".html";
}
function momentUrl(code) {
  return KOMPAS.basis + "beslismoment/" + encodeURIComponent(code) + ".html";
}
function vraagUrl(code) {
  return KOMPAS.basis + "vraag/" + encodeURIComponent(code) + ".html";
}
function filterUrl(groep, code) {
  return KOMPAS.basis + "instrumenten.html?" + groep + "=" + encodeURIComponent(code);
}

/* ------------------------------------------------------------
   Kenmerken per instrument

   Dezelfde set als de generator bouwt, maar hier alleen over de
   koppeltabellen die in KOMPAS_MODEL zitten. De adviseur scoort
   hierop; de bibliotheek heeft zijn eigen, uitgebreidere index.
   ------------------------------------------------------------ */
var KOPPELING = [
  ["rol", "instrument_rol", "rol_id"],
  ["fase", "instrument_procesfase", "procesfase_id"],
  ["moment", "instrument_beslismoment", "beslismoment_id"],
  ["opgave", "instrument_opgave", "opgave_id"],
  ["objecttype", "instrument_objecttype", "objecttype_id"],
  ["eigenaar", "instrument_eigenaartype", "eigenaartype_id"]
];

var KENMERK = {};
(function bouwKenmerken() {
  tab("instrument").forEach(function (i) {
    var kn = { type: i.primaire_instrumenttype_id ? [i.primaire_instrumenttype_id] : [] };
    KOPPELING.forEach(function (k) { kn[k[0]] = []; });
    KENMERK[i.instrument_code] = kn;
  });
  KOPPELING.forEach(function (k) {
    tab(k[1]).forEach(function (r) {
      var kn = KENMERK[r.instrument_id];
      if (kn && r[k[2]] != null) { kn[k[0]].push(String(r[k[2]])); }
    });
  });
}());

/* De instrumenten die versie 1 toont. */
function bBasis() {
  return tab("instrument").filter(function (i) { return i.tonen_in_v1 !== "nee"; });
}
