/**
 * Parse LDraw (.ldr) files into ManifestData for the LEGO Three.js builder.
 * LDR: 1 <color> <x> <y> <z> <3x3 matrix> <part.dat>
 * 1 stud = 20 LDU, 1 brick height = 24 LDU.
 */

import type { ManifestData } from './legoManualGenerator'

export function parseLdrToManifest(text: string): ManifestData {
  const bricks: ManifestData['bricks'] = []
  const lines = text.split(/\r?\n/)

  for (const line of lines) {
    const t = line.trim()
    if (!t || t.startsWith('0 ')) continue
    // Type 1 = part reference: 1 colour x y z a b c d e f g h i file.dat
    if (!t.startsWith('1 ')) continue

    const parts = t.split(/\s+/)
    if (parts.length < 15) continue

    const color = parseInt(parts[1], 10)
    const x = parseFloat(parts[2])
    const y = parseFloat(parts[3])
    const z = parseFloat(parts[4])
    const file = parts[14]
    if (!file?.toLowerCase().endsWith('.dat')) continue

    const partId = file.replace(/\.dat$/i, '')
    // LDU -> studs: 1 stud = 20 LDU, 1 brick = 24 LDU
    const studX = x / 20
    const studZ = z / 20
    const layer = y / 24

    bricks.push({
      part_id: partId,
      position: [studX, layer, studZ],
      rotation: 0,
      color_id: isNaN(color) ? 15 : color,
    })
  }

  return {
    manifest_version: '1.0',
    total_bricks: bricks.length,
    bricks,
  }
}

export async function loadLdrFromUrl(url: string): Promise<ManifestData> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load LDR: ${res.status}`)
  const text = await res.text()
  return parseLdrToManifest(text)
}
