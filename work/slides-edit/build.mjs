import fs from 'node:fs/promises';
import {Presentation,PresentationFile} from 'file:///C:/Users/victo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
import {applyPresentationChartFont} from 'file:///C:/Users/victo/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations/container_tools/artifact_tool_utils.mjs';
const proto=JSON.parse(await fs.readFile('work/slides-edit/import.json','utf8'));
const src=proto.slides[19];
proto.slides=[0,1,2,3].map((i)=>{let s=structuredClone(src);s.id=`replica${i}`;s.index=i;s.elements=s.elements.slice(0,7);s.elements.forEach((e,j)=>{e.id=`rep${i}el${j}`;});return s;});
const p=Presentation.load(proto), S=JSON.parse(await fs.readFile('outputs/extension/summary.json','utf8')).categories;
const C={ink:'#14283F',teal:'#119F9A',muted:'#607892',purple:'#8C7CA0',bg:'#F7F9FC'};
const titles=['Our replication: first three runs','Disambiguation still shows a consistency gap','No clear improvement over historical GPT-5','Supplement: six-run combination estimates'];
const source='Source: Saved replication data, 19 Oct 2026. Methods and evidence in speaker notes.';
function text(s,str,x,y,w,h,size=26,color=C.ink,bold=false){let a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=str;a.text.style={fontFamily:'Aptos',fontSize:size,color,bold};return a;}
for(let i=0;i<4;i++){const s=p.slides.items[i];s.shapes.items[1].text=i===3?'SUPPLEMENTARY ANALYSIS':'OUR INSIGHTS';s.shapes.items[2].text=titles[i];s.shapes.items[5].text=source;s.shapes.items[6].text=String(i===3?25:20+i);}
let s=p.slides.items[0];
text(s,'GPT-6 Luna (medium reasoning)',62,160,1100,40,28,C.ink,true);
text(s,'Gemini 2.5 Flash thinking simulates users and supports scoring',62,207,1120,40,24,C.muted);
const kinds=['base','hallucination','disambiguation'], names=['Base','Hallucination','Disambiguation'];
const values=[['Task type','Tasks','Pass@1','Pass@3','Pass³'],...kinds.map((k,i)=>[names[i],String(S[k].available_tasks),...['pass1','pass_at3','pass_all3'].map(m=>(100*S[k].scores[m]).toFixed(1)+'%')])];
const t=s.tables.add({rows:4,columns:5,left:62,top:280,width:1156,height:246,columnWidths:[360,160,212,212,212],values});
for(let r=0;r<4;r++)for(let c=0;c<5;c++){let cell=t.getCell(r,c);cell.fill=r===0?'#E3F5F4':r%2?'#FFFFFF':C.bg;cell.text.style={fontFamily:'Aptos',fontSize:26,color:C.ink,bold:r===0};}
t.borders.assign({fill:'#DCE5ED',width:1,style:'solid'});
text(s,'125 tasks × 3 runs = 375 primary trials',62,555,1155,42,28,C.teal,true);
text(s,'Pass@1 uses run 1. Pass@3 and Pass³ use runs 1–3.',62,608,1150,40,22,C.muted);
s.speakerNotes.text="Sources: outputs/extension/summary.json and trial-index.csv. Author analysis: analyze_results_v2.py and analyze_results.py at commit ce6dc9d08f4ff81eb4c1a5c317aff25112ee950b. Main estimates use trial IDs 0,1,2 for both models. Pass@1 is trial 0 only; Pass@3 is any success in the first three, Pass^3 all three. 125 tasks, 375 primary trials. Six full repetitions (750 trials) and 84 partial seventh-round trials are stored, but excluded from primary estimates. Gemini 2.5 Flash thinking simulates users and supports original scoring. Offline correction, no new API calls.";
s=p.slides.items[1];
const d=S.disambiguation;
let chart=s.charts.add('bar',{position:{left:62,top:180,width:680,height:410},categories:['Pass@3','Pass³'],series:[{name:'Disambiguation',values:[d.scores.pass_at3,d.scores.pass_all3].map(v=>Number(v.toFixed(8))),fill:C.teal}],hasLegend:false,barOptions:{direction:'column',grouping:'clustered',gapWidth:100},xAxis:{textStyle:{fontSize:25,fill:C.ink}},yAxis:{min:0,max:1,majorUnit:.25,numberFormatCode:'0%',textStyle:{fontSize:19,fill:C.muted},majorGridlines:{fill:'#DCE5ED',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:28,bold:true,fill:C.ink}},chartFill:C.bg,plotAreaFill:C.bg});applyPresentationChartFont(chart,{fontFamily:'Aptos'});
text(s,'40.0-point gap',790,209,425,65,43,C.teal,true);
text(s,'At least one success: 80.0%\nThree successes: 40.0%',790,295,425,90,26);
text(s,'10 of 25 tasks succeeded\nin all first three runs.',790,430,425,86,28,C.ink,true);
text(s,'A successful run does not guarantee repeatable behavior.',62,612,1150,44,27,C.ink,true);
s.speakerNotes.text="Source: outputs/extension/summary.json categories.disambiguation.scores. First-three Pass@1 68%, Pass@3 80%, Pass^3 40%, gap 40 percentage points. 10/25 tasks pass all three. Six-run combination estimates appear only in the appendix. This is observed inconsistency, not a causal test of a clarification mechanism.";
s=p.slides.items[2];
chart=s.charts.add('bar',{position:{left:62,top:185,width:760,height:380},categories:names,series:[{name:'GPT-6 Luna (first 3)',values:kinds.map(k=>Number(S[k].matched.luna.pass_all3.toFixed(8))),fill:C.teal},{name:'GPT-5 (first 3)',values:kinds.map(k=>Number(S[k].matched.gpt5.pass_all3.toFixed(8))),fill:C.purple}],hasLegend:true,legend:{position:'top',textStyle:{fontSize:18,fill:C.ink}},barOptions:{direction:'column',grouping:'clustered',gapWidth:75},xAxis:{textStyle:{fontSize:21,fill:C.ink}},yAxis:{min:0,max:1,majorUnit:.25,numberFormatCode:'0%',textStyle:{fontSize:18,fill:C.muted},majorGridlines:{fill:'#DCE5ED',width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.0%',textStyle:{fontSize:22,bold:true,fill:C.ink}},chartFill:C.bg,plotAreaFill:C.bg});applyPresentationChartFont(chart,{fontFamily:'Aptos'});
text(s,'Pass³ on matched tasks',62,151,740,32,22,C.muted);
text(s,'Same task definitions',865,195,350,45,27,C.teal,true);
text(s,'48 Base\n45 Hallucination\n19 Disambiguation',865,252,350,125,27);
text(s,'Historical code, simulator\nand judge conditions differ.',865,419,350,100,25,C.muted);
text(s,'All paired 95% confidence intervals for the Pass³ difference include zero.',62,584,1150,43,25,C.ink,true);
text(s,'A controlled rerun is needed to isolate the effect of a model upgrade.',62,632,1150,32,22,C.muted);
s.speakerNotes.text="Sources: outputs/extension/summary.json matched and task-definition-audit.json. Both models use trial IDs 0,1,2 only. First-trial Pass@1, any/all first-three indicators. Identical task definitions and original matching cohort retained. Paired task bootstrap 10,000 resamples, seed 769. Historical code, simulator and judge conditions differ, so no causal model-upgrade claim. No reasoning=none ablation. Data: {\"base\": {\"n\": 48, \"matched\": {\"luna\": {\"pass1\": 0.7708333333333334, \"pass_at3\": 0.8541666666666666, \"pass_all3\": 0.5833333333333334}, \"gpt5\": {\"pass1\": 0.7708333333333334, \"pass_at3\": 0.875, \"pass_all3\": 0.6666666666666666}, \"difference\": {\"pass1\": 0.0, \"pass_at3\": -0.020833333333333332, \"pass_all3\": -0.08333333333333333}, \"difference_bootstrap_95ci\": {\"pass1\": [-0.16666666666666666, 0.16666666666666666], \"pass_at3\": [-0.14583333333333334, 0.10416666666666667], \"pass_all3\": [-0.22916666666666666, 0.0625]}}}, \"hallucination\": {\"n\": 45, \"matched\": {\"luna\": {\"pass1\": 0.6444444444444445, \"pass_at3\": 0.7555555555555555, \"pass_all3\": 0.5111111111111111}, \"gpt5\": {\"pass1\": 0.7333333333333333, \"pass_at3\": 0.8222222222222222, \"pass_all3\": 0.6}, \"difference\": {\"pass1\": -0.08888888888888889, \"pass_at3\": -0.06666666666666667, \"pass_all3\": -0.08888888888888889}, \"difference_bootstrap_95ci\": {\"pass1\": [-0.24444444444444444, 0.06666666666666667], \"pass_at3\": [-0.2222222222222222, 0.06666666666666667], \"pass_all3\": [-0.24444444444444444, 0.044444444444444446]}}}, \"disambiguation\": {\"n\": 19, \"matched\": {\"luna\": {\"pass1\": 0.7368421052631579, \"pass_at3\": 0.8421052631578947, \"pass_all3\": 0.42105263157894735}, \"gpt5\": {\"pass1\": 0.5789473684210527, \"pass_at3\": 0.7894736842105263, \"pass_all3\": 0.47368421052631576}, \"difference\": {\"pass1\": 0.15789473684210525, \"pass_at3\": 0.05263157894736842, \"pass_all3\": -0.05263157894736842}, \"difference_bootstrap_95ci\": {\"pass1\": [-0.10526315789473684, 0.42105263157894735], \"pass_at3\": [-0.15789473684210525, 0.2631578947368421], \"pass_all3\": [-0.3157894736842105, 0.21052631578947367]}}}}";

s=p.slides.items[3];
text(s,'All six Luna runs, averaged over 20 three-run combinations',62,169,1140,42,27,C.ink,true);
text(s,'Supplementary estimates use all 750 balanced trials',62,220,1140,38,24,C.muted);
const extraValues=[['Task type','Runs','Mean success','Pass@3','Pass³'],...kinds.map((k,i)=>[names[i],'6',...['pass1','pass_at3','pass_all3'].map(m=>(100*S[k].balanced_scores[m]).toFixed(1)+'%')])];
const extraTable=s.tables.add({rows:4,columns:5,left:62,top:286,width:1156,height:246,columnWidths:[360,120,252,212,212],values:extraValues});
for(let r=0;r<4;r++)for(let c=0;c<5;c++){let cell=extraTable.getCell(r,c);cell.fill=r===0?'#E3F5F4':r%2?'#FFFFFF':C.bg;cell.text.style={fontFamily:'Aptos',fontSize:25,color:C.ink,bold:r===0};}
extraTable.borders.assign({fill:'#DCE5ED',width:1,style:'solid'});
text(s,'Mean success averages all six runs. Main Pass@1 uses run 1 only.',62,557,1156,46,23,C.muted);
text(s,'Primary paper comparison remains the first-three-run analysis.',62,611,1156,42,25,C.ink,true);
s.speakerNotes.text='Supplement only: k=3, Luna n=6, Pass^3=C(c,3)/C(6,3), Pass@3=1-C(6-c,3)/C(6,3). Mean success=c/6. Historical comparison in full report uses all 10 triples of GPT-5 n=5. These estimates are separate from main first-three results. All-six success rates are separate stricter metrics. Partial seventh rounds excluded. See summary.json balanced_scores and balanced_matched.';

for(let i=0;i<4;i++){let b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(`work/slides-edit/new-${20+i}.png`,new Uint8Array(await b.arrayBuffer()));}
await (await PresentationFile.exportPptx(p)).save('work/slides-edit/newslides.pptx');console.log('Created three primary slides and one supplementary slide');process.exit(0);
