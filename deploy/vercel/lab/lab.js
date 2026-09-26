(async () => {
  'use strict';
  const State=await import('/lab/state.mjs?v=1');
  const catalog = {
    phase1:['Safety gate','landing'], phase2:['Temporal supervision','landing'], phase3:['Independent reference','landing'], phase4:['Provenance gap','gap'], phase5:['Robustness stress test','landing'],
    phase6:['Image perception','camera'], phase6b:['Component observability','camera'], phase7:['Plant mismatch','dynamics'], phase8:['Trace discrepancy','trace'], phase9:['Camera evidence diagnostic','trace'], phase10:['Temporal estimator','temporal'], phase10r:['Estimator under shift','temporal'],
    phase11:['Reliability and coverage','uncertainty'], phase12:['Normalized uncertainty','uncertainty'], phase13a:['External-validity shift','uncertainty'], phase13b:['Paired degradation','uncertainty'], phase13c:['Staleness attribution','uncertainty'],
    phase14:['Recoverability bound','residual'], phase15:['Feasibility frontier','residual'], phase16:['Latency and level error','residual'], phase17:['Coefficient mismatch','residual'], phase18:['Residual comparison','residual'], phase19:['Distribution-wide residuals','residual'],
    phase20:['Shapley attenuation','context'], phase21:['Context spectrum','context'], phase22:['Additive transfer','context']
  };
  const fields = {
    seed:['Random seed',2026,0,2147483647,1], samples:['Samples',128,32,1024,32], episodes:['Paired episodes',3,1,10,1], offset:['Lateral offset (m)',1.5,-3,3,.1], altitude:['Altitude (m)',6,1,10,.5], noise:['Noise scale (m)',.15,.01,2,.01], bias:['Bias (m)',.3,-2,2,.05], dropout:['Dropout probability',.1,0,.8,.05], severity:['Degradation severity',1,.1,3,.1], lag:['Staleness (frames)',2,0,12,1], tau:['Actuator lag (s)',.24,.05,2,.01], coefficient:['Reference coefficient',.65,-.95,.95,.05], alternative:['Alternative coefficient',.85,-.95,.95,.05], coverage:['Target coverage',.95,.6,.99,.01], shift:['Test noise multiplier',2,1,5,.1], radius:['Interval half-width (m)',1,.1,5,.1], interaction:['Edge × oblique interaction',.04,0,.3,.01], edge:['Edge effect',.04,0,.2,.005], oblique:['Oblique effect',.03,0,.2,.005], dim:['Dim-light effect',.025,0,.2,.005], blur_noise:['Blur / noise effect',.035,0,.2,.005], low_contrast:['Low-contrast effect',.02,0,.2,.005]
  };
  const groups = {
    landing:['condition','episodes','offset','altitude','noise','bias','dropout','seed'], camera:['condition','samples','offset','altitude','severity','seed'], dynamics:['samples','tau','severity','altitude','seed'], trace:['samples','noise','bias','shift','seed'], temporal:['samples','offset','altitude','noise','dropout','seed'], uncertainty:['samples','noise','bias','coverage','shift','seed'], residual:['samples','noise','lag','coefficient','alternative','coverage','radius','seed'], context:['edge','oblique','dim','blur_noise','low_contrast','interaction','noise','seed']
  };
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label = s => 'Phase ' + s.slice(5).toUpperCase();
  const fmt = v => typeof v === 'number' ? new Intl.NumberFormat('en-US',{maximumFractionDigits:4}).format(v) : v === null ? 'Unavailable' : String(v);
  const colors = ['#3457b2','#171a20','#9a6225'];
  let phase = document.body.dataset.phase || location.pathname.match(/(?:\/phases\/|\/)(phase\d+[a-z]*)(?:\/|\.html|$)/i)?.[1]?.toLowerCase() || new URLSearchParams(location.search).get('phase') || 'phase1';
  if (!catalog[phase]) phase = 'phase1';
  let worker, requestId=0, result=null, timer, busy=false, stacks={},stackId=0, guideStep=0, previousByKey={};

  const questions = {
    phase1:'Can a safety check stop a bad landing?', phase2:'Does looking at recent readings help?', phase3:'Can a second opinion catch a mistake?', phase4:'Why is this research step missing?', phase5:'What happens when the camera struggles?',
    phase6:'Can the camera find the landing pad?', phase6b:'Does a confident reading deserve our trust?', phase7:'What if the drone reacts more slowly?', phase8:'How different are two sets of errors?', phase9:'How much can camera errors matter?', phase10:'Can recent readings improve a position estimate?', phase10r:'What happens when the measurements get worse?',
    phase11:'How often does an error range cover the truth?', phase12:'Can we adjust an error range to the conditions?', phase13a:'Does an error range still work in new conditions?', phase13b:'How much does coverage fall in new conditions?', phase13c:'What happens when readings arrive late?',
    phase14:'How wide must the allowed error range be?', phase15:'Is the chosen error range wide enough?', phase16:'How do old readings affect the next error?', phase17:'What if our error model has the wrong setting?', phase18:'Which of two error models fits better?', phase19:'How do the two models compare across many errors?',
    phase20:'Which conditions contribute to the change?', phase21:'Do conditions act alone or together?', phase22:'Can a simple model predict new measurements?'
  };
  const lessons = {
    landing:'A simulated drone tries to land twice with the same random conditions: once with the baseline method, and once with Aegis. Compare the outcomes. A small batch cannot prove that a real drone is safe.',
    camera:'The computer draws a landing pad, adds the chosen camera problems, then tries to locate it. Confidence is the estimator’s score; a high score does not guarantee a correct reading.',
    dynamics:'Both models receive the same movement command. One reacts immediately; the other has a delay and disturbances. The gap shows why a simple model can miss real movement.',
    trace:'Two generated sets of errors are compared. Add a consistent offset or increase the spread to see how the measures respond. These are synthetic examples, not captured flight data.',
    temporal:'An estimate is a best guess of position. This experiment feeds imperfect readings to the original estimator and compares its guess with a position we know, because we generated it.',
    uncertainty:'An error range is like saying “the answer is probably within this much.” Coverage measures how often that range actually contains the generated error. New conditions can make that promise less reliable.',
    residual:'An error model uses the current error to predict the next one. The residual is what it misses. This simplified equation helps explain the research, but does not simulate the whole aircraft.',
    context:'Five conditions each switch on or off, giving 32 combinations. You set how much each condition changes a made-up advantage score. The original analysis methods then explain that constructed example.',
    gap:'The archive has no recorded experiment for Phase 4. It is kept visible so the missing step is not mistaken for a successful test.'
  };
  const help = {
    seed:'Same seed and settings repeat the same random example.',samples:'More generated readings give a larger example, not a safety guarantee.',episodes:'Each trial runs both methods with the same seed.',offset:'Sideways distance from the landing-pad center. Negative means the other side.',altitude:'Starting height above the ground, in meters.',noise:'Random measurement variation. Larger values make readings less consistent.',bias:'A consistent measurement offset. Unlike noise, it does not average away.',dropout:'Fraction of readings missing: 0.1 means about 10%.',severity:'Strength of the simulated degradation or movement command.',lag:'How many frames old the reading is. Zero means no delay.',tau:'Time for the actuator response to build. Larger means slower.',coefficient:'How strongly the current error predicts the next one.',alternative:'A second coefficient to compare on the same generated errors.',coverage:'Desired fraction inside the range: 0.95 means 95%.',shift:'Multiplier on test noise relative to the reference conditions.',radius:'Distance from the center to either end of the allowed interval.',interaction:'Extra change when edge and angled view occur together.',edge:'Effect assigned to a landing pad near the image edge.',oblique:'Effect assigned to viewing the pad at an angle.',dim:'Effect assigned to dim lighting.',blur_noise:'Effect assigned to blur or image noise.',low_contrast:'Effect assigned to a pad that blends into the background.'
  };
  const metricHelp = {
    'First-order variance':['Effects acting alone','Share of variation in the constructed surface explained by individual conditions. Observation noise does not change this structural measure.'],
    'Interaction variance':['Effects working together','Share of constructed variation from combinations of conditions. This is not the fraction of unsafe flights.'],
    'Parseval error':['Calculation consistency','Numerical mismatch in an exact mathematical identity. Near zero means the calculation agrees with itself, not that a drone is safe.'],
    'Prediction R²':['How well predictions fit','1 is a perfect match to these observations; 0 is as good as their average. Negative means worse than that average. This is not an accuracy percentage.'],
    'Prediction RMSE':['Typical prediction error','Root mean squared error in the constructed score. Lower is closer; large errors count more.'],
    'Shapley efficiency error':['Attribution consistency','Difference between total assigned contributions and the endpoint change. Near zero checks the accounting.'],
    'Endpoint attenuation':['Total change across conditions','Difference between no conditions active and all five active, in percentage points of the constructed score.'],
    'Context cells':['Condition combinations','All 32 on/off combinations of five conditions.'],
    'Minimum invariant half-width':['Required half-width','Calculated from this sample’s residual bound and the chosen coefficient. It is not a whole-aircraft guarantee.'],
    'Aegis successful landings':['Aegis successful landings','Successful simulated outcomes divided by the number of trials.'],
    'Available frames':['Readings available','Share of generated frames where the estimator returned a measurement.'],
    'Mean confidence':['Average confidence score','The estimator’s confidence, which can be high even when a reading is wrong.']
  };
  function explainMetric(m) {
    return metricHelp[m.label] || [m.label, /RMSE/.test(m.label)?'Root mean squared error: lower is closer to the reference, with larger mistakes weighted more heavily.':/coverage/i.test(m.label)?'Fraction of generated errors inside the estimated range. Compare with the target; this is not a guarantee on future data.':/unsafe/i.test(m.label)?'Count of simulated unsafe touchdowns in this batch. Zero in a small batch does not establish safety.':/bound/i.test(m.label)?'An estimate based on this generated sample and the selected coverage.': 'Computed from this run only. See the method details and exact data below.'];
  }
  function addGuide(main) {
    const guide=document.createElement('section'); guide.className='aegis-guide'; guide.id='understand-aegis';
    const isPhase=/phase\d/i.test(location.pathname), group=catalog[phase][1];
    guide.innerHTML=`<div class="lab-shell"><div class="guide-intro"><h2>${isPhase?esc(questions[phase]):'A drone can be confident—and still be wrong.'}</h2><p>${isPhase?esc(lessons[group]):'AegisLand studies how a computer estimates where a drone should land, what happens when that estimate is wrong, and whether another check can notice the mistake. The work uses computer simulations.'}</p></div><details class="guide-more"><summary>The basics & research glossary</summary><div class="guide-columns"><div><h3>Start with the idea</h3><p>Think of parking with a blurry reversing camera. A clear-looking answer may still be wrong. Here, the question is whether the software knows enough to trust its answer.</p><a href="#experiment-lab">Try it with your own settings →</a></div><div><h3>Read the research</h3><p>Each “phase” is one step in the investigation. PASS means it met that step’s stated checks. FAIL means it did not. Neither is a certificate that a real aircraft is safe.</p><a href="/phases/">Browse the steps →</a></div><div><h3>Keep the two kinds of results apart</h3><p>The published record is fixed (“frozen”). Your browser experiments create new examples. They never replace the published findings.</p><details><summary>Explain the research words</summary><dl><dt>Estimate</dt><dd>A calculated guess, such as where the landing pad is.</dd><dt>Ground truth</dt><dd>The known answer used to check a guess.</dd><dt>Noise / bias</dt><dd>Random variation / a consistent offset.</dd><dt>RMSE / MAE</dt><dd>Two ways to summarize error. RMSE weights large mistakes more; MAE averages their sizes.</dd><dt>Holdout</dt><dd>Data set aside to evaluate a model after it is fixed.</dd><dt>Residual</dt><dd>The part left over after a model’s prediction.</dd><dt>Coverage</dt><dd>How often an estimated range contains the error being checked.</dd><dt>Percentage point (pp)</dt><dd>The difference between two percentages: 30% minus 20% is 10 percentage points.</dd></dl></details></div></div></details></div>`;
    const first=main.firstElementChild;
    const homeAudit=document.body.classList.contains('home-workspace') ? main.querySelector('#current-audit') : null;
    const archiveGroups=document.body.classList.contains('archive-workspace') ? main.querySelector('#categories') : null;
    if(homeAudit) homeAudit.after(guide);
    else if(archiveGroups) archiveGroups.after(guide);
    else if(first) first.after(guide);
    else main.append(guide);
  }

  const comparisonKey=data=>[catalog[data.phase][1],data.x_label,data.y_label].join('|');
  let sharedSetup=null,restoreNotice='';
  try{sharedSetup=State.readSetup(location.search,fields,catalog);if(sharedSetup)phase=sharedSetup.phase;}catch{restoreNotice='This setup link contains invalid settings. Default settings are shown.';}
  try{stacks=State.restore(localStorage.getItem(State.STORAGE_KEY),fields,catalog,comparisonKey);stackId=Math.max(0,...Object.values(stacks).flat().map(r=>r.id));}catch{restoreNotice='Saved comparisons could not be restored. You can clear saved data or run a new experiment.';}
  function start() {
    if (document.getElementById('experiment-lab')) return;
    const main = document.querySelector('main');
    if (!main) return;
    addGuide(main);
    const section=document.createElement('section');
    section.id='experiment-lab'; section.className='experiment-lab'; section.setAttribute('aria-labelledby','lab-title');
    section.innerHTML=`<div class="lab-shell"><div class="lab-heading"><div><h2 id="lab-title">Make the experiment yours.</h2><p>Choose a question, try a starting scenario, then change one setting at a time. Each run calculates a new example in your browser.</p></div><a class="lab-record" href="/phases/${phase}/">Read ${label(phase)} →</a></div><div class="lab-welcome"><div><strong>New to this?</strong><p class="lab-guide-copy">Run a baseline, add noise, then compare what changed.</p></div><button type="button" class="lab-walkthrough">Start guided experiment</button></div><div class="lab-saved-tools"><label>Saved runs<select class="lab-saved-select"><option value="">Choose a saved run</option></select></label><button type="button" class="lab-restore">Restore run</button><button type="button" class="lab-forget">Clear saved data</button><p class="lab-storage-status" role="status">Comparisons are saved on this device.</p></div><div class="lab-layout"><form class="lab-controls"><div class="lab-field"><label for="lab-phase">What would you like to explore?</label><select id="lab-phase">${Object.entries(catalog).map(([s,[name]])=>`<option value="${s}" ${s===phase?'selected':''}>${label(s)} · ${questions[s]}</option>`).join('')}</select></div><div class="lab-field"><label for="lab-preset">Starting scenario</label><select id="lab-preset"><option value="default">Balanced example</option><option value="gentle">Small disturbances</option><option value="stress">Stronger disturbances</option><option value="custom">Custom settings</option></select><p class="lab-preset-note">Presets are examples, not difficulty levels or validated flight conditions.</p></div><label class="lab-help-toggle"><input type="checkbox" id="lab-show-help"> Explain settings and numbers</label><fieldset id="lab-fields" aria-label="Experiment inputs"></fieldset><div class="lab-actions"><button class="lab-run" type="submit">Run experiment</button><button class="lab-cancel" type="button" hidden>Cancel</button><button class="lab-reset" type="button">Reset</button><button class="lab-share" type="button">Share settings</button></div><p class="lab-status" role="status" aria-live="polite">Ready. Python loads on your first run.</p></form><div class="lab-results" aria-busy="false"><div class="lab-empty"><h3>What will this test tell you?</h3><p>${esc(lessons[catalog[phase][1]])}</p></div></div></div></div>`;
    const before=main.querySelector('#timeline, #supporters');before?before.before(section):main.appendChild(section);
    const comparison=document.createElement('div');comparison.className='lab-comparison';section.querySelector('.lab-layout').after(comparison);
    const fieldsEl=section.querySelector('#lab-fields'), resultsEl=section.querySelector('.lab-results'), status=section.querySelector('.lab-status');
    const form=section.querySelector('form'), phaseSelect=section.querySelector('#lab-phase');
    const runButton=section.querySelector('.lab-run'), cancelButton=section.querySelector('.lab-cancel');
    section.querySelector('#lab-show-help').onchange=e=>section.classList.toggle('lab-explained',e.target.checked);
    const savedPanel=document.createElement('details');savedPanel.className='lab-saved-panel';savedPanel.innerHTML='<summary>Saved runs on this device</summary>';const savedTools=section.querySelector('.lab-saved-tools');savedTools.before(savedPanel);savedPanel.append(savedTools);
    function controls() {
      const group=catalog[phase][1];
      let names=[...(groups[group]||[])];
      if(phase==='phase10r') names.push('bias','shift');
      if(phase.startsWith('phase13')) names.push('lag');
      if(group==='residual'&&!['phase14','phase15'].includes(phase)) names=names.filter(n=>!['coverage','radius'].includes(n));
      if(group==='dynamics') names=names.filter(n=>n!=='altitude');
      fieldsEl.innerHTML=names.map(name=>{
        if(name==='condition') return `<div class="lab-field"><label for="lab-condition">Camera condition</label><select id="lab-condition" name="condition">${['clean','blur','low_light','occlusion','mixed'].map(x=>`<option value="${x}" ${x==='mixed'?'selected':''}>${x.replace('_',' ')}</option>`).join('')}</select></div>`;
        let [title,value,min,max,step]=fields[name];
        if(group==='context'&&name==='noise'){title='Observation noise';value=.015;step=.005;}
        const hint=group==='context'&&name==='noise'?'Random variation added to fresh observations only. It does not alter the constructed surface or its variance shares.':help[name];
        return `<div class="lab-field"><label for="lab-${name}">${title}</label><div class="lab-input-pair">${name!=='seed'?`<input type="range" aria-label="${title} slider" data-for="${name}" min="${min}" max="${max}" step="${step}" value="${value}">`: ''}<input id="lab-${name}" name="${name}" type="number" value="${value}" min="${min}" max="${max}" step="${step}" aria-describedby="help-${name}" required></div><small id="help-${name}">${esc(hint)}</small></div>`;
      }).join('');
      if(group==='gap') fieldsEl.innerHTML='<p>Phase 4 has no recorded implementation or experiment. The archive preserves this provenance gap.</p>';
      if(group==='context') {
        const noise=section.querySelector('[name=noise]');noise.value='.015';noise.step='.005';
        section.querySelector('[for=lab-noise]').textContent='Observation noise';
      }
      section.querySelector('#lab-preset').disabled=group==='gap';
      runButton.disabled=group==='gap';
      section.querySelector('.lab-record').href=`/phases/${phase}/`;
      section.querySelector('.lab-record').textContent=`Read ${label(phase)} →`;
      status.textContent=group==='gap'?'No test exists for this phase.':'Ready. Python loads on your first run.';
      if(group==='camera') {section.querySelector('[name=samples]').max='128';section.querySelector('[data-for=samples]').max='128';}
      const advanced=document.createElement('details');advanced.className='lab-advanced';advanced.innerHTML='<summary>Repeatability & sample size</summary><div class="lab-advanced-fields"></div>';
      for(const key of ['samples','episodes','seed']) {const input=fieldsEl.querySelector('[name='+key+']');if(input) advanced.lastElementChild.append(input.closest('.lab-field'));}
      fieldsEl.append(advanced);
      const primary={landing:['condition','offset','noise'],camera:['condition','severity','altitude'],dynamics:['tau','severity'],trace:['noise','bias','shift'],temporal:['noise','dropout','offset'],uncertainty:['noise','coverage','shift'],residual:['lag','coefficient','alternative'],context:['edge','interaction','noise']};
      const extra=document.createElement('details');extra.className='lab-advanced';extra.innerHTML='<summary>More conditions</summary><div class="lab-advanced-fields"></div>';
      for(const field of [...fieldsEl.children]){if(!field.classList.contains('lab-field'))continue;const key=field.querySelector('[name]')?.name;if(!(primary[group]||[]).includes(key))extra.lastElementChild.append(field);}
      if(extra.lastElementChild.children.length)advanced.before(extra);
      section.querySelector('#lab-preset').value='default';
      const scope=section.querySelector('.lab-scope')||document.createElement('p');
      scope.className='lab-scope';
      const scopes={landing:'Runs the original landing simulation with your conditions.',camera:'Runs original camera and observability components on generated frames; not the full landing loop.',dynamics:'Runs the original Phase 7 plant model against the point-mass plant.',trace:'A synthetic diagnostic. Full PX4/Gazebo and camera-capture pipelines require external simulator evidence.',temporal:'Runs the original AegisT10 estimator on your generated measurement sequence.',uncertainty:'A core-method exercise with fresh synthetic data; not the frozen fitted candidate.',residual:'A scalar residual and recoverability exercise; not a full frozen phase evaluation.',context:'Original analysis functions on a surface you define. These are not the published frozen coefficients.',gap:'No recorded experiment exists.'};
      scope.textContent=executionKind(phase)+'. '+scopes[group];fieldsEl.before(scope);
    }
    function setBusy(value) {
      section.querySelectorAll('.lab-walkthrough,.lab-restore,.lab-forget,.lab-share,.lab-related-run').forEach(b=>b.disabled=value);
      busy=value; fieldsEl.disabled=value; phaseSelect.disabled=value;section.querySelector('#lab-preset').disabled=value||phase==='phase4';
      runButton.disabled=value||catalog[phase][1]==='gap'; cancelButton.hidden=!value;
      section.querySelector('.lab-reset').disabled=value;
      resultsEl.setAttribute('aria-busy',String(value));
    }
    function fail(message) {
      clearTimeout(timer); setBusy(false); status.dataset.error='true'; status.textContent=message;
      worker?.terminate(); worker=null;
    }
    function download(content, type, extension) {
      const url=URL.createObjectURL(new Blob([content],{type})); const a=document.createElement('a');
      a.href=url;a.download=`aegisland-${result.phase}-seed-${result.inputs.seed}.${extension}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
    function render(data) {
      data.series.forEach((line,i)=>{line.color=colors[i%colors.length];});
      const last=previousByKey[comparisonKey(data)]||Object.values(stacks).flat().filter(r=>comparisonKey(r.data)===comparisonKey(data)).at(-1)?.data;
      const takeaway=State.takeaway(data,last);previousByKey[comparisonKey(data)]=structuredClone(data);
      result=data;
      try{localStorage.setItem(State.STORAGE_KEY+'.last',JSON.stringify(State.validateResult(data,fields,catalog)));}catch{storageMessage('Latest result could not be saved on this device. Export JSON to keep it.');}
      const keys=Object.keys(data.rows[0]||{});
      resultsEl.innerHTML=`<p class="lab-help">${label(data.phase)} · Exploratory run · Seed ${data.inputs.seed}</p><h3>${esc(questions[data.phase])}</h3><p class="lab-run-takeaway" role="status">${esc(takeaway)}</p><p class="lab-run-kind">${esc(data.execution_kind||executionKind(data.phase))}</p><details class="lab-result-context"><summary>What this experiment tests</summary><p class="lab-takeaway">${esc(lessons[catalog[data.phase][1]])}</p></details><p class="lab-stale" hidden>Inputs changed. Run again to update these results.</p><dl class="lab-summary">${data.metrics.map(m=>`<div><dt>${esc(explainMetric(m)[0])}</dt><dd>${esc(m.value===null?'Unavailable':new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(m.value))}<span>${esc(m.unit)}</span></dd><p class="lab-metric-help">${esc(explainMetric(m)[1])}</p></div>`).join('')}</dl>${data.series.length?'<figure class="lab-chart"></figure>':''}${data.image?'<figure class="lab-image"><canvas width="96" height="96" aria-label="Generated synthetic camera frame"></canvas><figcaption>Last generated camera frame. Rendered by the original synthetic landing-pad model.</figcaption></figure>':''}${data.attribution?`<div class="lab-attribution">${Object.entries(data.attribution).map(([k,v])=>`<span>${esc(k.replace('_',' '))}: <strong>${fmt(v*100)} pp</strong></span>`).join('')}</div>`:''}<details class="lab-method"><summary>How this result was calculated</summary><p class="lab-note">${esc(data.note)}</p><p class="lab-note">Technical metrics: ${data.metrics.map(m=>esc(m.label)).join(', ')}. Seed ${data.inputs.seed}. Original source ${esc(data.source_commit.slice(0,7))}.</p></details><div class="lab-output-actions"><button type="button" class="lab-save">Add run to comparison</button><button type="button" class="lab-json">Download JSON</button><button type="button" class="lab-csv">Download CSV</button></div><details><summary>Inspect all ${data.rows.length} rows</summary><div class="lab-table" tabindex="0" role="region" aria-label="Experiment data"><table><thead><tr>${keys.map(k=>`<th scope="col">${esc(k)}</th>`).join('')}</tr></thead><tbody>${data.rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(fmt(r[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
      const related=Object.keys(catalog).filter(p=>p!==data.phase&&catalog[p][1]===catalog[data.phase][1]);
      if(related.length){const box=document.createElement('div');box.className='lab-related';box.innerHTML=`<label>Related phase<select>${related.map(p=>`<option value="${p}">${label(p)} · ${esc(questions[p])}</option>`).join('')}</select></label><button type="button" class="lab-related-run">Compare with related phase</button><p>Keep these inputs and run the related method. Shared measurements appear on one graph.</p>`;resultsEl.querySelector('.lab-output-actions').before(box);box.querySelector('button').onclick=()=>{if(busy)return;const source=structuredClone(result);if(!saveRun(source))return;switchTo({...source.inputs,phase:box.querySelector('select').value});form.requestSubmit();};}
      renderComparison();
      resultsEl.querySelector('.lab-save').onclick=()=>{if(saveRun(result)){renderComparison();comparison.scrollIntoView({block:'start'});status.textContent='Run saved on this device. Try another setting or a related phase.';}};
      if(data.series.length) {
        const figure=resultsEl.querySelector('.lab-chart');drawChart(figure,data);
        const controls=document.createElement('div');controls.className='lab-chart-controls';
        controls.innerHTML=data.series.map((line,i)=>`<label><input type="checkbox" style="accent-color:${line.color}" checked data-series="${i}">${esc(line.label)}</label>`).join('');
        figure.before(controls);
        controls.onchange=()=>{const selected=[...controls.querySelectorAll('input:checked')].map(x=>data.series[Number(x.dataset.series)]);if(selected.length)drawChart(figure,{...data,series:selected});else figure.innerHTML='<p>Select a line to show the chart.</p>';};
        const count=Math.max(...data.series.map(line=>line.values.length));
        const inspect=document.createElement('div');inspect.innerHTML=`<label for="lab-inspect">Inspect one chart position</label><input id="lab-inspect" class="lab-inspect" type="range" min="0" max="${count-1}" value="0" step="1"><div class="lab-point-readout" role="status"></div>`;figure.after(inspect);
        const showPoint=()=>{const i=Number(inspect.querySelector('input').value);inspect.querySelector('.lab-point-readout').textContent=(data.rows[i]?.Context? 'Combination '+i+': '+data.rows[i].Context:'Chart position '+i)+'. '+data.series.map(line=>line.label+': '+fmt(line.values[i]??null)).join('; ');};inspect.oninput=()=>{showPoint();markPoint(Number(inspect.querySelector('input').value));};showPoint();
        const markPoint=i=>{
          const svg=figure.querySelector('svg');if(!svg)return;
          const width=svg.viewBox.baseVal.width,x=54+i/Math.max(1,count-1)*(width-78);
          let cursor=svg.querySelector('.lab-crosshair');if(!cursor){cursor=document.createElementNS('http://www.w3.org/2000/svg','line');cursor.setAttribute('class','lab-crosshair');cursor.setAttribute('y1','24');cursor.setAttribute('y2','244');cursor.setAttribute('stroke','#50545a');cursor.setAttribute('stroke-dasharray','4 4');svg.append(cursor);}cursor.setAttribute('x1',x);cursor.setAttribute('x2',x);
        };
        const pointAt=event=>{const svg=figure.querySelector('svg');if(!svg)return;const rect=svg.getBoundingClientRect(),width=svg.viewBox.baseVal.width;const x=(event.clientX-rect.left)/rect.width*width;const i=Math.max(0,Math.min(count-1,Math.round((x-54)/(width-78)*(count-1))));inspect.querySelector('input').value=i;showPoint();markPoint(i);};
        figure.addEventListener('pointermove',event=>{if(event.pointerType==='mouse')pointAt(event);});figure.addEventListener('pointerdown',pointAt);
        figure.tabIndex=0;figure.setAttribute('aria-label','Interactive chart. Use left and right arrow keys to inspect readings.');figure.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const input=inspect.querySelector('input');input.value=event.key==='Home'?0:event.key==='End'?count-1:Math.max(0,Math.min(count-1,Number(input.value)+(event.key==='ArrowRight'?1:-1)));showPoint();markPoint(Number(input.value));});
        const hint=document.createElement('p');hint.className='lab-chart-hint';hint.textContent='Point or tap the chart to inspect a reading. Keyboard: left and right arrows.';figure.before(hint);
      }
      if(data.image) {
        const canvas=resultsEl.querySelector('canvas'), ctx=canvas.getContext('2d'), im=ctx.createImageData(96,96);
        data.image.flat().forEach((v,i)=>{im.data[i*4]=im.data[i*4+1]=im.data[i*4+2]=v;im.data[i*4+3]=255;});ctx.putImageData(im,0,0);
      }
      resultsEl.querySelector('.lab-json').onclick=()=>download(JSON.stringify(result,null,2),'application/json','json');
      resultsEl.querySelector('.lab-csv').onclick=()=>{
        const cell=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
        download([keys,...result.rows.map(r=>keys.map(k=>r[k]))].map(row=>row.map(cell).join(',')).join('\r\n'),'text/csv','csv');
      };
    }
    function renderComparison() {
      const target=comparison;
      const saved=stacks[comparisonKey(result)]||[];
      if(!saved.length){target.innerHTML='<h4>Build a comparison</h4><p>Add a run, then try another setting or a related phase. Compatible runs appear here on one shared graph. Different measurement families and axes stay separate.</p>';return;}
      const identical=saved.find(r=>JSON.stringify(r.data.inputs)===JSON.stringify(result.inputs));
      const runs=[...saved.map((r,i)=>({...r,name:label(r.data.phase)+' · Run '+(i+1)})),...(!identical?[{id:'current',name:label(result.phase)+' · Current',data:result}]:[])];
      const metrics=[...new Map(runs.flatMap(r=>r.data.metrics).map(m=>[m.label,m])).values()];
      const changed=Object.keys(result.inputs).filter(k=>runs.some(r=>r.data.inputs[k]!==runs[0].data.inputs[k]));
      target.innerHTML=`<h4>Compare ${runs.length} ${runs.length===1?'run':'runs'} on one graph</h4><p>Related methods with matching axes and units. Only shared measurements can be overlaid; this is not a ranking or statistical test. Saved on this device, including after a reload.</p><p class="lab-stack-scroll-hint">Scroll the table sideways to see every run on a small screen.</p><div class="lab-table lab-stack-table" tabindex="0" role="region" aria-label="Run comparison"><table><thead><tr><th scope="col">Measure / setting</th>${runs.map(r=>`<th scope="col">${r.name}${r.id!=='current'?`<button type="button" data-remove="${r.id}" aria-label="Remove ${r.name}">Remove</button>`:''}</th>`).join('')}</tr></thead><tbody>${metrics.map(m=>`<tr><th scope="row">${esc(explainMetric(m)[0])}${m.unit?' ('+esc(m.unit)+')':''}</th>${runs.map(r=>`<td>${fmt(r.data.metrics.find(x=>x.label===m.label)?.value??null)}</td>`).join('')}</tr>`).join('')}${changed.map(k=>`<tr class="lab-setting-row"><th scope="row">${esc(k==='noise'&&catalog[result.phase][1]==='context'?'Observation noise':fields[k]?.[0]||k)}</th>${runs.map(r=>`<td>${esc(fmt(r.data.inputs[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div><details class="lab-stack-plot" open><summary>Shared graph</summary><label>Measurement<select class="lab-stack-series"></select></label><figure class="lab-stack-chart"></figure><p>Each line is one run. Identical results overlap exactly. Only measurements present in every run are offered; different run lengths end at their last reading.</p></details><div class="lab-output-actions"><button type="button" class="lab-export-stack">Download comparison JSON</button><button type="button" class="lab-clear">Clear these runs</button></div>`;
      target.querySelectorAll('[data-remove]').forEach(button=>button.onclick=()=>{stacks[comparisonKey(result)]=saved.filter(r=>r.id!==Number(button.dataset.remove));persist();renderComparison();});
      target.querySelector('.lab-clear').onclick=()=>{stacks[comparisonKey(result)]=[];persist();renderComparison();};
      target.querySelector('.lab-export-stack').onclick=()=>download(JSON.stringify({schema:'aegisland.comparison.v1',phase:result.phase,runs:runs.map(r=>({name:r.name,result:r.data}))},null,2),'application/json','comparison.json');
      const select=target.querySelector('.lab-stack-series');
      const names=runs[0].data.series.map(line=>line.label).filter(name=>runs.every(r=>r.data.series.some(line=>line.label===name)));
      
      target.querySelector('.lab-stack-table').before(target.querySelector('.lab-stack-plot'));
      select.innerHTML=names.map(n=>`<option>${esc(n)}</option>`).join('');
      const plot=()=>{const series=runs.flatMap((r,i)=>{const line=r.data.series.find(l=>l.label===select.value);return line?[{...line,label:r.name,color:['#3457b2','#171a20','#9a6225','#28775e','#925ba1'][i]}]:[];});const figure=target.querySelector('.lab-stack-chart');if(series.length)drawChart(figure,{...result,series});else figure.innerHTML='<p>No chart series is available for these runs.</p>';};
      plot();select.onchange=plot;target.querySelector('.lab-stack-plot').ontoggle=event=>{if(event.target.open)plot();};
    }
    function executionKind(p){return ['phase1','phase2','phase3','phase5'].includes(p)?'Original closed-loop landing simulation':(['phase6','phase6b','phase7','phase10','phase10r'].includes(p)?'Original components with synthetic inputs':'Simplified method demonstration — not the full phase evaluation');}
    function storageMessage(text){section.querySelector('.lab-storage-status').textContent=text;}
    function populateSaved(){const select=section.querySelector('.lab-saved-select');select.innerHTML='<option value="">Choose a saved run</option>'+Object.values(stacks).flat().map(r=>`<option value="${r.id}">${label(r.data.phase)} · Run ${r.id} · Seed ${r.data.inputs.seed}</option>`).join('');}
    function persist(){try{localStorage.setItem(State.STORAGE_KEY,State.serialize(stacks,fields,catalog));storageMessage('Comparisons saved on this device. Shared links contain settings only.');}catch(e){storageMessage(e.message+' Runs remain available until you close this page.');}populateSaved();}
    function saveRun(data){const saved=stacks[comparisonKey(data)]||=[];if(saved.some(r=>JSON.stringify(r.data.inputs)===JSON.stringify(data.inputs)))return true;if(saved.length>=4||Object.values(stacks).flat().length>=24){status.textContent='Comparison storage is full. Remove a saved run first.';return false;}saved.push({id:++stackId,data:structuredClone(data)});persist();return true;}
    function applyInputs(inputs){for(const [key,value]of Object.entries(inputs)){const input=fieldsEl.querySelector('[name="'+key+'"]');if(input){input.value=value;if(input.type==='number'&&!['seed','samples','episodes','lag'].includes(key))input.step='any';const slider=fieldsEl.querySelector('[data-for="'+key+'"]');if(slider)slider.value=value;}}preset.value='custom';}
    function switchTo(inputs){phaseSelect.value=inputs.phase;phaseSelect.onchange();applyInputs(inputs);}
    section.querySelector('.lab-restore').onclick=()=>{const entry=Object.values(stacks).flat().find(r=>r.id===Number(section.querySelector('.lab-saved-select').value));if(!entry){storageMessage('Choose a saved run first.');return;}switchTo(entry.data.inputs);render(structuredClone(entry.data));status.textContent='Restored saved result. Run again to recompute it.';};
    section.querySelector('.lab-forget').onclick=()=>{stacks={};previousByKey={};try{localStorage.removeItem(State.STORAGE_KEY);localStorage.removeItem(State.STORAGE_KEY+'.last');}catch{}populateSaved();if(result)renderComparison();storageMessage('Saved data cleared from this device.');};
    section.querySelector('.lab-share').onclick=()=>{if(!form.reportValidity())return;const raw={phase};new FormData(form).forEach((v,k)=>raw[k]=k==='condition'?v:Number(v));let setup;try{setup=State.validateSetup(raw,fields,catalog);}catch(e){status.textContent=e.message;return;}const link=State.setupLink(location.hostname==='127.0.0.1'||location.hostname==='localhost'?'https://aegisland-research-cockpit.vercel.app':location.origin,setup);let panel=section.querySelector('.lab-share-panel');if(!panel){panel=document.createElement('div');panel.className='lab-share-panel';panel.innerHTML='<label>Shareable settings link<input readonly aria-label="Shareable settings link"></label><button type="button">Copy link</button><p>Includes settings only. Opening the link does not run an experiment.</p>';form.append(panel);}panel.querySelector('input').value=link;panel.querySelector('button').onclick=async()=>{try{await navigator.clipboard.writeText(link);status.textContent='Settings link copied.';}catch{panel.querySelector('input').select();status.textContent='Select and copy the link shown.';}};panel.querySelector('input').focus();panel.querySelector('input').select();};
    const guideButton=section.querySelector('.lab-walkthrough'),guideCopy=section.querySelector('.lab-guide-copy');
    guideButton.onclick=()=>{if(busy)return;if(guideStep===2&&result){const baseline=structuredClone(result);if(!saveRun(baseline))return;switchTo({...baseline.inputs,noise:.5});guideStep=3;guideCopy.textContent='Running the same scenario with noise increased from 0.05 m to 0.5 m. Seed and other inputs stay fixed.';}else{switchTo({phase:'phase1',condition:'clean',episodes:3,offset:1.5,altitude:6,noise:.05,bias:0,dropout:0,seed:2026});guideStep=1;guideCopy.textContent='Step 1 of 3: run a baseline with small measurement noise.';}form.requestSubmit();};
    function guideFinished(){if(guideStep===1){guideStep=2;guideCopy.textContent='Step 2 of 3: the baseline is ready. Increase only the measurement noise and run again.';guideButton.textContent='Increase noise and compare';}else if(guideStep===3){guideStep=4;guideCopy.textContent='Step 3 of 3: compare the two runs below. More noise may change the outcomes, but a small batch cannot establish safety.';guideButton.textContent='Restart walkthrough';comparison.scrollIntoView({block:'start'});}}
    const preset=section.querySelector('#lab-preset');
    preset.onchange=()=>{
      guideStep=0;guideButton.textContent='Start guided experiment';const choice=preset.value;if(choice==='custom')return;
      controls();preset.value=choice;
      const group=catalog[phase][1];
      const adjustments=choice==='gentle'?{noise:group==='context'?.01:.05,bias:0,dropout:0,severity:.5,lag:0,tau:.1,shift:1,interaction:0}:choice==='stress'?{noise:group==='context'?.06:.5,bias:.6,dropout:.3,severity:2,lag:6,tau:.8,shift:3,interaction:.15}:{};
      for(const [key,value] of Object.entries(adjustments)){const input=fieldsEl.querySelector('[name='+key+']');if(input){input.value=value;const slider=fieldsEl.querySelector('[data-for='+key+']');if(slider)slider.value=value;}}
      markStale();
    };
    function markStale(){if(result){resultsEl.querySelector('.lab-stale').hidden=false;status.textContent='Settings changed. The results below still belong to the previous run.';}}
    phaseSelect.onchange=()=>{phase=phaseSelect.value;result=null;comparison.innerHTML='<h4>Your saved runs stay here</h4><p>Run this phase to compare it with saved runs that use the same measurement family and axes.</p>';guideStep=0;guideButton.textContent='Start guided experiment';controls();resultsEl.innerHTML='<div class="lab-empty"><h3>'+esc(questions[phase])+'</h3><p>'+esc(lessons[catalog[phase][1]])+'</p></div>'; };
    form.addEventListener('input',event=>{const el=event.target;if(el.dataset.for){const input=fieldsEl.querySelector('[name='+el.dataset.for+']');input.value=el.value;}else if(el.name){const slider=fieldsEl.querySelector('[data-for='+el.name+']');if(slider&&el.value!=='')slider.value=el.value;}if(el.closest('#lab-fields')){preset.value='custom';guideStep=0;guideButton.textContent='Start guided experiment';}markStale();});
    section.querySelector('.lab-reset').onclick=()=>{guideStep=0;guideButton.textContent='Start guided experiment';controls();markStale();};
    cancelButton.onclick=()=>{requestId++;clearTimeout(timer);worker?.terminate();worker=null;setBusy(false);status.textContent='Run cancelled. Adjust inputs or run again.';};
    form.onsubmit=event=>{
      event.preventDefault();for(const invalid of fieldsEl.querySelectorAll(':invalid')){const details=invalid.closest('details');if(details)details.open=true;}if(busy||!form.reportValidity()||phase==='phase4')return;
      const inputs={phase};new FormData(form).forEach((v,k)=>{inputs[k]=k==='condition'?v:Number(v);});
      setBusy(true);status.dataset.error='false';status.textContent='Preparing experiment…';
      const id=++requestId;
      try {
        if(!worker) {
          worker=new Worker('/lab/worker.js');
          worker.onmessage=({data})=>{if(data.id!==requestId)return;if(data.type==='status')status.textContent=data.message;else if(data.type==='result'){clearTimeout(timer);setBusy(false);render(data.result);status.textContent='Run complete. Results reflect the inputs shown.';resultsEl.scrollIntoView({block:'start'});guideFinished();}else fail('The experiment could not finish. Check your connection and retry. '+data.message.split('\n').slice(-1)[0]);};
          worker.onerror=()=>fail('Python could not load. Check your connection, allow the runtime download, and retry.');
        }
        timer=setTimeout(()=>fail('The run exceeded three minutes. Try fewer samples or episodes.'),180000);
        worker.postMessage({id,inputs});
      }catch(error){fail('This browser could not start the experiment worker. Try an up-to-date browser.');}
    };
    controls();populateSaved();
    if(sharedSetup){switchTo(sharedSetup);status.textContent='Shared settings loaded. Review them, then run the experiment.';}
    else{try{const text=localStorage.getItem(State.STORAGE_KEY+'.last');if(text&&text.length<1500000){const last=State.validateResult(JSON.parse(text),fields,catalog);if(last.phase===phase){applyInputs(last.inputs);render(last);status.textContent='Latest result restored from this device. Run again to recompute.';}}}catch{storageMessage('The previous result could not be restored. Run a new experiment.');}}
    if(restoreNotice)storageMessage(restoreNotice);
    // One entry action near the phase introduction; preserve all recorded content.
    const heading=main.querySelector('h1');
    if(heading&&!document.body.classList.contains('home-workspace')){const a=document.createElement('a');a.href='#experiment-lab';a.className='lab-entry';a.textContent='Run an experiment';heading.parentElement.appendChild(a);const intro=document.createElement('a');intro.href='#understand-aegis';intro.className='lab-intro-link';intro.textContent='New here? Start with the explanation';heading.parentElement.appendChild(intro);}
    if(location.hash==='#experiment-lab') section.scrollIntoView();
  }
  function drawChart(figure,data) {
    const values=data.series.flatMap(s=>s.values).filter(Number.isFinite);
    if(!values.length)return;
    const lo=Math.min(...values),hi=Math.max(...values),pad=(hi-lo)*.08||.1;
    const min=lo-pad,max=hi+pad,n=Math.max(...data.series.map(s=>s.values.length));
    const width=Math.max(320,Math.min(680,figure.clientWidth));
    const right=width-24;
    const x=i=>54+i/Math.max(1,n-1)*(right-54),y=v=>24+(max-v)/(max-min)*220;
    const ticks=Array.from({length:5},(_,i)=>min+(max-min)*i/4);
    figure.innerHTML=`<div class="lab-legend">${data.series.map((s,i)=>`<span><i style="background:${s.color||colors[i%3]}"></i>${esc(s.label)}</span>`).join('')}</div><svg viewBox="0 0 ${width} 290" role="img" aria-label="${esc(data.y_label)} by ${esc(data.x_label)}. Exact values are available in the data table.">${ticks.map(v=>`<line x1="54" x2="${right}" y1="${y(v)}" y2="${y(v)}" stroke="#e2e3e3"/><text x="46" y="${y(v)+4}" text-anchor="end">${Number(v.toPrecision(3))}</text>`).join('')}${data.series.map((s,j)=>{let open=false;const d=s.values.map((v,i)=>{if(!Number.isFinite(v)){open=false;return '';}const c=open?'L':'M';open=true;return `${c}${x(i).toFixed(2)},${y(v).toFixed(2)}`;}).join(' ');return `<path d="${d}" fill="none" stroke="${s.color||colors[j%3]}" stroke-width="1.8"/>`;}).join('')}<text x="54" y="265">0</text><text x="${right}" y="265" text-anchor="end">${n-1}</text><text x="${width/2}" y="285" text-anchor="middle">${esc(data.x_label)}</text></svg><figcaption>${esc(data.y_label)}. ${catalog[data.phase][1]==='context'?'Each horizontal position is a different on/off combination, not a moment in time. The exact condition names are in the data table.':'Gaps indicate unavailable estimates.'}</figcaption>`;
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
