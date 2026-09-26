// Copie les fichiers produits par le moteur (data/processed/) dans public/data/,
// servi tel quel par Vite en dev et recopié dans dist/ au build.
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = resolve(webDir, '../data/processed/network.geojson')
const target = resolve(webDir, 'public/data/network.geojson')

if (!existsSync(source)) {
  console.error(`Fichier introuvable : ${source}`)
  console.error(
    'Générez-le depuis engine/ : uv run python -m transit_sim.cli build-network --gtfs ../data/raw/twisto --date 2026-10-06',
  )
  process.exit(1)
}
mkdirSync(dirname(target), { recursive: true })
copyFileSync(source, target)
console.log(`Copié : ${source} -> ${target}`)
