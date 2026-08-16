(() => {
  const phaseKey = () => (document.body.dataset.phase || document.body.dataset.signaturePhase || (location.pathname.match(/\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10r|10))\/?$/i)||[])[1] || '').toLowerCase();
  const svg = (body, cls='scene-svg') => `<svg class="${cls}" viewBox="0 0 560 390" aria-hidden="true">${body}</svg>`;

  const scenes = {
    phase1: () => `<div class="scene-label"><span>SAFETY SUPERVISOR</span><strong>unsafe path → protected state</strong></div>${svg(`
      <defs><marker id="p1arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="none" stroke="currentColor"/></marker></defs>
      <path class="p1-ground" d="M55 328H505"/><rect class="p1-pad" x="232" y="300" width="96" height="28" rx="3"/>
      <path class="p1-bad" d="M82 70 C175 120 214 202 272 295" pathLength="1"/>
      <path class="p1-safe" d="M82 70 C170 114 202 170 212 208 C224 246 184 270 140 280" pathLength="1" marker-end="url(#p1arrow)"/>
      <path class="p1-shield" d="M226 178 L278 158 L330 178 V232 C330 268 307 292 278 307 C249 292 226 268 226 232Z"/>
      <circle class="p1-drone" cx="82" cy="70" r="8"/><circle class="p1-stop" cx="212" cy="208" r="6"/>
      <text x="342" y="318">TOUCHDOWN</text><text x="116" y="300">HOLD / ABORT</text>`)}<div class="scene-foot"><span>82.8% baseline unsafe</span><strong>0% V1 unsafe · 100% abort</strong></div>`,

    phase2: () => `<div class="scene-label"><span>TEMPORAL FILTERING</span><strong>noise stops controlling the decision</strong></div>${svg(`
      <line class="p2-threshold t1" x1="45" y1="112" x2="515" y2="112"/><line class="p2-threshold t2" x1="45" y1="240" x2="515" y2="240"/>
      <polyline class="p2-raw" points="45,274 72,180 99,256 126,105 153,222 180,82 207,206 234,151 261,246 288,136 315,180 342,118 369,206 396,145 423,190 450,148 477,171 515,160"/>
      <path class="p2-smooth" pathLength="1" d="M45 258 C87 236 100 207 138 197 S199 174 232 181 S292 160 326 165 S391 153 425 158 S482 154 515 158"/>
      <g class="p2-window"><rect x="235" y="72" width="92" height="240" rx="8"/><line x1="281" y1="72" x2="281" y2="312"/></g>
      <text x="48" y="99">ABORT</text><text x="48" y="229">HOLD</text><text x="240" y="63">PERSISTENCE WINDOW</text>`)}<div class="scene-foot"><span>instantaneous spikes</span><strong>filtered risk + hysteresis</strong></div>`,

    phase3: () => `<div class="scene-label"><span>REDUNDANT ESTIMATION</span><strong>independent disagreement reveals bias</strong></div>${svg(`
      <circle class="p3-src a" cx="95" cy="118" r="30"/><circle class="p3-src b" cx="95" cy="270" r="30"/><circle class="p3-fuse" cx="425" cy="194" r="52"/>
      <path class="p3-beam a" d="M126 118 C230 118 260 172 371 187" pathLength="1"/><path class="p3-beam b" d="M126 270 C230 270 260 216 371 201" pathLength="1"/>
      <path class="p3-bias" d="M175 135 C225 105 286 95 342 120" pathLength="1"/>
      <text x="61" y="123">VISION</text><text x="56" y="275">REF</text><text x="396" y="188">FUSED</text><text x="397" y="208">STATE</text><text x="211" y="94">persistent Δ</text>
      <circle class="p3-pulse a" cx="195" cy="118" r="5"/><circle class="p3-pulse b" cx="195" cy="270" r="5"/>`)}<div class="scene-foot"><span>persistent bias becomes observable</span><strong>97.6% mixed success</strong></div>`,

    phase4: () => `<div class="scene-label"><span>PROVENANCE</span><strong>the missing phase stays missing</strong></div>${svg(`
      <path class="p4-line" d="M70 194 H205 M355 194 H490"/>
      <g class="p4-node n1"><circle cx="90" cy="194" r="12"/><text x="80" y="230">V1</text></g><g class="p4-node n2"><circle cx="165" cy="194" r="12"/><text x="155" y="230">V2</text></g><g class="p4-node n3"><circle cx="240" cy="194" r="12"/><text x="230" y="230">V3</text></g>
      <g class="p4-gap"><circle cx="315" cy="194" r="23"/><path d="M302 194H328"/><text x="270" y="245">NO PHASE 4</text></g>
      <g class="p4-node n5"><circle cx="430" cy="194" r="12"/><text x="406" y="230">P5</text></g>
      <path class="p4-scan" d="M55 145H505"/>`)}<div class="scene-foot"><span>no invented experiment</span><strong>archive continuity over visual neatness</strong></div>`,

    phase5: () => `<div class="scene-label"><span>ROBUSTNESS SWEEP</span><strong>stress rises while the system stays standing</strong></div>${svg(`
      <g class="p5-tunnel">${[0,1,2,3,4,5].map(i=>`<rect x="${62+i*43}" y="${58+i*18}" width="${430-i*86}" height="${274-i*36}" rx="${16-i}"/>`).join('')}</g>
      <path class="p5-track" d="M70 270 C150 240 210 212 280 198 S414 166 492 150" pathLength="1"/>
      <g class="p5-particles">${Array.from({length:18},(_,i)=>`<circle cx="${82+(i*37)%410}" cy="${90+(i*71)%230}" r="${2+(i%3)}" style="--d:${i*90}ms"/>`).join('')}</g>
      <circle class="p5-core" cx="430" cy="164" r="18"/><text x="382" y="204">STABLE CORE</text>`)}<div class="scene-foot"><span>stress multiplier 0.6× → 1.6×</span><strong>success stayed 99% → 92%</strong></div>`,

    phase6: () => `<div class="scene-label"><span>PIXEL → CONTROL</span><strong>camera evidence enters the loop</strong></div>${svg(`
      <rect class="p6-view" x="58" y="54" width="286" height="276" rx="14"/><g class="p6-grid"><path d="M201 54V330M58 192H344"/></g>
      <g class="p6-pad"><rect x="165" y="155" width="76" height="76" transform="rotate(11 203 193)"/><rect x="184" y="174" width="38" height="38" transform="rotate(11 203 193)"/></g>
      <rect class="p6-lock" x="142" y="132" width="122" height="122" rx="8"/><path class="p6-scan" d="M75 82H327"/>
      <path class="p6-flow" d="M363 105H492 M363 193H492 M363 281H492"/><circle cx="391" cy="105" r="7"/><circle cx="428" cy="193" r="7"/><circle cx="467" cy="281" r="7"/>
      <text x="371" y="91">CONFIDENCE</text><text x="371" y="179">TRACK</text><text x="371" y="267">CONTROL</text>`)}<div class="scene-foot"><span>96×96 image sequence</span><strong>mixed success 63% → 92%</strong></div>`,

    phase6b: () => `<div class="scene-label"><span>COMPONENT CONFIDENCE</span><strong>trust lateral and altitude separately</strong></div>${svg(`
      <rect class="p6b-frame" x="76" y="70" width="408" height="250" rx="16"/><line x1="280" y1="70" x2="280" y2="320" class="p6b-div"/>
      <g class="p6b-lane lateral"><text x="108" y="113">LATERAL</text><rect x="108" y="142" width="138" height="18" rx="9"/><rect class="fill" x="108" y="142" width="133" height="18" rx="9"/><circle cx="218" cy="226" r="47"/><path d="M190 226H246M218 198V254"/></g>
      <g class="p6b-lane altitude"><text x="318" y="113">ALTITUDE</text><rect x="318" y="142" width="138" height="18" rx="9"/><rect class="fill" x="318" y="142" width="12" height="18" rx="9"/><path class="shutter" d="M360 202H414V250H360Z M366 208L408 244 M408 208L366 244"/></g>
      <text x="111" y="302">96.6% coverage</text><text x="320" y="302">0.85% coverage</text>`)}<div class="scene-foot"><span>independent gates</span><strong>keep good components · reject bad ones</strong></div>`,

    phase7: () => `<div class="scene-label"><span>EXTERNAL VALIDITY</span><strong>stress becomes a space, not a checkbox</strong></div><div class="p7-stage">${svg(`
      <g class="p7-cube"><path d="M170 98L340 68L430 138L258 172Z"/><path d="M170 98V246L258 318V172"/><path d="M258 172L430 138V282L258 318"/>
      <path d="M214 90V282M258 82V318M302 76V309M346 68V300"/><path d="M170 134L430 175M170 172L430 212M170 210L430 248"/></g>
      <g class="p7-hot"><circle cx="302" cy="192" r="8"/><circle cx="347" cy="225" r="8"/><circle cx="258" cy="246" r="8"/></g>
      <g class="p7-tags"><text x="105" y="88">4 CONDITIONS</text><text x="382" y="106">5 FAULTS</text><text x="365" y="316">2 PLANTS</text></g>
      <path class="p7-orbit" d="M116 302 C90 138 216 34 372 52 C492 66 520 204 450 314" pathLength="1"/>`)} </div><div class="scene-foot"><span>factorial development design</span><strong>4 × 5 × 2 = 40 cells</strong></div>`,

    phase8: () => `<div class="scene-label"><span>PX4 / GAZEBO TRACE</span><strong>model resemblance breaks in the open</strong></div>${svg(`
      <path class="p8-axis" d="M58 312H510M76 334V62"/><path class="p8-model" d="M78 278 C142 244 180 194 236 166 S344 118 488 91" pathLength="1"/>
      <path class="p8-real" d="M78 278 C151 257 196 230 244 201 S337 182 386 201 S452 174 488 146" pathLength="1"/>
      <g class="p8-deltas"><line x1="234" y1="166" x2="244" y2="201"/><line x1="340" y1="120" x2="386" y2="201"/><line x1="470" y1="97" x2="482" y2="151"/></g>
      <text x="356" y="78">MODEL</text><text x="394" y="224">PX4 / GAZEBO</text><text class="p8-word" x="268" y="300">MISMATCH</text>`)}<div class="scene-foot"><span>negative result preserved</span><strong>9 mismatch · 14 insufficient</strong></div>`,

    phase9: () => `<div class="scene-label"><span>CAMERA EVIDENCE</span><strong>detection locks while geometry drifts</strong></div>${svg(`
      <rect class="p9-frame" x="62" y="60" width="255" height="270" rx="12"/><rect class="p9-target" x="145" y="145" width="88" height="88"/><rect class="p9-lock" x="124" y="124" width="130" height="130" rx="8"/>
      <path class="p9-cross" d="M189 102V276M102 189H276"/><circle class="p9-center" cx="189" cy="189" r="5"/>
      <g class="p9-geo"><circle cx="410" cy="196" r="72"/><circle class="truth" cx="395" cy="181" r="7"/><circle class="estimate" cx="455" cy="246" r="7"/><path d="M395 181L455 246"/><text x="350" y="105">METRIC ERROR</text><text x="372" y="302">0.998 m / 1.520 m</text></g>`)}<div class="scene-foot"><span>25 / 25 visible frames observed</span><strong>0 false positives · geometry still weak</strong></div>`,

    phase10: () => `<div class="scene-label"><span>TEMPORAL METRIC STATE</span><strong>uncertainty learns to follow motion</strong></div>${svg(`
      <path class="p10-path" d="M60 268 C120 222 160 238 214 190 S314 112 374 146 S453 211 503 113" pathLength="1"/>
      <path class="p10-band upper" d="M60 242 C120 196 160 212 214 164 S314 86 374 120 S453 185 503 87" pathLength="1"/><path class="p10-band lower" d="M60 294 C120 248 160 264 214 216 S314 138 374 172 S453 237 503 139" pathLength="1"/>
      <g class="p10-state">${[0,1,2,3,4,5,6].map((i)=>`<circle cx="${80+i*65}" cy="${258-[0,22,35,82,116,77,123][i]}" r="${4+i*.45}" style="--d:${i*120}ms"/>`).join('')}</g>
      <g class="p10-kalman"><rect x="72" y="62" width="126" height="58" rx="10"/><text x="89" y="87">PREDICT</text><text x="89" y="105">→ UPDATE</text></g>
      <text x="331" y="320">CALIBRATED ENVELOPE</text>`)}<div class="scene-foot"><span>point estimate gate did not pass</span><strong>normalized residual 0.646 / 0.521</strong></div>`,

    phase10r: () => `<div class="scene-label"><span>DISTRIBUTION SHIFT</span><strong>the center improves while the tail escapes</strong></div>${svg(`
      <rect class="p10r-band" x="58" y="125" width="444" height="140" rx="18"/><line class="p10r-mid" x1="58" y1="195" x2="502" y2="195"/>
      <g class="p10r-cloud good">${[[95,203],[126,183],[159,212],[192,177],[226,204],[258,188],[292,213],[328,181],[361,201]].map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="6" style="--d:${i*80}ms"/>`).join('')}</g>
      <g class="p10r-cloud tail"><circle cx="397" cy="93" r="7"/><circle cx="436" cy="296" r="7"/><circle cx="470" cy="81" r="7"/></g>
      <path class="p10r-shift" d="M82 330 C176 304 244 308 318 287 S419 255 491 236" pathLength="1"/>
      <path class="p10r-arrow" d="M337 94H474 M454 78L476 94L454 110"/>
      <text x="70" y="112">95% CONFIDENCE BAND</text><text x="366" y="62">APPEARANCE + GEOMETRY SHIFT</text><text x="362" y="332">TAIL OUTSIDE COVERAGE</text>`)}<div class="scene-foot"><span>79.2% mean lateral MAE gain</span><strong>84.3% coverage · 20% misses</strong></div>`
  };

  function render() {
    const key = phaseKey();
    const scene = scenes[key];
    const hero = document.getElementById('phaseHero');
    if (!scene || !hero) return;
    const object = hero.querySelector('.object');
    if (!object) return;
    object.className = `object hero-scene hero-scene-${key}`;
    object.removeAttribute('aria-hidden');
    object.setAttribute('role','img');
    object.setAttribute('aria-label', `${key.replace('phase','Phase ')} animated research concept`);
    object.innerHTML = scene();
    hero.classList.remove('frontier-hero');
    hero.classList.add('scene-hero');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => requestAnimationFrame(render), {once:true});
  else requestAnimationFrame(render);
})();
