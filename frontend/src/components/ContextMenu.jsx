import { useEffect, useRef, useState } from "react";

const ITEMS = [
  { label: "Export Data...", action: "export" },
  { label: "Calibrate Sensors...", action: "calibrate" },
  { label: "Set Alert Thresholds...", action: "thresholds" },
  { label: null, action: null },
  { label: "Refresh Feed", action: "refresh" }
];

export default function ContextMenu({ onAction }) {
  const [menu, setMenu] = useState(null);
  const ref = useRef(null);

  useEffect(() => {
    function open(e) {
      e.preventDefault();
      const mx = Math.min(e.clientX, window.innerWidth - 210);
      const my = Math.min(e.clientY, window.innerHeight - 140);
      setMenu({ x: mx, y: my });
    }
    function close() {
      setMenu(null);
    }
    document.addEventListener("contextmenu", open);
    document.addEventListener("click", close);
    document.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("contextmenu", open);
      document.removeEventListener("click", close);
      document.removeEventListener("scroll", close, true);
    };
  }, []);

  if (!menu) return null;

  return (
    <div
      ref={ref}
      className="ctx-menu"
      style={{ left: menu.x, top: menu.y }}
      onClick={(e) => {
        const item = e.target.closest("[data-action]");
        if (item) onAction(item.getAttribute("data-action"));
        setMenu(null);
      }}
    >
      {ITEMS.map((it, i) =>
        it.action === null ? (
          <div className="ctx-sep" key={i} />
        ) : (
          <div className="ctx-item" data-action={it.action} key={it.action}>
            {it.label}
          </div>
        )
      )}
    </div>
  );
}
