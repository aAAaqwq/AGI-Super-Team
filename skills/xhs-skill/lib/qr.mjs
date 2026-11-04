import { readFile } from 'node:fs/promises';
import jsQR from 'jsqr';
import { PNG } from 'pngjs';

export async function decodeQrFromPng(pngPath) {
  const buf = await readFile(pngPath);
  let png;
  try {
    png = PNG.sync.read(buf);
  } catch (e) {
    throw new Error(`Failed to read PNG: ${pngPath}`);
  }

  const code = jsQR(new Uint8ClampedArray(png.data), png.width, png.height);
  if (!code || !code.data) {
    throw new Error(`No QR code detected in PNG: ${pngPath}`);
  }

  return {
    text: code.data,
    width: png.width,
    height: png.height,
  };
}
