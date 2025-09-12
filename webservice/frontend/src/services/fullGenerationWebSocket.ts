import { FullGenerationProgressMessage, FullGenerationResultData, FullGenerationStatus } from '../types'
import { buildWsUrl } from './wsUrl'

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
  private maxReconnectAttempts = 15   // V2와 동일하게 증가
  private reconnectDelay = 1000       // V2와 동일한 재연결 지연
  private pingInterval: number | null = null  // Ping-Pong 시스템

  constructor(sessionId: string, config: FullGenerationWebSocketConfig = {}) {
    this.sessionId = sessionId
    this.config = config
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected')
      return
    }

    
    // V2와 동일한 방식으로 WebSocket URL 구성
    const wsUrl = buildWsUrl(`/api/webservice/v2/ws/full-generation/${this.sessionId}`)
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
      
      // V2와 동일한 Ping-Pong 시스템 (15초 간격)
      // 서버 keepalive(25초)보다 빈번하게 전송하여 연결 유지
      this.pingInterval = window.setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.sendMessage('ping')
          console.debug(`🏓 FullGenWS 클라이언트 ping 전송: ${this.sessionId}`)
        }
      }, 15000)  // FastAPI WebSocket RPC 권장 패턴: 15초 간격
    }

    this.ws.onmessage = (event) => {
      try {
        // 먼저 raw 메시지가 pong 응답인지 확인 (V2와 동일)
        const rawMessage = event.data.trim()
        
        // JSON pong 응답 처리 (서버에서 {"type":"pong","timestamp":...} 형태로 전송)
        if (rawMessage.startsWith('{"type":"pong"')) {
          console.debug(`🏓 FullGenWS pong 응답 수신: ${this.sessionId}`, rawMessage)
          return // pong 메시지는 여기서 처리 완료
        }
        
        const message: FullGenerationProgressMessage = JSON.parse(rawMessage)
        
        // V2와 동일한 시스템 메시지 필터링
        const isSystemMessage = message.details?.type === 'ping' || 
                                message.details?.type === 'keepalive' ||
                                message.progress === -1 ||  // keepalive 메시지 식별자
                                message.message?.includes('ping') || 
                                message.message?.includes('연결 유지') ||
                                message.message?.includes('연결 상태') ||
                                message.message?.includes('WebSocket 연결이 설정되었습니다')
        
        if (!isSystemMessage) {
          console.log('[FullGenWS] Received message:', message)
        } else {
          // 시스템 메시지는 디버그 로그로만 출력
          console.debug('🔔 FullGenWS 시스템 메시지 필터링됨:', message.message)
        }
        
        // 시스템 메시지가 아닌 경우에만 상태에 따른 콜백 호출
        if (!isSystemMessage) {
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
      
      // ping 인터벌 정리 (V2와 동일)
      if (this.pingInterval) {
        clearInterval(this.pingInterval)
        this.pingInterval = null
      }

      // V2와 동일한 재연결 로직
      // 정상 종료(1000)이 아니거나, 예상치 못한 종료인 경우 재연결 시도
      const shouldReconnect = (event.code !== 1000 || event.wasClean === false) && 
                             this.reconnectAttempts < this.maxReconnectAttempts

      if (shouldReconnect) {
        console.log(`🔄 FullGenWS 재연결 시도 (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts}) - code: ${event.code}`)
        this.attemptReconnect()
      } else if (event.code !== 1000) {
        console.warn(`⚠️ FullGenWS 재연결 시도 한계 초과 또는 영구 종료: ${this.sessionId}`)
        this.config.onError?.('WebSocket 연결이 불안정합니다. 페이지를 새로고침해 주세요.')
      }
    }
  }

  private attemptReconnect(): void {
    // V2와 동일한 재연결 로직
    setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, this.reconnectDelay)
  }

  disconnect(): void {
    console.log('[FullGenWS] Disconnecting...')
    
    // ping 인터벌 정리 (V2와 동일)
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')  // V2와 동일하게 정상 종료 코드 지정
      this.ws = null
    }
  }

  sendMessage(message: string | Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const msgToSend = typeof message === 'string' ? message : JSON.stringify(message)
      this.ws.send(msgToSend)
      if (message !== 'ping') {  // ping 메시지는 로그 스팸 방지
        console.log('[FullGenWS] Message sent:', message)
      }
    } else {
      console.error('[FullGenWS] Cannot send message - WebSocket not connected')
      this.config.onError?.('WebSocket이 연결되어 있지 않습니다.')
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}