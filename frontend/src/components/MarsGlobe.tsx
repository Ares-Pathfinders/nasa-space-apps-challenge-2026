import React, { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Html } from '@react-three/drei';
import * as THREE from 'three';
import { ExplorationSite, LayerMode } from '../types/mars';
import { createProceduralMarsTextures } from './MarsTextures';
import marsSurfaceTextureUrl from '../../images/8k_mars.jpg';

interface MarsGlobeProps {
  sites: ExplorationSite[];
  selectedSite: ExplorationSite | null;
  onSelectSite: (site: ExplorationSite) => void;
  layerMode: LayerMode;
}

const GLOBE_RADIUS = 2.5;

function latLonToVector3(lat: number, lon: number, radius = GLOBE_RADIUS): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = radius * Math.sin(phi) * Math.sin(theta);
  const y = radius * Math.cos(phi);

  return new THREE.Vector3(x, y, z);
}

// Marker component with pulsing antenna and holographic label
const SiteMarker: React.FC<{
  site: ExplorationSite;
  isSelected: boolean;
  onSelect: () => void;
}> = ({ site, isSelected, onSelect }) => {
  const pos = useMemo(() => {
    return latLonToVector3(site.coordinates.latitude, site.coordinates.longitude, GLOBE_RADIUS * 1.012);
  }, [site.coordinates.latitude, site.coordinates.longitude]);

  return (
    <group position={pos}>
      {/* 3D Pin / Beacon */}
      <mesh onClick={(e) => { e.stopPropagation(); onSelect(); }}>
        <sphereGeometry args={[0.045, 16, 16]} />
        <meshStandardMaterial
          color={isSelected ? "#45f3ff" : "#ffb703"}
          emissive={isSelected ? "#45f3ff" : "#e77d22"}
          emissiveIntensity={isSelected ? 1.4 : 0.8}
        />
      </mesh>

      {/* Pulsing ring indicator */}
      <mesh>
        <ringGeometry args={[0.06, 0.08, 24]} />
        <meshBasicMaterial
          color={isSelected ? "#45f3ff" : "#ff5722"}
          side={THREE.DoubleSide}
          transparent
          opacity={isSelected ? 0.9 : 0.6}
        />
      </mesh>

      {/* Tactical HUD Pin Label */}
      <Html
        distanceFactor={6}
        position={[0, 0.12, 0]}
        center
        className="pointer-events-auto"
      >
        <button
          onClick={(e) => { e.stopPropagation(); onSelect(); }}
          className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono whitespace-nowrap transition-all duration-200 border ${
            isSelected
              ? 'bg-hud-cyan/20 border-hud-cyan text-hud-cyan shadow-[0_0_12px_rgba(69,243,255,0.5)] scale-110'
              : 'bg-black/80 border-slate-700 text-slate-300 hover:border-amber-400 hover:text-amber-400'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-hud-cyan animate-ping' : 'bg-amber-400'}`} />
          {site.name.split(' - ')[0]}
        </button>
      </Html>
    </group>
  );
};

// Subtle atmospheric glow shell
const AtmosphereGlow: React.FC<{ layerMode: LayerMode }> = ({ layerMode }) => {
  const atmosphereColor = useMemo(() => {
    if (layerMode === 'thermal') return '#9d4edd';
    if (layerMode === 'elevation') return '#0099cc';
    return '#c86d3b';
  }, [layerMode]);

  return (
    <mesh scale={[1.045, 1.045, 1.045]}>
      <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
      <meshBasicMaterial
        color={atmosphereColor}
        transparent
        opacity={0.12}
        side={THREE.BackSide}
      />
    </mesh>
  );
};

const SolarSystemBackdrop: React.FC = () => (
  <group renderOrder={-1}>
    {/* A distant sun provides a visible reference point and warm directional light. */}
    <group position={[11, 7, -22]}>
      <mesh>
        <sphereGeometry args={[2.1, 32, 32]} />
        <meshBasicMaterial color="#ffd166" />
      </mesh>
      <mesh scale={[1.35, 1.35, 1.35]}>
        <sphereGeometry args={[2.1, 32, 32]} />
        <meshBasicMaterial color="#ff9f1c" transparent opacity={0.14} side={THREE.BackSide} />
      </mesh>
    </group>

    {/* Thin orbital traces add depth without competing with the Mars globe. */}
    <mesh rotation={[Math.PI / 2.15, 0.08, 0]} position={[0, -0.5, -4]}>
      <torusGeometry args={[7.2, 0.008, 8, 128]} />
      <meshBasicMaterial color="#718096" transparent opacity={0.18} />
    </mesh>
    <mesh rotation={[Math.PI / 2.15, -0.12, 0]} position={[0, 0.8, -5]}>
      <torusGeometry args={[10.2, 0.006, 8, 128]} />
      <meshBasicMaterial color="#4a5568" transparent opacity={0.14} />
    </mesh>

    {/* Stylized distant planets. Their scale is intentionally exaggerated for the HUD view. */}
    <mesh position={[-8, 4.2, -15]}>
      <sphereGeometry args={[0.38, 24, 24]} />
      <meshStandardMaterial color="#b7b7b7" roughness={0.9} />
    </mesh>
    <mesh position={[7.5, -3.2, -16]}>
      <sphereGeometry args={[0.52, 24, 24]} />
      <meshStandardMaterial color="#4b8fc9" roughness={0.75} metalness={0.05} />
    </mesh>
    <mesh position={[-10, -3.5, -19]}>
      <sphereGeometry args={[0.44, 24, 24]} />
      <meshStandardMaterial color="#d87845" roughness={0.92} />
    </mesh>
    <group position={[5, 5, -20]}>
      <mesh>
        <sphereGeometry args={[0.8, 24, 24]} />
        <meshStandardMaterial color="#d8a15d" roughness={0.8} />
      </mesh>
      <mesh rotation={[Math.PI / 2.5, 0.2, 0]}>
        <torusGeometry args={[1.05, 0.12, 12, 64]} />
        <meshBasicMaterial color="#d6b27a" transparent opacity={0.75} />
      </mesh>
    </group>
    <mesh position={[14, -2, -25]}>
      <sphereGeometry args={[0.32, 24, 24]} />
      <meshStandardMaterial color="#80c9d5" roughness={0.7} />
    </mesh>
  </group>
);

export const MarsGlobe: React.FC<MarsGlobeProps> = ({
  sites,
  selectedSite,
  onSelectSite,
  layerMode,
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const globeRef = useRef<THREE.Group>(null);
  const controlsRef = useRef<any>(null);
  const { camera } = useThree();

  // Create procedural textures on client-side
  const { optTexture, topoTexture, thermTexture, bumpTexture } = useMemo(() => {
    return createProceduralMarsTextures();
  }, []);
  const marsSurfaceTexture = useMemo(() => {
    const texture = new THREE.TextureLoader().load(marsSurfaceTextureUrl);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = 8;
    return texture;
  }, []);

  // Determine active texture and color map based on chosen layer
  const currentTexture = useMemo(() => {
    switch (layerMode) {
      case 'elevation':
        return topoTexture;
      case 'thermal':
        return thermTexture;
      case 'radiation':
        return thermTexture;
      case 'optical':
      default:
        return marsSurfaceTexture;
    }
  }, [layerMode, marsSurfaceTexture, optTexture, topoTexture, thermTexture]);

  // Slow ambient rotation of Mars
  useFrame((_, delta) => {
    if (globeRef.current) {
      globeRef.current.rotation.y += delta * 0.02;
    }
  });

  // Smooth camera refocus when user selects a site
  React.useEffect(() => {
    if (selectedSite && controlsRef.current) {
      const targetPos = latLonToVector3(
        selectedSite.coordinates.latitude,
        selectedSite.coordinates.longitude,
        GLOBE_RADIUS
      );

      // Desired camera position pulled outward from target
      const camTarget = targetPos.clone().multiplyScalar(1.9);
      const globeCenter = new THREE.Vector3(0, 0, 0);
      
      const startCam = camera.position.clone();
      const startTime = performance.now();
      const duration = 1000; // 1 second smooth transition

      const animateCamera = (now: number) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 0.5 - Math.cos(progress * Math.PI) / 2;

        camera.position.lerpVectors(startCam, camTarget, ease);
        // Keep OrbitControls centered on Mars, even while focusing a site.
        controlsRef.current.target.lerp(globeCenter, ease);
        controlsRef.current.update();

        if (progress < 1) {
          requestAnimationFrame(animateCamera);
        }
      };

      requestAnimationFrame(animateCamera);
    }
  }, [selectedSite, camera]);

  return (
    <>
      {/* Space Environment: Deep space stars & cosmic lighting */}
      <color attach="background" args={['#030508']} />
      <Stars radius={200} depth={80} count={3500} factor={4} saturation={0.5} fade speed={1.2} />
      <SolarSystemBackdrop />

      {/* Directional Sun Light illuminating the red planet */}
      <ambientLight intensity={0.35} />
      <directionalLight position={[10, 6, 8]} intensity={1.8} castShadow />
      <pointLight position={[11, 7, -22]} intensity={2.2} distance={70} decay={1.5} color="#ffd166" />
      <pointLight position={[-10, -6, -8]} intensity={0.15} color="#45f3ff" />

      {/* 3D Mars Planet Sphere */}
      <group ref={globeRef}>
        <mesh ref={meshRef} receiveShadow castShadow>
          <sphereGeometry args={[GLOBE_RADIUS, 128, 128]} />
          <meshStandardMaterial
            map={currentTexture}
            bumpMap={bumpTexture}
            bumpScale={layerMode === 'optical' ? 0.05 : 0.08}
            roughness={0.85}
            metalness={0.05}
          />
        </mesh>

        {/* Mars Atmospheric Glow */}
        <AtmosphereGlow layerMode={layerMode} />

        {/* 3D Site Exploration Pins */}
        {sites.map((site) => (
          <SiteMarker
            key={site.id}
            site={site}
            isSelected={selectedSite?.id === site.id}
            onSelect={() => onSelectSite(site)}
          />
        ))}
      </group>

      {/* Interactive Orbit Controls with smooth damping */}
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        enableDamping
        dampingFactor={0.06}
        minDistance={3.2}
        maxDistance={9.0}
        rotateSpeed={0.65}
        zoomSpeed={0.8}
        minPolarAngle={0.12}
        maxPolarAngle={Math.PI - 0.12}
      />
    </>
  );
};
