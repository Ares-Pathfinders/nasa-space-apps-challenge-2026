import { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  Activity,
  Crosshair,
  Navigation,
  Route,
  Wifi,
} from 'lucide-react';
import { MarsGlobe } from './components/MarsGlobe';
import { fetchHealth } from './services/api';

type LocalMapPhase = 'global' | 'zooming' | 'ready';

function App() {
  const [apiOnline, setApiOnline] = useState(false);
  const [localMapPhase, setLocalMapPhase] = useState<LocalMapPhase>('global');

  useEffect(() => {
    fetchHealth().then((health) => setApiOnline(health.status === 'operational'));
  }, []);

  const handleOpenLocalMap = () => {
    setLocalMapPhase('zooming');
    setTimeout(() => {
      setLocalMapPhase('ready');
    }, 4500);
  };

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#050608] text-slate-100">
      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 0.4, 6.4], fov: 42 }} dpr={[1, 2]} shadows>
          <MarsGlobe
            sites={[]}
            selectedSite={null}
            onSelectSite={() => undefined}
            onOpenCuriosityMap={handleOpenLocalMap}
            focusCuriosity={localMapPhase !== 'global'}
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
          <div className="flex items-center gap-2 border-l border-slate-700 pl-5 text-[10px] uppercase tracking-widest text-slate-400"><Wifi size={14} className={apiOnline ? 'text-hud-green' : 'text-amber-400'} /> {apiOnline ? 'API online' : 'offline cache'}</div>
        </div>
      </header>

      {localMapPhase !== 'global' && (
        <div className={`local-map-transition ${localMapPhase === 'ready' ? 'local-map-transition--ready' : ''}`}>
          <div className="local-map-surface">
            <iframe src="/tactical" className="w-full h-full border-0" allow="fullscreen" />
          </div>
          <div className="local-map-chrome" style={{ zIndex: 50 }}>
            <button
              onClick={() => setLocalMapPhase('global')}
              className="hud-panel mx-auto flex items-center gap-2 border border-hud-cyan bg-black/90 px-6 py-2.5 font-display text-xs tracking-wider text-hud-cyan hover:bg-hud-cyan/20"
            >
              <span>🌐</span> <span>VOLVER A VISTA GLOBAL 3D</span>
            </button>
          </div>
        </div>
      )}

      <div className="absolute bottom-6 left-1/2 z-20 hidden -translate-x-1/2 items-center gap-6 border border-slate-800 bg-black/50 px-4 py-2 text-[9px] uppercase tracking-[0.18em] text-slate-500 backdrop-blur md:flex"><span className="flex items-center gap-2"><Navigation size={13} className="text-hud-cyan" /> orbital view</span><span className="flex items-center gap-2"><Activity size={13} className="text-hud-green" /> systems nominal</span><span className="flex items-center gap-2"><Route size={13} className="text-hud-amber" /> EVA route ready</span></div>
    </main>
  );
}

export default App;
