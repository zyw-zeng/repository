/** 提供 POST SSE 流的底层读取能力，供后续聊天功能复用。 */

export interface StreamEvent<T = unknown> {
  event: string;
  data: T;
}

export class StreamResponseError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "StreamResponseError";
  }
}

function parseEventBlock(block: string): StreamEvent | undefined {
  const lines = block.split(/\r?\n/);
  const event = lines
    .find((line) => line.startsWith("event:"))
    ?.slice(6)
    .trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!event || !data) return undefined;
  return { event, data: JSON.parse(data) as unknown };
}

export async function* readEventStream(
  path: string,
  body: unknown,
  signal?: AbortSignal,
  requestId?: string,
): AsyncGenerator<StreamEvent> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  // 前端预先生成请求 ID，使首个 SSE 事件到达前也能请求服务端取消。
  if (requestId) headers["X-Request-ID"] = requestId;
  const response = await fetch(`/api/backend${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    let detail = "";
    try {
      const payload = (await response.json()) as {
        detail?: string;
        message?: string;
      };
      detail = payload.detail ?? payload.message ?? "";
    } catch {
      // 非 JSON 错误响应仍使用 HTTP 状态提供稳定提示。
    }
    throw new StreamResponseError(
      response.status,
      detail || `流式请求失败：HTTP ${response.status}`,
    );
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const event = parseEventBlock(block);
        if (event) yield event;
      }
    }
    // 某些代理会在最后一个事件后直接关闭连接，不附加空行。
    const finalEvent = parseEventBlock(buffer.trim());
    if (finalEvent) yield finalEvent;
  } finally {
    reader.releaseLock();
  }
}
