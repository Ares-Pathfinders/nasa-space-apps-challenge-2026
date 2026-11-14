import { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  Activity,
  Camera,
  CheckCircle2,
  ChevronRight,
  Crosshair,
  Layers3,
  MapPin,
  Mountain,
  Navigation,
  Radiation,
  Route,
  ShieldAlert,
  Thermometer,
  Wifi,
  X,
} from 'lucide-react';
import { MarsGlobe } from './components/MarsGlobe';
import { fetchHealth, fetchRoverPhotos, fetchSites } from './services/api';
import { ExplorationSite, LayerMode, RoverPhotosResponse } from './types/mars';

const layers: Array<{ id: LayerMode; label: string; detail: string; icon: typeof Layers3 }> = [
  { id: 'optical', label: 'Óptica', detail: 'Color real', icon: Layers3 },
  { id: 'elevation', label: 'Topográfica', detail: 'MOLA / relieve', icon: Mountain },
  { id: 'thermal', label: 'Térmica', detail: 'Inercia térmica', icon: Thermometer },
  { id: 'radiation', label: 'Radiación', detail: 'RAD / dosis', icon: Radiation },
];

function Metric({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="border-l border-slate-700 pl-3">
      <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-1 font-display text-sm text-slate-100">{value} <span className="font-mono text-[10px] text-slate-500">{unit}</span></p>
    </div>
  );
}

function App() {
  const [sites, setSites] = useState<ExplorationSite[]>([]);
  const [selectedSite, setSelectedSite] = useState<ExplorationSite | null>(null);
  const [layerMode, setLayerMode] = useState<LayerMode>('optical');
  const [photos, setPhotos] = useState<RoverPhotosResponse | null>(null);
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    fetchSites().then((loadedSites) => {
      setSites(loadedSites);
      setSelectedSite(loadedSites[0] ?? null);
    });
    fetchHealth().then((health) => setApiOnline(health.status === 'operational'));
  }, []);

  useEffect(() => {
    if (!selectedSite) return;
    const rover = selectedSite.rover_mission.toLowerCase().includes('perseverance') ? 'perseverance' : 'curiosity';
    fetchRoverPhotos(rover, selectedSite.default_sol, selectedSite.recommended_cameras[0]).then(setPhotos);
  }, [selectedSite]);

  const activeLayer = layers.find((layer) => layer.id === layerMode) ?? layers[0];

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#050608] text-slate-100">
      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 0.4, 6.4], fov: 42 }} dpr={[1, 2]} shadows>
          <MarsGlobe sites={sites} selectedSite={selectedSite} onSelectSite={setSelectedSite} layerMode={layerMode} />
        </Canvas>
      </div>

      <div className="scanline absolute inset-0 z-10 opacity-20" />
      <header className="hud-panel absolute left-4 right-4 top-4 z-20 flex h-16 items-center justify-between px-4 sm:left-6 sm:right-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center border border-hud-cyan/50 text-hud-cyan"><Crosshair size={19} /></div>
          <div>
            <p className="font-display text-sm tracking-[0.22em] text-slate-100">ARES<span className="text-hud-cyan">/</span>NAV</p>
            <p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">Martian surface navigator</p>
          </div>
        </div>
        <div className="hidden items-center gap-6 md:flex">
          <div className="text-right"><p className="text-[9px] uppercase tracking-widest text-slate-500">Mission clock</p><p className="font-display text-xs text-hud-cyan">SOL 1000 / 14:32 LMST</p></div>
          <div className="flex items-center gap-2 border-l border-slate-700 pl-5 text-[10px] uppercase tracking-widest text-slate-400"><Wifi size={14} className={apiOnline ? 'text-hud-green' : 'text-amber-400'} /> {apiOnline ? 'API online' : 'offline cache'}</div>
        </div>
      </header>

      <aside className="hud-panel absolute bottom-4 left-4 top-24 z-20 flex w-[min(19rem,calc(100vw-2rem))] flex-col p-4 sm:left-6 sm:bottom-6 sm:w-72">
        <div className="flex items-center justify-between border-b border-slate-700 pb-3">
          <div><p className="font-display text-[11px] tracking-[0.16em] text-hud-cyan">DATA LAYERS</p><p className="mt-1 text-[9px] uppercase tracking-widest text-slate-500">Live planetary model</p></div>
          <Layers3 size={17} className="text-slate-500" />
        </div>
        <div className="mt-4 space-y-2">
          {layers.map(({ id, label, detail, icon: Icon }) => (
            <button key={id} onClick={() => setLayerMode(id)} className={`flex w-full items-center gap-3 border px-3 py-2.5 text-left transition-colors ${layerMode === id ? 'border-hud-cyan/60 bg-hud-cyan/10 text-hud-cyan' : 'border-slate-800 bg-black/20 text-slate-400 hover:border-slate-600'}`}>
              <Icon size={16} />
              <span className="flex-1"><span className="block text-[11px] uppercase tracking-wider">{label}</span><span className="block text-[9px] text-slate-500">{detail}</span></span>
              {layerMode === id && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-hud-cyan" />}
            </button>
          ))}
        </div>
        <div className="mt-6 flex items-center justify-between"><p className="text-[9px] uppercase tracking-[0.18em] text-slate-500">Exploration zones</p><span className="text-[10px] text-hud-cyan">{sites.length.toString().padStart(2, '0')}</span></div>
        <div className="mt-2 space-y-1 overflow-y-auto">
          {sites.map((site) => <button key={site.id} onClick={() => setSelectedSite(site)} className={`flex w-full items-center gap-2 border-l-2 px-2 py-2 text-left text-[10px] transition-colors ${selectedSite?.id === site.id ? 'border-hud-amber bg-hud-amber/10 text-hud-amber' : 'border-slate-800 text-slate-400 hover:border-slate-500'}`}><MapPin size={13} /><span className="truncate">{site.name}</span></button>)}
        </div>
        <div className="mt-auto hidden border-t border-slate-800 pt-3 sm:block"><p className="text-[9px] uppercase tracking-widest text-slate-600">Active visualization</p><p className="mt-1 text-xs text-slate-300">{activeLayer.label} <span className="text-slate-600">//</span> {activeLayer.detail}</p></div>
      </aside>

      {selectedSite && <aside className="hud-panel absolute bottom-4 right-4 top-24 z-20 flex w-[min(23rem,calc(100vw-2rem))] flex-col overflow-y-auto p-4 sm:right-6 sm:bottom-6 sm:w-80">
        <div className="flex items-start justify-between border-b border-slate-700 pb-3"><div><p className="text-[9px] uppercase tracking-[0.2em] text-hud-amber">Point of interest / {selectedSite.id}</p><h1 className="mt-2 font-display text-base leading-tight text-slate-100">{selectedSite.name}</h1><p className="mt-1 text-[10px] text-slate-500">{selectedSite.region}</p></div><button title="Close site details" onClick={() => setSelectedSite(null)} className="text-slate-500 hover:text-slate-200"><X size={17} /></button></div>
        <div className="mt-4 grid grid-cols-2 gap-3"><Metric label="Latitude" value={`${selectedSite.coordinates.latitude.toFixed(3)}°`} /><Metric label="Longitude" value={`${selectedSite.coordinates.longitude.toFixed(3)}°`} /><Metric label="Mean temp" value={`${selectedSite.environment.avg_temp_c}`} unit="°C" /><Metric label="Radiation" value={`${selectedSite.environment.radiation_mgy_day}`} unit="mGy/d" /></div>
        <div className="mt-5 border border-hud-amber/30 bg-hud-amber/5 p-3"><div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-hud-amber"><ShieldAlert size={14} /> Safety advisory</div><p className="mt-2 text-[11px] leading-relaxed text-slate-300">{selectedSite.hazards[0]?.description}</p><p className="mt-2 text-[10px] text-slate-500">MITIGATION: {selectedSite.hazards[0]?.mitigation}</p></div>
        <div className="mt-5"><div className="flex items-center justify-between"><p className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-slate-400"><Camera size={14} /> Rover POV / {photos?.total_photos ?? 0}</p><span className="text-[9px] text-slate-600">{photos?.source === 'nasa_api' ? 'NASA API' : 'CACHE'}</span></div><div className="mt-2 grid grid-cols-2 gap-2">{photos?.photos.slice(0, 4).map((photo) => <img key={photo.id} src={photo.img_src} alt={`${photo.camera.full_name} on sol ${photo.sol}`} className="aspect-square w-full object-cover opacity-80 grayscale-[20%] hover:opacity-100" />)}</div></div>
        <div className="mt-auto pt-5"><button disabled className="flex w-full items-center justify-between border border-hud-cyan/30 bg-hud-cyan/10 px-3 py-3 text-left text-[10px] uppercase tracking-widest text-hud-cyan disabled:cursor-not-allowed disabled:opacity-70"><span className="flex items-center gap-2"><Route size={15} /> Hyperlocal 3D view</span><ChevronRight size={15} /></button><div className="mt-3 flex items-center justify-between text-[9px] uppercase tracking-widest text-slate-600"><span className="flex items-center gap-1"><CheckCircle2 size={12} className="text-hud-green" /> telemetry synced</span><span>sol {selectedSite.default_sol}</span></div></div>
      </aside>}

      <div className="absolute bottom-6 left-1/2 z-20 hidden -translate-x-1/2 items-center gap-6 border border-slate-800 bg-black/50 px-4 py-2 text-[9px] uppercase tracking-[0.18em] text-slate-500 backdrop-blur md:flex"><span className="flex items-center gap-2"><Navigation size={13} className="text-hud-cyan" /> orbital view</span><span className="flex items-center gap-2"><Activity size={13} className="text-hud-green" /> systems nominal</span><span className="flex items-center gap-2"><Route size={13} className="text-hud-amber" /> EVA route ready</span></div>
    </main>
  );
}

export default App;