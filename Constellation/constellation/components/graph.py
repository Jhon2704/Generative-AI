"""
Componente del knowledge graph interactivo para CONSTELLATION.
Implementa un grafo force-directed con canvas HTML5 via JavaScript personalizado.
Incluye filtros, leyenda y drag & drop de nodos.
"""
from __future__ import annotations

import json
import reflex as rx

from ..state.graph_state import GraphState
from ..state.app_state import AppState


# ── Script JavaScript para el grafo force-directed ────────────
# Se inyecta inline para máximo control sin dependencias NPM adicionales
GRAPH_SCRIPT = """
(function() {
  // No hay guardia global — canvas._graphInstance evita doble-init por elemento

  const COLORS = {
    background: '#03040a',
    nodePending: '#2a2a2e',
    nodeStroke: '#1e1e28',
    linkStrong: '#E2001A',
    linkWeak: '#2a2a3a',
    text: '#e5e5e5',
    textMuted: '#666680',
    selected: '#E2001A',
  };

  // Física simplificada: spring + repulsión
  class ForceGraph {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.nodes = [];
      this.links = [];
      this.dragging = null;
      this.dragOffX = 0;
      this.dragOffY = 0;
      this.scale = 1;
      this.panX = 0;
      this.panY = 0;
      this.animFrame = null;
      this.selectedId = null;
      this.onClick = null;
      this.onPositionChange = null;
      // Estrellas de fondo (espacio screen-space)
      this.stars = Array.from({length: 140}, () => ({
        x: Math.random(),
        y: Math.random(),
        r: 0.2 + Math.random() * 1.1,
        a: 0.08 + Math.random() * 0.55,
        phase: Math.random() * Math.PI * 2,
        warm: Math.random() > 0.88,
        blue: Math.random() > 0.84,
      }));
      this._bindEvents();
      this._tick();
    }

    setData(graphData) {
      const existingPos = {};
      this.nodes.forEach(n => { existingPos[n.id] = { x: n.x, y: n.y }; });

      this.nodes = graphData.nodes.map(n => {
        const prev = existingPos[n.id];
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        return {
          ...n,
          x: prev ? prev.x : (n.posX || cx + (Math.random() - 0.5) * 400),
          y: prev ? prev.y : (n.posY || cy + (Math.random() - 0.5) * 400),
          vx: 0, vy: 0,
        };
      });
      this.links = graphData.links || [];
    }

    setSelected(id) { this.selectedId = id; }

    _tick() {
      this._simulate();
      this._draw();
      this.animFrame = requestAnimationFrame(() => this._tick());
    }

    _simulate() {
      const alpha = 0.05;
      const nodes = this.nodes;
      const len = nodes.length;

      // Repulsión entre todos los nodos
      for (let i = 0; i < len; i++) {
        for (let j = i + 1; j < len; j++) {
          const a = nodes[i], b = nodes[j];
          let dx = b.x - a.x, dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = Math.min(800 / (dist * dist), 5);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          a.vx -= fx; a.vy -= fy;
          b.vx += fx; b.vy += fy;
        }
      }

      // Atracción por links (spring)
      this.links.forEach(link => {
        const s = nodes.find(n => n.id === link.source);
        const t = nodes.find(n => n.id === link.target);
        if (!s || !t) return;
        const dx = t.x - s.x, dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const targetDist = link.strength === 'strong' ? 120 : 200;
        const force = (dist - targetDist) * 0.02;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        s.vx += fx; s.vy += fy;
        t.vx -= fx; t.vy -= fy;
      });

      // Centrado suave
      const cx = this.canvas.width / 2;
      const cy = this.canvas.height / 2;
      nodes.forEach(n => {
        n.vx += (cx - n.x) * 0.001;
        n.vy += (cy - n.y) * 0.001;
        n.vx *= 0.85;
        n.vy *= 0.85;
        if (this.dragging !== n) {
          n.x += n.vx;
          n.y += n.vy;
        }
      });
    }

    _draw() {
      const ctx = this.ctx;
      const w = this.canvas.width;
      const h = this.canvas.height;

      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = COLORS.background;
      ctx.fillRect(0, 0, w, h);

      // ── Estrellas (screen space, no se mueven con el pan/zoom) ──
      const now = Date.now();
      this.stars.forEach(star => {
        const sx = star.x * w;
        const sy = star.y * h;
        const twinkle = 0.55 + 0.45 * Math.sin(now / 2200 + star.phase);
        const alpha = (star.a * twinkle).toFixed(3);
        const rgb = star.warm ? '255,210,140' : (star.blue ? '150,185,255' : '215,225,255');
        ctx.beginPath();
        ctx.arc(sx, sy, star.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb},${alpha})`;
        ctx.fill();
      });

      ctx.save();
      ctx.translate(this.panX, this.panY);
      ctx.scale(this.scale, this.scale);

      // Dibujar links
      this.links.forEach(link => {
        const s = this.nodes.find(n => n.id === link.source);
        const t = this.nodes.find(n => n.id === link.target);
        if (!s || !t) return;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = link.strength === 'strong' ? '#E2001A33' : '#2a2a2a';
        ctx.lineWidth = link.strength === 'strong' ? 2 : 1;
        ctx.setLineDash(link.strength === 'strong' ? [] : [4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // ── Helper: dibuja la forma del nodo ─────────────────────
      const drawShape = (x, y, r, shape) => {
        ctx.beginPath();
        switch(shape) {
          case 'square': {
            const s = r * 1.4;
            ctx.rect(x - s, y - s, s * 2, s * 2);
            break;
          }
          case 'diamond': {
            const d = r * 1.6;
            ctx.moveTo(x, y - d);
            ctx.lineTo(x + d, y);
            ctx.lineTo(x, y + d);
            ctx.lineTo(x - d, y);
            ctx.closePath();
            break;
          }
          case 'hexagon': {
            for (let i = 0; i < 6; i++) {
              const a = Math.PI / 180 * (60 * i - 30);
              const px = x + r * 1.35 * Math.cos(a);
              const py = y + r * 1.35 * Math.sin(a);
              i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
            }
            ctx.closePath();
            break;
          }
          case 'star': {
            for (let i = 0; i < 5; i++) {
              const oa = Math.PI / 180 * (72 * i - 90);
              const ia = Math.PI / 180 * (72 * i - 90 + 36);
              i === 0 ? ctx.moveTo(x + r*1.6*Math.cos(oa), y + r*1.6*Math.sin(oa))
                      : ctx.lineTo(x + r*1.6*Math.cos(oa), y + r*1.6*Math.sin(oa));
              ctx.lineTo(x + r*0.65*Math.cos(ia), y + r*0.65*Math.sin(ia));
            }
            ctx.closePath();
            break;
          }
          case 'triangle': {
            const h = r * 1.8;
            ctx.moveTo(x, y - h);
            ctx.lineTo(x + h * 0.87, y + h * 0.5);
            ctx.lineTo(x - h * 0.87, y + h * 0.5);
            ctx.closePath();
            break;
          }
          default: // circle
            ctx.arc(x, y, r, 0, Math.PI * 2);
        }
      };

      // Dibujar nodos
      this.nodes.forEach(node => {
        const r = 10;
        const isSelected = node.id === this.selectedId;
        const shape = node.shape || 'circle';

        // Pulso animado para nodos pendientes
        if (node.pending) {
          const pulse = 1 + 0.3 * Math.sin(now / 400);
          ctx.beginPath();
          ctx.arc(node.x, node.y, r * pulse + 5, 0, Math.PI * 2);
          ctx.fillStyle = '#E2001A22';
          ctx.fill();
        }

        // Halo de selección
        if (isSelected) {
          drawShape(node.x, node.y, r + 4, shape);
          ctx.strokeStyle = COLORS.selected;
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Nodo principal
        drawShape(node.x, node.y, r, shape);
        ctx.fillStyle = node.pending ? COLORS.nodePending : (node.color || '#4f8ef7');
        ctx.fill();
        ctx.strokeStyle = isSelected ? COLORS.selected : COLORS.nodeStroke;
        ctx.lineWidth = isSelected ? 2 : 1;
        ctx.stroke();

        // Emoji del proyecto encima del nodo
        if (node.emoji && !node.pending) {
          ctx.font = '10px serif';
          ctx.textAlign = 'center';
          ctx.fillText(node.emoji, node.x, node.y + 4);
        }

        // Etiqueta del nodo
        const label = (node.label || '').substring(0, 28);
        ctx.font = '10px Barlow, sans-serif';
        ctx.fillStyle = isSelected ? COLORS.text : COLORS.textMuted;
        ctx.textAlign = 'center';
        ctx.fillText(label, node.x, node.y + r + 15);
      });

      ctx.restore();
    }

    _toWorld(clientX, clientY) {
      const rect = this.canvas.getBoundingClientRect();
      return {
        x: (clientX - rect.left - this.panX) / this.scale,
        y: (clientY - rect.top  - this.panY) / this.scale,
      };
    }

    _nodeAt(wx, wy) {
      return this.nodes.find(n => {
        const dx = n.x - wx, dy = n.y - wy;
        return Math.sqrt(dx * dx + dy * dy) < 14;
      });
    }

    _bindEvents() {
      const c = this.canvas;
      let isPanning = false, panStartX = 0, panStartY = 0;
      let lastPanX = 0, lastPanY = 0;
      let mouseDownNode = null;
      let mouseDownTime = 0;
      let lastClickNodeId = null;
      let lastClickTime = 0;

      c.addEventListener('mousedown', e => {
        const w = this._toWorld(e.clientX, e.clientY);
        const node = this._nodeAt(w.x, w.y);
        mouseDownTime = Date.now();
        if (node) {
          this.dragging = node;
          mouseDownNode = node;
          this.dragOffX = node.x - w.x;
          this.dragOffY = node.y - w.y;
        } else {
          isPanning = true;
          panStartX = e.clientX - this.panX;
          panStartY = e.clientY - this.panY;
        }
      });

      c.addEventListener('mousemove', e => {
        if (this.dragging) {
          const w = this._toWorld(e.clientX, e.clientY);
          this.dragging.x = w.x + this.dragOffX;
          this.dragging.y = w.y + this.dragOffY;
        } else if (isPanning) {
          this.panX = e.clientX - panStartX;
          this.panY = e.clientY - panStartY;
        } else {
          // Cambiar cursor al pasar sobre un nodo
          const w = this._toWorld(e.clientX, e.clientY);
          c.style.cursor = this._nodeAt(w.x, w.y) ? 'pointer' : 'grab';
        }
      });

      c.addEventListener('mouseup', e => {
        const elapsed = Date.now() - mouseDownTime;
        if (mouseDownNode && elapsed < 200) {
          const now = Date.now();
          const isDouble = (mouseDownNode.id === lastClickNodeId) && (now - lastClickTime < 400);
          if (isDouble) {
            // Doble clic → navegar a la conversación
            if (this.onDoubleClick) this.onDoubleClick(mouseDownNode.conversationId || '');
            lastClickNodeId = null;
            lastClickTime = 0;
          } else {
            // Click simple → seleccionar nodo
            if (this.onClick) this.onClick(mouseDownNode.id);
            lastClickNodeId = mouseDownNode.id;
            lastClickTime = now;
          }
        } else if (this.dragging && elapsed >= 200) {
          // Drag terminado: notificar posición
          if (this.onPositionChange) {
            this.onPositionChange(this.dragging.id, this.dragging.x, this.dragging.y);
          }
        }
        this.dragging = null;
        mouseDownNode = null;
        isPanning = false;
      });

      // Zoom con rueda
      c.addEventListener('wheel', e => {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        this.scale = Math.min(Math.max(this.scale * factor, 0.2), 5);
      }, { passive: false });

      // Touch support
      let lastTouchDist = 0;
      c.addEventListener('touchstart', e => {
        e.preventDefault();
        if (e.touches.length === 1) {
          const t = e.touches[0];
          const w = this._toWorld(t.clientX, t.clientY);
          const node = this._nodeAt(w.x, w.y);
          if (node) {
            this.dragging = node;
            this.dragOffX = node.x - w.x;
            this.dragOffY = node.y - w.y;
          }
        } else if (e.touches.length === 2) {
          const dx = e.touches[0].clientX - e.touches[1].clientX;
          const dy = e.touches[0].clientY - e.touches[1].clientY;
          lastTouchDist = Math.sqrt(dx * dx + dy * dy);
        }
      }, { passive: false });

      c.addEventListener('touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 1 && this.dragging) {
          const t = e.touches[0];
          const w = this._toWorld(t.clientX, t.clientY);
          this.dragging.x = w.x + this.dragOffX;
          this.dragging.y = w.y + this.dragOffY;
        } else if (e.touches.length === 2) {
          const dx = e.touches[0].clientX - e.touches[1].clientX;
          const dy = e.touches[0].clientY - e.touches[1].clientY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (lastTouchDist) {
            const factor = dist / lastTouchDist;
            this.scale = Math.min(Math.max(this.scale * factor, 0.2), 5);
          }
          lastTouchDist = dist;
        }
      }, { passive: false });

      c.addEventListener('touchend', e => {
        this.dragging = null;
        lastTouchDist = 0;
      });
    }

    destroy() {
      if (this.animFrame) cancelAnimationFrame(this.animFrame);
    }
  }

  // ── Inicialización del grafo ─────────────────────────────────
  function initGraph() {
    const canvas = document.getElementById('constellation-graph');
    if (!canvas || canvas._graphInstance) return;

    // Ajustar tamaño al contenedor con ResizeObserver para capturar cambios de layout
    function resize() {
      // Subir por el árbol hasta encontrar un contenedor con altura real
      let el = canvas.parentElement;
      while (el && el.clientHeight < 50) el = el.parentElement;
      if (!el) el = canvas.parentElement;
      const w = el ? el.clientWidth  : window.innerWidth;
      const h = el ? el.clientHeight : window.innerHeight - 60;
      if (w > 0 && h > 0) {
        canvas.width  = w;
        canvas.height = h;
      }
    }

    // Exponer resize globalmente para que rx.call_script pueda llamarlo
    window._constellationResize = resize;

    resize();
    setTimeout(resize, 150);
    setTimeout(resize, 600);
    window.addEventListener('resize', resize);

    // ResizeObserver: redimensiona el canvas cuando el contenedor cambia (ej. cambio de vista)
    if (window.ResizeObserver) {
      let container = canvas.parentElement;
      while (container && container.clientHeight < 50) container = container.parentElement;
      if (container) {
        new ResizeObserver(() => { resize(); }).observe(container);
      }
    }

    const graph = new ForceGraph(canvas);
    canvas._graphInstance = graph;

    // Callback: click simple → seleccionar nodo
    graph.onClick = (nodeId) => {
      graph.setSelected(nodeId);
      const inp = document.getElementById('constellation-node-select');
      if (inp) {
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(inp, nodeId);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
    };

    // Callback: doble clic → navegar a la conversación
    graph.onDoubleClick = (conversationId) => {
      if (!conversationId) return;
      const inp = document.getElementById('constellation-node-dblclick');
      if (inp) {
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(inp, conversationId);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
      }
    };

    // Callback: arrastrar nodo → persistir posición
    graph.onPositionChange = (nodeId, x, y) => {
      const event = new CustomEvent('graph-node-move', { detail: { nodeId, x, y } });
      document.dispatchEvent(event);
    };

    // Exponer para actualización de datos desde Python
    window._constellationGraph = graph;
    console.log('[Constellation] ForceGraph inicializado, canvas:', canvas.width, 'x', canvas.height);

    // Cargar datos ya presentes en el DOM — evita race condition con load_graph
    const dataEl = document.getElementById('graph-data-json');
    if (dataEl) {
      try {
        const json = dataEl.textContent.trim();
        if (json && json.length > 20) {
          const parsed = JSON.parse(json);
          if (parsed.nodes && parsed.nodes.length > 0) {
            graph.setData(parsed);
            console.log('[Constellation] Datos cargados desde DOM en init:', parsed.nodes.length, 'nodos');
          }
        }
      } catch(e) { console.warn('[Constellation] Error parseando datos DOM:', e); }
    }
  }

  // Intentar inicializar ahora y tras carga del DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initGraph);
  } else {
    initGraph();
    // Reintentar por si el canvas no estaba listo
    setTimeout(initGraph, 100);
    setTimeout(initGraph, 500);
  }

  // Reintentar tras navegación SPA de Reflex — sin guardia global, seguro llamarlo varias veces
  const observer = new MutationObserver(() => {
    const canvas = document.getElementById('constellation-graph');
    if (canvas && !canvas._graphInstance) {
      initGraph();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

})();
"""


def _graph_controls() -> rx.Component:
    """Barra de controles del grafo: filtros y leyenda."""
    return rx.hstack(
        # ── Filtros ────────────────────────────────────────────
        rx.hstack(
            _filter_button("Todo", "all"),
            _filter_button("Míos", "mine"),
            _filter_button("Públicos", "public"),
            spacing="1",
        ),
        rx.spacer(),
        # ── Botón admin proyectos ──────────────────────────────
        rx.icon_button(
            rx.icon("folder-plus", size=14),
            size="1",
            variant="ghost",
            color_scheme="gray",
            on_click=GraphState.toggle_project_admin,
            title="Administrar proyectos",
            _hover={"color": "#E2001A"},
        ),
        # ── Indicador de carga ─────────────────────────────────
        rx.cond(
            GraphState.loading,
            rx.spinner(size="1", color="#E2001A"),
            rx.box(),
        ),
        padding="8px 12px",
        border_bottom="1px solid #1a1a1a",
        background="#07080c",
        width="100%",
        flex_shrink="0",
        align="center",
    )


def _filter_button(label: str, value: str) -> rx.Component:
    """Botón de filtro para el grafo."""
    is_active = GraphState.active_filter == value
    return rx.button(
        label,
        on_click=lambda: GraphState.set_filter(value),
        background=rx.cond(is_active, "#E2001A", "transparent"),
        color=rx.cond(is_active, "#ffffff", "#888888"),
        border=rx.cond(is_active, "1px solid #E2001A", "1px solid #1e1e1e"),
        border_radius="4px",
        font_size="11px",
        font_family="Barlow Condensed, sans-serif",
        font_weight="600",
        letter_spacing="0.05em",
        height="24px",
        padding_x="8px",
        cursor="pointer",
        _hover={"border_color": "#E2001A", "color": "#ffffff"},
        transition="all 0.1s",
    )


def _project_legend() -> rx.Component:
    """Leyenda dinámica de proyectos con filtros clicables."""
    return rx.box(
        rx.vstack(
            rx.text(
                "Proyectos",
                font_size="10px",
                font_weight="600",
                color="#555555",
                text_transform="uppercase",
                letter_spacing="0.08em",
                font_family="Barlow Condensed, sans-serif",
            ),
            rx.foreach(
                GraphState.projects,
                lambda proj: rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="50%",
                        background=proj.color,
                        flex_shrink="0",
                    ),
                    rx.text(
                        proj.emoji + " " + proj.name,
                        font_size="11px",
                        color=rx.cond(
                            GraphState.active_filter == proj.id,
                            "#e5e5e5",
                            "#888888",
                        ),
                        font_weight=rx.cond(
                            GraphState.active_filter == proj.id,
                            "600",
                            "400",
                        ),
                        font_family="Barlow, sans-serif",
                        cursor="pointer",
                        _hover={"color": "#e5e5e5"},
                        on_click=GraphState.set_filter(proj.id),
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
            ),
            spacing="2",
            align_items="flex-start",
            width="100%",
        ),
        position="absolute",
        bottom="16px",
        left="12px",
        background="#0a0a0aee",
        border="1px solid #1e1e1e",
        border_radius="8px",
        padding="10px 12px",
        min_width="140px",
        z_index="10",
    )


def graph_canvas() -> rx.Component:
    """
    Componente principal del grafo interactivo.
    Renderiza un canvas HTML5 con el grafo force-directed.
    El script JS se inyecta una vez y actualiza el grafo via window._constellationGraph.
    """
    return rx.box(
        # ── Controles superiores ──────────────────────────────
        _graph_controls(),

        # ── Canvas del grafo ──────────────────────────────────
        rx.box(
            rx.html(
                """<canvas
                  id="constellation-graph"
                  style="display:block;width:100%;height:100%;cursor:grab;"
                ></canvas>"""
            ),
            # El script se inyecta via rx.script para que el navegador lo ejecute
            rx.script(GRAPH_SCRIPT),
            flex="1",
            position="relative",
            overflow="hidden",
            background="#07080c",
            id="graph-container",
        ),

        # ── Leyenda de proyectos ──────────────────────────────
        rx.cond(
            GraphState.projects,
            rx.box(
                _project_legend(),
                position="absolute",
                bottom="0",
                left="0",
                z_index="5",
                pointer_events="auto",
            ),
            rx.box(),
        ),

        # ── Script de sync: polling cada 250ms como mecanismo principal ──
        rx.script(
            """
            (function() {
              // Limpiar intervalo anterior si existe (hot-reload)
              if (window._graphSyncInterval) clearInterval(window._graphSyncInterval);
              var lastJson = '';
              var lastNodeCount = -1;
              window._graphSyncInterval = setInterval(function() {
                var el = document.getElementById('graph-data-json');
                if (!el) return;
                var json = el.textContent.trim();
                // Ignorar si no hay datos reales o no cambió
                if (!json || json === lastJson) return;
                try {
                  var parsed = JSON.parse(json);
                  var nc = parsed.nodes ? parsed.nodes.length : 0;
                  // Si hay nodos nuevos o datos cambiaron, actualizar
                  if (nc !== lastNodeCount || json !== lastJson) {
                    lastJson = json;
                    lastNodeCount = nc;
                    if (!window._constellationGraph) return; // esperar init
                    window._constellationGraph.setData(parsed);
                    if (window._constellationResize) window._constellationResize();
                    console.log('[Constellation] Sync poll: ' + nc + ' nodos actualizados');
                  }
                } catch(e) {}
              }, 250);
            })();
            """
        ),

        # ── Elemento oculto con datos JSON del grafo ──────────
        rx.box(
            rx.text(
                GraphState.graph_data_json,
                id="graph-data-json",
                display="none",
            ),
        ),

        # ── Input oculto: recibe nodeId desde JS y llama select_node ──
        rx.input(
            id="constellation-node-select",
            on_change=GraphState.select_node,
            position="absolute",
            opacity="0",
            pointer_events="none",
            width="0",
            height="0",
            border="none",
            padding="0",
            overflow="hidden",
            tab_index=-1,
            aria_hidden="true",
        ),

        # ── Input oculto: doble clic → navegar a la conversación ──
        rx.input(
            id="constellation-node-dblclick",
            on_change=GraphState.open_conversation,
            position="absolute",
            opacity="0",
            pointer_events="none",
            width="0",
            height="0",
            border="none",
            padding="0",
            overflow="hidden",
            tab_index=-1,
            aria_hidden="true",
        ),

        position="relative",
        height="100%",
        width="100%",
        display="flex",
        flex_direction="column",
        overflow="hidden",
        background="#07080c",
    )
