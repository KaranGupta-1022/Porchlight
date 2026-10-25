import type { ReactNode } from 'react'

type Props = { title: string; children: ReactNode; onClose: () => void; tall?: boolean }

export default function BottomSheet({ title, children, onClose, tall = false }: Props) {
  return (
    <div className="sheet-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <section className={`bottom-sheet ${tall ? 'sheet-tall' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="sheet-grabber" aria-hidden="true" />
        <div className="sheet-topline">
          <span className="eyebrow">PORCHLIGHT</span>
          <button className="icon-button close-button" aria-label="Close" onClick={onClose}>×</button>
        </div>
        {children}
      </section>
    </div>
  )
}
