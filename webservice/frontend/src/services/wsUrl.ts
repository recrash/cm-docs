
export function buildWsUrl(path: string) {
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // 개발 모드에선 8000으로 직결, 필요하면 .env로 오버라이드
    const host = import.meta.env.DEV
      ? (import.meta.env.VITE_WS_DEV_HOST ?? 'localhost:8000')
      : (import.meta.env.VITE_WS_HOST ?? window.location.host);
    return `${scheme}//${host}${path}`;
}