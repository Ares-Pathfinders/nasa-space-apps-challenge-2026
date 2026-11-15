import { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  Crosshair,
  Wifi,
} from 'lucide-react';
import { MarsGlobe } from './components/MarsGlobe';
import { fetchHealth } from './services/api';
import { RoverId } from './types/mars';

type LocalMapPhase = 'global' | 'zooming' | 'handoff' | 'ready' | 'exit-handoff' | 'zooming-out';
const LOCAL_MAP_ZOOM_DURATION_MS = 6500;
const LOCAL_MAP_HANDOFF_START_MS = 6200;
const LOCAL_MAP_HANDOFF_DURATION_MS = 1200;

function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [localMapPhase, setLocalMapPhase] = useState<LocalMapPhase>('global');
  const [selectedRover, setSelectedRover] = useState<RoverId | null>(null);
  const [zoomComplete, setZoomComplete] = useState(false);
  const [tacticalReady, setTacticalReady] = useState(false);
  const [handoffComplete, setHandoffComplete] = useState(false);
  const [terrain3DActive, setTerrain3DActive] = useState(false);

  useEffect(() => {
    fetchHealth().then((health) => setApiOnline(health.status === 'operational'));
  }, []);

  const handleOpenLocalMap = (rover: RoverId) => {
    setSelectedRover(rover);
    setTerrain3DActive(false);
    setZoomComplete(false);
    setTacticalReady(false);
    setHandoffComplete(false);
    setLocalMapPhase('zooming');
    setTimeout(() => {
      setLocalMapPhase('handoff');
      setTimeout(() => setHandoffComplete(true), LOCAL_MAP_HANDOFF_DURATION_MS);
    }, LOCAL_MAP_HANDOFF_START_MS);
    setTimeout(() => {
      setZoomComplete(true);
    }, LOCAL_MAP_ZOOM_DURATION_MS);
  };

  const handleCloseLocalMap = () => {
    setTerrain3DActive(false);
    setLocalMapPhase('exit-handoff');
    window.setTimeout(() => {
      setLocalMapPhase('zooming-out');
      window.setTimeout(() => {
        setLocalMapPhase('global');
        setSelectedRover(null);
        setZoomComplete(false);
        setTacticalReady(false);
        setHandoffComplete(false);
      }, LOCAL_MAP_ZOOM_DURATION_MS);
    }, LOCAL_MAP_HANDOFF_DURATION_MS);
  };

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data === 'close-tactical') handleCloseLocalMap();
      if (event.data === 'tactical-ready') setTacticalReady(true);
      if (event.data?.type === 'terrain3d-state' && typeof event.data.active === 'boolean') {
        setTerrain3DActive(event.data.active);
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  useEffect(() => {
    if (localMapPhase === 'handoff' && zoomComplete && tacticalReady && handoffComplete) {
      setLocalMapPhase('ready');
    }
  }, [handoffComplete, localMapPhase, tacticalReady, zoomComplete]);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#050608] text-slate-100">
      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 0.4, 6.4], fov: 42 }} dpr={[1, 2]} shadows>
          <MarsGlobe
            sites={[]}
            selectedSite={null}
            onSelectSite={() => undefined}
            onOpenRoverMap={handleOpenLocalMap}
            focusRover={localMapPhase !== 'global' && localMapPhase !== 'zooming-out' ? selectedRover : null}
            layerMode="optical"
          />
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
          <div className="flex items-center gap-2 border-l border-slate-700 pl-5 text-[10px] uppercase tracking-widest text-slate-400"><Wifi size={14} className={apiOnline ? 'text-hud-green' : 'text-amber-400'} /> {apiOnline ? 'Connected to mission control' : 'No connection to mission control'}</div>
        </div>
      </header>

      {localMapPhase !== 'global' && (
        <div className={`local-map-transition local-map-transition--${localMapPhase}`}>
          <div className="local-map-surface">
            <iframe
              src={`/tactical.html?zone=${selectedRover === 'perseverance' ? 'jezero' : 'gale'}`}
              className="w-full h-full border-0"
              allow="fullscreen"
              title="Mars tactical map"
            />
          </div>
          {(localMapPhase === 'handoff' || localMapPhase === 'ready' || localMapPhase === 'exit-handoff' || localMapPhase === 'zooming-out') && (
            <div
              className={`local-map-handoff${localMapPhase === 'ready' || localMapPhase === 'zooming-out' ? ' local-map-handoff--out' : ''}`}
              aria-hidden="true"
            >
              <span>{localMapPhase === 'exit-handoff' || localMapPhase === 'zooming-out' ? '3D' : '2D'}</span>
            </div>
          )}
          {localMapPhase === 'ready' && (
            <div className={`local-map-chrome${terrain3DActive ? ' local-map-chrome--terrain3d' : ''}`} style={{ zIndex: 50 }}>
              <button
                onClick={handleCloseLocalMap}
                className="hud-panel mx-auto flex items-center gap-2 border border-hud-cyan bg-black/90 px-6 py-2.5 font-display text-xs tracking-wider text-hud-cyan hover:bg-hud-cyan/20"
              >
                <span>🌐</span> <span>BACK TO 3D GLOBE VIEW</span>
              </button>
            </div>
          )}
        </div>
      )}

      {localMapPhase === 'global' && (
        <section aria-label="Select rover" className="hud-panel absolute bottom-6 left-6 z-20 w-64 p-3">
          <p className="mb-2 font-display text-[9px] uppercase tracking-[0.18em] text-slate-400">Select rover</p>
          <div className="grid gap-2">
            <button
              onClick={() => handleOpenLocalMap('curiosity')}
              className="flex items-center gap-2 border border-emerald-400/40 bg-black/70 px-3 py-2 text-left text-xs text-slate-100 hover:border-emerald-300"
            >
              <span className="h-2 w-2 rounded-full bg-emerald-300" />
              <span>Curiosity</span>
              <span className="ml-auto text-[9px] text-slate-400">Gale · MSL</span>
            </button>
            <button
              onClick={() => handleOpenLocalMap('perseverance')}
              className="flex items-center gap-2 border border-amber-400/40 bg-black/70 px-3 py-2 text-left text-xs text-slate-100 hover:border-amber-300"
            >
              <span className="h-2 w-2 rounded-full bg-amber-300" />
              <span>Perseverance</span>
              <span className="border border-amber-300/60 px-1 text-[8px] font-semibold tracking-wider text-amber-300">WIP</span>
              <span className="ml-auto text-[9px] text-slate-400">Jezero · M2020</span>
            </button>
          </div>
        </section>
      )}

    </main>
  );
}

export default App;
