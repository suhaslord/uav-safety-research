(() => {
  "use strict";
  const format=(value)=>Number(value).toFixed(3);
  const pp=(value)=>(value>=0?"+":"")+(value*100).toFixed(1)+" pp";
  const esc=(value)=>String(value).replace(/[&<>"]/g,(ch)=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));

  function groupedChart(rows,metric,title,description){
    const w=820,h=300,left=56,right=18,top=18,bottom=58,plotH=h-top-bottom,plotW=w-left-right;
    const maxValue=Math.max(0.1,...rows.flatMap((row)=>[row.baseline[metric],row.phase23[metric]]))*1.15;
    const groupW=plotW/rows.length,barW=Math.min(30,groupW*.24);
    const grid=[0,.25,.5,.75,1].map((ratio)=>{
      const y=top+plotH*(1-ratio);
      return '<line class="grid" x1="'+left+'" y1="'+y+'" x2="'+(w-right)+'" y2="'+y+'"/><text x="'+(left-10)+'" y="'+(y+4)+'" text-anchor="end">'+Math.round(maxValue*ratio*100)+'%</text>';
    }).join("");
    const bars=rows.map((row,index)=>{
      const cx=left+groupW*(index+.5),baseH=row.baseline[metric]/maxValue*plotH,phaseH=row.phase23[metric]/maxValue*plotH;
      const baseX=cx-barW-2,phaseX=cx+2,labelY=h-20;
      return '<rect class="bar-baseline" x="'+baseX+'" y="'+(top+plotH-baseH)+'" width="'+barW+'" height="'+baseH+'" rx="3"><title>'+esc(row.label)+' baseline: '+format(row.baseline[metric])+'</title></rect><text class="value" x="'+(baseX+barW/2)+'" y="'+(top+plotH-baseH-5)+'" text-anchor="middle">'+format(row.baseline[metric])+'</text><rect class="bar-phase23" x="'+phaseX+'" y="'+(top+plotH-phaseH)+'" width="'+barW+'" height="'+phaseH+'" rx="3"><title>'+esc(row.label)+' Phase 23: '+format(row.phase23[metric])+'</title></rect><text class="value" x="'+(phaseX+barW/2)+'" y="'+(top+plotH-phaseH-5)+'" text-anchor="middle">'+format(row.phase23[metric])+'</text><text x="'+cx+'" y="'+labelY+'" text-anchor="middle">'+esc(row.label)+'</text>';
    }).join("");
    return '<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-labelledby="'+metric+'-title '+metric+'-desc"><title id="'+metric+'-title">'+esc(title)+'</title><desc id="'+metric+'-desc">'+esc(description)+'</desc>'+grid+'<line class="axis" x1="'+left+'" y1="'+(top+plotH)+'" x2="'+(w-right)+'" y2="'+(top+plotH)+'"/>'+bars+'</svg>';
  }

  function deltaChart(rows,metric,id,title,description){
    const w=820,h=300,left=56,right=18,top=22,bottom=58,plotH=h-top-bottom,plotW=w-left-right;
    const values=rows.map((row)=>row.delta[metric]*100),range=Math.max(5,...values.map(Math.abs))*1.2;
    const zeroY=top+plotH/2,half=plotH/2;
    const grid=[-range,-range/2,0,range/2,range].map((value)=>{
      const y=zeroY-value/range*half;
      return '<line class="'+(value===0?'axis':'grid')+'" x1="'+left+'" y1="'+y+'" x2="'+(w-right)+'" y2="'+y+'"/><text x="'+(left-10)+'" y="'+(y+4)+'" text-anchor="end">'+(value>0?'+':'')+value.toFixed(0)+' pp</text>';
    }).join("");
    const groupW=plotW/rows.length,barW=Math.min(44,groupW*.42);
    const bars=rows.map((row,index)=>{
      const value=row.delta[metric]*100,height=Math.abs(value)/range*half,x=left+groupW*(index+.5)-barW/2;
      const y=value>=0?zeroY-height:zeroY,cls=value>=0?'bar-positive':'bar-negative';
      return '<rect class="'+cls+'" x="'+x+'" y="'+y+'" width="'+barW+'" height="'+height+'" rx="3"><title>'+esc(row.label)+': '+(value>=0?'+':'')+value.toFixed(1)+' percentage points</title></rect><text class="value" x="'+(x+barW/2)+'" y="'+(value>=0?y-6:y+height+15)+'" text-anchor="middle">'+(value>=0?'+':'')+value.toFixed(1)+'</text><text x="'+(x+barW/2)+'" y="'+(h-20)+'" text-anchor="middle">'+esc(row.label)+'</text>';
    }).join("");
    return '<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-labelledby="'+id+'-title '+id+'-desc"><title id="'+id+'-title">'+esc(title)+'</title><desc id="'+id+'-desc">'+esc(description)+'</desc>'+grid+bars+'</svg>';
  }

  async function render(){
    const response=await fetch("/data/phase24-results.json",{cache:"no-store"});
    if(!response.ok)throw new Error("Results data returned "+response.status);
    const result=await response.json();
    if(result.schema_version!=="phase24.robustness-audit.v1"||result.conditions.length!==6)throw new Error("Unexpected Phase 24 data schema");
    const rows=result.conditions,summary=result.summary;
    document.getElementById("macroMapDelta").textContent=pp(summary.macro_map50.delta);
    document.getElementById("macroRecallDelta").textContent=pp(summary.macro_recall.delta);
    document.getElementById("mapWins").textContent=summary.map50_improved_conditions.length+" / "+rows.length;
    document.getElementById("tailMapDelta").textContent=pp(summary.severe_tail.macro_map50_delta);
    document.querySelector('[data-phase24-chart="map50"]').innerHTML=groupedChart(rows,"map50","mAP50 by condition","Baseline and Phase 23 mAP50 for six camera stress conditions.");
    document.querySelector('[data-phase24-chart="recall"]').innerHTML=groupedChart(rows,"recall","Recall by condition","Baseline and Phase 23 recall for six camera stress conditions.");
    document.querySelector('[data-phase24-chart="delta"]').innerHTML=deltaChart(rows,"map50","map-delta","mAP50 change by condition","Positive bars are gains; occlusion and mixed stress regress.");
    document.querySelector('[data-phase24-chart="recall-delta"]').innerHTML=deltaChart(rows,"recall","recall-delta","Recall change by condition","Positive bars are gains; occlusion and mixed stress regress.");
    document.getElementById("conditionRows").innerHTML=rows.map((row)=>{
      const severe=["occlusion","mixed"].includes(row.condition)?' class="severe"':"";
      const mapClass=row.delta.map50>=0?"pos":"neg",recallClass=row.delta.recall>=0?"pos":"neg";
      return '<tr'+severe+'><td>'+esc(row.label)+'</td><td>'+format(row.baseline.map50)+'</td><td>'+format(row.phase23.map50)+'</td><td class="'+mapClass+'">'+pp(row.delta.map50)+'</td><td>'+format(row.baseline.recall)+'</td><td>'+format(row.phase23.recall)+'</td><td class="'+recallClass+'">'+pp(row.delta.recall)+'</td></tr>';
    }).join("");
    const tail=summary.severe_tail;
    document.getElementById("tailReadout").innerHTML='<strong>Severe-stress readout:</strong> averaged across occlusion and mixed stress, mAP50 moves from '+format(tail.macro_map50_baseline)+' to '+format(tail.macro_map50_phase23)+' ('+pp(tail.macro_map50_delta)+'; '+tail.macro_map50_relative_percent.toFixed(1)+'% relative). Recall moves from '+format(tail.macro_recall_baseline)+' to '+format(tail.macro_recall_phase23)+' ('+pp(tail.macro_recall_delta)+').';
  }

  render().catch((error)=>{
    document.querySelectorAll("[data-phase24-chart]").forEach((node)=>node.innerHTML='<div class="error">The chart data did not load. The reproducible report remains linked below.</div>');
    const metrics=document.getElementById("headlineMetrics");
    if(metrics)metrics.setAttribute("aria-label","Phase 24 results unavailable: "+error.message);
    const table=document.getElementById("conditionRows");
    if(table)table.innerHTML='<tr><td colspan="7" class="error">Results data unavailable.</td></tr>';
  });
})();
