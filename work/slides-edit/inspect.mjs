import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from 'file:///C:/Users/victo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/victo/Downloads/CAR_bench_presentation_FIXED_backup.pptx'));
console.log((await p.inspect({kind:'slide,layout',maxChars:3000})).ndjson);
for(const i of [18,19,20,21]){let b=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(`work/slides-edit/source-${i+1}.png`,new Uint8Array(await b.arrayBuffer()));}
await fs.writeFile('work/slides-edit/import.json',JSON.stringify(p.toProto()));

