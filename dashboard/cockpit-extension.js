(() => {
  const header = document.getElementById("siteHeader");
  if (!header) return;

  let queued = false;
  let loaderStartedAt = performance.now();

  function installBrandPolish() {
    if (!document.getElementById("aegisBrandPolish")) {
      const style = document.createElement("style");
      style.id = "aegisBrandPolish";
      style.textContent = `
        .aegis-boot {
          position: fixed;
          inset: 0;
          z-index: 9999;
          display: grid;
          place-items: center;
          background: #ffffff;
          color: #171a20;
          opacity: 1;
          visibility: visible;
          transition: opacity .33s cubic-bezier(.5,0,0,.75), visibility .33s;
        }
        .aegis-boot.is-leaving { opacity: 0; visibility: hidden; }
        .aegis-boot-inner {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 18px;
        }
        .aegis-boot-brand,
        .hero-brand-lockup {
          display: inline-flex;
          align-items: center;
          gap: 12px;
        }
        .aegis-boot-mark,
        .hero-brand-mark {
          width: 40px;
          height: 40px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
          background: #171a20;
          color: #ffffff;
          font-size: 18px;
          line-height: 1;
          font-weight: 500;
        }
        .aegis-boot-word,
        .hero-brand-word {
          color: #171a20;
          font-size: 14px;
          line-height: 20px;
          font-weight: 500;
          letter-spacing: .26em;
        }
        .aegis-boot-status {
          margin: 0;
          color: #5c5e62;
          font-size: 12px;
          line-height: 18px;
        }
        .hero-intro > div:first-child {
          position: relative;
          max-width: 500px !important;
          padding: 28px 30px 30px;
          border-radius: 4px;
          background: rgba(255,255,255,.90);
          color: #171a20;
        }
        .hero-brand-lockup { margin: 2px 0 18px; }
        .hero-brand-mark { width: 36px; height: 36px; font-size: 16px; }
        .hero-brand-word { font-size: 13px; }
        .hero-intro h1,
        .hero-intro .kicker,
        .hero-intro .hero-subtitle { color: #171a20 !important; }
        .hero-intro .hero-subtitle { opacity: .88; }
        .hero-intro .kicker { color: #5c5e62 !important; }
        @media (max-width: 767px) {
          .hero-intro > div:first-child {
            padding: 22px 22px 24px;
            background: rgba(255,255,255,.94);
          }
          .hero-brand-mark { width: 32px; height: 32px; font-size: 15px; }
          .hero-brand-word { font-size: 11px; letter-spacing: .22em; }
          .aegis-boot-mark { width: 38px; height: 38px; }
          .aegis-boot-word { font-size: 13px; letter-spacing: .22em; }
        }
        @media (prefers-reduced-motion: reduce) {
          .aegis-boot { transition-duration: .01ms !important; }
        }
      `;
      document.head.appendChild(style);
    }

    if (!document.querySelector(".aegis-boot")) {
      const loader = document.createElement("div");
      loader.className = "aegis-boot";
      loader.setAttribute("role", "status");
      loader.setAttribute("aria-live", "polite");
      loader.innerHTML = `
        <div class="aegis-boot-inner">
          <div class="aegis-boot-brand" aria-label="AegisLand">
            <span class="aegis-boot-mark" aria-hidden="true">A</span>
            <span class="aegis-boot-word">AEGISLAND</span>
          </div>
          <p class="aegis-boot-status">Loading audited research cockpit…</p>
        </div>`;
      document.body.prepend(loader);
      loaderStartedAt = performance.now();
    }

    const heroContent = document.querySelector(".hero-intro > div:first-child");
    if (heroContent && !heroContent.querySelector(".hero-brand-lockup")) {
      const lockup = document.createElement("div");
      lockup.className = "hero-brand-lockup";
      lockup.setAttribute("aria-label", "AegisLand brand mark");
      lockup.innerHTML = `<span class="hero-brand-mark" aria-hidden="true">A</span><span class="hero-brand-word">AEGISLAND</span>`;
      const title = heroContent.querySelector("h1");
      if (title) heroContent.insertBefore(lockup, title);
      else heroContent.prepend(lockup);
    }
  }

  function releaseLoader() {
    const loader = document.querySelector(".aegis-boot");
    if (!loader || loader.dataset.releaseScheduled === "true") return;
    loader.dataset.releaseScheduled = "true";
    const elapsed = performance.now() - loaderStartedAt;
    const wait = Math.max(0, 900 - elapsed);
    window.setTimeout(() => {
      loader.classList.add("is-leaving");
      window.setTimeout(() => loader.remove(), 360);
    }, wait);
  }

  installBrandPolish();

  function sectionUnderHeader() {
    const sections = [...document.querySelectorAll("main .viewport-section")];
    if (!sections.length) return null;

    const headerRect = header.getBoundingClientRect();
    const probeY = Math.min(window.innerHeight - 1, Math.max(1, headerRect.bottom + 2));

    for (const section of sections) {
      const rect = section.getBoundingClientRect();
      if (rect.top <= probeY && rect.bottom > probeY) return section;
    }

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

  function enhanceLineage() {
    const source = document.querySelector(".lineage-list");
    if (!source || source.dataset.enhanced === "true") return;

    const items = [...source.children].filter(node => node.tagName === "LI");
    if (items.length < 11) return;

    const eras = [
      {
        number: "01",
        title: "Foundation",
        description: "Protocol through the frozen V1–V3 supervisor evolution.",
        items: items.slice(0, 4)
      },
      {
        number: "02",
        title: "Perception + robustness",
        description: "Stress testing, image perception, and the frozen Phase 6B study.",
        items: items.slice(4, 7)
      },
      {
        number: "03",
        title: "External validation",
        description: "Development stress, trace validation, and genuine PX4/Gazebo evidence.",
        items: items.slice(7, 10)
      },
      {
        number: "04",
        title: "Current frontier",
        description: "Phase 9 camera evidence remains draft, seen, and explicitly non-safety-accepted.",
        items: items.slice(10, 11),
        current: true
      }
    ];

    const map = document.createElement("div");
    map.className = "lineage-map";
    map.setAttribute("aria-label", "AegisLand research lineage by era");

    eras.forEach(era => {
      const section = document.createElement("section");
      section.className = `lineage-era${era.current ? " lineage-era-current" : ""}`;

      const heading = document.createElement("div");
      heading.className = "lineage-era-heading";
      heading.innerHTML = `<span>${era.number}</span><h3>${era.title}</h3><p>${era.description}</p>`;

      const list = document.createElement("ol");
      list.className = "lineage-era-list";
      list.style.setProperty("--era-count", String(Math.max(1, era.items.length)));
      era.items.forEach(item => list.appendChild(item));

      section.append(heading, list);
      map.appendChild(section);
    });

    source.dataset.enhanced = "true";
    source.replaceWith(map);
  }

  function buildMobileMenu() {
    if (document.querySelector(".mobile-menu-toggle")) return;

    const toggle = document.createElement("button");
    toggle.className = "mobile-menu-toggle";
    toggle.type = "button";
    toggle.textContent = "Menu";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", "mobileMenuSheet");
    header.appendChild(toggle);

    const sheet = document.createElement("nav");
    sheet.className = "mobile-menu-sheet";
    sheet.id = "mobileMenuSheet";
    sheet.setAttribute("aria-label", "Mobile navigation");
    sheet.innerHTML = `
      <div class="mobile-menu-head">
        <span class="mobile-menu-brand">AEGISLAND</span>
        <button class="mobile-menu-close" type="button" aria-label="Close menu">Close</button>
      </div>
      <div class="mobile-menu-primary">
        <a href="#result">Result</a>
        <a href="#telemetry">Telemetry</a>
        <a href="#geometry">Geometry</a>
        <a href="#timeline">Lineage</a>
        <a href="#provenance">Provenance</a>
      </div>
      <div class="mobile-menu-secondary">
        <a href="https://github.com/suhaslord/uav-safety-research" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://www.linkedin.com/in/suhas-beemineni-1984763b8/" target="_blank" rel="noreferrer">LinkedIn</a>
        <a href="phase7.html">Phase 7</a>
        <button type="button" data-mobile-status>Status</button>
      </div>`;
    document.body.appendChild(sheet);

    const closeButton = sheet.querySelector(".mobile-menu-close");
    const mobileStatus = sheet.querySelector("[data-mobile-status]");
    const desktopStatus = document.getElementById("refreshStatus");

    const setOpen = open => {
      sheet.classList.toggle("is-open", open);
      document.body.classList.toggle("mobile-menu-open", open);
      toggle.setAttribute("aria-expanded", String(open));
      if (open) {
        requestAnimationFrame(() => closeButton?.focus());
      } else {
        toggle.focus({preventScroll: true});
      }
    };

    toggle.addEventListener("click", () => setOpen(!sheet.classList.contains("is-open")));
    closeButton?.addEventListener("click", () => setOpen(false));
    sheet.querySelectorAll("a").forEach(link => link.addEventListener("click", () => setOpen(false)));
    mobileStatus?.addEventListener("click", () => {
      desktopStatus?.click();
      setOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && sheet.classList.contains("is-open")) setOpen(false);
    });
    window.matchMedia("(min-width: 768px)").addEventListener("change", event => {
      if (event.matches && sheet.classList.contains("is-open")) setOpen(false);
    });
  }

  window.addEventListener("scroll", scheduleHeaderSync, {passive: true});
  window.addEventListener("resize", scheduleHeaderSync, {passive: true});
  window.addEventListener("load", () => {
    syncHeaderSurface();
    releaseLoader();
  }, {once: true});
  document.addEventListener("DOMContentLoaded", () => {
    syncHeaderSurface();
    enhanceLineage();
    buildMobileMenu();
    releaseLoader();
    setTimeout(syncHeaderSurface, 0);
    setTimeout(syncHeaderSurface, 120);
  }, {once: true});
})();