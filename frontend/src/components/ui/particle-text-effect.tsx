/**
 * KAINXU / 21st.dev particle text — scaffold parity with shadcn paste (fixed 1000×500,
 * 100px Arial, physics constants from the recipe). Vite: omit Next.js `"use client"`.
 * Optional `embedded` / `hideCaption` / `fullBleed` support the PLANR hero; simulation
 * stays 1000×500 and scales via CSS so behavior matches the original demo.
 */
import { useEffect, useRef } from "react"

import { cn } from "@/lib/utils"

interface Vector2D {
  x: number
  y: number
}

/** Bitmap size — must match random spawn helpers (1000 / 500) in the paste. */
const CANVAS_W = 1000
const CANVAS_H = 500

class Particle {
  pos: Vector2D = { x: 0, y: 0 }
  vel: Vector2D = { x: 0, y: 0 }
  acc: Vector2D = { x: 0, y: 0 }
  target: Vector2D = { x: 0, y: 0 }

  closeEnoughTarget = 100
  maxSpeed = 1.0
  maxForce = 0.1
  particleSize = 10
  isKilled = false

  startColor = { r: 0, g: 0, b: 0 }
  targetColor = { r: 0, g: 0, b: 0 }
  colorWeight = 0
  colorBlendRate = 0.01

  move() {
    let proximityMult = 1
    const distance = Math.sqrt(
      Math.pow(this.pos.x - this.target.x, 2) + Math.pow(this.pos.y - this.target.y, 2),
    )

    if (distance < this.closeEnoughTarget) {
      proximityMult = distance / this.closeEnoughTarget
    }

    const towardsTarget = {
      x: this.target.x - this.pos.x,
      y: this.target.y - this.pos.y,
    }

    const magnitude = Math.sqrt(
      towardsTarget.x * towardsTarget.x + towardsTarget.y * towardsTarget.y,
    )
    if (magnitude > 0) {
      towardsTarget.x = (towardsTarget.x / magnitude) * this.maxSpeed * proximityMult
      towardsTarget.y = (towardsTarget.y / magnitude) * this.maxSpeed * proximityMult
    }

    const steer = {
      x: towardsTarget.x - this.vel.x,
      y: towardsTarget.y - this.vel.y,
    }

    const steerMagnitude = Math.sqrt(steer.x * steer.x + steer.y * steer.y)
    if (steerMagnitude > 0) {
      steer.x = (steer.x / steerMagnitude) * this.maxForce
      steer.y = (steer.y / steerMagnitude) * this.maxForce
    }

    this.acc.x += steer.x
    this.acc.y += steer.y

    this.vel.x += this.acc.x
    this.vel.y += this.acc.y
    this.pos.x += this.vel.x
    this.pos.y += this.vel.y
    this.acc.x = 0
    this.acc.y = 0
  }

  draw(ctx: CanvasRenderingContext2D, drawAsPoints: boolean) {
    if (this.colorWeight < 1.0) {
      this.colorWeight = Math.min(this.colorWeight + this.colorBlendRate, 1.0)
    }

    const currentColor = {
      r: Math.round(
        this.startColor.r + (this.targetColor.r - this.startColor.r) * this.colorWeight,
      ),
      g: Math.round(
        this.startColor.g + (this.targetColor.g - this.startColor.g) * this.colorWeight,
      ),
      b: Math.round(
        this.startColor.b + (this.targetColor.b - this.startColor.b) * this.colorWeight,
      ),
    }

    if (drawAsPoints) {
      ctx.fillStyle = `rgb(${currentColor.r}, ${currentColor.g}, ${currentColor.b})`
      ctx.fillRect(this.pos.x, this.pos.y, 2, 2)
    } else {
      ctx.fillStyle = `rgb(${currentColor.r}, ${currentColor.g}, ${currentColor.b})`
      ctx.beginPath()
      ctx.arc(this.pos.x, this.pos.y, this.particleSize / 2, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  kill(width: number, height: number) {
    if (!this.isKilled) {
      const randomPos = this.generateRandomPos(
        width / 2,
        height / 2,
        (width + height) / 2,
      )
      this.target.x = randomPos.x
      this.target.y = randomPos.y

      this.startColor = {
        r: this.startColor.r + (this.targetColor.r - this.startColor.r) * this.colorWeight,
        g: this.startColor.g + (this.targetColor.g - this.startColor.g) * this.colorWeight,
        b: this.startColor.b + (this.targetColor.b - this.startColor.b) * this.colorWeight,
      }
      this.targetColor = { r: 0, g: 0, b: 0 }
      this.colorWeight = 0

      this.isKilled = true
    }
  }

  private generateRandomPos(x: number, y: number, mag: number): Vector2D {
    const randomX = Math.random() * 1000
    const randomY = Math.random() * 500

    const direction = {
      x: randomX - x,
      y: randomY - y,
    }

    const magnitude = Math.sqrt(direction.x * direction.x + direction.y * direction.y)
    if (magnitude > 0) {
      direction.x = (direction.x / magnitude) * mag
      direction.y = (direction.y / magnitude) * mag
    }

    return {
      x: x + direction.x,
      y: y + direction.y,
    }
  }
}

export interface ParticleTextEffectProps {
  words?: string[]
  /** Embed in a parent layout (e.g. hero section). */
  embedded?: boolean
  /** Hide the help caption under the canvas. */
  hideCaption?: boolean
  /** Stretch the canvas with CSS to fill a positioned parent; simulation stays 1000×500. */
  fullBleed?: boolean
}

const DEFAULT_WORDS = ["HELLO", "21st.dev", "ParticleTextEffect", "BY", "KAINXU"]

export function ParticleTextEffect({
  words = DEFAULT_WORDS,
  embedded = false,
  hideCaption = false,
  fullBleed = false,
}: ParticleTextEffectProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | undefined>(undefined)
  const particlesRef = useRef<Particle[]>([])
  const frameCountRef = useRef(0)
  const wordIndexRef = useRef(0)
  const mouseRef = useRef({
    x: 0,
    y: 0,
    isPressed: false,
    isRightClick: false,
  })
  const cancelledRef = useRef(false)

  const pixelSteps = 6
  const drawAsPoints = true

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    if (fullBleed && !containerRef.current) return

    cancelledRef.current = false
    particlesRef.current = []
    frameCountRef.current = 0
    wordIndexRef.current = 0

    const generateRandomPos = (x: number, y: number, mag: number): Vector2D => {
      const randomX = Math.random() * 1000
      const randomY = Math.random() * 500

      const direction = {
        x: randomX - x,
        y: randomY - y,
      }

      const magnitude = Math.sqrt(direction.x * direction.x + direction.y * direction.y)
      if (magnitude > 0) {
        direction.x = (direction.x / magnitude) * mag
        direction.y = (direction.y / magnitude) * mag
      }

      return {
        x: x + direction.x,
        y: y + direction.y,
      }
    }

    const nextWord = (word: string, c: HTMLCanvasElement) => {
      const offscreenCanvas = document.createElement("canvas")
      offscreenCanvas.width = c.width
      offscreenCanvas.height = c.height
      const offscreenCtx = offscreenCanvas.getContext("2d")!

      offscreenCtx.fillStyle = "white"
      offscreenCtx.font = "bold 100px Arial"
      offscreenCtx.textAlign = "center"
      offscreenCtx.textBaseline = "middle"
      offscreenCtx.fillText(word, c.width / 2, c.height / 2)

      const imageData = offscreenCtx.getImageData(0, 0, c.width, c.height)
      const pixels = imageData.data

      const newColor = {
        r: Math.random() * 255,
        g: Math.random() * 255,
        b: Math.random() * 255,
      }

      const particles = particlesRef.current
      let particleIndex = 0

      const coordsIndexes: number[] = []
      for (let i = 0; i < pixels.length; i += pixelSteps * 4) {
        coordsIndexes.push(i)
      }

      for (let i = coordsIndexes.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[coordsIndexes[i], coordsIndexes[j]] = [coordsIndexes[j], coordsIndexes[i]]
      }

      for (const coordIndex of coordsIndexes) {
        const pixelIndex = coordIndex
        const alpha = pixels[pixelIndex + 3]

        if (alpha > 0) {
          const x = (pixelIndex / 4) % c.width
          const y = Math.floor(pixelIndex / 4 / c.width)

          let particle: Particle

          if (particleIndex < particles.length) {
            particle = particles[particleIndex]
            particle.isKilled = false
            particleIndex++
          } else {
            particle = new Particle()

            const randomPos = generateRandomPos(
              c.width / 2,
              c.height / 2,
              (c.width + c.height) / 2,
            )
            particle.pos.x = randomPos.x
            particle.pos.y = randomPos.y

            particle.maxSpeed = Math.random() * 6 + 4
            particle.maxForce = particle.maxSpeed * 0.05
            particle.particleSize = Math.random() * 6 + 6
            particle.colorBlendRate = Math.random() * 0.0275 + 0.0025

            particles.push(particle)
          }

          particle.startColor = {
            r:
              particle.startColor.r +
              (particle.targetColor.r - particle.startColor.r) * particle.colorWeight,
            g:
              particle.startColor.g +
              (particle.targetColor.g - particle.startColor.g) * particle.colorWeight,
            b:
              particle.startColor.b +
              (particle.targetColor.b - particle.startColor.b) * particle.colorWeight,
          }
          particle.targetColor = newColor
          particle.colorWeight = 0

          particle.target.x = x
          particle.target.y = y
        }
      }

      for (let i = particleIndex; i < particles.length; i++) {
        particles[i].kill(c.width, c.height)
      }
    }

    const toBitmapCoords = (c: HTMLCanvasElement, clientX: number, clientY: number) => {
      const rect = c.getBoundingClientRect()
      const sx = rect.width > 0 ? c.width / rect.width : 1
      const sy = rect.height > 0 ? c.height / rect.height : 1
      return {
        x: (clientX - rect.left) * sx,
        y: (clientY - rect.top) * sy,
      }
    }

    const animate = () => {
      if (cancelledRef.current) return
      const c = canvasRef.current
      if (!c) return

      const ctx = c.getContext("2d")!
      const particles = particlesRef.current

      ctx.fillStyle = "rgba(0, 0, 0, 0.1)"
      ctx.fillRect(0, 0, c.width, c.height)

      for (let i = particles.length - 1; i >= 0; i--) {
        const particle = particles[i]
        particle.move()
        particle.draw(ctx, drawAsPoints)

        if (particle.isKilled) {
          if (
            particle.pos.x < 0 ||
            particle.pos.x > c.width ||
            particle.pos.y < 0 ||
            particle.pos.y > c.height
          ) {
            particles.splice(i, 1)
          }
        }
      }

      if (mouseRef.current.isPressed && mouseRef.current.isRightClick) {
        particles.forEach((particle) => {
          const distance = Math.sqrt(
            Math.pow(particle.pos.x - mouseRef.current.x, 2) +
              Math.pow(particle.pos.y - mouseRef.current.y, 2),
          )
          if (distance < 50) {
            particle.kill(c.width, c.height)
          }
        })
      }

      frameCountRef.current++
      if (frameCountRef.current % 240 === 0) {
        wordIndexRef.current = (wordIndexRef.current + 1) % words.length
        nextWord(words[wordIndexRef.current], c)
      }

      animationRef.current = requestAnimationFrame(animate)
    }

    canvas.width = CANVAS_W
    canvas.height = CANVAS_H
    nextWord(words[0], canvas)
    animate()

    const handleMouseDown = (e: MouseEvent) => {
      mouseRef.current.isPressed = true
      mouseRef.current.isRightClick = e.button === 2
      const p = toBitmapCoords(canvas, e.clientX, e.clientY)
      mouseRef.current.x = p.x
      mouseRef.current.y = p.y
    }

    const handleMouseUp = () => {
      mouseRef.current.isPressed = false
      mouseRef.current.isRightClick = false
    }

    const handleMouseMove = (e: MouseEvent) => {
      const p = toBitmapCoords(canvas, e.clientX, e.clientY)
      mouseRef.current.x = p.x
      mouseRef.current.y = p.y
    }

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault()
    }

    canvas.addEventListener("mousedown", handleMouseDown)
    canvas.addEventListener("mouseup", handleMouseUp)
    canvas.addEventListener("mousemove", handleMouseMove)
    canvas.addEventListener("contextmenu", handleContextMenu)

    return () => {
      cancelledRef.current = true
      if (animationRef.current !== undefined) {
        cancelAnimationFrame(animationRef.current)
      }
      canvas.removeEventListener("mousedown", handleMouseDown)
      canvas.removeEventListener("mouseup", handleMouseUp)
      canvas.removeEventListener("mousemove", handleMouseMove)
      canvas.removeEventListener("contextmenu", handleContextMenu)
    }
  }, [words, fullBleed])

  const wrapClass = cn(
    fullBleed && "absolute inset-0 h-full w-full min-h-0",
    embedded &&
      !fullBleed &&
      "flex min-h-0 w-full flex-1 flex-col items-center justify-center",
    !embedded &&
      !fullBleed &&
      "flex min-h-screen flex-col items-center justify-center bg-black p-4",
  )

  const canvasClass = cn(
    fullBleed && "block h-full w-full",
    !fullBleed && "h-auto max-w-full rounded-lg border border-gray-800 shadow-2xl",
  )

  return (
    <div ref={containerRef} className={wrapClass}>
      <canvas
        ref={canvasRef}
        className={canvasClass}
        {...(!fullBleed ? { style: { maxWidth: "100%", height: "auto" } } : {})}
      />
      {!hideCaption && (
        <div className="mt-4 max-w-md text-center text-sm text-white">
          <p className="mb-2">Particle Text Effect</p>
          <p className="text-xs text-zinc-300">
            Right-click and hold while moving mouse to destroy particles • Words change
            automatically every 4 seconds
          </p>
        </div>
      )}
    </div>
  )
}
