(() => {
  const RESULT_URL = "/phases/phase10r/";

  function install() {
    if (document.getElementById("phase10rFrontier")) return;
    const hero = document.querySelector("main .hero");
    if (!hero) return;

    const style = document.createElement("style");
    style.id = "phase10rFrontierStyle";
    style.textContent = `
      .phase10r-frontier{background:#171a20;color:#fff;padding:24px clamp(24px,7vw,120px);display:grid;grid-template-columns:minmax(0,1fr) auto;gap:28px;align-items:center;border-top:1px solid rgba(255,255,255,.12)}
      .phase10r-frontier-copy{display:grid;gap:6px}.phase10r-frontier-kicker{margin:0;color:#9fa0a3;font-size:10px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}.phase10r-frontier strong{font-size:clamp(17px,2vw,24px);font-weight:500;letter-spacing:-.02em}.phase10r-frontier p{margin:0;color:#c7c7c7;font-size:13px;line-height:1.55}.phase10r-frontier-metrics{display:flex;gap:22px;align-items:center}.phase10r-frontier-metrics span{display:grid;gap:2px;min-width:86px}.phase10r-frontier-metrics b{font-size:18px;font-weight:500}.phase10r-frontier-metrics small{color:#9fa0a3;font-size:9px;text-transform:uppercase;letter-spacing:.08em}.phase10r-frontier a{color:#fff;border-bottom:1px solid rgba(255,255,255,.45);padding-bottom:2px}
      @media(max-width:767px){.phase10r-frontier{grid-template-columns:1fr;padding:22px 20px}.phase10r-frontier-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.phase10r-frontier-metrics span{min-width:0}.phase10r-frontier-metrics b{font-size:16px}}
    `;
    document.head.appendChild(style);

    const section = document.createElement("section");
    section.id = "phase10rFrontier";
    section.className = "phase10r-frontier";
    section.setAttribute("aria-label", "Frozen Phase 10R holdout frontier");
    section.innerHTML = `
      <div class="phase10r-frontier-copy">
        <p class="phase10r-frontier-kicker">Frozen frontier · Phase 10R protected holdout</p>
        <strong>Average ambiguous-view error fell sharply. Tail risk, availability, and calibration under shift did not.</strong>
        <p>Final all-gates verdict: mixed / failed overall · frozen without retuning · <a href="${RESULT_URL}">open Phase 10R ↗</a></p>
      </div>
      <div class="phase10r-frontier-metrics" aria-label="Phase 10R frozen holdout metrics">
        <span><b>79.2%</b><small>lateral MAE gain</small></span>
        <span><b>20.0%</b><small>miss rate</small></span>
        <span><b>84.3%</b><small>95% lat coverage</small></span>
      </div>`;
    hero.insertAdjacentElement("afterend", section);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})();
