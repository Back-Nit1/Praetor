import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { createClient, resolveSource } from "./api";
import "./index.css";

const root = createRoot(document.getElementById("root")!);
try {
  const client = createClient(resolveSource(import.meta.env.VITE_DATA_SOURCE), import.meta.env.VITE_API_BASE ?? "");
  root.render(<StrictMode><App client={client} /></StrictMode>);
} catch (e) {
  root.render(<p role="alert" style={{ padding: 16 }}>{(e as Error).message}</p>);
}
