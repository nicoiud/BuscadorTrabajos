import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    // Default es 3 reintentos con backoff exponencial (~7s) antes de mostrar el
    // error — con un solo backend local eso hace que un fallo real (ej. Ollama sin
    // levantar) se vea como que "no pasa nada" en vez de fallar rápido.
    queries: { retry: 1 },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
