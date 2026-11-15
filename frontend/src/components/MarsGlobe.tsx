import React, { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Html } from '@react-three/drei';
import * as THREE from 'three';
import { ExplorationSite, LayerMode, RoverId } from '../types/mars';
import { createProceduralMarsTextures } from './MarsTextures';
import marsSurfaceTextureUrl from '../../images/8k_mars.jpg';
import mercuryTextureUrl from '../../images/2k_mercury.jpg';
import venusTextureUrl from '../../images/2k_venus_surface.jpg';
import earthTextureUrl from '../../images/2k_earth_daymap.jpg';
import moonTextureUrl from '../../images/2k_moon.jpg';
import jupiterTextureUrl from '../../images/2k_jupiter.jpg';
import saturnTextureUrl from '../../images/2k_saturn.jpg';
import saturnRingTextureUrl from '../../images/2k_saturn_ring_alpha.png';
import uranusTextureUrl from '../../images/2k_uranus.jpg';
import neptuneTextureUrl from '../../images/2k_neptune.jpg';
import sunTextureUrl from '../../images/2k_sun.jpg';

interface MarsGlobeProps {
  sites: ExplorationSite[];
  selectedSite: ExplorationSite | null;
  onSelectSite: (site: ExplorationSite) => void;
  onOpenRoverMap: (rover: RoverId) => void;
  focusRover: RoverId | null;
  layerMode: LayerMode;
}

const GLOBE_RADIUS = 0.9;
const SUN_POSITION: [number, number, number] = [0, 0, 0];
const ORBIT_SCALE = 25;
const MARS_ORBIT_RADIUS = 1.52 * ORBIT_SCALE;
const MARS_POSITION: [number, number, number] = [MARS_ORBIT_RADIUS, 0, 0];
const ROVER_LOCATIONS: Record<RoverId, {
  latitude: number;
  longitude: number;
  color: string;
  label: string;
}> = {
  curiosity: {
    latitude: -4.78530567,
    longitude: 137.41715099,
    color: '#62f6a5',
    label: 'CURIOSITY // MAPA TÁCTICO',
  },
  perseverance: {
    latitude: 18.43559434,
    longitude: 77.23322287,
    color: '#ffb703',
    label: 'PERSEVERANCE // MAPA TÁCTICO',
  },
};

function scaledOrbit(astronomicalUnits: number): number {
  return astronomicalUnits * ORBIT_SCALE;
}

function orbitPosition(radius: number, angle: number): [number, number, number] {
  return [
    SUN_POSITION[0] + Math.cos(angle) * radius,
    SUN_POSITION[1],
    SUN_POSITION[2] + Math.sin(angle) * radius,
  ];
}

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

const RoverMarker: React.FC<{ rover: RoverId; onOpen: () => void }> = ({ rover, onOpen }) => {
  const markerRef = useRef<THREE.Group>(null);
  const visualRef = useRef<THREE.Group>(null);
  const { camera } = useThree();
  const { latitude, longitude, color, label } = ROVER_LOCATIONS[rover];
  const position = useMemo(
    () => latLonToVector3(latitude, longitude, GLOBE_RADIUS * 1.018),
    [latitude, longitude],
  );

  useFrame(() => {
    if (!markerRef.current || !visualRef.current) return;
    const markerWorldPosition = new THREE.Vector3();
    markerRef.current.getWorldPosition(markerWorldPosition);
    const cameraDistance = camera.position.distanceTo(markerWorldPosition);
    const constantScreenScale = THREE.MathUtils.clamp(cameraDistance / 6.4, 0.04, 2);
    visualRef.current.scale.setScalar(constantScreenScale);
  });

  return (
    <group ref={markerRef} position={position}>
      <group ref={visualRef}>
        <mesh onClick={(event) => { event.stopPropagation(); onOpen(); }}>
          <sphereGeometry args={[0.035, 20, 20]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.2} />
        </mesh>
        <mesh onClick={(event) => { event.stopPropagation(); onOpen(); }} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.052, 0.075, 32]} />
          <meshBasicMaterial color={color} transparent opacity={0.95} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <Html position={[0, 0.16, 0]} center className="pointer-events-auto">
        <button
          onClick={onOpen}
          style={{ color, borderColor: color, boxShadow: `0 0 14px ${color}80` }}
          className="flex items-center gap-1.5 whitespace-nowrap border bg-black/85 px-2 py-1 font-mono text-[10px] transition-transform hover:scale-105"
        >
          <span className="h-1.5 w-1.5 animate-pulse rounded-full" style={{ backgroundColor: color }} />
          {label}
        </button>
      </Html>
    </group>
  );
};

// Subtle atmospheric glow shell
const SolarSystemBackdrop: React.FC = () => {
  const textures = useMemo(() => {
    const loader = new THREE.TextureLoader();
    const loadColorTexture = (url: string) => {
      const texture = loader.load(url);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = 4;
      return texture;
    };

    return {
      sun: loadColorTexture(sunTextureUrl),
      mercury: loadColorTexture(mercuryTextureUrl),
      venus: loadColorTexture(venusTextureUrl),
      earth: loadColorTexture(earthTextureUrl),
      moon: loadColorTexture(moonTextureUrl),
      jupiter: loadColorTexture(jupiterTextureUrl),
      saturn: loadColorTexture(saturnTextureUrl),
      uranus: loadColorTexture(uranusTextureUrl),
      neptune: loadColorTexture(neptuneTextureUrl),
      saturnRing: loader.load(saturnRingTextureUrl),
    };
  }, []);

  return (
  <group renderOrder={-1}>
    {/* A distant sun provides a visible reference point and warm directional light. */}
    <group position={SUN_POSITION}>
      <mesh>
        <sphereGeometry args={[2.1, 32, 32]} />
        <meshBasicMaterial map={textures.sun} />
      </mesh>
    </group>

    {/* Every orbit is centered on the visible Sun, with one path per planet. */}
    {[0.39, 0.72, 1, 1.52, 5.2, 9.58, 19.2, 30.1].map((astronomicalUnits) => {
      const radius = scaledOrbit(astronomicalUnits);
      return (
      <mesh key={astronomicalUnits} rotation={[Math.PI / 2, 0, 0]} position={SUN_POSITION}>
        <torusGeometry args={[radius, 0.012, 8, 160]} />
        <meshBasicMaterial color="#c69b62" transparent opacity={0.2} depthWrite={false} />
      </mesh>
      );
    })}

    {/* Stylized distant planets. Their scale is intentionally exaggerated for the HUD view. */}
    <mesh position={orbitPosition(scaledOrbit(0.39), 0.5)}>
      <sphereGeometry args={[0.65, 24, 24]} />
      <meshStandardMaterial map={textures.mercury} roughness={0.9} />
    </mesh>
    <mesh position={orbitPosition(scaledOrbit(1), 1.7)}>
      <sphereGeometry args={[1.45, 24, 24]} />
      <meshStandardMaterial map={textures.earth} roughness={0.75} metalness={0.05} />
    </mesh>
    <mesh position={orbitPosition(scaledOrbit(0.72), 1.1)}>
      <sphereGeometry args={[1.35, 24, 24]} />
      <meshStandardMaterial map={textures.venus} roughness={0.92} />
    </mesh>
    <mesh position={[orbitPosition(scaledOrbit(1), 1.7)[0] + 0.14, 0.1, orbitPosition(scaledOrbit(1), 1.7)[2] - 0.1]}>
      <sphereGeometry args={[0.35, 20, 20]} />
      <meshStandardMaterial map={textures.moon} roughness={0.95} />
    </mesh>
    <group position={orbitPosition(scaledOrbit(9.58), 3)}>
      <mesh>
        <sphereGeometry args={[3.9, 24, 24]} />
        <meshStandardMaterial map={textures.saturn} roughness={0.8} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[4.45, 6.35, 128]} />
        <meshBasicMaterial
          map={textures.saturnRing}
          alphaMap={textures.saturnRing}
          transparent
          opacity={0.88}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
    <mesh position={orbitPosition(scaledOrbit(19.2), 3.7)}>
      <sphereGeometry args={[1.9, 24, 24]} />
      <meshStandardMaterial map={textures.uranus} roughness={0.7} />
    </mesh>
    <mesh position={orbitPosition(scaledOrbit(5.2), 2.4)}>
      <sphereGeometry args={[5.0, 24, 24]} />
      <meshStandardMaterial map={textures.jupiter} roughness={0.8} />
    </mesh>
    <mesh position={orbitPosition(scaledOrbit(30.1), 4.4)}>
      <sphereGeometry args={[1.85, 24, 24]} />
      <meshStandardMaterial map={textures.neptune} roughness={0.7} />
    </mesh>
  </group>
  );
};

export const MarsGlobe: React.FC<MarsGlobeProps> = ({
  sites,
  selectedSite,
  onSelectSite,
  onOpenRoverMap,
  focusRover,
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

  React.useEffect(() => {
    const marsCenter = new THREE.Vector3(...MARS_POSITION);
    camera.position.set(marsCenter.x, marsCenter.y + 0.4, marsCenter.z + 6.4);
    camera.lookAt(marsCenter);
    if (controlsRef.current) {
      controlsRef.current.target.copy(marsCenter);
      controlsRef.current.update();
    }
  }, [camera]);

  React.useEffect(() => {
    if (focusRover || !controlsRef.current) return;

    const marsCenter = new THREE.Vector3(...MARS_POSITION);
    camera.position.set(marsCenter.x, marsCenter.y + 0.4, marsCenter.z + 6.4);
    camera.lookAt(marsCenter);
    controlsRef.current.enabled = true;
    controlsRef.current.minDistance = 3.2;
    controlsRef.current.target.copy(marsCenter);
    controlsRef.current.update();
  }, [focusRover, camera]);

  // Slow ambient rotation of Mars
  useFrame((_, delta) => {
    if (globeRef.current && !focusRover) {
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
      const marsWorldPosition = new THREE.Vector3(...MARS_POSITION);
      const camTarget = targetPos.multiplyScalar(1.9).add(marsWorldPosition);
      const globeCenter = marsWorldPosition.clone();
      
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

  React.useEffect(() => {
    if (!focusRover || !controlsRef.current) return;

    const controls = controlsRef.current;
    const transitionMinDistance = 0.01;
    controls.enabled = false;
    controls.minDistance = transitionMinDistance;

    const roverPosition = new THREE.Vector3(...MARS_POSITION);
    const roverLocation = ROVER_LOCATIONS[focusRover];
    const roverLocalSurface = latLonToVector3(
      roverLocation.latitude,
      roverLocation.longitude,
      GLOBE_RADIUS,
    );
    // The marker is a child of the rotating Mars group, so its world position
    // must include the globe's current rotation before we aim the camera.
    const globeRotation = globeRef.current?.rotation.y ?? 0;
    const roverSurface = roverLocalSurface
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), globeRotation)
      .add(roverPosition);
    const startRelativeCamera = camera.position.clone().sub(roverPosition);
    const startRadius = startRelativeCamera.length();
    const startDirection = startRelativeCamera.normalize();
    const endDirection = roverSurface.clone().sub(roverPosition).normalize();
    const orbitRotation = new THREE.Quaternion().setFromUnitVectors(startDirection, endDirection);
    const endRadius = GLOBE_RADIUS + 0.15;
    const safeOrbitRadius = Math.max(startRadius, GLOBE_RADIUS + 1.4);
    const endTarget = roverSurface.clone();
    const startTarget = roverPosition.clone();
    controls.target.copy(startTarget);
    const startTime = performance.now();
    const duration = 6500;

    const animateLocalFocus = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = 0.5 - Math.cos(progress * Math.PI) / 2;
      // Finish the orbital reorientation before moving the camera into the
      // close-up distance, avoiding a line of sight through Mars.
      const rotationProgress = THREE.MathUtils.smoothstep(progress, 0, 0.68);
      const zoomProgress = THREE.MathUtils.smoothstep(progress, 0.58, 1);
      const partialRotation = new THREE.Quaternion().slerp(orbitRotation, rotationProgress);
      const orbitDirection = startDirection.clone().applyQuaternion(partialRotation).normalize();
      const orbitRadius = THREE.MathUtils.lerp(safeOrbitRadius, endRadius, zoomProgress);
      camera.position.copy(roverPosition).add(orbitDirection.multiplyScalar(orbitRadius));
      controls.target.lerpVectors(startTarget, endTarget, zoomProgress);
      controls.update();
      if (progress < 1) {
        requestAnimationFrame(animateLocalFocus);
      } else {
        // Keep the final transition zoom instead of letting OrbitControls pull back.
        controls.target.copy(endTarget);
        camera.lookAt(endTarget);
        controls.minDistance = 0.12;
        controls.enabled = true;
      }
    };

    requestAnimationFrame(animateLocalFocus);
  }, [focusRover, camera]);

  return (
    <>
      {/* Space Environment: Deep space stars & cosmic lighting */}
      <color attach="background" args={['#030508']} />
      <Stars radius={200} depth={80} count={3500} factor={4} saturation={0.5} fade speed={1.2} />
      <Stars radius={420} depth={220} count={2600} factor={1.1} saturation={0.25} fade speed={0.2} />
      <SolarSystemBackdrop />

      {/* Directional Sun Light illuminating the red planet */}
      <ambientLight intensity={0.16} />
      <directionalLight
        position={SUN_POSITION}
        rotation={[0, Math.PI / 2, 0]}
        intensity={3.2}
        castShadow
      />
      <pointLight position={SUN_POSITION} intensity={900} distance={0} decay={2} color="#fff1cf" />

      {/* 3D Mars Planet Sphere */}
      <group ref={globeRef} position={MARS_POSITION}>
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

        {/* 3D Site Exploration Pins */}
        {sites.map((site) => (
          <SiteMarker
            key={site.id}
            site={site}
            isSelected={selectedSite?.id === site.id}
            onSelect={() => onSelectSite(site)}
          />
        ))}
        <RoverMarker rover="curiosity" onOpen={() => onOpenRoverMap('curiosity')} />
        <RoverMarker rover="perseverance" onOpen={() => onOpenRoverMap('perseverance')} />
      </group>

      {/* Interactive Orbit Controls with smooth damping */}
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        enableDamping
        dampingFactor={0.06}
        minDistance={3.2}
        maxDistance={1500}
        rotateSpeed={0.65}
        zoomSpeed={0.8}
        minPolarAngle={0.12}
        maxPolarAngle={Math.PI - 0.12}
      />
    </>
  );
};
