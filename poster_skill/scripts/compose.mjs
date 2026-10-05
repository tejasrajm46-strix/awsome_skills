#!/usr/bin/env node
/** Compose a deterministic, self-contained HTML poster from DNA/content JSON.
 * Template mode accepts a raster image background and keeps the source file intact.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
function args(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (!key.startsWith('--')) continue;
    out[key.slice(2)] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
  }
  return out;
}
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
function imageSize(file) {
  const data = fs.readFileSync(file);
  if (data.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) return {width:data.readUInt32BE(16),height:data.readUInt32BE(20)};
  if (data[0]===0xff && data[1]===0xd8) {
    let offset=2;
    while(offset+4<data.length) {
      if(data[offset]!==0xff){offset++;continue;}
      const marker=data[offset+1]; offset+=2;
      if(marker===0xd8||marker===0xd9||(marker>=0xd0&&marker<=0xd7))continue;
      if(offset+2>data.length)break;
      const length=data.readUInt16BE(offset);
      if(length<2||offset+length>data.length)break;
      if([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)) return {height:data.readUInt16BE(offset+3),width:data.readUInt16BE(offset+5)};
      offset+=length;
    }
  }
  throw new Error('Could not read template dimensions. Use a PNG or JPEG image.');
}
const cssColor = value => /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(String(value || '')) ? value : '#111111';
function htmlText(value) { return esc(value).replace(/\n/g, '<br>'); }
function main() {
  const a = args(process.argv.slice(2));
  if (a.help || !a.content || !a.out) {
    console.log('compose.mjs --content content.json --out poster.html [--dna dna.json] [--template reference.png]');
    process.exitCode = a.help ? 0 : 2; return;
  }
  const contentPath = path.resolve(a.content);
  const content = JSON.parse(fs.readFileSync(contentPath, 'utf8'));
  const dna = a.dna ? JSON.parse(fs.readFileSync(path.resolve(a.dna), 'utf8')) : {};
  const canvas = dna.canvas || {};
  const templateInput = a.template || dna.image?.src || content.template || '';
  const templatePath = templateInput
    ? (a.template ? path.resolve(a.template) : path.resolve(path.dirname(contentPath), templateInput))
    : '';
  let templateSize = null;
  if (templatePath) {
    if (!fs.existsSync(templatePath)) throw new Error(`Template image not found: ${templatePath}`);
    const ext = path.extname(templatePath).toLowerCase();
    if (!['.png','.jpg','.jpeg'].includes(ext)) throw new Error('Flattened template background must be PNG or JPEG. Use a native editor for layered or WebP source files.');
    templateSize = imageSize(templatePath);
  }
  const width = clamp(Number(canvas.width || templateSize?.width || (canvas.preset === 'story' ? 1080 : 1200)), 320, 10000);
  const height = clamp(Number(canvas.height || templateSize?.height || (canvas.preset === 'story' ? 1920 : 1600)), 320, 14000);
  if (templateSize && Math.abs(width / height - templateSize.width / templateSize.height) > 0.002) {
    throw new Error(`Canvas ${width}x${height} does not match template aspect ratio ${templateSize.width}x${templateSize.height}. Match the template ratio or explicitly prepare a crop/extended background first.`);
  }
  const palette = dna.palette || {};
  const background = cssColor(palette.bg || '#10151c');
  const foreground = cssColor(palette.text || palette.primary || '#f7f4ed');
  const muted = cssColor(palette.muted || '#b8c0ca');
  const accent = cssColor(palette.accent || '#66d6c1');
  const template = templatePath;
  let templateCss = '';
  if (templatePath) {
    templateCss = `background-image:url('${pathToFileURL(templatePath).href}');background-size:100% 100%;background-position:center;background-repeat:no-repeat;`;
  }
  const headline = content.headline || content.title || 'Untitled';
  const lines = Array.isArray(content.headline_lines) ? content.headline_lines : null;
  const hstyle = dna.typography?.display || {};
  const bodyStyle = dna.typography?.body || {};
  const align = ['left','center','right'].includes(dna.layout?.align) ? dna.layout.align : 'left';
  const regions = Array.isArray(content.regions) ? content.regions : [];
  const mainStyle = template ? '' : `background:${background};color:${foreground};`;
  const regionHtml = regions.map((r, i) => {
    const x = clamp(Number(r.x ?? 8), 0, 100), y = clamp(Number(r.y ?? 14), 0, 100);
    const w = clamp(Number(r.w ?? 84), 1, 100 - x), h = clamp(Number(r.h ?? 14), 1, 100 - y);
    const size = clamp(Number(r.size ?? 3.2), 0.6, 24);
    const color = cssColor(r.color || foreground);
    const weight = clamp(Number(r.weight ?? 500), 100, 900);
    const text = htmlText(r.text || '');
    const role = esc(r.role || `replacement-${i + 1}`);
    const hasSample = r.cover && templatePath && Number.isFinite(Number(r.patchX)) && Number.isFinite(Number(r.patchY));
    const sampleOffsetX = hasSample ? (Number(r.patchX) * width / 100).toFixed(2) : 0;
    const sampleOffsetY = hasSample ? (Number(r.patchY) * height / 100).toFixed(2) : 0;
    const patchBg = hasSample
      ? `background-image:url('${pathToFileURL(templatePath).href}');background-size:${width}px ${height}px;background-position:-${sampleOffsetX}px -${sampleOffsetY}px;background-repeat:no-repeat;`
      : `background:${cssColor(r.patchColor || palette.bg || '#10151c')};`;
    const patch = r.cover ? `${patchBg}padding:${clamp(Number(r.padding ?? 1), 0, 12)}%;border-radius:${clamp(Number(r.radius ?? 0), 0, 8)}%;` : '';
    return `<div class="region" data-role="${role}"${r.cover ? ` data-covers-source="true" data-cover-method="${hasSample ? 'sampled-background' : 'solid-fill'}"` : ''} style="left:${x}%;top:${y}%;width:${w}%;min-height:${h}%;font-size:${size}cqh;color:${color};font-weight:${weight};text-align:${['left','center','right'].includes(r.align) ? r.align : align};${patch}">${text}</div>`;
  }).join('\n');
  const titleLines = lines ? lines.map(line => `<span>${htmlText(typeof line === 'string' ? line : line.text)}</span>`).join('') : `<span>${htmlText(headline)}</span>`;
  const details = [content.subhead, content.date, content.venue, ...(content.details || []).map(d => `${d.label ? `${d.label}: ` : ''}${d.value ?? ''}`), content.cta?.label, content.cta?.note]
    .filter(Boolean).map((text, i) => `<p class="detail detail-${i}" data-content="detail">${htmlText(text)}</p>`).join('\n');
  const defaultTitle = template ? '' : `<header class="headline" data-content="headline">${titleLines}</header><section class="details" data-content="details">${details}</section>`;
  const font = esc(hstyle.family || 'Arial, sans-serif');
  const bodyFont = esc(bodyStyle.family || 'Arial, sans-serif');
  const out = path.resolve(a.out);
  fs.mkdirSync(path.dirname(out), {recursive:true});
  const doc = `<!doctype html><html lang="${esc(dna.meta?.language || 'en')}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="poster-canvas" content="${width}x${height}"><meta name="poster-dpi" content="${Number(canvas.dpi || 300)}"><title>${esc(content.title || headline)}</title><style>
*{box-sizing:border-box}html,body{margin:0;width:100%;height:100%;background:#333}.poster{position:relative;isolation:isolate;width:${width}px;height:${height}px;overflow:hidden;container-type:size;${mainStyle}${templateCss}font-family:${bodyFont};color:${foreground}}.poster:before{content:"";position:absolute;inset:0;z-index:0;pointer-events:none;background:${template ? 'transparent' : `radial-gradient(ellipse at 80% 20%,${accent}22,transparent 45%)`}}.headline{z-index:1;position:absolute;left:8%;top:12%;width:84%;font-family:${font};font-weight:${Number(hstyle.weight || 800)};font-size:12cqh;line-height:${Number(hstyle.lineHeight || 0.94)};letter-spacing:${Number(hstyle.tracking || -0.025)}em;text-align:${align};text-wrap:balance}.headline span{display:block}.details{position:absolute;left:8%;right:8%;bottom:10%;color:${muted};font-size:2.1cqh;line-height:1.35}.detail{margin:0.7em 0}.detail:last-child{color:${accent};font-weight:700}.details{z-index:1}.region{z-index:1;position:absolute;overflow-wrap:anywhere;line-height:1.08;padding:0.08em 0;text-wrap:pretty}.poster[data-template="true"] .headline,.poster[data-template="true"] .details{display:none}@media print{html,body{width:${width}px;height:${height}px;background:white}.poster{break-after:avoid;print-color-adjust:exact;-webkit-print-color-adjust:exact}}
</style></head><body><main class="poster" data-template="${template ? 'true':'false'}">${defaultTitle}${regionHtml}</main></body></html>`;
  fs.writeFileSync(out, doc, 'utf8');
  console.log(JSON.stringify({html:out,canvas:{width,height,dpi:Number(canvas.dpi||300)},template:templatePath||null,templateSize,regions:regions.length,covers:regions.filter(r=>r.cover).length,sampledBackgroundPatches:regions.filter(r=>r.cover&&templatePath&&Number.isFinite(Number(r.patchX))&&Number.isFinite(Number(r.patchY))).length,mode:template?'template-reference':'original-design',notice:template&&regions.some(r=>r.cover)?'Cover patches require visual inspection for seams and complete source-text removal. Sampled background patches clone nearby pixels; complex areas may need inpainting.':null},null,2));
}
try { main(); } catch (err) { console.error(`compose failed: ${err.message}`); process.exitCode = 1; }
