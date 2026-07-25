export type Difficulty = "beginner" | "intermediate" | "advanced";
export type NodeStatus = "locked" | "available" | "seen" | "mastered";
export type ResourceType = "github" | "doc" | "youtube" | "article";

export interface Resource {
  type: ResourceType;
  title: string;
  url: string;
  reason: string;
}

export interface DAGNode {
  id: string;
  title: string;
  description: string;
  prerequisites: string[];
  difficulty: Difficulty;
  estimated_hours: number;
  success_criteria: string;
  status: NodeStatus;
  resources: Resource[];
  completed_at: string | null;
  triggering_content: string | null;
}

export interface ComprehensionResult {
  verdict: "pass" | "needs_review";
  feedback: string;
}

export type WSMessage =
  | { event: "dag.generated"; data: { nodes: DAGNode[] } }
  | { event: "dag.updated"; data: { nodes: DAGNode[] } }
  | { event: "dag.regenerated"; data: { nodes: DAGNode[] } };
