import { useEffect, useRef } from 'react'
import { useStore } from '../store'

export function BrainActivityGraph() {
  const brainHistory = useStore((s) => s.brainHistory)
  const brainActivity = useStore((s) => s.brainActivity)
  const svgRef = useRef<SVGSVGElement>(null!)

  const w = 200
  const h = 60
  const points = brainHistory.map((v, i) => {
    const x = (i / (brainHistory.length - 1)) * w
    const y = h - v * h
    return `${x},${y}`
  }).join(' ')

  // Glowing pulse ring
  const glowSize = 3 + brainActivity * 5

  return (
    <div className="holographic-panel" style={{ width: 220, height: 90 }}>
      <div className="panel-header">CORTICAL ACTIVITY</div>
      <div style={{ position: 'relative' }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${w} ${h}`}
          style={{ width: '100%', height: 60 }}
        >
          {/* Grid lines */}
          {[0.25, 0.5, 0.75].map((f) => (
            <line
              key={f}
              x1={0} y1={h - h * f}
              x2={w} y2={h - h * f}
              stroke="rgba(68,136,255,0.06)"
              strokeWidth={0.5}
            />
          ))}

          {/* Filled area under curve */}
          <defs>
            <linearGradient id="brainGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(68,136,255,0.3)" />
              <stop offset="100%" stopColor="rgba(68,136,255,0)" />
            </linearGradient>
          </defs>
          <polyline
            points={`0,${h} ${points} ${w},${h}`}
            fill="url(#brainGrad)"
          />

          {/* Activity line */}
          <polyline
            points={points}
            fill="none"
            stroke="#4488ff"
            strokeWidth={1.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="graph-line"
          />

          {/* Glow line (bloom target) */}
          <polyline
            points={points}
            fill="none"
            stroke="rgba(68,136,255,0.3)"
            strokeWidth={4}
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#glow)"
          />

          {/* Current activity dot */}
          <circle
            cx={w}
            cy={h - brainActivity * h}
            r={glowSize}
            fill="#4488ff"
            opacity={0.6}
          />
          <circle
            cx={w}
            cy={h - brainActivity * h}
            r={1.5}
            fill="#fff"
          />
        </svg>
      </div>
    </div>
  )
}
