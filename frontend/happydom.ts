import { GlobalRegistrator } from "@happy-dom/global-registrator";

// An explicit origin so `history.pushState("/path")` resolves to a real
// pathname — happy-dom's default "about:blank" document has no origin to
// resolve a relative path against.
GlobalRegistrator.register({ url: "http://localhost/" });
