#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const compose = path.join(root, 'scripts', 'compose.mjs');
const render = path.join(root, 'scripts', 'render.mjs');
const qa = path.join(root, 'scripts', 'qa.mjs');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'poster-template-test-'));

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const name = Buffer.from(type, 'ascii');
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0);
  name.copy(out, 4);
  data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}
function makePng(width, height, rgb) {
  const scanline = Buffer.alloc(1 + width * 4);
  scanline[0] = 0;
  for (let x = 0; x < width; x++) {
    scanline[1 + x * 4] = rgb[0];
    scanline[2 + x * 4] = rgb[1];
    scanline[3 + x * 4] = rgb[2];
    scanline[4 + x * 4] = 255;
  }
  const raw = Buffer.alloc(scanline.length * height);
  for (let y = 0; y < height; y++) scanline.copy(raw, y * scanline.length);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // RGBA
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0)),
  ]);
}
function browserAvailable() {
  const candidates = [process.env.CHROME_PATH, process.env.CHROMIUM_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  if (candidates.some(p => p && fs.existsSync(p))) return true;
  const command = process.platform === 'win32' ? 'where' : 'which';
  return ['chrome', 'google-chrome', 'chromium', 'chromium-browser'].some(name =>
    spawnSync(command, [name], {encoding: 'utf8'}).status === 0);
}

const background = path.join(tmp, 'background.png');
fs.writeFileSync(background, makePng(600, 900, [51, 102, 153]));
fs.writeFileSync(path.join(tmp, 'content.json'), JSON.stringify({
  title: 'New event',
  regions: [{role: 'event-title', text: 'A New Event', x: 10, y: 20, w: 70, h: 18, size: 5, cover: true, patchColor: '#ffffff'}],
}));
fs.writeFileSync(path.join(tmp, 'dna.json'), JSON.stringify({canvas: {dpi: 150}, palette: {bg: '#ffffff', text: '#111111'}}));
const html = path.join(tmp, 'poster.html');
try {
  const composed = spawnSync(process.execPath, [compose, '--dna', path.join(tmp, 'dna.json'),
    '--content', path.join(tmp, 'content.json'), '--template', background, '--out', html], {encoding: 'utf8'});
  if (composed.status !== 0) throw Error(composed.stderr || composed.stdout);
  const source = fs.readFileSync(html, 'utf8');
  if (!source.includes('600x900') || !source.includes('A New Event') ||
      !source.includes('background-image:url(\'file:') || !source.includes('data-covers-source="true"')) {
    throw Error('Template background, replacement text, or geometry missing');
  }
  const checked = spawnSync(process.execPath, [qa, '--html', html], {encoding: 'utf8'});
  if (checked.status !== 0) throw Error(checked.stderr || checked.stdout);
  const report = JSON.parse(checked.stdout);
  if (report.mode !== 'template-reference' || report.coveredSourceRegions !== 1 || !report.manualVisualReviewRequired) {
    throw Error('Template QA report incomplete');
  }

  const mismatched = path.join(tmp, 'wrong.json');
  fs.writeFileSync(mismatched, JSON.stringify({canvas: {width: 1000, height: 1000}}));
  const bad = spawnSync(process.execPath, [compose, '--dna', mismatched, '--content', path.join(tmp, 'content.json'),
    '--template', background, '--out', path.join(tmp, 'wrong.html')], {encoding: 'utf8'});
  if (bad.status === 0) throw Error('Mismatched aspect ratio was accepted');

  if (browserAvailable()) {
    const rendered = spawnSync(process.execPath, [render, '--html', html, '--out', path.join(tmp, 'rendered'),
      '--preview', '--formats', 'png'], {encoding: 'utf8', timeout: 180000});
    if (rendered.status !== 0) throw Error(rendered.stderr || rendered.stdout);
    const png = fs.readFileSync(path.join(tmp, 'rendered.preview.png'));
    if (!png.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) ||
        png.readUInt32BE(16) !== 300 || png.readUInt32BE(20) !== 450) {
      throw Error('Chrome preview dimensions or PNG signature are wrong');
    }
    console.log('PASS: Chrome rendered a correctly scaled 300x450 template preview');
  } else {
    console.log('SKIP: Chrome preview integration (no Chrome/Chromium available)');
  }
  console.log('PASS: template background dimensions, replacement regions, patch markers, static QA and aspect-ratio refusal');
} finally {
  fs.rmSync(tmp, {recursive: true, force: true});
}
