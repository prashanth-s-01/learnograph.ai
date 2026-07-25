"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DAGNode, WSMessage } from "@/types/dag";

interface UseWebSocketReturn {
  nodes: DAGNode[];
  connected: boolean;
}

export function useWebSocket(sessionId: string): UseWebSocketReturn {
  const [nodes, setNodes] = useState<DAGNode[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const url = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data);
        if (
          msg.event === "dag.generated" ||
          msg.event === "dag.updated" ||
          msg.event === "dag.regenerated"
        ) {
          setNodes(msg.data.nodes);
        }
      } catch {
        // ignore malformed frames
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { nodes, connected };
}
