import type { GenerationProgress } from '../types';
import logger from './logger';

export class ScenarioWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onProgressCallback: (progress: GenerationProgress) => void;
  private onErrorCallback: (error: string) => void;
  private onCompleteCallback: (result: Record<string, unknown>) => void;

  constructor(
    url: string,
    onProgress: (progress: GenerationProgress) => void,
    onError: (error: string) => void,
    onComplete: (result: Record<string, unknown>) => void
  ) {
    this.url = url;
    this.onProgressCallback = onProgress;
    this.onErrorCallback = onError;
    this.onCompleteCallback = onComplete;
  }

  connect(request: Record<string, unknown>) {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        logger.info('WebSocket connected', { url: this.url });
        this.ws?.send(JSON.stringify(request));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          logger.info('WebSocket message received:', data);
          
          if (data.status === 'error') {
            logger.error('WebSocket message error:', new Error(data.message), data);
            this.onErrorCallback(data.message);
            return;
          }

          if (data.status === 'completed') {
            logger.info('Scenario generation completed.', data.details?.result);
            const result = data.details?.result || data;
            logger.info('Calling onCompleteCallback with result:', result);
            this.onCompleteCallback(result);
            return;
          }

          this.onProgressCallback(data);
        } catch (error) {
          logger.error('Error parsing WebSocket message:', error as Error);
          this.onErrorCallback('메시지 파싱 오류가 발생했습니다.');
        }
      };

      this.ws.onerror = (event) => {
        logger.error('WebSocket error:', undefined, { event });
        this.onErrorCallback('WebSocket 연결 오류가 발생했습니다.');
      };

      this.ws.onclose = (event) => {
        logger.info('WebSocket closed:', { code: event.code, reason: event.reason });
        if (event.code !== 1000) { // 1000 is normal closure
          this.onErrorCallback('연결이 예상치 못하게 종료되었습니다.');
        }
      };
    } catch (error) {
      logger.error('Error creating WebSocket:', error as Error);
      this.onErrorCallback('WebSocket 생성 중 오류가 발생했습니다.');
    }
  }

  disconnect() {
    if (this.ws) {
      logger.info('Disconnecting WebSocket.');
      this.ws.close(1000, 'User initiated close');
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
