interface Props {
  title: string
  children: React.ReactNode
  width?: number
  height?: number
  className?: string
  style?: React.CSSProperties
}

export function HolographicPanel({ title, children, width, height, className = '', style }: Props) {
  return (
    <div
      className={`holographic-panel ${className}`}
      style={{
        width: width ? `${width}px` : undefined,
        height: height ? `${height}px` : undefined,
        ...style,
      }}
    >
      <div className="panel-header">{title}</div>
      <div className="panel-corner top-left" />
      <div className="panel-corner top-right" />
      <div className="panel-corner bottom-left" />
      <div className="panel-corner bottom-right" />
      <div className="panel-scanline" />
      {children}
    </div>
  )
}
