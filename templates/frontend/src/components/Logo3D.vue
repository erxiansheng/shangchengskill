<template>
  <div ref="containerRef" class="logo3d-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

const containerRef = ref(null)

let renderer, scene, camera, model, mixer
let animationId = null
let clock = new THREE.Clock()

// Cached model info
let modelBaseY = 0
let modelScale = 1
let modelRadius = 1 // half-width of the model for edge padding

// Velocity-based random movement (bouncing off edges)
let velX = 1.2 + Math.random() * 0.5
let velY = 0.6 + Math.random() * 0.3
let velZ = 0.3 + Math.random() * 0.2
let posX = 0
let posY = 1.5
let posZ = 0

// Boundaries in 3D world space — tighter X bounds to prevent clipping at edges
const boundsX = { min: -3.5, max: 3.5 }
const boundsY = { min: 0.3, max: 3.5 }
const boundsZ = { min: -2.0, max: 1.5 }

// Random direction changes
let nextDirectionChangeTime = 0

onMounted(() => {
  if (!containerRef.value) return
  init()
  animate()
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  window.removeEventListener('resize', onResize)
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
  }
  mixer = null
})

function init() {
  const container = containerRef.value
  const width = container.clientWidth
  const height = container.clientHeight

  scene = new THREE.Scene()

  // Camera
  camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 200)
  camera.position.set(0, 2, 10)
  camera.lookAt(0, 1.5, 0)

  renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance'
  })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.8
  container.appendChild(renderer.domElement)

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 1.0)
  scene.add(ambientLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.8)
  mainLight.position.set(4, 6, 8)
  scene.add(mainLight)

  const fillLight = new THREE.DirectionalLight(0xffffff, 0.6)
  fillLight.position.set(-4, 3, 4)
  scene.add(fillLight)

  const rimLight = new THREE.DirectionalLight(0x1ee07f, 0.4)
  rimLight.position.set(0, 4, -5)
  scene.add(rimLight)

  // Load compressed GLB model (animated). Source resolution order:
  //   1. /api/v1/models3d/active  -> first enabled model from KV (admin-managed)
  //   2. /logo_opt.glb            -> bundled fallback (templates/frontend/public)
  const loader = new GLTFLoader()
  loader.setMeshoptDecoder(MeshoptDecoder)

  resolveModelUrl().then((url) => {
    loader.load(
      url,
    (gltf) => {
      model = gltf.scene

      const box = new THREE.Box3().setFromObject(model)
      const center = box.getCenter(new THREE.Vector3())
      const size = box.getSize(new THREE.Vector3())
      const maxDim = Math.max(size.x, size.y, size.z)

      // Responsive scale: smaller on mobile, full on PC
      const vw = window.innerWidth
      const targetSize = vw <= 768 ? 1.5 : vw <= 1024 ? 2 : 2.5
      const scale = targetSize / maxDim
      model.scale.setScalar(scale)
      modelScale = scale

      // Tighten bounds on mobile so model stays in view
      if (vw <= 768) {
        boundsX.min = -1.8; boundsX.max = 1.8
        boundsY.min = 0.2;  boundsY.max = 2.5
        boundsZ.min = -1.2; boundsZ.max = 0.8
      } else if (vw <= 1024) {
        boundsX.min = -2; boundsX.max = 2
        boundsY.min = 0.3;  boundsY.max = 2.5
      }

      // Cache model radius for edge padding
      modelRadius = Math.max(size.x, size.z) * scale * 0.5

      // Store base Y
      modelBaseY = -box.min.y * scale

      // Center offset
      model.position.set(0, modelBaseY, 0)

      // Fix materials
      model.traverse((child) => {
        if (child.isMesh && child.material) {
          const mats = Array.isArray(child.material) ? child.material : [child.material]
          mats.forEach(m => {
            m.side = THREE.FrontSide
            m.transparent = false
            m.depthWrite = true
            m.depthTest = true
          })
        }
      })

      // Play all animations (walk cycle, idle, etc.)
      if (gltf.animations && gltf.animations.length > 0) {
        mixer = new THREE.AnimationMixer(model)
        gltf.animations.forEach((clip) => {
          const action = mixer.clipAction(clip)
          action.play()
        })
      }

      // Initial random position
      posX = (Math.random() - 0.5) * 3
      posY = 1.0 + Math.random() * 1.5
      posZ = (Math.random() - 0.5) * 1.5

      // Randomize initial direction
      velX *= (Math.random() > 0.5 ? 1 : -1)
      velY *= (Math.random() > 0.5 ? 1 : -1)
      velZ *= (Math.random() > 0.5 ? 1 : -1)

      scene.add(model)
    },
    undefined,
    (error) => {
      console.error('Error loading GLB model:', error)
    }
  )
  })

  window.addEventListener('resize', onResize)
}

// Resolve which .glb URL to load. Prefer KV-managed model so admins can
// swap the homepage 3D logo from /admin/models3d without redeploying.
async function resolveModelUrl() {
  try {
    const res = await fetch('/api/v1/models3d/active', { headers: { 'cache-control': 'no-cache' } })
    if (res.ok) {
      const json = await res.json()
      const list = json?.data || []
      if (list.length > 0 && list[0].asset_url) return list[0].asset_url
    }
  } catch (e) { /* fall through */ }
  return '/logo_opt.glb'
}

function onResize() {
  if (!containerRef.value || !renderer || !camera) return
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  const delta = clock.getDelta()
  const elapsed = clock.getElapsedTime()

  // Update animation mixer (plays embedded animations)
  if (mixer) mixer.update(delta)

  if (!model) {
    if (renderer && scene && camera) renderer.render(scene, camera)
    return
  }

  // --- Random velocity perturbation ---
  if (elapsed > nextDirectionChangeTime) {
    velX += (Math.random() - 0.5) * 0.4
    velY += (Math.random() - 0.5) * 0.3
    velZ += (Math.random() - 0.5) * 0.15

    // Clamp speeds
    velX = clamp(velX, -2.0, 2.0)
    velY = clamp(velY, -1.2, 1.2)
    velZ = clamp(velZ, -0.6, 0.6)

    nextDirectionChangeTime = elapsed + 1.5 + Math.random() * 3
  }

  // --- Update position ---
  posX += velX * delta
  posY += velY * delta
  posZ += velZ * delta

  // --- Bounce off edges ---
  if (posX > boundsX.max) { posX = boundsX.max; velX = -Math.abs(velX) * (0.8 + Math.random() * 0.4) }
  if (posX < boundsX.min) { posX = boundsX.min; velX =  Math.abs(velX) * (0.8 + Math.random() * 0.4) }
  if (posY > boundsY.max) { posY = boundsY.max; velY = -Math.abs(velY) * (0.8 + Math.random() * 0.4) }
  if (posY < boundsY.min) { posY = boundsY.min; velY =  Math.abs(velY) * (0.8 + Math.random() * 0.4) }
  if (posZ > boundsZ.max) { posZ = boundsZ.max; velZ = -Math.abs(velZ) * (0.8 + Math.random() * 0.4) }
  if (posZ < boundsZ.min) { posZ = boundsZ.min; velZ =  Math.abs(velZ) * (0.8 + Math.random() * 0.4) }

  // Apply position
  model.position.x = posX
  model.position.y = modelBaseY + posY
  model.position.z = posZ

  // --- Scale based on Z depth (subtle) ---
  const depthFactor = 1 + posZ * 0.03
  model.scale.setScalar(modelScale * depthFactor)

  // --- Dynamic z-index: far (small) = behind text, near (big) = in front ---
  // hero-content has z-index: 2, so use 1 for behind and 10 for in front
  if (containerRef.value) {
    containerRef.value.style.zIndex = posZ < -0.3 ? '1' : '10'
  }

  // --- Face the movement direction ---
  const targetRotY = Math.atan2(velX, velZ)
  model.rotation.y += (targetRotY - model.rotation.y) * 0.06

  // Walk bob animation
  const speed = Math.sqrt(velX * velX + velY * velY)
  const walkCycle = elapsed * 6
  model.rotation.z = Math.sin(walkCycle) * 0.06 * Math.min(speed, 1)
  model.rotation.x = Math.sin(elapsed * 1.5) * 0.03

  // Tiny bounce from "running"
  const runBounce = Math.abs(Math.sin(walkCycle)) * 0.05 * Math.min(speed, 1)
  model.position.y += runBounce

  if (renderer && scene && camera) {
    renderer.render(scene, camera)
  }
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}
</script>

<style scoped>
.logo3d-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 10;
  overflow: visible;
}

.logo3d-container canvas {
  display: block;
  width: 100% !important;
  height: 100% !important;
}
</style>
