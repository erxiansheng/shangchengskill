<template>
  <canvas ref="canvas" class="particles-bg"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { themeStore } from '../stores/theme.js'

const canvas = ref(null)
let ctx = null
let animationFrame = null
let particles = []
let mouse = { x: null, y: null, radius: 150 }
let width = 0
let height = 0

class Particle {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.baseX = x
    this.baseY = y
    this.size = Math.random() * 1.5 + 0.5
    this.density = (Math.random() * 30) + 1
    this.setColorForTheme()
    this.alpha = Math.random() * 0.5 + 0.1
    this.twinkleFactor = Math.random() * 0.05
    this.twinkleDir = Math.random() > 0.5 ? 1 : -1
  }

  setColorForTheme() {
    if (themeStore.isDark) {
      this.colorBase = `rgba(${30 + Math.random() * 50}, ${200 + Math.random() * 55}, ${150 + Math.random() * 50}`
    } else {
      this.colorBase = `rgba(${80 + Math.random() * 60}, ${160 + Math.random() * 50}, ${200 + Math.random() * 55}`
    }
  }

  draw() {
    ctx.fillStyle = `${this.colorBase}, ${this.alpha})`
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.closePath()
    ctx.fill()
  }

  update() {
    let dx = mouse.x - this.x
    let dy = mouse.y - this.y
    let distance = Math.sqrt(dx * dx + dy * dy)
    let forceDirectionX = dx / distance
    let forceDirectionY = dy / distance
    let maxDistance = mouse.radius
    let force = (maxDistance - distance) / maxDistance
    let directionX = forceDirectionX * force * this.density
    let directionY = forceDirectionY * force * this.density

    if (distance < mouse.radius) {
      this.x -= directionX
      this.y -= directionY
    } else {
      if (this.x !== this.baseX) {
        let dx = this.x - this.baseX
        this.x -= dx / 10
      }
      if (this.y !== this.baseY) {
        let dy = this.y - this.baseY
        this.y -= dy / 10
      }
    }
    
    // Slight wave motion
    this.baseY += Math.sin(Date.now() / 1000 + this.baseX / 200) * 0.2
    
    // Twinkling effect
    if (Math.random() > 0.98) this.twinkleDir *= -1;
    this.alpha += this.twinkleFactor * this.twinkleDir;
    if (this.alpha <= 0.05) { this.alpha = 0.05; this.twinkleDir = 1; }
    if (this.alpha >= 0.8) { this.alpha = 0.8; this.twinkleDir = -1; }
  }
}

const init = () => {
  particles = []
  const spacing = 20
  for (let y = 0; y < height; y += spacing) {
    for (let x = 0; x < width; x += spacing) {
      // Create a wave pattern density
      if (Math.random() > 0.4) {
        particles.push(new Particle(x, y))
      }
    }
  }
}

const animate = () => {
  ctx.clearRect(0, 0, width, height)
  for (let i = 0; i < particles.length; i++) {
    particles[i].update()
    particles[i].draw()
  }
  animationFrame = requestAnimationFrame(animate)
}

const handleResize = () => {
  if (!canvas.value) return
  width = window.innerWidth
  height = window.innerHeight
  canvas.value.width = width
  canvas.value.height = height
  init()
}

const handleMouseMove = (e) => {
  mouse.x = e.x
  mouse.y = e.y
}

onMounted(() => {
  if (canvas.value) {
    // Set correct bg immediately based on current theme
    canvas.value.style.backgroundColor = themeStore.isDark ? '#050508' : '#faf9f5'
    ctx = canvas.value.getContext('2d')
    handleResize()
    window.addEventListener('resize', handleResize)
    window.addEventListener('mousemove', handleMouseMove)
    animate()
  }
})

// Watch for theme changes and reinitialize particles
watch(() => themeStore.theme, () => {
  if (canvas.value) {
    canvas.value.style.backgroundColor = themeStore.isDark ? '#050508' : '#faf9f5'
    init()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('mousemove', handleMouseMove)
  cancelAnimationFrame(animationFrame)
})
</script>

<style scoped>
.particles-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: -2;
  background-color: #050508;
  pointer-events: none;
  transition: background-color 0.5s ease;
}
</style>
