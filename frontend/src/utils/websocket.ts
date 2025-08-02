import type { GenerationProgress } from '../types'

export class ScenarioWebSocket {
  private ws: WebSocket | null = null
  private url: string
  private onProgressCallback: (progress: GenerationProgress) => void
  private onErrorCallback: (error: string) => void
  private onCompleteCallback: (result: any) => void

  constructor(
    url: string,
    onProgress: (progress: GenerationProgress) => void,
    onError: (error: string) => void,
    onComplete: (result: any) => void
  ) {
    this.url = url
    this.onProgressCallback = onProgress
    this.onErrorCallback = onError
    this.onCompleteCallback = onComplete
  }

  connect(request: any) {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        // 요청 데이터 전송
        this.ws?.send(JSON.stringify(request))
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.status === 'error') {
            this.onErrorCallback(data.message)
            return
          }

          if (data.status === 'completed') {
            this.onCompleteCallback(data.details?.result || data)
            return
          }

          // 진행 상황 업데이트
          this.onProgressCallback(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
          this.onErrorCallback('메시지 파싱 오류가 발생했습니다.')
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.onErrorCallback('WebSocket 연결 오류가 발생했습니다.')
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        if (event.code !== 1000) {
          // 정상 종료가 아닌 경우
          this.onErrorCallback('연결이 예상치 못하게 종료되었습니다.')
        }
      }
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      this.onErrorCallback('WebSocket 생성 중 오류가 발생했습니다.')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'User initiated close')
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}