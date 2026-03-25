type EventHandler = (event: any) => void

class WebSocketManager {
  private ws: WebSocket | null = null
  private handlers: Set<EventHandler> = new Set()
  private reconnectTimer: number | null = null

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`)
    this.ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        this.handlers.forEach(h => h(event))
      } catch {}
    }
    this.ws.onclose = () => {
      this.reconnectTimer = window.setTimeout(() => this.connect(), 3000)
    }
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  subscribe(handler: EventHandler) {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }
}

export const wsManager = new WebSocketManager()
