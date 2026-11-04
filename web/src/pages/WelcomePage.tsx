import { useEffect, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { Link } from 'react-router-dom';

const orbitLabels = [
  { text: '000° // N', className: 'welcome-orbit-label welcome-orbit-label-north' },
  { text: '090° // E', className: 'welcome-orbit-label welcome-orbit-label-east' },
  { text: '180° // S', className: 'welcome-orbit-label welcome-orbit-label-south' },
  { text: '270° // W', className: 'welcome-orbit-label welcome-orbit-label-west' },
];

export default function WelcomePage() {
  const symbolRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ active: false, x: 0, y: 0, rotateX: 0, rotateY: 0 });
  const [symbolRotation, setSymbolRotation] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    let animationFrame = 0;
    let lastTime = performance.now();

    const animate = (time: number) => {
      const elapsed = time - lastTime;
      lastTime = time;
      if (!dragState.current.active) {
        setSymbolRotation((rotation) => ({ x: rotation.x, y: rotation.y + elapsed * 0.012 }));
      }
      animationFrame = requestAnimationFrame(animate);
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, []);

  const handleSymbolPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragState.current = {
      active: true,
      x: event.clientX,
      y: event.clientY,
      rotateX: symbolRotation.x,
      rotateY: symbolRotation.y,
    };
    setIsDragging(true);
  };

  const handleSymbolPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragState.current.active) return;
    const { x, y, rotateX, rotateY } = dragState.current;
    setSymbolRotation({
      x: Math.max(-35, Math.min(35, rotateX - (event.clientY - y) * 0.35)),
      y: rotateY + (event.clientX - x) * 0.45,
    });
  };

  const handleSymbolPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragState.current.active = false;
    setIsDragging(false);
  };

  return (
    <div className="welcome-page">
      <div aria-hidden className="welcome-grid" />
      <div aria-hidden className="welcome-vignette" />

      <header className="welcome-header">
        <Link to="/welcome" className="welcome-brand" aria-label="Kintix home">
          <span className="welcome-brand-mark">K</span>
          <span>
            <strong>KINTI<span>X</span></strong>
            <small>Intelligent Automation, Human Control</small>
          </span>
        </Link>
        <Link to="/login" className="welcome-login-link">
          Operator login <span aria-hidden>↗</span>
        </Link>
      </header>

      <main>
        <section className="welcome-hero" aria-labelledby="welcome-title">
          <div className="welcome-copy">
            <p className="welcome-eyebrow"><span /> KINTIX OPERATIONS INTELLIGENCE / 01</p>
            <h1 id="welcome-title">Turn complex work<br /><em>into clear action.</em></h1>
            <p className="welcome-description">
              A governed intelligence layer for discovering, scoring, and automating
              the processes that move your enterprise forward.
            </p>
            <div className="welcome-actions">
              <Link to="/login" className="welcome-primary-action">Enter command center <span aria-hidden>→</span></Link>
              <a href="#capabilities" className="welcome-secondary-action">Explore the system <span aria-hidden>↓</span></a>
            </div>
          </div>

          <div className="welcome-radar" aria-label="Kintix intelligence visualization">
            <div className="welcome-radar-ring welcome-radar-ring-outer" />
            <div className="welcome-radar-ring welcome-radar-ring-middle" />
            <div className="welcome-radar-ring welcome-radar-ring-inner" />
            <div className="welcome-radar-sweep" />
            <div className="welcome-radar-ticks" />
            {orbitLabels.map((label) => <span key={label.text} className={label.className}>{label.text}</span>)}
            <div
              ref={symbolRef}
              className={`welcome-core ${isDragging ? 'welcome-core-dragging' : ''}`}
              style={{
                transform: `rotateX(${symbolRotation.x}deg) rotateY(${symbolRotation.y}deg)`,
              }}
              onPointerDown={handleSymbolPointerDown}
              onPointerMove={handleSymbolPointerMove}
              onPointerUp={handleSymbolPointerUp}
              onPointerCancel={handleSymbolPointerUp}
              role="button"
              tabIndex={0}
              aria-label="Interactive Kintix symbol. Drag to rotate."
            >
              <div className="welcome-core-glow" />
              <svg viewBox="0 0 120 150" role="img" aria-label="Kintix mark">
                <polygon className="welcome-core-hexagon" points="60,5 108,33 108,117 60,145 12,117 12,33" />
                <path d="M28 17v116M28 77l55-60M28 77l55 56M52 29c38-7 43 42 7 48 38 7 31 54-7 43" />
                <path d="M39 19h18c28 0 30 45 2 52 29 6 26 48-2 59H39" />
              </svg>
              <span>{isDragging ? 'RELEASE TO SET' : 'DRAG TO ROTATE'}</span>
            </div>
          </div>
        </section>

        <section id="capabilities" className="welcome-capabilities">
          <p className="welcome-eyebrow"><span /> SYSTEM CAPABILITIES / 02</p>
          <div className="welcome-capability-grid">
            <article><b>01</b><h2>Discover</h2><p>Surface the work hidden in your operational telemetry.</p></article>
            <article><b>02</b><h2>Decide</h2><p>Score every opportunity against value, risk, and human control.</p></article>
            <article><b>03</b><h2>Deliver</h2><p>Move approved automation from blueprint to measurable outcome.</p></article>
          </div>
        </section>
      </main>

      <footer className="welcome-footer">
        <span><i /> All systems nominal</span>
        <span>KINTIX / 2026</span>
      </footer>
    </div>
  );
}
