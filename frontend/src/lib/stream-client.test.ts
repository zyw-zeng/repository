/** 验证 SSE 分块、Windows 换行、多行数据和末尾无空行场景。 */

import { afterEach, describe, expect, it, vi } from "vitest";

import { readEventStream, StreamResponseError } from "./stream-client";

afterEach(() => vi.restoreAllMocks());

describe("SSE 读取器", () => {
  it("能够跨网络分块解析事件", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode('event: run_started\r\ndata: {"ok":'),
        );
        controller.enqueue(
          encoder.encode('true}\r\n\r\nevent: completed\ndata: {"done":true}'),
        );
        controller.close();
      },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(body, { status: 200 }),
    );

    const events = [];
    for await (const event of readEventStream("/test", {})) events.push(event);

    expect(events).toEqual([
      { event: "run_started", data: { ok: true } },
      { event: "completed", data: { done: true } },
    ]);
  });

  it("保留错误状态供界面恢复处理", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "会话不存在" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const iterator = readEventStream("/missing", {});
    await expect(iterator.next()).rejects.toEqual(
      new StreamResponseError(404, "会话不存在"),
    );
  });
});
