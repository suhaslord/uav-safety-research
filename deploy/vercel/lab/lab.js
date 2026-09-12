(() => {
  'use strict';
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
  let worker, requestId=0, result=null, timer, busy=false;
  function start() {
    if (document.getElementById('experiment-lab')) return;
    const main = document.querySelector('main');
    if (!main) return;
    const section=document.createElement('section');
    section.id='experiment-lab'; section.className='experiment-lab'; section.setAttribute('aria-labelledby','lab-title');
    section.innerHTML=`<div class="lab-shell"><div class="lab-heading"><div><h2 id="lab-title">Run an experiment.</h2><p>Change the conditions. See what changes. Runs stay in your browser, separate from the frozen research record.</p></div><a class="lab-record" href="/phases/${phase}/">Read ${label(phase)} →</a></div><div class="lab-layout"><form class="lab-controls"><div class="lab-field"><label for="lab-phase">Research phase</label><select id="lab-phase">${Object.entries(catalog).map(([s,[name]])=>`<option value="${s}" ${s===phase?'selected':''}>${label(s)} · ${name}</option>`).join('')}</select></div><fieldset id="lab-fields" aria-label="Experiment inputs"></fieldset><div class="lab-actions"><button class="lab-run" type="submit">Run experiment</button><button class="lab-cancel" type="button" hidden>Cancel</button><button class="lab-reset" type="button">Reset</button></div><p class="lab-status" role="status" aria-live="polite">Ready. Python loads on your first run.</p></form><div class="lab-results" aria-busy="false"><div class="lab-empty"><h3>Your conditions. New results.</h3><p>Choose a phase and adjust its inputs, then run the experiment. You’ll get computed metrics, a chart, and downloadable data.</p></div></div></div></div>`;
    main.appendChild(section);
    const fieldsEl=section.querySelector('#lab-fields'), resultsEl=section.querySelector('.lab-results'), status=section.querySelector('.lab-status');
    const form=section.querySelector('form'), phaseSelect=section.querySelector('#lab-phase');
    const runButton=section.querySelector('.lab-run'), cancelButton=section.querySelector('.lab-cancel');
    function controls() {
      const group=catalog[phase][1];
      let names=[...(groups[group]||[])];
      if(phase==='phase10r') names.push('bias','shift');
      if(phase.startsWith('phase13')) names.push('lag');
      fieldsEl.innerHTML=names.map(name=>{
        if(name==='condition') return `<div class="lab-field"><label for="lab-condition">Camera condition</label><select id="lab-condition" name="condition">${['clean','blur','low_light','occlusion','mixed'].map(x=>`<option value="${x}" ${x==='mixed'?'selected':''}>${x.replace('_',' ')}</option>`).join('')}</select></div>`;
        const [title,value,min,max,step]=fields[name];
        return `<div class="lab-field"><label for="lab-${name}">${title}</label><input id="lab-${name}" name="${name}" type="number" value="${value}" min="${min}" max="${max}" step="${step}" required></div>`;
      }).join('');
      if(group==='gap') fieldsEl.innerHTML='<p>Phase 4 has no recorded implementation or experiment. The archive preserves this provenance gap.</p>';
      if(group==='context') {
        const noise=section.querySelector('[name=noise]');noise.value='.015';noise.step='.005';
        section.querySelector('[for=lab-noise]').textContent='Observation noise';
      }
      runButton.disabled=group==='gap';
      section.querySelector('.lab-record').href=`/phases/${phase}/`;
      section.querySelector('.lab-record').textContent=`Read ${label(phase)} →`;
      status.textContent=group==='gap'?'No test exists for this phase.':'Ready. Python loads on your first run.';
      if(group==='camera') section.querySelector('[name=samples]').max='128';
      const scope=section.querySelector('.lab-scope')||document.createElement('p');
      scope.className='lab-scope';
      const scopes={landing:'Runs the original landing simulation with your conditions.',camera:'Runs original camera and observability components on generated frames; not the full landing loop.',dynamics:'Runs the original Phase 7 plant model against the point-mass plant.',trace:'A synthetic diagnostic. Full PX4/Gazebo and camera-capture pipelines require external simulator evidence.',temporal:'Runs the original AegisT10 estimator on your generated measurement sequence.',uncertainty:'A core-method exercise with fresh synthetic data; not the frozen fitted candidate.',residual:'A scalar residual and recoverability exercise; not a full frozen phase evaluation.',context:'Original analysis functions on a surface you define. These are not the published frozen coefficients.',gap:'No recorded experiment exists.'};
      scope.textContent=scopes[group];fieldsEl.before(scope);
    }
    function setBusy(value) {
      busy=value; fieldsEl.disabled=value; phaseSelect.disabled=value;
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
      result=data;
      const keys=Object.keys(data.rows[0]||{});
      resultsEl.innerHTML=`<p class="lab-help">${label(data.phase)} · Exploratory run · Seed ${data.inputs.seed}</p><h3>${esc(data.title)}</h3><p class="lab-stale" hidden>Inputs changed. Run again to update these results.</p><dl class="lab-summary">${data.metrics.map(m=>`<div><dt>${esc(m.label)}</dt><dd>${esc(fmt(m.value))}<span>${esc(m.unit)}</span></dd></div>`).join('')}</dl>${data.series.length?'<figure class="lab-chart"></figure>':''}${data.image?'<figure class="lab-image"><canvas width="96" height="96" aria-label="Generated synthetic camera frame"></canvas><figcaption>Last generated camera frame. Rendered by the original synthetic landing-pad model.</figcaption></figure>':''}${data.attribution?`<div class="lab-attribution">${Object.entries(data.attribution).map(([k,v])=>`<span>${esc(k.replace('_',' '))}: <strong>${fmt(v*100)} pp</strong></span>`).join('')}</div>`:''}<p class="lab-note">${esc(data.note)}</p><div class="lab-output-actions"><button type="button" class="lab-json">Download JSON</button><button type="button" class="lab-csv">Download CSV</button></div><details><summary>Inspect all ${data.rows.length} rows</summary><div class="lab-table" tabindex="0" role="region" aria-label="Experiment data"><table><thead><tr>${keys.map(k=>`<th scope="col">${esc(k)}</th>`).join('')}</tr></thead><tbody>${data.rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(fmt(r[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
      if(data.series.length) drawChart(resultsEl.querySelector('.lab-chart'),data);
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
    phaseSelect.onchange=()=>{phase=phaseSelect.value;result=null;controls();resultsEl.innerHTML='<div class="lab-empty"><h3>'+esc(catalog[phase][0])+'</h3><p>'+(phase==='phase4'?'Read the phase record for the documented gap.':'Adjust the inputs and run a new experiment. Results will appear here.')+'</p></div>';};
    form.addEventListener('input',()=>{if(result) resultsEl.querySelector('.lab-stale').hidden=false;});
    section.querySelector('.lab-reset').onclick=()=>{controls();if(result)resultsEl.querySelector('.lab-stale').hidden=false;};
    cancelButton.onclick=()=>{requestId++;clearTimeout(timer);worker?.terminate();worker=null;setBusy(false);status.textContent='Run cancelled. Adjust inputs or run again.';};
    form.onsubmit=event=>{
      event.preventDefault();if(busy||!form.reportValidity()||phase==='phase4')return;
      const inputs={phase};new FormData(form).forEach((v,k)=>{inputs[k]=k==='condition'?v:Number(v);});
      setBusy(true);status.dataset.error='false';status.textContent='Preparing experiment…';
      const id=++requestId;
      try {
        if(!worker) {
          worker=new Worker('/lab/worker.js');
          worker.onmessage=({data})=>{if(data.id!==requestId)return;if(data.type==='status')status.textContent=data.message;else if(data.type==='result'){clearTimeout(timer);setBusy(false);render(data.result);status.textContent='Run complete. Results reflect the inputs shown.';resultsEl.scrollIntoView({block:'start'});}else fail('The experiment could not finish. Check your connection and retry. '+data.message.split('\n').slice(-1)[0]);};
          worker.onerror=()=>fail('Python could not load. Check your connection, allow the runtime download, and retry.');
        }
        timer=setTimeout(()=>fail('The run exceeded three minutes. Try fewer samples or episodes.'),180000);
        worker.postMessage({id,inputs});
      }catch(error){fail('This browser could not start the experiment worker. Try an up-to-date browser.');}
    };
    controls();
    // One entry action near the phase introduction; preserve all recorded content.
    const heading=main.querySelector('h1');
    if(heading){const a=document.createElement('a');a.href='#experiment-lab';a.className='lab-entry';a.textContent='Run an experiment';heading.parentElement.appendChild(a);}
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
    figure.innerHTML=`<div class="lab-legend">${data.series.map((s,i)=>`<span><i style="background:${colors[i%3]}"></i>${esc(s.label)}</span>`).join('')}</div><svg viewBox="0 0 ${width} 290" role="img" aria-label="${esc(data.y_label)} by ${esc(data.x_label)}. Exact values are available in the data table.">${ticks.map(v=>`<line x1="54" x2="${right}" y1="${y(v)}" y2="${y(v)}" stroke="#e2e3e3"/><text x="46" y="${y(v)+4}" text-anchor="end">${Number(v.toPrecision(3))}</text>`).join('')}${data.series.map((s,j)=>{let open=false;const d=s.values.map((v,i)=>{if(!Number.isFinite(v)){open=false;return '';}const c=open?'L':'M';open=true;return `${c}${x(i).toFixed(2)},${y(v).toFixed(2)}`;}).join(' ');return `<path d="${d}" fill="none" stroke="${colors[j%3]}" stroke-width="1.8"/>`;}).join('')}<text x="54" y="265">0</text><text x="${right}" y="265" text-anchor="end">${n-1}</text><text x="${width/2}" y="285" text-anchor="middle">${esc(data.x_label)}</text></svg><figcaption>${esc(data.y_label)}. Gaps indicate unavailable estimates.</figcaption>`;
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
