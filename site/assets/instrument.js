"use strict";
/* ============================================================
   Instrumentpagina – het feedbackblok

   In dit prototype blijft het antwoord in de browser. Het datamodel
   heeft er een tabel voor (gebruikersfeedback, met feedbacktype,
   bruikbaarheidsscore en gevonden_wat_gezocht); een echte site stuurt
   het daarheen. Dit laat zien hoe dat eruitziet zonder te doen alsof
   er iets verstuurd wordt.
   ============================================================ */
(function () {
  var host = document.getElementById("feedback-keuzes");
  var dank = document.getElementById("feedback-dank");
  if (!host || !dank) { return; }

  var ANTWOORD = {
    gevonden: "Fijn. In een echte site was dit geregistreerd als " +
      "„gevonden wat gezocht” met bruikbaarheidsscore 5.",
    deels: "Dank. Dat landt in het model als bruikbaarheidsscore 3 — " +
      "precies het signaal waar het kernteam naar zoekt.",
    verouderd: "Dank. Dit is het feedbacktype „informatie verouderd”; " +
      "in een echte site gaat er een controle naar de beheerder van dit instrument.",
    onvindbaar: "Dank. Dit is het feedbacktype „instrument niet gevonden”, " +
      "het signaal dat de navigatie je niet bracht waar je moest zijn."
  };

  var pad = "kompas.feedback." + (document.body.dataset.instrument || "pagina");

  function toon(soort) {
    dank.textContent = ANTWOORD[soort] || "Dank voor je reactie.";
    dank.hidden = false;
    Array.prototype.forEach.call(host.querySelectorAll("[data-feedback]"), function (b) {
      b.setAttribute("aria-pressed", b.dataset.feedback === soort ? "true" : "false");
    });
  }

  host.addEventListener("click", function (e) {
    var knop = e.target.closest("[data-feedback]");
    if (!knop) { return; }
    try { window.localStorage.setItem(pad, knop.dataset.feedback); } catch (err) { /* niets */ }
    toon(knop.dataset.feedback);
  });

  try {
    var eerder = window.localStorage.getItem(pad);
    if (eerder) { toon(eerder); }
  } catch (err) { /* niets */ }
}());
