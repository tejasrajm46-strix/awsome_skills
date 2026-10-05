#!/usr/bin/env node
/** Check only runtime prerequisites; never installs packages or mutates the workspace. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';

const checks = [];
const add = (name, ok, detail, required = true) => checks.push({ name, ok, detail, required });
const major = Number(process.versions.node.split('.')[0]);
add('node', major >= 18, `v${process.versions.node}; Node 18+ required`);
const candidates = [process.env.CHROME_PATH, process.env.CHROMIUM_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
const browser = candidates.filter(Boolean).find(p => { try { return fs.existsSync(p); } catch { return false; } });
add('browser', Boolean(browser), browser || 'Chrome/Chromium not found; set CHROME_PATH', true);
const convertCandidates = process.platform === 'darwin' ? ['/usr/bin/sips'] : ['magick', 'convert'];
const convert = convertCandidates.find(bin => bin.startsWith('/') ? fs.existsSync(bin) : process.env.PATH?.split(path.delimiter).some(dir => fs.existsSync(path.join(dir, bin))));
add('image converter', Boolean(convert), convert || 'No sips/ImageMagick detected; PNG may work but JPG export is unavailable', false);
try {
  const probe = path.join(os.tmpdir(), `poster-check-${process.pid}`);
  fs.writeFileSync(probe, 'ok'); fs.rmSync(probe);
  add('temp directory', true, os.tmpdir());
} catch (err) { add('temp directory', false, err.message); }
let failed = false;
console.log('Poster environment check');
for (const c of checks) {
  console.log(`${c.ok ? ' OK ' : c.required ? 'FAIL' : 'WARN'} ${c.name}: ${c.detail}`);
  if (!c.ok && c.required) failed = true;
}
process.exitCode = failed ? 1 : 0;
