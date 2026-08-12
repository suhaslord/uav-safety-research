(() => {
  const header = document.getElementById("siteHeader");
  if (!header) return;

  let queued = false;

  function sectionUnderHeader() {
    const sections = [...document.querySelectorAll("main .viewport-section")];
    if (!sections.length) return null;

    const headerRect = header.getBoundingClientRect();
    const probeY = Math.min(window.innerHeight - 1, Math.max(1, headerRect.bottom + 2));

    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      if (rect.top <= probeY && rect.bottom > probeY) return section;
    }

    // Boundary fallback: choose the section whose visible edge is closest to the probe.
    let best = null;
    let bestDistance = Infinity;
    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      const distance = Math.min(Math.abs(rect.top - probeY), Math.abs(rect.bottom - probeY));
      if (distance < bestDistance) {
        bestDistance = distance;
        best = section;
      }
    }
    return best;
  }

  function syncHeaderSurface() {
    queued = false;
    const section = sectionUnderHeader();
    const dark = Boolean(section?.classList.contains("dark"));
    header.classList.toggle("on-dark", dark);
    header.dataset.surface = dark ? "dark" : "light";
    header.dataset.section = section?.id || (section?.classList.contains("hero") ? "hero" : "section");
  }

  function scheduleHeaderSync() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(syncHeaderSurface);
  }

  window.addEventListener("scroll", scheduleHeaderSync, {passive: true});
  window.addEventListener("resize", scheduleHeaderSync, {passive: true});
  window.addEventListener("load", syncHeaderSurface, {once: true});
  document.addEventListener("DOMContentLoaded", () => {
    syncHeaderSurface();
    // Recheck after the original cockpit script has completed its own initial state work.
    setTimeout(syncHeaderSurface, 0);
    setTimeout(syncHeaderSurface, 120);
  }, {once: true});
})();
