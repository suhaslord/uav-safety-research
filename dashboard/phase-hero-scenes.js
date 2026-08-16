(() => {
  const phaseKey = () => (document.body.dataset.phase || document.body.dataset.signaturePhase || (location.pathname.match(/\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10r|10))\/?$/i)||[])[1] || '').toLowerCase();
  const svg = (body) => `<svg class="scene-svg" viewBox="0 0 560 340" aria-hidden="true">${body}</svg>`;
  const shell = (eyebrow, title, body, left, right, micro='') => `
    <div class="scene-label"><span>${eyebrow}</span><strong>${title}</strong></div>
    <div class="scene-canvas">${body}${micro}</div>
    <div class="scene-foot"><span>${left}</span><strong>${right}</strong></div>`;

  const scenes = {
    phase1: () => shell(
      'SAFETY SUPERVISOR',
      'intercept risk before touchdown',
      svg(`
        <path class="p1-ground" d="M58 286H502"/><rect class="p1-pad" x="386" y="260" width="82" height="26" rx="4"/>
        <path class="p1-unsafe" d="M82 68 C176 96 270 170 410 258" pathLength="1"/>
        <path class="p1-divert" d="M82 68 C170 96 235 148 262 188 C278 214 236 242 164 246" pathLength="1"/>
        <path class="p1-shield" d="M248 151 L290 135 L332 151 V194 C332 225 312 246 290 258 C268 246 248 225 248 194Z"/>
        <g class="p1-vehicle"><path d="M-12 0H12M0-8V8"/><circle r="4"/></g>
        <g class="p1-risk"><circle cx="224" cy="158" r="5"/><circle cx="241" cy="174" r="3"/><circle cx="254" cy="188" r="2"/></g>
        <path class="p1-abort" d="M148 237l16 9-16 9"/>
      `),
      'baseline mixed unsafe: 82.8%',
      'V1 unsafe: 0% · abort: 100%',
      '<div class="scene-micro p1-micro"><span>approach</span><span>supervise</span><span>hold / abort</span></div>'
    ),

    phase2: () => shell(
      'TEMPORAL FILTERING',
      'persistent evidence beats a single bad frame',
      svg(`
        <line class="p2-grid" x1="52" y1="92" x2="508" y2="92"/><line class="p2-grid" x1="52" y1="242" x2="508" y2="242"/>
        <polyline class="p2-raw" points="52,255 80,172 108,238 136,104 164,217 192,83 220,205 248,143 276,227 304,128 332,174 360,121 388,197 416,141 444,179 472,149 508,163"/>
        <path class="p2-smooth" d="M52 244 C94 228 116 200 154 194 S214 173 250 179 S310 158 346 164 S408 153 448 158 S486 156 508 160" pathLength="1"/>
        <g class="p2-window"><rect x="0" y="58" width="104" height="238" rx="10"/><line x1="52" y1="58" x2="52" y2="296"/></g>
        <circle class="p2-state" cx="508" cy="160" r="7"/>
      `),
      'instantaneous spikes remain visible',
      'filtered risk + hysteresis drive state',
      '<div class="scene-micro p2-micro"><span>raw observation</span><span>persistence window</span><span>decision state</span></div>'
    ),

    phase3: () => shell(
      'REDUNDANT ESTIMATION',
      'independent disagreement makes bias observable',
      svg(`
        <g class="p3-sensor a"><circle cx="96" cy="108" r="34"/><path d="M82 108h28M96 94v28"/></g>
        <g class="p3-sensor b"><circle cx="96" cy="238" r="34"/><path d="M80 248l12-18 12 12 12-20"/></g>
        <path class="p3-beam a" d="M132 108 C225 108 265 144 376 163" pathLength="1"/>
        <path class="p3-beam b" d="M132 238 C225 238 265 198 376 177" pathLength="1"/>
        <g class="p3-comparator"><circle cx="421" cy="170" r="54"/><circle cx="421" cy="170" r="31"/><path d="M402 170h38M421 151v38"/></g>
        <path class="p3-delta" d="M170 116 C230 78 302 82 350 116"/>
        <circle class="p3-pulse a" cx="160" cy="108" r="5"/><circle class="p3-pulse b" cx="160" cy="238" r="5"/>
      `),
      'persistent delta becomes a signal',
      'mixed success: 97.6%',
      '<div class="scene-micro p3-micro"><span>vision estimate</span><span>reference estimate</span><span>fused state</span></div>'
    ),

    phase4: () => shell(
      'PROVENANCE',
      'a missing experiment stays visibly missing',
      svg(`
        <path class="p4-line left" d="M64 170H262"/><path class="p4-line right" d="M338 170H500"/>
        <g class="p4-node n1"><circle cx="96" cy="170" r="10"/></g><g class="p4-node n2"><circle cx="168" cy="170" r="10"/></g><g class="p4-node n3"><circle cx="240" cy="170" r="10"/></g>
        <g class="p4-gap"><circle cx="300" cy="170" r="28"/><path d="M285 170h30"/></g>
        <g class="p4-node n5"><circle cx="388" cy="170" r="10"/></g><g class="p4-node n6"><circle cx="460" cy="170" r="10"/></g>
        <path class="p4-scan" d="M54 105H506"/>
      `),
      'no synthetic Phase 4 evidence',
      'archive continuity > visual neatness',
      '<div class="scene-micro p4-micro"><span>V1</span><span>V2</span><span>V3</span><span class="gap">missing</span><span>P5</span><span>P6</span></div>'
    ),

    phase5: () => shell(
      'ROBUSTNESS SWEEP',
      'increase stress while watching the core trajectory survive',
      svg(`
        <g class="p5-rings"><rect x="58" y="52" width="444" height="236" rx="20"/><rect x="98" y="76" width="364" height="188" rx="17"/><rect x="138" y="100" width="284" height="140" rx="14"/><rect x="178" y="124" width="204" height="92" rx="12"/></g>
        <path class="p5-track" d="M75 238 C148 222 197 190 255 180 S368 151 486 122" pathLength="1"/>
        <g class="p5-stress">${Array.from({length:20},(_,i)=>`<circle cx="${76+(i*37)%410}" cy="${74+(i*61)%190}" r="${2+(i%3)}" style="--d:${i*75}ms"/>`).join('')}</g>
        <circle class="p5-core" cx="436" cy="136" r="18"/>
        <circle class="p5-core-ring" cx="436" cy="136" r="32"/>
      `),
      'stress multiplier: 0.6× → 1.6×',
      'success: 99% → 92%',
      '<div class="scene-micro p5-micro"><span>clean</span><span>blur</span><span>occlusion</span><span>mixed stress</span></div>'
    ),

    phase6: () => shell(
      'PIXEL → CONTROL',
      'camera evidence becomes a causal control input',
      svg(`
        <rect class="p6-view" x="54" y="48" width="292" height="244" rx="14"/><path class="p6-grid" d="M200 48V292M54 170H346"/>
        <g class="p6-target"><rect x="162" y="132" width="78" height="78" transform="rotate(10 201 171)"/><rect x="181" y="151" width="40" height="40" transform="rotate(10 201 171)"/></g>
        <rect class="p6-lock" x="137" y="107" width="128" height="128" rx="8"/><path class="p6-scan" d="M72 72H328"/>
        <path class="p6-flow" d="M366 96H500M366 170H500M366 244H500"/>
        <g class="p6-node n1"><circle cx="396" cy="96" r="9"/><circle cx="396" cy="96" r="18"/></g>
        <g class="p6-node n2"><circle cx="433" cy="170" r="9"/><circle cx="433" cy="170" r="18"/></g>
        <g class="p6-node n3"><circle cx="470" cy="244" r="9"/><circle cx="470" cy="244" r="18"/></g>
      `),
      '96×96 image sequence',
      'mixed success: 63% → 92%',
      '<div class="scene-micro p6-micro"><span>detect</span><span>confidence</span><span>track</span><span>control</span></div>'
    ),

    phase6b: () => shell(
      'COMPONENT CONFIDENCE',
      'trust lateral and altitude independently',
      svg(`
        <rect class="p6b-frame" x="70" y="54" width="420" height="232" rx="18"/><line class="p6b-div" x1="280" y1="54" x2="280" y2="286"/>
        <g class="p6b-lateral"><rect class="track" x="106" y="95" width="140" height="16" rx="8"/><rect class="fill" x="106" y="95" width="134" height="16" rx="8"/><circle cx="176" cy="186" r="44"/><path d="M150 186h52M176 160v52"/><path class="gate" d="M118 244h116"/></g>
        <g class="p6b-altitude"><rect class="track" x="316" y="95" width="140" height="16" rx="8"/><rect class="fill" x="316" y="95" width="13" height="16" rx="8"/><path class="shutter" d="M345 150h80v72h-80zM352 157l66 58M418 157l-66 58"/><path class="gate reject" d="M328 244h116"/></g>
      `),
      'lateral coverage: 96.6%',
      'altitude coverage: 0.85% → abstain',
      '<div class="scene-micro p6b-micro"><span>lateral: keep</span><span>altitude: reject</span></div>'
    ),

    phase7: () => shell(
      'EXTERNAL VALIDITY',
      'turn stress testing into a structured 3D space',
      `<div class="p7-stage">${svg(`
        <g class="p7-cube"><path d="M166 82L340 56L442 126L266 157Z"/><path d="M166 82V232L266 306V157"/><path d="M266 157L442 126V274L266 306"/>
        <path d="M210 75V264M254 68V297M298 62V300M342 56V292"/><path d="M166 120L442 165M166 158L442 204M166 196L442 243"/></g>
        <g class="p7-hot"><circle cx="304" cy="180" r="7"/><circle cx="351" cy="216" r="7"/><circle cx="260" cy="236" r="7"/><circle cx="397" cy="174" r="7"/></g>
        <path class="p7-orbit" d="M108 286 C82 132 214 27 376 45 C500 59 527 199 458 298" pathLength="1"/>
        <circle class="p7-probe" cx="108" cy="286" r="5"/>
      `)}</div>`,
      'factorial development design',
      '4 conditions × 5 faults × 2 plants = 40 cells',
      '<div class="scene-micro p7-micro"><span>conditions</span><span>faults</span><span>plant models</span></div>'
    ),

    phase8: () => shell(
      'PX4 / GAZEBO TRACE',
      'let the external simulator disagree visibly',
      svg(`
        <path class="p8-axis" d="M62 286H506M74 302V54"/>
        <path class="p8-model" d="M80 252 C144 221 184 178 238 151 S350 104 490 80" pathLength="1"/>
        <path class="p8-real" d="M80 252 C150 238 197 211 246 186 S337 169 388 190 S454 163 490 136" pathLength="1"/>
        <g class="p8-deltas"><line x1="238" y1="151" x2="246" y2="186"/><line x1="346" y1="106" x2="388" y2="190"/><line x1="472" y1="84" x2="484" y2="141"/></g>
        <circle class="p8-runner model" cx="80" cy="252" r="5"/><circle class="p8-runner real" cx="80" cy="252" r="5"/>
      `),
      'negative evidence remains first-class',
      '9 mismatch · 14 insufficient',
      '<div class="scene-micro p8-micro"><span>frozen model</span><span>external simulator</span><span>diagnostic mismatch</span></div>'
    ),

    phase9: () => shell(
      'CAMERA EVIDENCE',
      'perfect detection can coexist with weak metric geometry',
      svg(`
        <rect class="p9-frame" x="54" y="48" width="274" height="244" rx="14"/><rect class="p9-target" x="143" y="126" width="92" height="92"/><rect class="p9-lock" x="121" y="104" width="136" height="136" rx="8"/>
        <path class="p9-cross" d="M189 80V264M92 172H286"/><circle class="p9-center" cx="189" cy="172" r="5"/>
        <g class="p9-geo"><circle cx="425" cy="171" r="76"/><circle class="truth" cx="404" cy="148" r="7"/><circle class="estimate" cx="462" cy="222" r="7"/><path class="error" d="M404 148L462 222"/><circle class="p9-range" cx="404" cy="148" r="30"/></g>
      `),
      '25 / 25 visible frames observed · 0 FP',
      'geometry: 0.998 m lateral · 1.520 m altitude',
      '<div class="scene-micro p9-micro"><span>detection locked</span><span>truth</span><span>metric estimate drifts</span></div>'
    ),

    phase10: () => shell(
      'TEMPORAL METRIC STATE',
      'make uncertainty follow the evolving state',
      svg(`
        <path class="p10-envelope" d="M58 245 C112 205 159 218 212 174 C270 126 320 88 375 120 C424 148 458 177 504 91 L504 143 C458 229 424 200 375 172 C320 140 270 178 212 226 C159 270 112 257 58 297Z"/>
        <path class="p10-path" d="M58 271 C112 231 159 244 212 200 C270 152 320 114 375 146 C424 174 458 203 504 117" pathLength="1"/>
        <g class="p10-state">${[[78,257],[143,235],[208,204],[273,157],[338,131],[403,168],[468,151]].map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="${4+i*.35}" style="--d:${i*115}ms"/>`).join('')}</g>
        <g class="p10-filter"><rect x="62" y="58" width="132" height="54" rx="10"/><path d="M82 85h24l10-12 12 24 12-12h30"/></g>
        <circle class="p10-cursor" cx="58" cy="271" r="7"/>
      `),
      'point estimate gate: not passed',
      'normalized residual: 0.646 lateral · 0.521 altitude',
      '<div class="scene-micro p10-micro"><span>predict</span><span>update</span><span>calibrated envelope</span></div>'
    ),

    phase10r: () => shell(
      'FROZEN DISTRIBUTION SHIFT',
      'mean error improves while tail risk escapes coverage',
      svg(`
        <rect class="p10r-band" x="54" y="110" width="452" height="126" rx="20"/><line class="p10r-mid" x1="54" y1="173" x2="506" y2="173"/>
        <g class="p10r-good">${[[92,179],[126,162],[160,186],[194,153],[228,178],[263,165],[298,188],[333,158],[368,175]].map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="6" style="--d:${i*75}ms"/>`).join('')}</g>
        <g class="p10r-tail"><circle cx="405" cy="83" r="7"/><circle cx="443" cy="273" r="7"/><circle cx="477" cy="72" r="7"/></g>
        <path class="p10r-shift" d="M76 282 C168 270 248 275 321 252 S422 224 492 205" pathLength="1"/>
        <path class="p10r-arrow" d="M345 78H486M465 64l22 14-22 14"/>
        <g class="p10r-scan"><line x1="372" y1="72" x2="372" y2="278"/></g>
      `),
      'ambiguous lateral MAE gain: 79.2%',
      '95% coverage: 84.3% · truth-visible misses: 20.0%',
      '<div class="scene-micro p10r-micro"><span>center tightens</span><span>shift arrives</span><span>tail escapes</span></div>'
    )
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