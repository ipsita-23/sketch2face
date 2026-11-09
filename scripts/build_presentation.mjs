/** Editable college viva deck. All chart values come from saved experiment outputs. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import {execFileSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const runtime=process.env.ACADEMIC_RUNTIME || '/Users/theashgen/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const p=Presentation.create({slideSize:{width:1280,height:720}});
p.theme.defaultFont='Arial';
const summary=JSON.parse(await fs.readFile(path.join(root,'outputs/results/summary.json'),'utf8'));
const defs=JSON.parse(await fs.readFile(path.join(root,'scripts/academic_slides.json'),'utf8'));
const out=path.join(root,'outputs/academic'); const tmp=path.join(root,'tmp/academic');
await fs.mkdir(tmp,{recursive:true});
const colors=['#7B8794','#087F8C','#C27A29'];
function text(s,t,x,y,w,h,size=30,color='#1A2733',bold=false){
 const sh=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 sh.text=t;sh.text.style={typeface:'Arial',fontSize:size,color,bold}; return sh;
}
function table(s,values,widths){
 const tb=s.tables.add({rows:values.length,columns:values[0].length,left:65,top:175,width:1150,height:425,values,columnWidths:widths});
 for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
  const ce=tb.getCell(r,c);ce.fill=r===0?'#122337':r%2?'#EDF4F5':'#FFFFFF';
  ce.text.style={typeface:'Arial',fontSize:24,bold:r===0,color:r===0?'#FFFFFF':'#1A2733'};
 }
}
const labels=[['baseline','Frozen baseline'],['matcher','Matcher seed 42'],['matcher_seed43','Matcher seed 43'],['matcher_seed44','Matcher seed 44'],['shared_input','Without adapters']];
const rows=[['Model','Epoch','Rank-1 (%)','Rank-5 (%)','Rank-10 (%)'],...labels.map(([k,l])=>[l,String(summary.runs[k].selected_epoch),...[1,5,10].map(j=>(summary.runs[k].overall.metrics[`rank_${j}`].accuracy*100).toFixed(2))])];
let notes=[];
for(let i=0;i<defs.length;i++){
 const d=defs[i],s=p.slides.add();s.background.fill=i===0?'#122337':'#FFFFFF';
 s.speakerNotes.text=d.note+'\nEvidence: outputs/results/summary.json. Paper source targets the official IEEE SPS ieeeconf.cls with cameraready. The paper template does not define slide formatting.';
 notes.push(`## Slide ${i+1} - ${d.title}\n\n${s.speakerNotes.text}`);
 if(i===0){
  text(s,'Sketch2Face',72,75,1130,85,68,'#FFFFFF',true);
  text(s,'Cross-modal face retrieval\nCUFS CUHK subset',76,215,1120,130,42,'#BCE6E8');
  text(s,'Ipsita  |  Roll: 12308012 (placeholder)\nB.Tech in Artificial Intelligence and Machine Learning\nLovely Professional University  |  2023-2027\nGuide: [Guide name - placeholder]',76,445,1140,200,24,'#FFFFFF');
  continue;
 }
 text(s,d.title,62,45,1150,90,45,'#122337',true);text(s,String(i+1),1190,675,40,25,16,'#526575');
 if(i===4)table(s,[['Stage','Operation','Output'],['Preprocessing','Grayscale, resize, normalize','3 x 224 x 224'],['Modality input','Sketch or photo residual adapter','3 x 224 x 224'],['Shared encoder','ImageNet-pretrained ResNet-18','512 features'],['Projection','Linear, ReLU, Linear, normalize','256-D embedding'],['Retrieval','Cosine similarity to gallery','Ranked photos']],[230,640,280]);
 else if(i===7)table(s,rows,[350,110,230,230,230]);
 else if(i===8||i===9){
  const cmc=i===8;
  const chart=s.charts.add(cmc?'line':'bar',{
   position:{left:75,top:165,width:1130,height:465},
   categories:cmc?Array.from({length:10},(_,j)=>String(j+1)):['Rank-1','Rank-5','Rank-10'],
   series:[['baseline','Frozen baseline'],['matcher','Trained matcher'],['shared_input','Without adapters']].map(([k,n],j)=>({name:n,values:cmc?summary.runs[k].overall.cmc.slice(0,10).map(v=>Number((v*100).toFixed(6))):[1,5,10].map(v=>summary.runs[k].overall.metrics[`rank_${v}`].accuracy*100).map(v=>Number(v.toFixed(6))),fill:colors[j],line:{fill:colors[j],width:3}})),
   hasLegend:true,legend:{position:'bottom',textStyle:{typeface:'Arial',fontSize:20}},
   barOptions:{direction:'column',grouping:'clustered'},lineOptions:{smooth:false},
   xAxis:{title:cmc?'Rank k':'Retrieval threshold',textStyle:{typeface:'Arial',fontSize:20}},
   yAxis:{min:0,max:100,majorUnit:20,title:'Correct retrieval (%)',textStyle:{typeface:'Arial',fontSize:20},majorGridlines:{fill:'#DDE4E8',width:1}},
  });
  text(s,'37 test sketches searching the same 37-photo gallery',80,635,1100,30,20,'#526575');
 }else if(i===12){
  const b=await fs.readFile(path.join(root,'outputs/figures/learning_curves.png'));
  s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',alt:'Measured training loss and validation retrieval',fit:'contain',position:{left:90,top:160,width:1100,height:470}});
 }else{
  const lines=d.lines.join('\n').split('\n');
  for(let j=0;j<lines.length;j++)text(s,lines[j],68,175+j*(i===15?86:105),1145,90,i===15?28:32);
 }
}
await fs.writeFile(path.join(out,'presentation_notes.md'),notes.join('\n\n')+'\n');
await (await PresentationFile.exportPptx(p)).save(path.join(tmp,'presentation-draft.pptx'));
for(let i=0;i<p.slides.items.length;i++){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(tmp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const skill=process.env.PRESENTATIONS_SKILL_DIR || '/Users/theashgen/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
await fs.mkdir(path.join(tmp,'final'),{recursive:true});
const finalPath=path.join(tmp,'final',`presentation-${Date.now()}.pptx`);
await finalizePresentation({workspaceDir:tmp,candidatePath:path.join(tmp,'presentation-draft.pptx'),finalPath,pythonExecutable:path.join(runtime,'python/bin/python'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','5','--require-native-table-slide','8'],explicitTotalSlideCount:16,requiredNativeTableOwnerSlides:[5,8],requiredNativeChartOwnerSlides:[9,10],fontPolicy:{basis:'design',families:['Arial']},materializeLiteralChartWorkbooks:true,verifyArtifactToolImport:true,receiptPath:path.join(tmp,'presentation.validation.json')});
await fs.copyFile(finalPath,path.join(out,'presentation.pptx'));
execFileSync(path.join(runtime,'bin/override/soffice'),['-env:UserInstallation='+pathToFileURL(path.join(tmp,'lo-profile')).href,'--headless','--convert-to','pdf','--outdir',out,path.join(out,'presentation.pptx')],{stdio:'inherit'});
console.log('Validated PPTX, PDF and notes written to outputs/academic. Slide renders remain private in tmp/academic.');
