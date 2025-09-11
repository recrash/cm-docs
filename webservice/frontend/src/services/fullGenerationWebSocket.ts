import { FullGenerationProgressMessage, FullGenerationResultData, FullGenerationStatus } from '../types'

export interface FullGenerationWebSocketConfig {
  onProgress?: (message: FullGenerationProgressMessage) => void
  onComplete?: (result: FullGenerationResultData) => void
  onError?: (error: string) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export class FullGenerationWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private config: FullGenerationWebSocketConfig
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private isIntentionallyClosed = false

  constructor(sessionId: string, config: FullGenerationWebSocketConfig = {}) {
    this.sessionId = sessionId
    this.config = config
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    this.isIntentionallyClosed = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/webservice/v2/ws/full-generation/${this.sessionId}`

    console.log(`[FullGenWS] Connecting to: ${wsUrl}`)

    try {
      this.ws = new WebSocket(wsUrl)
      this.setupEventHandlers()
    } catch (error) {
      console.error('[FullGenWS] Connection failed:', error)
      this.config.onError?.(`WebSocket 연결 실패: ${error}`)
    }
  }

  private setupEventHandlers(): void {
    if (!this.ws) return

    this.ws.onopen = () => {
      console.log('[FullGenWS] Connected successfully')
      this.reconnectAttempts = 0
      this.config.onConnect?.()
    }

    this.ws.onmessage = (event) => {
      try {
        const message: FullGenerationProgressMessage = JSON.parse(event.data)
        console.log('[FullGenWS] Received message:', message)

        // 진행 상황 업데이트
        this.config.onProgress?.(message)

        // 완료 상태 처리
        if (message.status === FullGenerationStatus.COMPLETED && message.result) {
          this.config.onComplete?.(message.result)
        }

        // 에러 상태 처리
        if (message.status === FullGenerationStatus.ERROR) {
          this.config.onError?.(message.message || '문서 생성 중 오류가 발생했습니다.')
        }
      } catch (error) {
        console.error('[FullGenWS] Message parsing error:', error)
        this.config.onError?.('메시지 파싱 오류가 발생했습니다.')
      }
    }

    this.ws.onerror = (error) => {
      console.error('[FullGenWS] WebSocket error:', error)
      this.config.onError?.('WebSocket 연결 오류가 발생했습니다.')
    }

    this.ws.onclose = (event) => {
      console.log('[FullGenWS] Connection closed:', event.code, event.reason)
      this.config.onDisconnect?.()

      // 의도적인 종료가 아니고 재연결 시도 횟수가 남아있으면 재연결 시도
      if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.attemptReconnect()
      }
    }
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++
    console.log(`[FullGenWS] Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`)

    this.reconnectTimer = setTimeout(() => {
      this.connect()
    }, 2000 * this.reconnectAttempts) as unknown as number // 재연결 시도마다 대기 시간 증가
  }

  disconnect(): void {
    console.log('[FullGenWS] Disconnecting...')
    this.isIntentionallyClosed = true

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  sendMessage(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      console.log('[FullGenWS] Message sent:', message)
    } else {
      console.error('[FullGenWS] Cannot send message - WebSocket not connected')
      this.config.onError?.('WebSocket이 연결되어 있지 않습니다.')
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}