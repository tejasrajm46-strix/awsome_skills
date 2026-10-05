#!/usr/bin/env node
/** Render poster HTML with installed Chrome/Chromium; no npm packages. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith('--')) {
      const key = argv[i].slice(2);
      out[key] = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
    }
  }
  return out;
}

function findChrome() {
  const candidates = [process.env.CHROME_PATH, process.env.CHROMIUM_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  for (const candidate of candidates) if (candidate && fs.existsSync(candidate)) return candidate;
  for (const name of ['chrome', 'google-chrome', 'chromium', 'chromium-browser']) {
    const result = spawnSync(process.platform === 'win32' ? 'where' : 'which', [name], {encoding: 'utf8'});
    if (result.status === 0 && result.stdout.trim()) return result.stdout.trim().split(/\r?\n/)[0];
  }
  return null;
}

function run(binary, argv) {
  const result = spawnSync(binary, argv, {encoding: 'utf8', timeout: 180000, windowsHide: true});
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error((result.stderr || result.stdout || `Chrome exit ${result.status}`).slice(-2000));
}

function temporaryHtml(source, directory, name, injectedStyle) {
  const html = source.replace('</head>', `<style>${injectedStyle}</style></head>`);
  const file = path.join(directory, `.${name}-${process.pid}-${Date.now()}.html`);
  fs.writeFileSync(file, html, 'utf8');
  return file;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.html) {
    console.log('render.mjs --html poster.html [--out out/poster] [--preview] [--formats png,jpg,pdf]');
    process.exitCode = args.help ? 0 : 2;
    return;
  }
  const html = path.resolve(args.html);
  if (!fs.existsSync(html)) throw new Error(`HTML not found: ${html}`);
  const source = fs.readFileSync(html, 'utf8');
  const canvas = source.match(/name="poster-canvas" content="(\d+)x(\d+)"/);
  const dpiMatch = source.match(/name="poster-dpi" content="(\d+)"/);
  if (!canvas) throw new Error('poster-canvas metadata missing');
  const width = Number(canvas[1]);
  const height = Number(canvas[2]);
  const dpi = Number(dpiMatch?.[1] || 300);
  const zoom = args.preview ? 0.5 : Number(args.zoom || 1);
  if (!(zoom > 0 && zoom <= 2)) throw new Error('zoom must be greater than 0 and at most 2');
  const chrome = findChrome();
  if (!chrome) throw new Error('Chrome/Chromium not found; set CHROME_PATH');
  const base = path.resolve(args.out || html.replace(/\.html?$/i, ''));
  fs.mkdirSync(path.dirname(base), {recursive: true});
  const formats = String(args.formats || 'png').split(',').map(value => value.trim().toLowerCase());
  const profile = path.join(os.tmpdir(), `poster-chrome-${process.pid}-${Date.now()}`);
  const cleanup = [];
  const common = ['--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
    '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`];
  try {
    if (formats.includes('png')) {
      const output = `${base}${args.preview ? '.preview' : ''}.png`;
      let renderHtml = html;
      let viewportWidth = width;
      let viewportHeight = height;
      if (args.preview) {
        renderHtml = temporaryHtml(source, path.dirname(html), 'poster-preview',
          `html,body{margin:0!important;width:${width}px!important;height:${height}px!important;overflow:hidden!important}body{transform:scale(${zoom});transform-origin:top left!important}`);
        cleanup.push(renderHtml);
        viewportWidth = Math.round(width * zoom);
        viewportHeight = Math.round(height * zoom);
      }
      run(chrome, [...common, '--force-device-scale-factor=1', '--run-all-compositor-stages-before-draw',
        `--window-size=${viewportWidth},${viewportHeight}`, `--screenshot=${output}`,
        `--virtual-time-budget=${Number(args.budget || 5000)}`, pathToFileURL(renderHtml).href]);
      if (!fs.existsSync(output) || fs.statSync(output).size < 100) throw new Error('Chrome did not create a valid PNG');
      console.log(`PNG ${output} ${fs.statSync(output).size} bytes`);
    }
    if (formats.includes('pdf')) {
      const output = `${base}.pdf`;
      const style = `@page{size:${(width / dpi).toFixed(5)}in ${(height / dpi).toFixed(5)}in;margin:0}html,body{margin:0!important;width:${width}px!important;height:${height}px!important}.poster{break-after:avoid;print-color-adjust:exact;-webkit-print-color-adjust:exact}`;
      const printHtml = temporaryHtml(source, path.dirname(html), 'poster-print', style);
      cleanup.push(printHtml);
      run(chrome, [...common, '--no-pdf-header-footer', `--print-to-pdf=${output}`,
        `--virtual-time-budget=${Number(args.budget || 5000)}`, pathToFileURL(printHtml).href]);
      if (!fs.existsSync(output) || fs.statSync(output).size < 100) throw new Error('Chrome did not create a valid PDF');
      console.log(`PDF ${output} ${fs.statSync(output).size} bytes; ${(width / dpi).toFixed(2)} x ${(height / dpi).toFixed(2)} in at ${dpi} dpi`);
    }
    if (formats.includes('jpg') || formats.includes('jpeg')) {
      const png = `${base}${args.preview ? '.preview' : ''}.png`;
      if (!fs.existsSync(png)) throw new Error('JPG output needs a PNG render; include png in --formats');
      const output = `${base}.jpg`;
      const quality = String(Math.max(1, Math.min(100, Number(args.quality || 92))));
      const candidates = process.platform === 'darwin' ? ['sips'] : ['magick', 'convert'];
      let converted = false;
      for (const tool of candidates) {
        const argv = tool === 'sips'
          ? ['-s', 'format', 'jpeg', '-s', 'formatOptions', quality, png, '--out', output]
          : [png, '-quality', quality, output];
        const result = spawnSync(tool, argv, {encoding: 'utf8', windowsHide: true});
        if (result.status === 0 && fs.existsSync(output)) {
          console.log(`JPG ${output} ${fs.statSync(output).size} bytes`);
          converted = true;
          break;
        }
      }
      if (!converted) throw new Error('JPG converter unavailable (ImageMagick or macOS sips); PNG remains available');
    }
  } finally {
    for (const file of cleanup) { try { fs.rmSync(file); } catch { /* best-effort cleanup */ } }
    try { fs.rmSync(profile, {recursive: true, force: true}); } catch { /* Chrome may still be closing */ }
  }
}

try { main(); } catch (error) {
  console.error(`render failed: ${error.message}`);
  process.exitCode = 1;
}
