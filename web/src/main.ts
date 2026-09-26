import { LngLatBounds, Map, Popup, type MapMouseEvent } from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'

const NETWORK_URL = `${import.meta.env.BASE_URL}data/network.geojson`
const TRAM_ROUTE_TYPE = 0
const FALLBACK_COLOR = '#888888'

const map = new Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        maxzoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    },
    // Fond désaturé pour que les couleurs des lignes ressortent.
    layers: [{ id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.7 } }],
  },
  center: [2.5, 46.6],
  zoom: 5,
})

function networkBounds(collection: FeatureCollection): LngLatBounds | null {
  const bounds = new LngLatBounds()
  let empty = true
  for (const feature of collection.features) {
    const geometry = feature.geometry
    const points =
      geometry.type === 'LineString'
        ? geometry.coordinates
        : geometry.type === 'Point'
          ? [geometry.coordinates]
          : []
    for (const [lon, lat] of points) {
      bounds.extend([lon, lat])
      empty = false
    }
  }
  return empty ? null : bounds
}

function popupContent(title: string, subtitle?: string): HTMLElement {
  const container = document.createElement('div')
  const strong = document.createElement('strong')
  strong.textContent = title
  container.append(strong)
  if (subtitle) {
    container.append(document.createElement('br'), subtitle)
  }
  return container
}

async function loadNetwork(): Promise<void> {
  const response = await fetch(NETWORK_URL)
  if (!response.ok) {
    throw new Error(`Impossible de charger ${NETWORK_URL} (HTTP ${response.status})`)
  }
  const network = (await response.json()) as FeatureCollection

  map.addSource('network', { type: 'geojson', data: network })
  map.addLayer({
    id: 'routes',
    type: 'line',
    source: 'network',
    filter: ['==', ['geometry-type'], 'LineString'],
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
      // Trams dessinés au-dessus des bus.
      'line-sort-key': ['case', ['==', ['get', 'route_type'], TRAM_ROUTE_TYPE], 1, 0],
    },
    paint: {
      'line-color': ['coalesce', ['get', 'route_color'], FALLBACK_COLOR],
      'line-width': ['case', ['==', ['get', 'route_type'], TRAM_ROUTE_TYPE], 6, 2.5],
    },
  })
  map.addLayer({
    id: 'stations',
    type: 'circle',
    source: 'network',
    filter: ['==', ['geometry-type'], 'Point'],
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 15, 4.5],
      'circle-color': '#ffffff',
      'circle-stroke-color': '#333333',
      'circle-stroke-width': 1,
    },
  })

  const bounds = networkBounds(network)
  if (bounds) {
    map.fitBounds(bounds, { padding: 40, duration: 0 })
  }

  const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 8 })

  // Une station survolée a priorité sur les lignes qui passent dessous.
  map.on('mousemove', (event: MapMouseEvent) => {
    const [feature] = map.queryRenderedFeatures(event.point, { layers: ['stations', 'routes'] })
    if (!feature) {
      map.getCanvas().style.cursor = ''
      popup.remove()
      return
    }
    const props = feature.properties
    const content =
      feature.layer.id === 'stations'
        ? popupContent(String(props.stop_name ?? props.stop_id))
        : popupContent(String(props.route_short_name ?? props.route_id), props.route_long_name)
    map.getCanvas().style.cursor = 'pointer'
    popup.setLngLat(event.lngLat).setDOMContent(content).addTo(map)
  })
  map.on('mouseout', () => popup.remove())
}

map.on('load', () => {
  loadNetwork().catch((error: unknown) => console.error(error))
})
