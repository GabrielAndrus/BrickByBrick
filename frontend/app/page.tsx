'use client';

import { useEffect, useRef, useState } from 'react';
import InstructionBook from './components/InstructionBook';

// Demo data for instruction book (simulating loaded environment)
const demoManualData = {
  total_steps: 5,
  difficulty: "Medium",
  estimated_time_minutes: 25,
  baseplate: {
    size_studs: [32, 32],
    lego_type: "Baseplate 32x32"
  },
  steps: [
    {
      step_number: 1,
      layer_z: 0,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 0] }, rotation: 0 },
        { part_id: "3001", position: { studs: [4, 0, 0] }, rotation: 0 },
        { part_id: "3003", position: { studs: [8, 0, 0] }, rotation: 0 },
      ],
      piece_counts: { "3001": 2, "3003": 1 } as Record<string, number>,
      instructions: "Start by placing the foundation bricks"
    },
    {
      step_number: 2,
      layer_z: 1,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 1] }, rotation: 0 },
        { part_id: "3004", position: { studs: [4, 0, 1] }, rotation: 90 },
      ],
      piece_counts: { "3001": 1, "3004": 1 } as Record<string, number>,
      instructions: "Build the walls"
    },
    {
      step_number: 3,
      layer_z: 2,
      bricks_in_step: [
        { part_id: "3003", position: { studs: [0, 0, 2] }, rotation: 0 },
        { part_id: "3003", position: { studs: [2, 0, 2] }, rotation: 0 },
      ],
      piece_counts: { "3003": 2 } as Record<string, number>,
      instructions: "Add support structure"
    },
    {
      step_number: 4,
      layer_z: 3,
      bricks_in_step: [
        { part_id: "3001", position: { studs: [0, 0, 3] }, rotation: 0 },
      ],
      piece_counts: { "3001": 1 } as Record<string, number>,
      instructions: "Continue walls upward"
    },
    {
      step_number: 5,
      layer_z: 4,
      bricks_in_step: [
        { part_id: "3068", position: { studs: [0, 0, 4] }, rotation: 0 },
      ],
      piece_counts: { "3068": 1 } as Record<string, number>,
      instructions: "Add the roof tiles"
    }
  ],
  layer_summary: {
    0: "Foundation layer",
    1: "First floor walls",
    2: "Support beams",
    3: "Upper walls", 
    4: "Roof"
  }
};

const demoPieceCount = {
  total_pieces: 47,
  total_unique: 4,
  breakdown: [
    { part_id: "3001", color_id: 5, quantity: 18, piece_name: "Brick 2x4" },
    { part_id: "3003", color_id: 1, quantity: 15, piece_name: "Brick 2x2" },
    { part_id: "3004", color_id: 15, quantity: 8, piece_name: "Brick 1x2" },
    { part_id: "3068", color_id: 7, quantity: 6, piece_name: "Tile 2x2" },
  ]
};

export default function Home() {
  const brickContainerRef = useRef<HTMLDivElement>(null);
  const [showInstructionBook, setShowInstructionBook] = useState(false);
  const [hasEnvironment, setHasEnvironment] = useState(false); // Set to true when environment is loaded

  useEffect(() => {
    // Dynamically import Three.js only on client side
    const initThreeJS = async () => {
      if (!brickContainerRef.current) return;
      
      const THREE = await import('three');
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');

      const container = brickContainerRef.current;
      const width = container.clientWidth;
      const height = container.clientHeight;

      // Scene setup
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xe4e4e4);

      const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
      camera.position.set(4, 3, 5);

      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.domElement.style.display = 'block';
      renderer.domElement.style.width = '100%';
      renderer.domElement.style.height = '100%';
      container.appendChild(renderer.domElement);

      // Controls
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.autoRotate = true;
      controls.autoRotateSpeed = 2;
      controls.target.set(0, 1, 0);

      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      scene.add(ambientLight);

      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
      directionalLight.position.set(5, 10, 5);
      directionalLight.castShadow = true;
      scene.add(directionalLight);

      // Create text texture for brick faces
      const createTextTexture = (text: string, bgColor: string) => {
        const canvas = document.createElement('canvas');
        canvas.width = 512;
        canvas.height = 256;
        const ctx = canvas.getContext('2d')!;
        
        // Background
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Text - using Montserrat font (same as site)
        ctx.fillStyle = '#ffffff';
        ctx.font = '800 72px Montserrat, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);
        
        const texture = new THREE.CanvasTexture(canvas);
        texture.needsUpdate = true;
        return texture;
      };

      // LEGO Brick creation function with text
      const createLegoBrick = (color: number, colorHex: string, width: number, depth: number, y: number, text: string) => {
        const group = new THREE.Group();
        
        // Main brick body
        const brickHeight = 0.96;
        const geometry = new THREE.BoxGeometry(width * 0.8, brickHeight, depth * 0.8);
        
        // Create materials array for each face (right, left, top, bottom, front, back)
        const textTexture = createTextTexture(text, colorHex);
        const baseMaterial = new THREE.MeshStandardMaterial({ 
          color, 
          roughness: 0.3,
          metalness: 0.1
        });
        const textMaterial = new THREE.MeshStandardMaterial({ 
          map: textTexture,
          roughness: 0.3,
          metalness: 0.1
        });
        
        // Materials: [+X, -X, +Y, -Y, +Z (front), -Z (back)]
        const materials = [
          baseMaterial, // right
          baseMaterial, // left
          baseMaterial, // top
          baseMaterial, // bottom
          textMaterial, // front - show text
          baseMaterial, // back
        ];
        
        const brick = new THREE.Mesh(geometry, materials);
        brick.castShadow = true;
        brick.receiveShadow = true;
        group.add(brick);

        // Add studs on top
        const studGeometry = new THREE.CylinderGeometry(0.24, 0.24, 0.17, 16);
        const studMaterial = new THREE.MeshStandardMaterial({ 
          color, 
          roughness: 0.3,
          metalness: 0.1
        });
        
        for (let x = 0; x < width; x++) {
          for (let z = 0; z < depth; z++) {
            const stud = new THREE.Mesh(studGeometry, studMaterial);
            stud.position.set(
              (x - (width - 1) / 2) * 0.8,
              brickHeight / 2 + 0.085,
              (z - (depth - 1) / 2) * 0.8
            );
            stud.castShadow = true;
            group.add(stud);
          }
        }

        group.position.y = y;
        return group;
      };

      // Create stacked bricks - "PIECE BY PIECE"
      const redBrick = createLegoBrick(0xc91a09, '#c91a09', 4, 2, 0, 'PIECE');
      redBrick.position.x = -0.4;
      scene.add(redBrick);

      const blueBrick = createLegoBrick(0x0055bf, '#0055bf', 4, 2, 1.13, 'BY');
      blueBrick.position.x = 0.2;
      scene.add(blueBrick);

      const yellowBrick = createLegoBrick(0xf2cd37, '#f2cd37', 4, 2, 2.26, 'PIECE');
      yellowBrick.position.x = 0.6;
      scene.add(yellowBrick);

      // Animation loop
      const animate = () => {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();

      // Handle resize
      const handleResize = () => {
        if (!container) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h, false);
      };
      window.addEventListener('resize', handleResize);
      
      // Initial resize to ensure proper fit
      handleResize();

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize);
        container.removeChild(renderer.domElement);
        renderer.dispose();
      };
    };

    initThreeJS();
  }, []);

  return (
    <>
      <header>
        <div className="header-left">
          <img src="/Brick.png" alt="Brick by Brick" className="header-logo-img" />
        </div>
        <div className="header-center"></div>
        <div className="header-right">
          <div className="icon-box">
            <i className="fa-brands fa-github"></i>
          </div>
          <div className="icon-box">
            <img src="/MLH.png" alt="MLH" className="mlh-logo-img" />
          </div>
          <div className="icon-box" style={{ border: 'none' }}>
            <img src="/uofthacks.png" alt="UofT Hacks" className="uofthacks-logo-img" />
          </div>
        </div>
      </header>

      <div className="hero-section">
        <div className="content-wrapper">
          <div className="text-section">
            <h1>Build<br/>your <em>identity,</em></h1>
            <p className="tagline">piece by piece.</p>
            <p>
              Transform your space into a buildable LEGO set. Upload your room, 
              and we'll generate a brick-by-brick recreation complete with 
              step-by-step instructions.
            </p>
            <p>
              Your memories, your space, your story — now in LEGO form.
            </p>
          </div>
          <div className="visual-section">
            <div className="brick-viewer-container" ref={brickContainerRef}></div>
          </div>
        </div>
      </div>

      <div className="builder-container">
        <div className="builder-top-row">
          <div className="env-wrapper">
            <div className="panel-header header-bg-red">Environment</div>
            <div className="panel panel-content">
              <div className="canvas-placeholder">
                this part is just<br/>whatever the 3d<br/>model is
              </div>
              <div className="zoom-controls">
                <div className="zoom-btn">
                  <i className="fa-solid fa-expand"></i>
                </div>
                <div className="zoom-btn">
                  <i className="fa-solid fa-plus"></i>
                </div>
                <div className="zoom-btn">
                  <i className="fa-solid fa-minus"></i>
                </div>
              </div>
              <button 
                className="view-details-btn"
                onClick={() => setShowInstructionBook(true)}
              >
                <i className="fa-solid fa-book"></i>
                View Details
              </button>
            </div>
          </div>

          <div className="obj-wrapper">
            <div className="panel-header header-bg-cyan">Objects</div>
            <div className="panel panel-content">
              <div className="objects-grid">
                <div className="obj-item"></div>
                <div className="obj-item"></div>
                <div className="obj-item"></div>
                <div className="obj-item"></div>
                <div className="obj-add">
                  <i className="fa-solid fa-plus"></i>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="full-set-row">
          <div className="panel-header header-bg-orange">Full Set</div>
          <div className="box-art-container">
            <div className="lego-box-perspective">
              <div className="box-spine">
                <div className="spine-logo">B<span>B</span></div>
                <div className="spine-age">9+</div>
                <div className="spine-sku">202601</div>
                <div className="spine-line"></div>
                
                <div className="spine-name">Name of<br/>Lego Set</div>
                <div className="spine-pcs">XXX<br/>pcs/pzs</div>
                <div className="spine-sub">Building Toy<br/>Jouet de construction</div>
              </div>
              <div className="box-front">
                <div className="box-front-text">3d model of the<br/>environment +<br/>objects</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Instruction Book Modal */}
      {showInstructionBook && (
        <InstructionBook
          projectName={hasEnvironment ? "My Room Build" : "No Environment"}
          manual={hasEnvironment ? demoManualData : {
            total_steps: 0,
            difficulty: "N/A",
            estimated_time_minutes: 0,
            steps: [],
            layer_summary: {}
          }}
          pieceCount={hasEnvironment ? demoPieceCount : {
            total_pieces: 0,
            total_unique: 0,
            breakdown: []
          }}
          isOpen={showInstructionBook}
          onClose={() => setShowInstructionBook(false)}
        />
      )}
    </>
  )
}
