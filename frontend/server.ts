import index from "./index.html";

Bun.serve({
  port: Number(process.env.PORT ?? 5173),
  routes: {
    "/*": index,
  },
  development: process.env.NODE_ENV !== "production",
});
