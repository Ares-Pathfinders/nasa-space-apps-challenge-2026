import * as THREE from 'three';

export function createProceduralMarsTextures() {
  const width = 2048;
  const height = 1024;

  // 1. Optical Color Texture
  const canvasOpt = document.createElement('canvas');
  canvasOpt.width = width;
  canvasOpt.height = height;
  const ctxOpt = canvasOpt.getContext('2d')!;

  // Base Martian rust gradient
  const bgGrad = ctxOpt.createLinearGradient(0, 0, 0, height);
  bgGrad.addColorStop(0, '#e5d7c3');      // North polar ice edge
  bgGrad.addColorStop(0.08, '#c86d3b');
  bgGrad.addColorStop(0.35, '#b94e22');
  bgGrad.addColorStop(0.5, '#993a15');   // Equatorial dark albedo belts
  bgGrad.addColorStop(0.7, '#ba5728');
  bgGrad.addColorStop(0.92, '#c86d3b');
  bgGrad.addColorStop(1, '#f0e6d6');      // South polar ice cap
  ctxOpt.fillStyle = bgGrad;
  ctxOpt.fillRect(0, 0, width, height);

  // Albedo dark markings (e.g. Syrtis Major, Acidalia)
  ctxOpt.fillStyle = 'rgba(55, 25, 15, 0.45)';
  // Syrtis Major-like dark triangular patch
  ctxOpt.beginPath();
  ctxOpt.ellipse(width * 0.72, height * 0.48, width * 0.08, height * 0.16, 0.2, 0, Math.PI * 2);
  ctxOpt.fill();

  // Mare Tyrrhenum / Cimmerium belt
  ctxOpt.beginPath();
  ctxOpt.ellipse(width * 0.6, height * 0.62, width * 0.22, height * 0.09, -0.1, 0, Math.PI * 2);
  ctxOpt.fill();

  // Sinus Meridiani / Acidalia
  ctxOpt.beginPath();
  ctxOpt.ellipse(width * 0.42, height * 0.38, width * 0.12, height * 0.14, 0.1, 0, Math.PI * 2);
  ctxOpt.fill();

  // Polar ice caps
  ctxOpt.fillStyle = '#ffffff';
  ctxOpt.beginPath();
  ctxOpt.ellipse(width * 0.5, 0, width * 0.4, height * 0.06, 0, 0, Math.PI * 2);
  ctxOpt.fill();
  ctxOpt.beginPath();
  ctxOpt.ellipse(width * 0.5, height, width * 0.35, height * 0.05, 0, 0, Math.PI * 2);
  ctxOpt.fill();

  // Random impact craters and dunes
  ctxOpt.fillStyle = 'rgba(40, 18, 10, 0.25)';
  for (let i = 0; i < 280; i++) {
    const rx = Math.random() * width;
    const ry = Math.random() * height * 0.8 + height * 0.1;
    const rad = Math.random() * 14 + 2;
    ctxOpt.beginPath();
    ctxOpt.arc(rx, ry, rad, 0, Math.PI * 2);
    ctxOpt.fill();
  }

  // 2. MOLA Topographic Elevation Texture (False Color)
  const canvasTopo = document.createElement('canvas');
  canvasTopo.width = width;
  canvasTopo.height = height;
  const ctxTopo = canvasTopo.getContext('2d')!;

  const topoGrad = ctxTopo.createLinearGradient(0, 0, width, height);
  topoGrad.addColorStop(0, '#002699');    // Lowlands (Deep Blue)
  topoGrad.addColorStop(0.3, '#0099cc');   // Basin (Cyan)
  topoGrad.addColorStop(0.5, '#22aa3b');   // Mean elevation zero (Green)
  topoGrad.addColorStop(0.7, '#e0b828');   // Highlands (Yellow)
  topoGrad.addColorStop(0.85, '#cc5511');  // Volcanic swells (Orange-Red)
  topoGrad.addColorStop(1.0, '#ffffff');   // Olympus Mons peak (White)
  ctxTopo.fillStyle = topoGrad;
  ctxTopo.fillRect(0, 0, width, height);

  // Olympus Mons & Tharsis volcanic peaks in Elevation
  ctxTopo.fillStyle = '#ffffff';
  ctxTopo.beginPath();
  ctxTopo.arc(width * 0.28, height * 0.42, 28, 0, Math.PI * 2); // Olympus Mons
  ctxTopo.fill();

  ctxTopo.fillStyle = '#ff7733';
  ctxTopo.beginPath();
  ctxTopo.arc(width * 0.35, height * 0.5, 22, 0, Math.PI * 2); // Ascraeus Mons
  ctxTopo.arc(width * 0.33, height * 0.57, 22, 0, Math.PI * 2); // Pavonis Mons
  ctxTopo.arc(width * 0.31, height * 0.64, 22, 0, Math.PI * 2); // Arsia Mons
  ctxTopo.fill();

  // Hellas Planitia Basin (Deep Blue)
  ctxTopo.fillStyle = '#001a66';
  ctxTopo.beginPath();
  ctxTopo.ellipse(width * 0.7, height * 0.72, 85, 60, 0, 0, Math.PI * 2);
  ctxTopo.fill();

  // 3. Thermal Inertia / Radiation Safety Texture
  const canvasTherm = document.createElement('canvas');
  canvasTherm.width = width;
  canvasTherm.height = height;
  const ctxTherm = canvasTherm.getContext('2d')!;

  const thermGrad = ctxTherm.createLinearGradient(0, 0, width, height);
  thermGrad.addColorStop(0, '#10052a');    // Frigid / High shadow (Dark Purple)
  thermGrad.addColorStop(0.3, '#3c096c');   // Moderate thermal inertia
  thermGrad.addColorStop(0.55, '#7b2cbf');  // Bedrock exposures
  thermGrad.addColorStop(0.8, '#ff6b35');   // High daytime thermal heat
  thermGrad.addColorStop(1.0, '#ffd166');   // Maximum thermal conductivity
  ctxTherm.fillStyle = thermGrad;
  ctxTherm.fillRect(0, 0, width, height);

  // 4. Bump / Normal Relief Texture
  const canvasBump = document.createElement('canvas');
  canvasBump.width = width;
  canvasBump.height = height;
  const ctxBump = canvasBump.getContext('2d')!;
  ctxBump.fillStyle = '#808080';
  ctxBump.fillRect(0, 0, width, height);

  // Canyon Valles Marineris carved slit
  ctxBump.fillStyle = '#202020';
  ctxBump.beginPath();
  ctxBump.ellipse(width * 0.42, height * 0.54, width * 0.16, 12, 0.05, 0, Math.PI * 2);
  ctxBump.fill();

  // Bump peaks
  ctxBump.fillStyle = '#ffffff';
  ctxBump.beginPath();
  ctxBump.arc(width * 0.28, height * 0.42, 28, 0, Math.PI * 2);
  ctxBump.fill();

  const optTexture = new THREE.CanvasTexture(canvasOpt);
  const topoTexture = new THREE.CanvasTexture(canvasTopo);
  const thermTexture = new THREE.CanvasTexture(canvasTherm);
  const bumpTexture = new THREE.CanvasTexture(canvasBump);

  [optTexture, topoTexture, thermTexture, bumpTexture].forEach(t => {
    t.wrapS = THREE.RepeatWrapping;
    t.wrapT = THREE.ClampToEdgeWrapping;
    t.generateMipmaps = true;
  });

  return { optTexture, topoTexture, thermTexture, bumpTexture };
}
