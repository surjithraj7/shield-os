import { useCallback, useRef } from "react";

export default function Window({
  id,
  title,
  x,
  y,
  z,
  open,
  minimized,
  maximized,
  onFocus,
  onClose,
  onToggleMin,
  onToggleMax,
  onMove,
  bodyClass,
  children
}) {
  const startPointer = useRef(null);
  const startPos = useRef(null);

  const handleDown = useCallback(
    (e) => {
      if (maximized) return;
      if (e.target.closest && e.target.closest("button")) return;
      onFocus(id);
      startPointer.current = { x: e.clientX, y: e.clientY };
      startPos.current = { x, y };
      if (e.currentTarget.setPointerCapture) e.currentTarget.setPointerCapture(e.pointerId);
    },
    [maximized, onFocus, id, x, y]
  );

  const handleMove = useCallback(
    (e) => {
      if (!startPointer.current || maximized) return;
      const dx = e.clientX - startPointer.current.x;
      const dy = e.clientY - startPointer.current.y;
      onMove(id, Math.max(0, startPos.current.x + dx), Math.max(0, startPos.current.y + dy));
    },
    [maximized, onMove, id]
  );

  const handleUp = useCallback(() => {
    startPointer.current = null;
  }, []);

  if (!open) return null;

  return (
    <section
      className={`window ${maximized ? "maximized" : ""}`}
      style={{ left: x, top: y, zIndex: z, display: minimized ? "none" : undefined }}
      onMouseDown={() => onFocus(id)}
    >
      <header
        className="titlebar"
        onPointerDown={handleDown}
        onPointerMove={handleMove}
        onPointerUp={handleUp}
      >
        <span className="titlebar-menu">&#9670;</span>
        <span className="titlebar-text">{title}</span>
        <span className="titlebar-btns">
          <button className="tbtn" title="Minimize" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onToggleMin(id); }}>_</button>
          <button className="tbtn" title="Maximize" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onToggleMax(id); }}>&#9645;</button>
          <button className="tbtn" title="Close" onPointerDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); onClose(id); }}>X</button>
        </span>
      </header>
      <div className={`window-body ${bodyClass || ""}`}>{children}</div>
    </section>
  );
}
