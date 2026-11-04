import { readFile } from 'node:fs/promises';

function u32be(buf, off) {
  return (buf[off] << 24) | (buf[off + 1] << 16) | (buf[off + 2] << 8) | buf[off + 3];
}

function u16be(buf, off) {
  return (buf[off] << 8) | buf[off + 1];
}

function isPng(buf) {
  return (
    buf.length >= 24 &&
    buf[0] === 0x89 &&
    buf[1] === 0x50 &&
    buf[2] === 0x4e &&
    buf[3] === 0x47 &&
    buf[4] === 0x0d &&
    buf[5] === 0x0a &&
    buf[6] === 0x1a &&
    buf[7] === 0x0a
  );
}

function parsePngSize(buf) {
  // PNG signature(8) + IHDR length(4) + type(4) => width starts at offset 16
  const width = u32be(buf, 16);
  const height = u32be(buf, 20);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('Invalid PNG IHDR size');
  }
  return { width, height, format: 'png' };
}

function isJpeg(buf) {
  return buf.length >= 4 && buf[0] === 0xff && buf[1] === 0xd8;
}

function parseJpegSize(buf) {
  // Walk markers until SOF0/SOF2.
  let i = 2; // after SOI
  while (i + 4 < buf.length) {
    if (buf[i] !== 0xff) {
      i += 1;
      continue;
    }
    // skip fill bytes 0xFF
    while (i < buf.length && buf[i] === 0xff) i += 1;
    if (i >= buf.length) break;
    const marker = buf[i];
    i += 1;

    // markers without length
    if (marker === 0xd9 || marker === 0xda) break; // EOI / SOS
    if (i + 2 > buf.length) break;
    const segLen = u16be(buf, i);
    if (segLen < 2) break;
    const segStart = i + 2;

    // SOF0(0xC0) / SOF2(0xC2) baseline/progressive
    if (marker === 0xc0 || marker === 0xc2) {
      if (segStart + 5 >= buf.length) break;
      const height = u16be(buf, segStart + 1);
      const width = u16be(buf, segStart + 3);
      if (width <= 0 || height <= 0) throw new Error('Invalid JPEG SOF size');
      return { width, height, format: 'jpeg' };
    }

    i = i + segLen;
  }
  throw new Error('Unsupported JPEG (no SOF marker found)');
}

export async function getImageSize(path) {
  const buf = await readFile(path);
  if (isPng(buf)) return parsePngSize(buf);
  if (isJpeg(buf)) return parseJpegSize(buf);
  throw new Error('Unsupported image format (only PNG/JPEG)');
}

