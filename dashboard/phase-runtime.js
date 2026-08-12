const ORDER = ["phase1","phase2","phase3","phase4","phase5","phase6","phase6b","phase7","phase8","phase9","phase10"];

const DETAILS = {
  phase1: {
    problem: "The baseline controller could continue toward touchdown even when perception quality collapsed. The first question was whether a confidence-aware safety supervisor could suppress those unsafe simulated touchdowns without changing the landing controller itself.",
    goal: "Add an interpretable supervisory layer that turns risk and confidence into PROCEED, HOLD, or ABORT decisions, then measure safety and availability separately instead of treating every non-crash as success.",
    systemIntro: "V1 sits outside the controller. It watches the same perception estimate, computes instantaneous risk, and changes the allowed flight state when fixed thresholds are crossed.",
    architecture: ["Noisy perception estimate","Instantaneous risk + confidence","PROCEED / HOLD / ABORT supervisor","Landing controller","Simulated touchdown outcome"],
    architectureNote: "The architecture was intentionally simple and interpretable. That simplicity also made it reactive: one severe observation could dominate the decision.",
    evidenceStory: "V1 proved the safety supervisor could suppress severe unsafe-touchdown rates, but it often did so by refusing to complete the landing. The mixed profile is the clearest example: unsafe touchdowns went from 82.8% to 0%, while aborts went to 100%.",
    evidenceFacts: ["5,000 total episodes","500 episodes per profile/controller cell","Simple threshold sweeps could not recover mixed-profile availability"],
    limitations: ["Mixed degradation produced 100% aborts and 0% successful landings.","Occlusion still produced roughly 94.6% aborts.","Low light lost availability even though the baseline was already very safe.","Threshold retuning alone did not solve the safety-versus-availability tradeoff."],
    nextReason: "V2 needed temporal evidence, persistence, and hysteresis so the system would stop treating isolated bad measurements as a reason to hold or abort immediately.",
    visual: {kind:"bars",title:"Mixed degradation · V1 tradeoff",note:"Percent of paired simulated outcomes",items:[{label:"Baseline unsafe",value:82.8,text:"82.8%"},{label:"V1 unsafe",value:0,text:"0%"},{label:"V1 abort",value:100,text:"100%"}]}
  },
  phase2: {
    problem: "V1 protected safety by overreacting. The harder problem was to preserve landing availability without giving back the safety benefit whenever perception briefly became noisy or uncertain.",
    goal: "Use temporal filtering, persistence, hysteresis, and recovery-aware hold behavior so risk must remain bad over time before the supervisor escalates.",
    systemIntro: "V2 replaces instantaneous decision-making with a small temporal state machine. Risk is filtered, threshold crossings must persist, and separate entry/exit rules reduce rapid mode switching.",
    architecture: ["Instantaneous risk","Exponentially filtered risk","Persistence counter","Hysteresis + hold recovery","PROCEED / HOLD / ABORT"],
    architectureNote: "The redesign successfully fixed over-conservatism, but a temporally consistent sensor can still be consistently wrong.",
    evidenceStory: "Availability improved dramatically: low-light, occlusion, and mixed abort rates fell to 0%. But mixed degradation remained unresolved because persistent lateral bias survived temporal smoothing; V2's mixed unsafe-touchdown rate was 84.8%.",
    evidenceFacts: ["7,500 paired simulation episodes","Occlusion success improved from 66.2% baseline to 69.4% V2","Mixed unsafe remained about 84.8%"],
    limitations: ["Persistent systematic bias is not identifiable from a single corrupted stream.","Mixed degradation was slightly worse than baseline in this finite sample.","Low-light safety matched baseline rather than improving it.","Temporal consistency alone cannot tell vehicle offset from sensor bias."],
    nextReason: "V3 needed an independent second estimate with different error structure so persistent disagreement could reveal a visual bias that one stream could not diagnose by itself.",
    visual: {kind:"bars",title:"Abort-rate correction from V1 → V2",note:"Fixed paired evaluation",items:[{label:"Low-light V1 abort",value:18.2,text:"18.2%"},{label:"Low-light V2 abort",value:0,text:"0%"},{label:"Occlusion V1 abort",value:94.6,text:"94.6%"},{label:"Occlusion V2 abort",value:0,text:"0%"},{label:"Mixed V1 abort",value:100,text:"100%"},{label:"Mixed V2 abort",value:0,text:"0%"}]}
  },
  phase3: {
    problem: "V2 had only one corrupted observation stream. Under persistent bias, the stream could be smooth, confident, and wrong, leaving the supervisor with no independent clue that its geometry had shifted.",
    goal: "Introduce a lower-rate independent reference estimate, measure persistent cross-estimator disagreement, infer visual bias, and correct or fuse only when the evidence supports it.",
    systemIntro: "V3 creates two error paths. The visual estimate and the independent reference evolve with separate randomness, then a disagreement layer estimates bias before confidence-gated fusion and control.",
    architecture: ["Visual estimate","Independent reference estimate","Persistent disagreement","Bias estimate + confidence gate","Fused state","Controller + safety supervisor"],
    architectureNote: "The important feature is not that the reference is perfect — it is imperfect — but that its errors are independent enough to make systematic visual bias observable.",
    evidenceStory: "This was the first major architecture jump. On the frozen mixed benchmark, V3 moved from roughly 84% unsafe with baseline/V2 to 2.4% unsafe while keeping 97.6% success and 0% aborts.",
    evidenceFacts: ["10,000 total frozen episodes","Mixed success 97.6%","Occlusion success 98.6%"],
    limitations: ["The plant was still planar rather than full 6-DOF.","Perception stress was abstract instead of camera-derived.","The reference estimator was a surrogate, not a physical navigation stack.","The frozen result still came from one held-out seed family."],
    nextReason: "Phase 5 needed to try much harder to break V3 across new seeds, stronger stress, weaker references, dropout, bias magnitude, and the first actual image front end.",
    visual: {kind:"bars",title:"Mixed-profile unsafe touchdown",note:"Frozen paired benchmark",items:[{label:"Baseline",value:84.2,text:"84.2%"},{label:"V2",value:84.0,text:"84.0%"},{label:"V3",value:2.4,text:"2.4%"},{label:"V3 success",value:97.6,text:"97.6%"}]}
  },
  phase4: {
    problem: "There is no standalone Phase 4 experiment in the repository. The early program used V1, V2, and V3 naming, then resumed explicit numbered phases at Phase 5.",
    goal: "Keep the research lineage honest by showing the naming gap instead of inventing a missing experiment, metric, or result for visual continuity.",
    systemIntro: "This archive page is a provenance marker, not a synthetic research milestone.",
    architecture: ["Aegis V1","Aegis V2","Aegis V3","Naming gap","Phase 5 robustness"],
    architectureNote: "Nothing is being inferred or back-filled here. The gap itself is part of the project history.",
    evidenceStory: "The correct visual for this stage is an explicit break in the sequence. That makes the archive more trustworthy than forcing every integer to correspond to a fabricated experiment.",
    evidenceFacts: ["Standalone Phase 4 result: none","Invented metrics: 0","Next explicit numbered milestone: Phase 5"],
    limitations: ["There is no separate Phase 4 protocol to summarize.","There are no Phase 4 outcome metrics.","Any stronger claim would be an invented reconstruction rather than repository evidence."],
    nextReason: "The next real milestone was Phase 5, which stress-tested frozen V3 and introduced the first synthetic image-perception benchmark.",
    visual: {kind:"gap",title:"Research numbering",note:"The discontinuity is intentional",labels:["V1","V2","V3","—","5"]}
  },
  phase5: {
    problem: "V3 looked excellent on its frozen benchmark, but that did not prove the effect survived other random families, stronger degradation, weaker reference quality, heavy dropout, or a move from abstract measurements to pixels.",
    goal: "Stress-test the frozen V3 architecture broadly and introduce a simple 96×96 synthetic landing-pad image benchmark before putting image perception into the control loop.",
    systemIntro: "Phase 5 has two tracks: robustness sweeps around frozen V3, and a standalone image front end that converts rendered pad pixels into an interpretable lateral estimate and confidence value.",
    architecture: ["Frozen V3 supervisor","Seed / severity / bias / dropout sweeps","Synthetic 96×96 landing-pad renderer","Pixel estimator","Error + confidence audit"],
    architectureNote: "The controller was not retuned to the stress sweeps. The image benchmark was kept separate so its failure modes could be inspected before control integration.",
    evidenceStory: "V3 remained strong across five unseen mixed seed families and degraded gradually as stress increased. The new image estimator exposed a different problem: it returned a valid answer for 100% of images, even when mixed-condition errors were large.",
    evidenceFacts: ["Five unseen seed families: V3 mixed success averaged 97.6%","1,500 synthetic images","Mixed image MAE 0.344 m; p95 1.002 m; 100% marked valid"],
    limitations: ["Performance still depended meaningfully on reference quality and update rate.","The image renderer was simple and synthetic.","The first image estimator lacked meaningful abstention.","Confidence was directionally useful but not well calibrated under all conditions."],
    nextReason: "Phase 6 needed to calibrate image confidence, add temporal tracking/abstention/reacquisition, and finally put pixel-derived perception inside the landing loop.",
    visual: {kind:"line",title:"V3 success as mixed degradation strengthens",note:"Stress multiplier → V3 success",labels:["0.6×","0.8×","1.0×","1.2×","1.4×","1.6×"],values:[99,96,97,98,94,92],suffix:"%"}
  },
  phase6: {
    problem: "The project still relied on abstract corrupted state values for its strongest controller result, and Phase 5 showed that a naive pixel estimator could be wrong while still claiming its output was valid.",
    goal: "Build a complete synthetic image-sequence pipeline — calibration, temporal tracking, abstention, reacquisition, velocity estimation, redundant integrity checks — and let those image-derived measurements drive the simulated landing.",
    systemIntro: "Phase 6 is the first full pixel-to-control chain. Image sequences produce measurements, measurements are calibrated and tracked over time, and the resulting state drives Aegis plus the landing controller.",
    architecture: ["Synthetic image sequence","Pixel measurement","Confidence calibration","Temporal track + abstention + reacquisition","Robust lateral velocity","Cross-estimator integrity","Frozen V3 supervisor + controller"],
    architectureNote: "The pipeline can mitigate bad image measurements through temporal state and redundancy even when the frame-level abstention classifier is imperfect.",
    evidenceStory: "On held-out landings, image+Aegis improved mixed success from 63% to 92% and reduced mixed unsafe touchdowns from 37% to 7%. But the separate 10,000-frame audit showed the abstention mechanism itself was weak: 70.35% of mixed raw frames were outside target while only 1.20% were abstained.",
    evidenceFacts: ["1,000 held-out landing episodes","10,000 held-out selective-perception frames","Mixed image+Aegis: 92% success / 7% unsafe / 1% safe abort"],
    limitations: ["Frame-level abstention was not selective enough.","Some paired episodes regressed even though aggregate outcomes improved.","The imagery and vehicle model remained synthetic/planar.","Frame-level calibration targets were not perfectly aligned with system-level landing risk."],
    nextReason: "Phase 6B needed component-wise confidence so the system could keep trustworthy lateral information while rejecting unreliable altitude/scale, or vice versa.",
    visual: {kind:"bars",title:"Held-out image landing performance",note:"Success rates",items:[{label:"Mixed image-only",value:63,text:"63%"},{label:"Mixed image + Aegis",value:92,text:"92%"},{label:"Occlusion image-only",value:89,text:"89%"},{label:"Occlusion image + Aegis",value:96,text:"96%"}]}
  },
  phase6b: {
    problem: "One global confidence score could throw away useful lateral information because altitude was weak, or accept poor scale information because lateral localization looked good.",
    goal: "Split confidence into lateral and altitude components, add a renderer-specific altitude observability cap, and let the redundant reference replace only the rejected component.",
    systemIntro: "Phase 6B turns one perception decision into two. Lateral and altitude estimates each receive their own confidence gate and can independently fall back to the reference stream.",
    architecture: ["Image features","Lateral confidence","Altitude confidence + scale observability","Component gates 0.80 / 0.80","Selective reference takeover","Aegis + controller"],
    architectureNote: "A frame no longer has to be globally classified as good or bad. Different geometry components can take different paths through the system.",
    evidenceStory: "The frozen mixed result improved from 57% image-only success to 94% Phase 6 and 99% Phase 6B, with Phase 6B unsafe touchdowns at 1%. Altitude confidence became highly selective, while mixed lateral bad-estimate rejection remained weak.",
    evidenceFacts: ["1,500 held-out landing episodes","10,000 held-out selective-perception frames","Mixed altitude reference takeover ≈72%; low-light success 97% with 3% timeout"],
    limitations: ["Mixed lateral bad-estimate rejection recall was only 10.47%.","Low light paid a measurable completion/availability cost.","The altitude observability cap was specific to the synthetic renderer.","No common-mode real sensor failure or physical camera was validated."],
    nextReason: "Phase 7 needed to attack the assumptions underneath Phase 6B with asynchronous sensors, latency, stale state, common-mode faults, and stronger vehicle dynamics instead of tuning the frozen gates again.",
    visual: {kind:"bars",title:"Mixed degradation · success progression",note:"Held-out paired landing result",items:[{label:"Image-only",value:57,text:"57%"},{label:"Phase 6",value:94,text:"94%"},{label:"Phase 6B",value:99,text:"99%"},{label:"Phase 6B unsafe",value:1,text:"1%"}]}
  },
  phase7: {
    problem: "The strongest frozen result still lived inside a relatively clean timing model and simplified vehicle dynamics. That made it easy to confuse algorithm strength with simulator assumptions.",
    goal: "Stress external validity by separating sensor channels, adding asynchronous delivery/latency/staleness/common-mode faults, and comparing the legacy plant with a stronger plant without retuning Phase 6B.",
    systemIntro: "Phase 7 turns the simulator into a sensor-transport system: measurements are acquired, delayed, dropped, aged, and delivered on different schedules before they reach component-selective fusion and a more demanding plant.",
    architecture: ["Camera + GNSS-like lateral + barometer/range-like vertical sensors","Independent acquisition schedules","Packet delivery queue + latency + dropout","Component freshness + uncertainty growth","Frozen Phase 6B fusion","Legacy / stronger Phase 7 plant"],
    architectureNote: "The stronger plant adds actuator lag, acceleration-rate limits, nonlinear drag, and colored disturbances. Shared faults can affect channels together rather than pretending redundancy is always independent.",
    evidenceStory: "The accepted development factorial contained 4 conditions × 5 fault families × 2 plants × 5 episodes = 200 paired episodes. Weak cells under occlusion/mixed with shared lateral bias and some latency-burst cases were preserved as development evidence rather than used to retune the frozen model.",
    evidenceFacts: ["200 paired development episodes","40 condition/fault/plant cells","Development seed 979797 explicitly marked seen"],
    limitations: ["This was development evidence, not a held-out Phase 7 result.","Each factorial cell had only n=5 episodes.","The synthetic sensor distributions were still hand-modeled surrogates.","Observed weak cells could motivate validation, but not retroactive retuning of Phase 6B."],
    nextReason: "Phase 8 needed an external trace schema and genuine PX4/Gazebo evidence so the internal surrogate could be compared with a higher-fidelity simulator instead of only becoming more complicated internally.",
    visual: {kind:"matrix",title:"Phase 7 development factorial",note:"4 conditions × 5 faults × 2 plants",rows:["clean","low light","occlusion","mixed"],cols:["independent","drift","shared bias","shared drop","latency"],footer:"2 plants · 5 paired episodes per cell · 200 episodes total"}
  },
  phase8: {
    problem: "Even a sophisticated internal simulator can still be wrong in systematic ways. The project needed to measure whether its noise, latency, dropout, correlation, and dynamics resembled an outside simulator at all.",
    goal: "Create a simulator-independent trace format, freeze comparison thresholds, run a reproducible PX4 SITL + Gazebo mission, and preserve the comparison result even if it disagreed with the internal surrogate.",
    systemIntro: "Phase 8 converts both the Phase 7 surrogate and external PX4/Gazebo logs into the same trace schema, then compares their distributions with fixed diagnostics such as KS distance, Wasserstein distance, correlations, latency, and dropout structure.",
    architecture: ["Frozen Phase 7 surrogate trace","PX4 v1.17.0 + Gazebo mission","ULog → external trace adapter","Shared trace schema","Frozen comparison metrics","close / watch / mismatch / insufficient"],
    architectureNote: "The comparison layer was frozen before the final external evidence. Earlier failed PX4 attempts stayed diagnostic and were not promoted into evidence.",
    evidenceStory: "The completed external mission produced 41.772 seconds of ground-truth behavior. The unchanged comparison returned diagnostic_mismatch: 1 close, 2 watch, 9 mismatch, and 14 insufficient. The mismatch was preserved instead of tuned away.",
    evidenceFacts: ["PX4 v1.17.0 / gz_x500","41.772 s completed mission","1 close · 2 watch · 9 mismatch · 14 insufficient"],
    limitations: ["The standard gz_x500 run had no vehicle_visual_odometry samples, so image-model resemblance was unavailable.","PX4 vehicle_local_position is a fused estimator output, not statistically independent of every aiding source.","The result validated external model resemblance only within simulation.","The frozen result explicitly disallowed controller tuning from this evidence."],
    nextReason: "Phase 9 needed genuine Gazebo camera payloads and pose-linked image analysis because Phase 8 could compare navigation behavior but could not validate AegisLand's camera perception path.",
    visual: {kind:"bars",title:"Frozen Phase 8 comparison",note:"Diagnostic classifications",items:[{label:"Close",value:1,text:"1"},{label:"Watch",value:2,text:"2"},{label:"Mismatch",value:9,text:"9"},{label:"Insufficient",value:14,text:"14"}]}
  },
  phase9: {
    problem: "Phase 8 still had no genuine camera perception evidence. The project needed raw simulator image bytes, image hashes, correct camera-world pose provenance, and a metric geometry path that could be audited frame by frame.",
    goal: "Capture Gazebo camera frames, preserve raw payload provenance, detect the ArUco landing target with a fixed fallback path, and compare PnP-derived geometry against synchronized simulator truth.",
    systemIntro: "Phase 9 starts at the actual Gazebo camera payload. Every selected frame is traceable through hashes and timestamps before detection, fallback logic, PnP geometry, and comparison with synchronized world-pose truth.",
    architecture: ["Gazebo raw camera payload","Frame SHA-256 + timestamp","ArUco detector","Fixed quad fallback","Square-marker PnP geometry","Synchronized camera-pose truth + residual audit"],
    architectureNote: "A camera-pose provenance bug was found and corrected before the valid evidence run. The invalid first selected frame was excluded from the analyzed pose-linked set.",
    evidenceStory: "On the audited seen trace, 25 of 67 analyzed frames were truth-visible and all 25 produced observations with zero false positives. Detection looked excellent, but geometry did not: lateral MAE was 0.998 m and altitude MAE 1.520 m. Later analysis showed the seven quad-fallback measurements dominated the multi-meter errors.",
    evidenceFacts: ["67 pose-linked analyzed frames","25/25 truth-visible frames observed; 0 false positives","18 ArUco + 7 fixed quad fallback observations"],
    limitations: ["The evidence role was seen external perception, not a final unseen benchmark.","Fallback geometry could produce catastrophic metric error.","Reprojection-derived uncertainty was strongly overconfident.","This remained simulator-camera evidence, not physical-flight validation."],
    nextReason: "Phase 10 needed a frozen temporal metric estimator and source-aware uncertainty calibration to protect the state from ambiguous fallback geometry and make reported uncertainty more honest.",
    visual: {kind:"combo",title:"Phase 9 camera evidence",note:"Availability + geometry",primary:[{label:"Truth-visible",value:25,text:"25"},{label:"Observed",value:25,text:"25"},{label:"Not visible",value:42,text:"42"}],secondary:[{label:"Lateral MAE",value:0.998,text:"0.998 m"},{label:"Altitude MAE",value:1.520,text:"1.520 m"}]}
  },
  phase10: {
    problem: "Phase 9's catastrophic geometry errors were concentrated in ambiguous fallback measurements, while its uncertainty proxy was badly overconfident. A single-frame point estimate did not use temporal continuity to protect the metric state.",
    goal: "Freeze a causal temporal metric estimator before a new PX4/Gazebo trajectory, explicitly reject or predict through ambiguous fallback geometry, and calibrate uncertainty only from development evidence.",
    systemIntro: "AegisT10 preserves the Phase 9 camera front end, then adds a causal position/velocity state, innovation gating for ambiguous geometry, prediction semantics, and development-frozen source-aware uncertainty calibration.",
    architecture: ["Phase 9 camera front end","Metric observation + detector source","Causal lateral/altitude + velocity state","Innovation gate / reject / predict","Source-aware uncertainty calibration","Frozen paired holdout evaluation"],
    architectureNote: "The estimator, gates, calibration, and holdout trajectory were frozen before the final evidence was exposed. No parameter was changed after the holdout result was known.",
    evidenceStory: "The final holdout produced 15 usable observations, all ArUco and no accepted quad fallbacks. Phase 9 was already centimeter-accurate on those rows, so AegisT10 matched its point estimates and the preregistered substantial-win gate failed. The real improvement was uncertainty honesty: normalized residual medians fell from 13.17/5.11 to 0.646/0.521.",
    evidenceFacts: ["65 raw camera frames · 20 truth-visible · 15 observations","Paired lateral MAE: 0.0277 m for both Phase 9 and AegisT10","2σ coverage: 93.3% lateral / 100% altitude"],
    limitations: ["The holdout contained zero accepted quad-fallback observations, so it did not exercise the failure mode that drove the large development point-error gain.","Five of 20 truth-visible frames were missed by the unchanged front end.","The first holdout changed trajectory/view geometry but kept the same Gazebo world rather than testing a lighting/world domain shift.","The preregistered ≥50% MAE / ≥35% p95 improvement gate did not pass."],
    nextReason: "The next research step should broaden perception-domain coverage and preregister a challenge set that independently contains partial or ambiguous observations, while preserving this negative/mixed Phase 10 result.",
    visual: {kind:"bars",title:"Uncertainty honesty on the frozen holdout",note:"Median |residual| / reported sigma · lower is better",items:[{label:"Phase 9 lateral",value:13.17,text:"13.17"},{label:"AegisT10 lateral",value:0.646,text:"0.646"},{label:"Phase 9 altitude",value:5.11,text:"5.11"},{label:"AegisT10 altitude",value:0.521,text:"0.521"}]}
  }
};

const esc = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const href = key => `/phases/${key}/`;

function currentKey() {
  const match = location.pathname.match(/\/(phase(?:1|2|3|4|5|6|6b|7|8|9|10))\/?$/i);
  return (document.body.dataset.phase || (match && match[1]) || new URLSearchParams(location.search).get("phase") || "phase10").toLowerCase();
}

function phaseNumber(label) {
  const match = String(label).match(/(?:Phase\s+)?(\d+[A-Z]?)/i);
  return match ? match[1].toUpperCase() : "—";
}

function renderRail(key) {
  const root = document.getElementById("phaseRail");
  if (!root) return;
  root.innerHTML = ORDER.map((item, index) => {
    const data = PHASES[item];
    const active = item === key;
    const gap = item === "phase4";
    return `<a class="rail-step${active ? " active" : ""}${gap ? " gap" : ""}" href="${href(item)}" aria-current="${active ? "page" : "false"}"><span>${String(index + 1).padStart(2,"0")}</span><i></i><strong>${esc(data.label.replace(" · ","\n"))}</strong></a>`;
  }).join("");
}

function renderConceptVisual(key, data, detail) {
  const root = document.getElementById("phaseOverviewVisual");
  if (!root) return;
  const number = phaseNumber(data.label);
  const nodes = detail.architecture.slice(0, 5).map((step, i) => `<span class="concept-node n${i + 1}"><b>${String(i + 1).padStart(2,"0")}</b><em>${esc(step)}</em></span>`).join("");
  root.innerHTML = `<figcaption><span>System signature</span><strong>${esc(data.era)}</strong></figcaption><div class="concept-object"><div class="concept-rings" aria-hidden="true"><i></i><i></i><i></i></div><div class="concept-number">${esc(number)}</div>${nodes}</div>`;
  root.dataset.phase = key;
}

function renderBars(visual) {
  const max = Math.max(1, ...visual.items.map(item => Number(item.value) || 0));
  return `<div class="viz-bars">${visual.items.map((item, index) => {
    const pct = Math.max(0, Math.min(100, (Number(item.value) || 0) / max * 100));
    return `<div class="viz-row" style="--delay:${index * 70}ms"><div class="viz-label"><span>${esc(item.label)}</span><strong>${esc(item.text ?? item.value)}</strong></div><div class="viz-track"><i class="viz-fill" style="--w:${pct}%"></i></div></div>`;
  }).join("")}</div>`;
}

function renderLine(visual) {
  const values = visual.values.map(Number);
  const width = 620, height = 260, padX = 34, padY = 30;
  const max = Math.max(...values), min = Math.min(...values);
  const span = Math.max(1, max - min);
  const points = values.map((value, index) => {
    const x = padX + index * (width - padX * 2) / Math.max(1, values.length - 1);
    const y = padY + (max - value) / span * (height - padY * 2);
    return {x,y,value,label:visual.labels[index]};
  });
  const poly = points.map(point => `${point.x},${point.y}`).join(" ");
  return `<div class="viz-line"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(visual.title)}"><g class="grid">${[0,1,2,3].map(i => `<line x1="${padX}" y1="${padY + i * (height - padY * 2) / 3}" x2="${width - padX}" y2="${padY + i * (height - padY * 2) / 3}"></line>`).join("")}</g><polyline class="data-line" pathLength="1" points="${poly}"></polyline>${points.map(point => `<circle cx="${point.x}" cy="${point.y}" r="4"></circle><text x="${point.x}" y="${height - 8}" text-anchor="middle">${esc(point.label)}</text><text class="value" x="${point.x}" y="${point.y - 12}" text-anchor="middle">${esc(point.value)}${esc(visual.suffix || "")}</text>`).join("")}</svg></div>`;
}

function renderMatrix(visual) {
  return `<div class="viz-matrix"><div class="matrix-cols">${visual.cols.map(col => `<span>${esc(col)}</span>`).join("")}</div>${visual.rows.map((row, r) => `<div class="matrix-row"><strong>${esc(row)}</strong><div class="matrix-cells">${visual.cols.map((_, c) => `<i style="--cell-delay:${(r * visual.cols.length + c) * 24}ms"></i>`).join("")}</div></div>`).join("")}<p>${esc(visual.footer || "")}</p></div>`;
}

function renderGap(visual) {
  return `<div class="viz-gap">${visual.labels.map((label, index) => `<span class="${label === "—" ? "missing" : ""}"><b>${esc(label)}</b><i></i></span>`).join("")}</div>`;
}

function renderCombo(visual) {
  const first = renderBars({items:visual.primary});
  const second = renderBars({items:visual.secondary});
  return `<div class="viz-combo"><section><span>Frame evidence</span>${first}</section><section><span>Metric geometry</span>${second}</section></div>`;
}

function renderEvidenceVisual(detail) {
  const root = document.getElementById("phaseEvidenceVisual");
  if (!root || !detail.visual) return;
  const visual = detail.visual;
  let body = "";
  if (visual.kind === "bars") body = renderBars(visual);
  else if (visual.kind === "line") body = renderLine(visual);
  else if (visual.kind === "matrix") body = renderMatrix(visual);
  else if (visual.kind === "gap") body = renderGap(visual);
  else if (visual.kind === "combo") body = renderCombo(visual);
  root.innerHTML = `<figcaption><span>${esc(visual.title)}</span><strong>${esc(visual.note || "")}</strong></figcaption>${body}`;
}

function renderArchitecture(detail) {
  const root = document.getElementById("phaseArchitecture");
  if (!root) return;
  root.innerHTML = detail.architecture.map((step, index) => `<div class="arch-step" style="--delay:${index * 60}ms"><span>${String(index + 1).padStart(2,"0")}</span><strong>${esc(step)}</strong>${index < detail.architecture.length - 1 ? "<i>→</i>" : ""}</div>`).join("");
}

function renderPhase() {
  const hero = document.getElementById("phaseHero");
  if (!hero) return;
  const key = currentKey();
  const data = PHASES[key];
  const detail = DETAILS[key];
  if (!data || !detail) return;

  document.title = `${data.label} — AegisLand`;
  hero.innerHTML = `<div class="hero-copy"><p class="kicker">${esc(data.era)} · AegisLand research archive</p><h1>${esc(data.label)}</h1><p class="deck">${esc(data.title)}</p><p class="lede">${esc(data.lede)}</p><div class="actions"><a class="button blue" href="#snapshot">Explore the case study</a><a class="button ash" href="${esc(data.sourceUrl)}" target="_blank" rel="noreferrer">Open source ↗</a></div></div><div class="object" aria-hidden="true"><span class="frame"></span><span class="axis x"></span><span class="axis y"></span><span class="node n1"></span><span class="node n2"></span><span class="scan"></span><strong>${esc(phaseNumber(data.label))}</strong></div><div class="hero-meta"><span>${esc(data.status)}</span><span>${esc(data.role)}</span></div>`;

  renderRail(key);
  renderConceptVisual(key, data, detail);
  renderEvidenceVisual(detail);
  renderArchitecture(detail);

  const problem = document.getElementById("phaseProblem");
  if (problem) problem.textContent = detail.problem;
  const goal = document.getElementById("phaseGoal");
  if (goal) goal.textContent = detail.goal;
  const systemIntro = document.getElementById("systemIntro");
  if (systemIntro) systemIntro.textContent = detail.systemIntro;
  const architectureNote = document.getElementById("architectureNote");
  if (architectureNote) architectureNote.textContent = detail.architectureNote;
  const evidenceStory = document.getElementById("phaseEvidenceStory");
  if (evidenceStory) evidenceStory.textContent = detail.evidenceStory;
  const facts = document.getElementById("evidenceFacts");
  if (facts) facts.innerHTML = detail.evidenceFacts.map((fact, index) => `<div><span>${String(index + 1).padStart(2,"0")}</span><p>${esc(fact)}</p></div>`).join("");

  const changes = document.getElementById("changeList");
  if (changes) changes.innerHTML = data.change.map((change, index) => `<article><span>${String(index + 1).padStart(2,"0")}</span><h3>${esc(change)}</h3></article>`).join("");

  const shift = document.getElementById("phaseShift");
  if (shift) shift.innerHTML = `<div><p class="kicker">Before</p><h2>${esc(data.before)}</h2></div><div><p class="kicker">After</p><h2>${esc(data.after)}</h2></div>`;

  const metrics = document.getElementById("phaseMetrics");
  if (metrics) metrics.innerHTML = data.metrics.map(([label,value], index) => `<article class="metric-card" style="--delay:${index * 70}ms"><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join("");

  const limits = document.getElementById("phaseLimitations");
  if (limits) limits.innerHTML = detail.limitations.map((item, index) => `<li><span>${String(index + 1).padStart(2,"0")}</span><p>${esc(item)}</p></li>`).join("");

  const finding = document.getElementById("phaseFinding");
  if (finding) finding.textContent = data.finding;
  const nextReason = document.getElementById("phaseNextReason");
  if (nextReason) nextReason.textContent = detail.nextReason;
  const source = document.getElementById("phaseSource");
  if (source) {
    source.href = data.sourceUrl;
    const strong = source.querySelector("strong");
    if (strong) strong.textContent = data.source;
  }

  const index = ORDER.indexOf(key);
  const prev = document.getElementById("prevPhase");
  const next = document.getElementById("nextPhase");
  if (prev) {
    if (index > 0) {
      const previous = ORDER[index - 1];
      prev.href = href(previous);
      prev.textContent = `← ${PHASES[previous].label}`;
    } else prev.hidden = true;
  }
  if (next) {
    if (index < ORDER.length - 1) {
      const upcoming = ORDER[index + 1];
      next.href = href(upcoming);
      next.innerHTML = `<span>Next research step</span><strong>${esc(PHASES[upcoming].label)}</strong><i>→</i>`;
    } else {
      next.href = "/";
      next.innerHTML = `<span>Current research cockpit</span><strong>AegisLand</strong><i>→</i>`;
    }
  }
}

function renderIndex() {
  const root = document.getElementById("archiveMap");
  if (!root) return;
  const eras = [];
  for (const key of ORDER) {
    const data = PHASES[key];
    let era = eras.find(item => item.name === data.era);
    if (!era) {
      era = {name:data.era,keys:[]};
      eras.push(era);
    }
    era.keys.push(key);
  }
  root.innerHTML = eras.map((era, index) => `<section class="era"><header><span>${String(index + 1).padStart(2,"0")}</span><h2>${esc(era.name)}</h2></header><div class="track">${era.keys.map(key => {const data = PHASES[key]; return `<a class="phase-link" href="${href(key)}"><span>${esc(data.label)}</span><strong>${esc(data.title)}</strong><small>${esc(data.status)}</small><i>→</i></a>`;}).join("")}</div></section>`).join("");
}

function motion() {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const bar = document.getElementById("archiveProgress");
  const progress = () => {
    if (!bar) return;
    const max = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${max > 0 ? scrollY / max : 0})`;
  };
  addEventListener("scroll", progress, {passive:true});
  progress();

  if (reduced) {
    document.querySelectorAll("[data-reveal]").forEach(node => node.classList.add("visible"));
    document.body.classList.add("motion-reduced");
    return;
  }

  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    entry.target.classList.add("visible");
    entry.target.querySelectorAll?.(".viz-fill,.arch-step,.metric-card,.matrix-cells i").forEach(node => node.classList.add("animate"));
    observer.unobserve(entry.target);
  }), {threshold:.14, rootMargin:"0px 0px -6% 0px"});
  document.querySelectorAll("[data-reveal]").forEach(node => observer.observe(node));

  addEventListener("pointermove", event => {
    const object = document.querySelector(".object");
    if (!object) return;
    object.style.setProperty("--px", `${(event.clientX / innerWidth - .5) * 8}px`);
    object.style.setProperty("--py", `${(event.clientY / innerHeight - .5) * 8}px`);
  }, {passive:true});
}

function loader() {
  const boot = document.getElementById("archiveBoot");
  if (!boot) return;
  const started = performance.now();
  const done = () => setTimeout(() => {
    boot.classList.add("leave");
    setTimeout(() => boot.remove(), 350);
  }, Math.max(0, 650 - (performance.now() - started)));
  document.readyState === "complete" ? done() : addEventListener("load", done, {once:true});
}

document.addEventListener("DOMContentLoaded", () => {
  renderPhase();
  renderIndex();
  motion();
  loader();
});