/**
 * v2 WebSocket 서비스
 * CLI 연동을 위한 실시간 진행 상황 관리
 */

import { buildWsUrl } from './wsUrl'

export interface V2ProgressMessage {
  client_id: string
  status: V2GenerationStatus
  message: string
  progress: number
  details?: Record<string, unknown>
  result?: {
    filename: string
    description: string
    download_url: string
    llm_response_time?: number
    prompt_size?: number
    added_chunks?: number
    test_cases?: Record<string, unknown>[]
    test_scenario_name?: string
  }
}

export enum V2GenerationStatus {
  RECEIVED = 'received',
  ANALYZING_GIT = 'analyzing_git',
  STORING_RAG = 'storing_rag',
  CALLING_LLM = 'calling_llm',
  PARSING_RESPONSE = 'parsing_response',
  GENERATING_EXCEL = 'generating_excel',
  COMPLETED = 'completed',
  ERROR = 'error'
}

export interface V2WebSocketCallbacks {
  onProgress: (progress: V2ProgressMessage) => void
  onError: (error: string) => void
  onComplete: (result: Record<string, unknown>) => void
}

export class V2ProgressWebSocket {
  private ws: WebSocket | null = null
  private clientId: string
  private callbacks: V2WebSocketCallbacks
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5  // 재연결 시도 횟수 증가
  private reconnectDelay = 3000     // 재연결 대기 시간 증가
  private pingInterval: number | null = null

  constructor(clientId: string, callbacks: V2WebSocketCallbacks) {
    this.clientId = clientId
    this.callbacks = callbacks
  }

  connect(): void {
    try {
      // WebSocket URL 구성 (개발 환경에서는 localhost:8000)
      // const wsUrl = `ws://localhost:8000/api/v2/ws/progress/${this.clientId}`
      const wsUrl = buildWsUrl(`/api/v2/ws/progress/${this.clientId}`)
      
      console.log(`🔌 v2 WebSocket 연결 시도: ${wsUrl}`)
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log(`✅ v2 WebSocket 연결 성공: ${this.clientId}`)
        this.reconnectAttempts = 0
        
        // 클라이언트에서 서버로 주기적 ping 전송 (60초마다)
        this.pingInterval = window.setInterval(() => {
          if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.sendMessage('ping')
            console.log(`🏓 v2 클라이언트 ping 전송: ${this.clientId}`)
          }
        }, 60000)
      }

      this.ws.onmessage = (event) => {
        try {
          const data: V2ProgressMessage = JSON.parse(event.data)
          console.log(`📨 v2 진행 상황 수신:`, data)
          
          // 상태에 따른 콜백 호출
          switch (data.status) {
            case V2GenerationStatus.ERROR:
              this.callbacks.onError(data.message)
              break
              
            case V2GenerationStatus.COMPLETED:
              if (data.result) {
                this.callbacks.onComplete(data.result)
              }
              this.callbacks.onProgress(data)
              break
              
            default:
              this.callbacks.onProgress(data)
              break
          }
          
        } catch (error) {
          console.error('❌ v2 WebSocket 메시지 파싱 오류:', error)
          this.callbacks.onError('메시지 파싱 오류가 발생했습니다.')
        }
      }

      this.ws.onclose = (event) => {
        console.log(`🔌 v2 WebSocket 연결 종료: ${this.clientId}`, event)
        
        // 비정상 종료인 경우 재연결 시도
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          console.log(`🔄 v2 WebSocket 재연결 시도 (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`)
          
          setTimeout(() => {
            this.reconnectAttempts++
            this.connect()
          }, this.reconnectDelay)
        }
      }

      this.ws.onerror = (error) => {
        console.error('❌ v2 WebSocket 오류:', error)
        this.callbacks.onError('WebSocket 연결 오류가 발생했습니다.')
      }

    } catch (error) {
      console.error('❌ v2 WebSocket 생성 오류:', error)
      this.callbacks.onError('WebSocket을 생성할 수 없습니다.')
    }
  }

  disconnect(): void {
    // ping 인터벌 정리
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    
    if (this.ws) {
      console.log(`🔌 v2 WebSocket 연결 종료 요청: ${this.clientId}`)
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  sendMessage(message: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message)
    } else {
      console.warn('⚠️ v2 WebSocket이 연결되지 않음')
    }
  }

  getReadyState(): number | null {
    return this.ws ? this.ws.readyState : null
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

/**
 * 고유한 클라이언트 ID 생성
 */
export function generateClientId(): string {
  return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * v2 시나리오 생성 상태를 한국어 메시지로 변환
 */
export function getV2StatusMessage(status: V2GenerationStatus): string {
  const statusMessages: Record<V2GenerationStatus, string> = {
    [V2GenerationStatus.RECEIVED]: '요청을 수신했습니다.',
    [V2GenerationStatus.ANALYZING_GIT]: 'Git 변경 내역을 분석 중입니다...',
    [V2GenerationStatus.STORING_RAG]: '분석 결과를 RAG 시스템에 저장 중입니다...',
    [V2GenerationStatus.CALLING_LLM]: 'LLM을 호출하여 시나리오를 생성 중입니다...',
    [V2GenerationStatus.PARSING_RESPONSE]: 'LLM 응답을 파싱 중입니다...',
    [V2GenerationStatus.GENERATING_EXCEL]: 'Excel 파일을 생성 중입니다...',
    [V2GenerationStatus.COMPLETED]: '시나리오 생성이 완료되었습니다!',
    [V2GenerationStatus.ERROR]: '오류가 발생했습니다.'
  }
  
  return statusMessages[status] || '알 수 없는 상태입니다.'
}