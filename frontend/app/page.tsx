'use client'

import { useEffect, useRef, useState } from 'react'
import { DotLottieReact } from '@lottiefiles/dotlottie-react'
import { useConnection, useWallet } from '@solana/wallet-adapter-react'
import { useWalletModal } from '@solana/wallet-adapter-react-ui'
import InstructionBook from './components/InstructionBook'
import { ModelDetailsDisplay } from './components/ModelDetailsDisplay'
import { 
  processManifestWithBackboard, 
  loadManifestFromFile,
  type InstructionManual,
  type PieceCount,
  type LegoMemoryEntry 
} from '../lib/legoManualGenerator'
import { convertVideoTo3DObject, executeAndAddObject } from '../lib/videoToThreeJS'
import { buildMemoTransaction } from '../lib/bbCoin'

// Default empty data for when no build is loaded
const emptyManualData: InstructionManual = {
  total_steps: 0,
  difficulty: "N/A",
  estimated_time_minutes: 0,
  steps: [],
  layer_summary: {}
}

const emptyPieceCount: PieceCount = {
  total_pieces: 0,
  total_unique: 0,
  breakdown: [],
  by_category: {},
  by_color: {},
  estimated_cost: 0
}

const NFT_GRADIENTS = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #9945ff 0%, #14f195 100%)',
]
function hashId(s: string) { let h = 0; for (let i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i) | 0; return Math.abs(h) }

// Hardcoded sample BB Coins (date, build metadata, pieces)
type CoinEntry = {
  id: string
  projectName: string
  date: string
  buildId: string
  totalPieces: number
  difficulty?: string
  estimatedTimeMinutes?: number
  breakdown: Array<{ part_id: string; quantity: number; piece_name?: string; color_name?: string }>
}
const SAMPLE_COINS: CoinEntry[] = [
  {
    id: 'sample-1',
    projectName: 'My Dorm Room',
    date: '2025-01-15T14:30:00Z',
    buildId: 'build-dorm-001',
    totalPieces: 247,
    difficulty: 'Intermediate',
    estimatedTimeMinutes: 120,
    breakdown: [
      { part_id: '3001', quantity: 45, piece_name: 'Brick 2×4', color_name: 'Red' },
      { part_id: '3003', quantity: 32, piece_name: 'Brick 2×2', color_name: 'Blue' },
      { part_id: '3022', quantity: 28, piece_name: 'Plate 2×2', color_name: 'White' },
      { part_id: '3020', quantity: 18, piece_name: 'Plate 2×4', color_name: 'Light Bluish Gray' },
      { part_id: '3832', quantity: 1, piece_name: 'Baseplate 32×32', color_name: 'Dark Tan' },
      { part_id: '3068', quantity: 24, piece_name: 'Tile 2×2', color_name: 'Black' },
      { part_id: '3004', quantity: 36, piece_name: 'Brick 1×2', color_name: 'Bright Green' },
      { part_id: '3005', quantity: 63, piece_name: 'Brick 1×1', color_name: 'Yellow' },
    ],
  },
  {
    id: 'sample-2',
    projectName: 'Campus Café',
    date: '2025-01-10T09:15:00Z',
    buildId: 'build-cafe-002',
    totalPieces: 189,
    difficulty: 'Beginner',
    estimatedTimeMinutes: 90,
    breakdown: [
      { part_id: '3001', quantity: 52, piece_name: 'Brick 2×4', color_name: 'Reddish Brown' },
      { part_id: '3023', quantity: 40, piece_name: 'Plate 1×2', color_name: 'Tan' },
      { part_id: '3622', quantity: 22, piece_name: 'Brick 1×3', color_name: 'White' },
      { part_id: '3069', quantity: 18, piece_name: 'Tile 1×2', color_name: 'Black' },
      { part_id: '3034', quantity: 2, piece_name: 'Plate 2×8', color_name: 'Dark Bluish Gray' },
      { part_id: '3002', quantity: 30, piece_name: 'Brick 2×3', color_name: 'Orange' },
      { part_id: '3070', quantity: 25, piece_name: 'Tile 1×1', color_name: 'Trans-Clear' },
    ],
  },
  {
    id: 'sample-3',
    projectName: 'Study Nook',
    date: '2025-01-05T16:45:00Z',
    buildId: 'build-study-003',
    totalPieces: 312,
    difficulty: 'Advanced',
    estimatedTimeMinutes: 180,
    breakdown: [
      { part_id: '3001', quantity: 68, piece_name: 'Brick 2×4', color_name: 'Blue' },
      { part_id: '3003', quantity: 44, piece_name: 'Brick 2×2', color_name: 'Dark Gray' },
      { part_id: '3020', quantity: 38, piece_name: 'Plate 2×4', color_name: 'Light Gray' },
      { part_id: '3040', quantity: 16, piece_name: 'Slope 45° 2×1', color_name: 'Red' },
      { part_id: '3022', quantity: 42, piece_name: 'Plate 2×2', color_name: 'Green' },
      { part_id: '3004', quantity: 55, piece_name: 'Brick 1×2', color_name: 'White' },
      { part_id: '3297', quantity: 12, piece_name: 'Slope 33° 2×2', color_name: 'Black' },
      { part_id: '3021', quantity: 20, piece_name: 'Plate 2×3', color_name: 'Yellow' },
      { part_id: '3005', quantity: 17, piece_name: 'Brick 1×1', color_name: 'Orange' },
    ],
  },
]

function LoadingOverlayInner({
  isFadingOut,
  uploading,
  uploadStatus,
}: {
  isFadingOut: boolean
  uploading: boolean
  uploadStatus: string | null
}) {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setReady(true))
    return () => cancelAnimationFrame(id)
  }, [])
  return (
    <div
      className={`loading-overlay ${!ready ? 'loading-overlay--fade-in' : ''} ${isFadingOut ? 'loading-overlay--fade-out' : ''}`}
    >
      <DotLottieReact
        src="/Comp 1.lottie"
        loop
        autoplay
        style={{ width: 420, height: 420 }}
      />
      {uploading && uploadStatus && (
        <p className="loading-overlay-status">{uploadStatus}</p>
      )}
    </div>
  )
}

export default function Home() {
  const brickContainerRef = useRef<HTMLDivElement>(null)
  const envContainerRef = useRef<HTMLDivElement>(null)
  const envPanelRef = useRef<HTMLDivElement>(null)
  const [showInstructionBook, setShowInstructionBook] = useState(false)
  const [showNothingModal, setShowNothingModal] = useState(false)
  const [hasEnvironment, setHasEnvironment] = useState(false) // Set to true when environment is loaded
  const [videoFile, setVideoFile] = useState<File | null>(null)
  const [videoPreview, setVideoPreview] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const [showThreeJS, setShowThreeJS] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const threeJSRendererRef = useRef<any>(null)
  
  // LEGO Build Data (from Backboard + Greedy Algorithm)
  const [buildData, setBuildData] = useState<LegoMemoryEntry | null>(null)
  const [manualData, setManualData] = useState<InstructionManual>(emptyManualData)
  const [pieceCount, setPieceCount] = useState<PieceCount>(emptyPieceCount)
  const [projectName, setProjectName] = useState<string>("My Dorm Room")
  
  // Confirmation modal for removing environment
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)
  
  // LEGO design toggle
  // Objects state
  const [objects, setObjects] = useState<Array<{ id: string; name: string; mesh: any; modelAnalysis?: any }>>([])
  const [objectFileInputRef, setObjectFileInputRef] = useState<HTMLInputElement | null>(null)
  const [addingObject, setAddingObject] = useState(false)
  const [selectedModelAnalysis, setSelectedModelAnalysis] = useState<any>(null)
  const [showModelDetails, setShowModelDetails] = useState(false)

  // Solana: BB Coin (send LEGO set metadata on-chain)
  const { connection } = useConnection()
  const { publicKey, sendTransaction } = useWallet()
  const { setVisible: setWalletModalVisible } = useWalletModal()
  const [bbCoinSending, setBbCoinSending] = useState(false)
  const [bbCoinStatus, setBbCoinStatus] = useState<string | null>(null)

  // BB Coins popup: login first, then show user coins (hardcoded samples for now)
  const [showCoinsPopup, setShowCoinsPopup] = useState(false)
  const [hoveredCoin, setHoveredCoin] = useState<CoinEntry | null>(null)
  const hoverLeaveRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const coins = SAMPLE_COINS

  // Initial load: 3 second Lottie splash
  const [initialLoadDone, setInitialLoadDone] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setInitialLoadDone(true), 5000)
    return () => clearTimeout(t)
  }, [])

  const showLoader = !initialLoadDone || uploading
  const [isFadingOut, setIsFadingOut] = useState(false)
  const fadeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (showLoader) {
      if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current)
      fadeTimeoutRef.current = null
      setIsFadingOut(false)
    } else {
      setIsFadingOut(true)
      fadeTimeoutRef.current = setTimeout(() => {
        setIsFadingOut(false)
        fadeTimeoutRef.current = null
      }, 500)
    }
    return () => { if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current) }
  }, [showLoader])

  const showOverlay = showLoader || isFadingOut

  // Fullscreen toggle handler
  const toggleFullscreen = () => {
    if (!envPanelRef.current) return
    
    if (!isFullscreen) {
      // Enter fullscreen
      if (envPanelRef.current.requestFullscreen) {
        envPanelRef.current.requestFullscreen()
      } else if ((envPanelRef.current as any).webkitRequestFullscreen) {
        (envPanelRef.current as any).webkitRequestFullscreen()
      }
      setIsFullscreen(true)
    } else {
      // Exit fullscreen
      if (document.exitFullscreen) {
        document.exitFullscreen()
      } else if ((document as any).webkitExitFullscreen) {
        (document as any).webkitExitFullscreen()
      }
      setIsFullscreen(false)
    }
  }

  // Listen for fullscreen change events
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange)
    
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange)
    }
  }, [])

  useEffect(() => {
    if (!showThreeJS || !envContainerRef.current) return

    // Clean up any existing renderer
    if (threeJSRendererRef.current) {
      threeJSRendererRef.current.cleanup()
      threeJSRendererRef.current = null
    }

    const container = envContainerRef.current
    while (container.firstChild) container.removeChild(container.firstChild)

    const timer = setTimeout(async () => {
      try {
        await initDormRoomThreeJS()
      } catch (error) {
        console.error('Error initializing Three.js:', error)
      }
    }, 100)

    return () => {
      clearTimeout(timer)
      if (threeJSRendererRef.current) {
        threeJSRendererRef.current.cleanup()
        threeJSRendererRef.current = null
      }
    }
  }, [showThreeJS])

  // Cleanup Three.js when component unmounts
  useEffect(() => {
    return () => {
      if (threeJSRendererRef.current) {
        threeJSRendererRef.current.cleanup()
        threeJSRendererRef.current = null
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    console.log('File selected:', file?.name, file?.type)
    if (file && file.type.startsWith('video/')) {
      setVideoFile(file)
      const url = URL.createObjectURL(file)
      setVideoPreview(url)
      setUploadStatus(null)
      console.log('Video preview set')
    } else {
      setUploadStatus('Please select a valid video file')
      console.error('Invalid file type:', file?.type)
    }
  }

  const initDormRoomThreeJS = async () => {
    if (!envContainerRef.current) return

    const THREE = await import('three')
    const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')

    const container = envContainerRef.current
    const width = container.clientWidth
    const height = container.clientHeight

    // Scene setup
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf2f2f0)
    scene.fog = new THREE.Fog(0xf2f2f0, 2, 15)

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100)
    camera.position.set(3, 2.5, 3)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.domElement.style.display = 'block'
    renderer.domElement.style.width = '100%'
    renderer.domElement.style.height = '100%'
    renderer.domElement.style.position = 'absolute'
    renderer.domElement.style.top = '0'
    renderer.domElement.style.left = '0'
    container.appendChild(renderer.domElement)
    console.log('Canvas appended to container')

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.set(0, 1, 0)
    controls.enableDamping = true

    // Materials
    const materials = {
      floor: new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.9 }),
      wall: new THREE.MeshStandardMaterial({ color: 0xfdfdfd, roughness: 0.8 }),
      woodLight: new THREE.MeshStandardMaterial({ color: 0xeebb99, roughness: 0.6 }),
      woodDark: new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.5 }),
      metalBlack: new THREE.MeshStandardMaterial({ color: 0x111111, metalness: 0.6, roughness: 0.4 }),
      fabricBlue: new THREE.MeshStandardMaterial({ color: 0x334488, roughness: 1.0 }),
      plasticWhite: new THREE.MeshStandardMaterial({ color: 0xeeeeee, roughness: 0.3 }),
      poohYellow: new THREE.MeshStandardMaterial({ color: 0xffcc00, roughness: 1.0 }),
      poohRed: new THREE.MeshStandardMaterial({ color: 0xcc2222, roughness: 1.0 }),
      coneOrange: new THREE.MeshStandardMaterial({ color: 0xff6600, roughness: 0.4 }),
      cork: new THREE.MeshStandardMaterial({ color: 0xccaa88, roughness: 1.0 })
    }

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambientLight)

    const ceilingLight = new THREE.PointLight(0xffffee, 0.8, 10)
    ceilingLight.position.set(0, 2.8, 0)
    ceilingLight.castShadow = true
    scene.add(ceilingLight)

    // 1. ROOM SHELL
    const roomGroup = new THREE.Group()
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(5, 5), materials.floor)
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    roomGroup.add(floor)

    const wallBack = new THREE.Mesh(new THREE.BoxGeometry(5, 3, 0.1), materials.wall)
    wallBack.position.set(0, 1.5, -2.5)
    roomGroup.add(wallBack)

    const wallRight = new THREE.Mesh(new THREE.BoxGeometry(0.1, 3, 5), materials.wall)
    wallRight.position.set(2.5, 1.5, 0)
    roomGroup.add(wallRight)

    const wallLeft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 3, 5), materials.wall)
    wallLeft.position.set(-2.5, 1.5, 0)
    roomGroup.add(wallLeft)
    scene.add(roomGroup)

    // 2. WALL SHELVES
    function createClutter(width: number) {
      const group = new THREE.Group()
      const colors = [0xffffff, 0x333333, 0xaa5555, 0x55aa55]
      for (let i = 0; i < 8; i++) {
        const h = 0.1 + Math.random() * 0.15
        const r = 0.03 + Math.random() * 0.03
        const geo = Math.random() > 0.5 
          ? new THREE.BoxGeometry(r * 2, h, r * 2) 
          : new THREE.CylinderGeometry(r, r, h)
        const mat = new THREE.MeshStandardMaterial({ 
          color: colors[Math.floor(Math.random() * colors.length)] 
        })
        const item = new THREE.Mesh(geo, mat)
        item.position.set((Math.random() - 0.5) * width * 0.8, h / 2, (Math.random() - 0.5) * 0.1)
        group.add(item)
      }
      return group
    }

    const shelfGroup = new THREE.Group()
    for (let i = 0; i < 3; i++) {
      const plank = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.05, 0.25), materials.woodLight)
      plank.position.set(0, i * 0.4, 0)
      plank.castShadow = true
      shelfGroup.add(plank)

      const bracket1 = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.2, 0.25), materials.metalBlack)
      bracket1.position.set(-0.5, i * 0.4 - 0.1, 0)
      shelfGroup.add(bracket1)

      const bracket2 = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.2, 0.25), materials.metalBlack)
      bracket2.position.set(0.5, i * 0.4 - 0.1, 0)
      shelfGroup.add(bracket2)

      const items = createClutter(1.2)
      items.position.y = i * 0.4 + 0.025
      shelfGroup.add(items)
    }
    shelfGroup.position.set(2.4, 1.4, 1.0)
    shelfGroup.rotation.y = -Math.PI / 2
    scene.add(shelfGroup)

    // 3. BOOK RACK & FRIDGE
    const rackGroup = new THREE.Group()
    const fridge = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.6), materials.metalBlack)
    fridge.position.y = 0.4
    fridge.castShadow = true
    rackGroup.add(fridge)

    const coffeeMaker = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.12, 0.25), 
      new THREE.MeshStandardMaterial({ color: 0x999999 })
    )
    coffeeMaker.position.set(0, 0.92, 0)
    rackGroup.add(coffeeMaker)

    const rackFrame = new THREE.Mesh(
      new THREE.BoxGeometry(0.5, 1.0, 0.3), 
      new THREE.MeshBasicMaterial({ color: 0x000000, wireframe: true })
    )
    rackFrame.position.set(0, 1.3, -0.1)
    rackGroup.add(rackFrame)

    for (let i = 0; i < 8; i++) {
      const book = new THREE.Mesh(
        new THREE.BoxGeometry(0.4, 0.08, 0.25), 
        new THREE.MeshStandardMaterial({ color: Math.random() * 0xffffff })
      )
      book.position.set(0, 0.9 + (i * 0.12), -0.1)
      book.rotation.y = (Math.random() - 0.5) * 0.2
      rackGroup.add(book)
    }
    rackGroup.position.set(2.2, 0, -0.5)
    rackGroup.rotation.y = -Math.PI / 2
    scene.add(rackGroup)

    // 4. DESK AREA
    const deskGroup = new THREE.Group()
    const deskTop = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.05, 0.7), materials.woodDark)
    deskTop.position.y = 0.75
    deskTop.castShadow = true
    deskGroup.add(deskTop)

    const legGeo = new THREE.BoxGeometry(0.05, 0.75, 0.7)
    const legL = new THREE.Mesh(legGeo, materials.woodDark)
    legL.position.set(-0.65, 0.375, 0)
    deskGroup.add(legL)

    const legR = new THREE.Mesh(legGeo, materials.woodDark)
    legR.position.set(0.65, 0.375, 0)
    deskGroup.add(legR)

    const pitcher = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.06, 0.25), 
      materials.plasticWhite
    )
    pitcher.position.set(0.4, 0.9, 0.1)
    deskGroup.add(pitcher)

    const chair = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), materials.fabricBlue)
    chair.position.set(0, 0.4, 0.4)
    deskGroup.add(chair)

    deskGroup.position.set(1.5, 0, -2.1)
    scene.add(deskGroup)

    // 5. DRESSER & POOH & CORKBOARD
    const dresserGroup = new THREE.Group()
    const dresserBody = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.9, 0.5), materials.woodLight)
    dresserBody.position.y = 0.45
    dresserBody.castShadow = true
    dresserGroup.add(dresserBody)

    for (let i = 0; i < 3; i++) {
      const drawer = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.25, 0.02), materials.woodLight)
      drawer.position.set(0, 0.2 + (i * 0.28), 0.26)
      dresserGroup.add(drawer)
    }

    const poohGroup = new THREE.Group()
    const poohBody = new THREE.Mesh(new THREE.SphereGeometry(0.25, 16, 16), materials.poohYellow)
    poohGroup.add(poohBody)

    const poohShirt = new THREE.Mesh(
      new THREE.CylinderGeometry(0.26, 0.26, 0.15, 16), 
      materials.poohRed
    )
    poohShirt.position.y = 0.1
    poohGroup.add(poohShirt)

    const poohHead = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), materials.poohYellow)
    poohHead.position.y = 0.35
    poohGroup.add(poohHead)

    poohGroup.position.set(-0.3, 1.15, 0)
    poohGroup.rotation.y = 0.5
    dresserGroup.add(poohGroup)

    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.1, 0.4, 16), materials.coneOrange)
    cone.position.set(0.4, 1.1, 0)
    dresserGroup.add(cone)

    dresserGroup.position.set(-2.2, 0, -1.0)
    dresserGroup.rotation.y = Math.PI / 2
    scene.add(dresserGroup)

    const corkboard = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.0, 0.05), materials.cork)
    corkboard.position.set(-2.45, 1.8, -1.0)
    corkboard.rotation.y = Math.PI / 2

    for (let i = 0; i < 5; i++) {
      const paper = new THREE.Mesh(new THREE.PlaneGeometry(0.2, 0.3), materials.wall)
      paper.position.set(0, 0, 0.03)
      paper.position.x = (Math.random() - 0.5) * 1.2
      paper.position.y = (Math.random() - 0.5) * 0.8
      paper.rotation.z = (Math.random() - 0.5) * 0.5
      corkboard.add(paper)
    }
    scene.add(corkboard)

    // 6. WINDOW
    const curtain = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.8, 0.1), materials.fabricBlue)
    curtain.position.set(0, 2.0, -2.4)
    scene.add(curtain)

    const radiator = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.6, 0.15), materials.plasticWhite)
    radiator.position.set(0, 0.3, -2.4)

    for (let i = 0; i < 10; i++) {
      const slat = new THREE.Mesh(
        new THREE.BoxGeometry(0.05, 0.4, 0.16), 
        new THREE.MeshStandardMaterial({ color: 0xcccccc })
      )
      slat.position.x = -0.6 + (i * 0.13)
      radiator.add(slat)
    }
    scene.add(radiator)

    // 7. BED
    const bed = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.5, 1.2), materials.woodLight)
    bed.position.set(-1.5, 0.25, 1.5)
    scene.add(bed)

    const mattress = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.2, 1.1), materials.plasticWhite)
    mattress.position.set(0, 0.35, 0)
    bed.add(mattress)

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    // Handle resize
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h, false)
    }
    window.addEventListener('resize', handleResize)
    handleResize()

    threeJSRendererRef.current = { 
      renderer, 
      scene,
      cleanup: () => {
        window.removeEventListener('resize', handleResize)
        if (container && renderer.domElement.parentNode === container) {
          container.removeChild(renderer.domElement)
        }
        renderer.dispose()
      }
    }
    
    console.log('Three.js dorm room scene initialized successfully')
  }

  const handleUpload = async () => {
    if (!videoFile) {
      console.error('No video file selected')
      setUploadStatus('❌ No video file selected')
      return
    }

    console.log('Processing video...', videoFile.name)
    setUploading(true)
    setUploadStatus('Processing video...')

    try {
      // Step 1: Simulate video upload (12s)
      await new Promise(resolve => setTimeout(resolve, 12000))
      setUploadStatus('Analyzing room structure...')
      
      // Step 2: Simulate analysis (12s)
      await new Promise(resolve => setTimeout(resolve, 12000))
      setUploadStatus('Applying greedy algorithm...')
      
      // Step 3: Simulate greedy algorithm + load manifest (11s)
      await new Promise(resolve => setTimeout(resolve, 11000))
      const manifest = await loadManifestFromFile('/bedroom_lego_manifest.json')
      console.log(`[Backboard] Loaded manifest with ${manifest.total_bricks} bricks`)
      
      // Step 4: Simulate instruction generation (8s) — total ~43s
      setUploadStatus('Generating instruction manual...')
      await new Promise(resolve => setTimeout(resolve, 8000))
      
      const buildEntry = processManifestWithBackboard(
        manifest,
        projectName,
        'dorm_room'
      )
      
      // Step 4: Update state with processed data
      setBuildData(buildEntry)
      setManualData(buildEntry.instruction_manual)
      setPieceCount(buildEntry.piece_count)
      setHasEnvironment(true)
      
      console.log(`[Backboard] Build ${buildEntry.build_id} saved with:`)
      console.log(`  - ${buildEntry.piece_count.total_pieces} total pieces`)
      console.log(`  - ${buildEntry.piece_count.total_unique} unique types`)
      console.log(`  - ${buildEntry.instruction_manual.total_steps} build steps`)
      console.log(`  - Difficulty: ${buildEntry.instruction_manual.difficulty}`)
      console.log(`  - Est. time: ${buildEntry.instruction_manual.estimated_time_minutes} minutes`)
      
      setUploadStatus('✅ LEGO build generated successfully!')
      
      // Show Three.js scene after a brief delay
      setTimeout(() => {
        setShowThreeJS(true)
        setUploading(false)
      }, 500)
      
    } catch (error) {
      console.error('Error processing video:', error)
      setUploadStatus(`❌ Error: ${error instanceof Error ? error.message : 'Processing failed'}`)
      setUploading(false)
    }
  }

  // Show confirmation before removing
  const confirmRemove = () => {
    setShowRemoveConfirm(true)
  }

  // Actually remove the environment/video
  const handleRemove = () => {
    setShowRemoveConfirm(false)
    if (videoPreview) {
      URL.revokeObjectURL(videoPreview)
    }
    if (threeJSRendererRef.current) {
      threeJSRendererRef.current.cleanup()
      threeJSRendererRef.current = null
    }
    setVideoFile(null)
    setVideoPreview(null)
    setUploadStatus('')
    setShowThreeJS(false)
    setHasEnvironment(false) // Reset environment state
    // Reset LEGO build data
    setBuildData(null)
    setManualData(emptyManualData)
    setPieceCount(emptyPieceCount)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Send current LEGO set metadata to BB Coin (on-chain Memo)
  const sendToBbCoin = async () => {
    if (!publicKey || !sendTransaction || !buildData) return
    setBbCoinSending(true)
    setBbCoinStatus(null)
    try {
      const { transaction } = buildMemoTransaction({
        projectName: projectName,
        buildId: buildData.build_id,
        totalPieces: pieceCount.total_pieces,
        stepCount: manualData.total_steps,
        estimatedCost: pieceCount.estimated_cost,
        breakdown: pieceCount.breakdown.map((b) => ({ part_id: b.part_id, quantity: b.quantity })),
      })
      const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('finalized')
      transaction.recentBlockhash = blockhash
      transaction.feePayer = publicKey
      const sig = await sendTransaction(transaction, connection, { skipPreflight: false })
      setBbCoinStatus(`Saved to BB Coin: ${sig.slice(0, 8)}...`)
    } catch (e) {
      setBbCoinStatus(`Error: ${e instanceof Error ? e.message : 'Failed to send'}`)
    } finally {
      setBbCoinSending(false)
    }
  }

  // Handle object video upload
  const handleObjectVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      processObjectVideo(file)
    }
  }

  // Process object video and add to scene
  const processObjectVideo = async (videoFile: File) => {
    setAddingObject(true)
    const objectName = videoFile.name.replace(/\\.[^/.]+$/, '') // Remove extension
    
    try {
      console.log(`Processing object video: ${objectName}`)
      const apiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY || ''
      
      // Generate Three.js code from video WITH model analysis
      const result = await convertVideoTo3DObject(videoFile, objectName, apiKey)
      
      if (!result?.threeJSCode) {
        throw new Error('Failed to generate Three.js code')
      }
      
      // Get the scene from the environment renderer
      if (!threeJSRendererRef.current?.scene) {
        throw new Error('No active 3D scene. Please load an environment first.')
      }
      
      // Execute the code and add to scene
      const { object, modelAnalysis } = await executeAndAddObject(
        result,
        threeJSRendererRef.current.scene,
        objectName
      )
      
      // Store the object reference with model analysis
      const newObject = {
        id: `obj-${Date.now()}`,
        name: objectName,
        mesh: object,
        modelAnalysis: modelAnalysis // Store for LEGO generation
      }
      setObjects(prev => [...prev, newObject])
      
      // Log model details
      if (modelAnalysis) {
        console.log(`🏗️ Model: ${modelAnalysis.modelName}`)
        console.log(`📊 Type: ${modelAnalysis.modelType}`)
        console.log(`📝 Description: ${modelAnalysis.description}`)
        console.log(`🧱 Pieces to use:`, modelAnalysis.extractedPieces)
        
        // Show model details modal
        setSelectedModelAnalysis(modelAnalysis)
        setShowModelDetails(true)
      }
      
      console.log(`✅ Successfully added object: ${objectName}`)
    } catch (error) {
      console.error('Error processing object video:', error)
      alert(`Failed to add object: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setAddingObject(false)
    }
  }

  return (
    <>
      {/* Loading overlay: 5s on open + during ~43s video upload/processing; fades in and out */}
      {showOverlay && (
        <LoadingOverlayInner
          isFadingOut={isFadingOut}
          uploading={uploading}
          uploadStatus={uploadStatus}
        />
      )}

      <header>
      <img
  src="/Brick.png"
  alt="Brick by Brick"
  style={{ marginLeft: "72px" }}
  className="header-logo-left"
/>

       
      </header>

      {/* Sticky BB Coins (bottom-left) */}
      <div
        className="bb-coins-fab"
        onClick={() => setShowCoinsPopup(true)}
        title="Your BB Coins"
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowCoinsPopup(true) } }}
      >
        <img src="/coin.svg" alt="BB Coins" className="bb-coins-fab-img" />
      </div>

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
            <img src="/piece_by_piece.svg" alt="Piece by Piece" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
        </div>
      </div>

      <div className="builder-container">
        <div className="builder-top-row">
          <div 
            className={`env-wrapper ${isFullscreen ? 'fullscreen-mode' : ''}`}
            ref={envPanelRef}
          >
            <div className="panel-header header-bg-red">Environment</div>
            <div className="panel panel-content">
              {!videoPreview && !showThreeJS ? (
                <div className="video-upload-area">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                    id="video-upload"
                  />
                  <label htmlFor="video-upload" className="upload-label">
                    <i className="fa-solid fa-cloud-arrow-up" style={{ fontSize: '48px', marginBottom: '15px', color: '#888' }}></i>
                    <div style={{ fontWeight: 700, fontSize: '16px', marginBottom: '8px' }}>Upload Video</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>Click to select a video file</div>
                  </label>
                </div>
              ) : showThreeJS ? (
                <div className="video-preview-container" style={{ padding: 0, overflow: 'hidden' }}>
                  <div ref={envContainerRef} style={{ width: '100%', height: '100%', minHeight: '400px', position: 'relative' }}></div>
                  <div className="video-controls-overlay">
                    <button
                      onClick={confirmRemove}
                      className="remove-btn"
                      title="Remove environment"
                    >
                      <i className="fa-solid fa-times"></i>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="video-preview-container">
                  <video
                    src={videoPreview || undefined}
                    controls
                    style={{ maxWidth: '100%', maxHeight: '100%', width: 'auto', height: 'auto', objectFit: 'contain' }}
                  />
                  <div className="video-controls-overlay">
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        console.log('Process Video button clicked')
                        handleUpload()
                      }}
                      disabled={uploading}
                      className="upload-btn"
                      type="button"
                    >
                      {uploading ? 'Uploading...' : 'Process Video'}
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        confirmRemove()
                      }}
                      className="remove-btn"
                      type="button"
                      title="Remove video"
                    >
                      <i className="fa-solid fa-times"></i>
                    </button>
                  </div>
                  {uploadStatus && (
                    <div className={`upload-status ${uploadStatus.includes('✅') ? 'success' : 'error'}`}>
                      {uploadStatus}
                    </div>
                  )}
                </div>
              )}
              <div className="zoom-controls">
                <button 
                  className="zoom-btn"
                  onClick={() => {
                    const a = document.createElement('a')
                    a.href = '/dorm_room_lego.ldr'
                    a.download = 'dorm_room_lego.ldr'
                    a.click()
                  }}
                  title="Download dorm room LEGO (.ldr)"
                >
                  🧱
                </button>
                <button 
                  className="zoom-btn" 
                  onClick={toggleFullscreen}
                  title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
                >
                  <i className={`fa-solid ${isFullscreen ? 'fa-compress' : 'fa-expand'}`}></i>
                </button>
                <button 
                  className="zoom-btn"
                  onClick={() => {
                    if (threeJSRendererRef.current?.zoomIn) {
                      threeJSRendererRef.current.zoomIn()
                    }
                  }}
                  title="Zoom In"
                >
                  <i className="fa-solid fa-plus"></i>
                </button>
                <button 
                  className="zoom-btn"
                  onClick={() => {
                    if (threeJSRendererRef.current?.zoomOut) {
                      threeJSRendererRef.current.zoomOut()
                    }
                  }}
                  title="Zoom Out"
                >
                  <i className="fa-solid fa-minus"></i>
                </button>
              </div>
            </div>
          </div>

          <div className="obj-wrapper">
            <div className="panel-header header-bg-cyan">Objects</div>
            <div className="panel panel-content">
              <div className="objects-grid">
                {objects.map((obj, index) => (
                  <div key={obj.id} className="obj-item" title={obj.name}>
                    <div style={{ fontSize: '24px' }}>📦</div>
                    <div style={{ fontSize: '10px', marginTop: '4px', textAlign: 'center' }}>{obj.name.substring(0, 8)}</div>
                  </div>
                ))}
                {objects.length < 4 && (
                  <div 
                    className="obj-add"
                    onClick={() => {
                      const fileInputRef = document.getElementById('object-video-upload') as HTMLInputElement
                      fileInputRef?.click()
                    }}
                    style={{ cursor: addingObject ? 'not-allowed' : 'pointer', opacity: addingObject ? 0.5 : 1 }}
                  >
                    <i className="fa-solid fa-plus"></i>
                  </div>
                )}
              </div>
              <input
                id="object-video-upload"
                type="file"
                accept="video/*"
                onChange={handleObjectVideoChange}
                style={{ display: 'none' }}
                disabled={addingObject || !hasEnvironment}
              />
              {addingObject && (
                <div style={{ marginTop: '12px', textAlign: 'center', fontSize: '12px', color: '#666' }}>
                  Generating 3D object...
                </div>
              )}
              {!hasEnvironment && (
                <div style={{ marginTop: '12px', textAlign: 'center', fontSize: '12px', color: '#999' }}>
                  Load environment first to add objects
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="full-set-row">
          <div className="panel-header header-bg-orange">Full Set</div>
          <div className="box-art-container" style={{ position: 'relative' }}>
            <div className="lego-box-perspective">
              <div className="box-spine">
                <div className="spine-logo">B<span>B</span></div>
                <div className="spine-age">9+</div>
                <div className="spine-sku">202601</div>
                <div className="spine-line"></div>
                
                <div className="spine-name">{projectName || 'Name of Lego Set'}</div>
                <div className="spine-pcs">{pieceCount?.total_pieces ?? '—'}<br/>pcs</div>
                <div className="spine-sub">Building Toy<br/>Jouet de construction</div>
              </div>
              <div className="box-front">
                <div className="box-front-text">
                  {hasEnvironment ? projectName : '3d model of the environment + objects'}
                </div>
              </div>
            </div>
          </div>
          <div className="full-set-buttons">
            <button 
              className="view-details-btn"
              onClick={() => {
                if (hasEnvironment) {
                  setShowInstructionBook(true)
                } else {
                  setShowNothingModal(true)
                }
              }}
            >
              <i className="fa-solid fa-book"></i>
              View Details
            </button>
          </div>
        </div>
      </div>

      {/* Nothing to Display Modal */}
      {showNothingModal && (
        <div 
          className="nothing-modal-overlay"
          onClick={() => setShowNothingModal(false)}
        >
          <div 
            className="nothing-modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              className="nothing-modal-close"
              onClick={() => setShowNothingModal(false)}
            >
              ✕
            </button>
            <div className="nothing-modal-icon">🧱</div>
            <h2 className="nothing-modal-title">No Build Available</h2>
            <p className="nothing-modal-text">No environment has been loaded yet.</p>
            <p className="nothing-modal-subtext">
              Upload or create an environment to see your LEGO build instructions here.
            </p>
          </div>
        </div>
      )}

      {/* Remove Confirmation Modal */}
      {showRemoveConfirm && (
        <div 
          className="confirm-modal-overlay"
          onClick={() => setShowRemoveConfirm(false)}
        >
          <div 
            className="confirm-modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="confirm-modal-icon">⚠️</div>
            <h2 className="confirm-modal-title">Are you sure?</h2>
            <p className="confirm-modal-text">
              This will remove your current environment and all generated LEGO build data.
            </p>
            <div className="confirm-modal-buttons">
              <button 
                className="confirm-btn confirm-btn-cancel"
                onClick={() => setShowRemoveConfirm(false)}
              >
                Cancel
              </button>
              <button 
                className="confirm-btn confirm-btn-remove"
                onClick={handleRemove}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Instruction Book Modal */}
      {showInstructionBook && (
        <InstructionBook
          projectName={projectName}
          manual={manualData}
          pieceCount={pieceCount}
          isOpen={showInstructionBook}
          onClose={() => setShowInstructionBook(false)}
        />
      )}

      {/* Model Details Modal */}
      {showModelDetails && selectedModelAnalysis && (
        <ModelDetailsDisplay
          modelAnalysis={selectedModelAnalysis}
          onClose={() => setShowModelDetails(false)}
        />
      )}

      {/* BB Coins Popup: login first, then user coins */}
      {showCoinsPopup && (
        <div className="coins-popup-overlay" onClick={() => setShowCoinsPopup(false)}>
          <div className="coins-popup" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="coins-popup-close" onClick={() => setShowCoinsPopup(false)} aria-label="Close">×</button>

            {!publicKey ? (
              <>
                <h2 className="coins-popup-title">Login to BB Coins</h2>
                <div className="coins-popup-connect">
                  <p>Connect your wallet to view your LEGO builds and BB Coins.</p>
                  <button type="button" className="coins-connect-btn" onClick={() => setWalletModalVisible(true)}>Connect wallet</button>
                </div>
              </>
            ) : (
              <>
                <h2 className="coins-popup-title">Your BB Coins</h2>
                <div className="coins-popup-body">
                  <div className="coins-grid">
                    {coins.map((c) => (
                      <div
                        key={c.id}
                        className="coin-cell"
                        onMouseEnter={() => { if (hoverLeaveRef.current) clearTimeout(hoverLeaveRef.current); hoverLeaveRef.current = null; setHoveredCoin(c) }}
                        onMouseLeave={() => { if (hoverLeaveRef.current) clearTimeout(hoverLeaveRef.current); hoverLeaveRef.current = setTimeout(() => { setHoveredCoin(null); hoverLeaveRef.current = null }, 180) }}
                      >
                        <img src="/coin.svg" alt="" className="coin-img" />
                      </div>
                    ))}
                  </div>
                  {hoveredCoin && (
                    <div
                      className="coin-nft-card"
                      style={{ background: NFT_GRADIENTS[hashId(hoveredCoin.id) % NFT_GRADIENTS.length] }}
                      onMouseEnter={() => { if (hoverLeaveRef.current) { clearTimeout(hoverLeaveRef.current); hoverLeaveRef.current = null } }}
                      onMouseLeave={() => { setHoveredCoin(null) }}
                    >
                      <div className="coin-nft-inner">
                        <span className="coin-nft-date">{new Date(hoveredCoin.date).toLocaleDateString(undefined, { dateStyle: 'medium' })}</span>
                        <span className="coin-nft-name">{hoveredCoin.projectName}</span>
                        <div className="coin-nft-meta">
                          {hoveredCoin.difficulty && <span>{hoveredCoin.difficulty}</span>}
                          {hoveredCoin.estimatedTimeMinutes != null && <span>~{hoveredCoin.estimatedTimeMinutes} min</span>}
                          <span>{hoveredCoin.totalPieces} pcs</span>
                        </div>
                        <div className="coin-nft-pieces-list">
                          <strong>Pieces</strong>
                          {hoveredCoin.breakdown.slice(0, 8).map((p, i) => (
                            <span key={i}>{p.piece_name || p.part_id} ({p.color_name || '—'}) ×{p.quantity}</span>
                          ))}
                          {hoveredCoin.breakdown.length > 8 && <span>… +{hoveredCoin.breakdown.length - 8} more</span>}
                        </div>
                        <a href={`https://www.rebrickable.com/search/?q=${encodeURIComponent(hoveredCoin.projectName)}`} target="_blank" rel="noopener noreferrer" className="coin-nft-link">Buy LEGOs for this build</a>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}

