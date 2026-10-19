import fs from 'node:fs/promises';import {PresentationFile,FileBlob} from 'file:///C:/Users/victo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const p=await PresentationFile.importPptx(await FileBlob.load('outputs/CAR_bench_presentation_corrected_first3.pptx'));
for(let i=0;i<p.slides.items.length;i++){let b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(`work/slides-edit/final-${i+1}.png`,new Uint8Array(await b.arrayBuffer()));}
let b=await p.export({format:'webp',montage:true,scale:.25});await fs.writeFile('work/slides-edit/montage.webp',new Uint8Array(await b.arrayBuffer()));console.log('Rendered 25 final slides');process.exit(0);
