import {
  __commonJS
} from "./chunk-JVWSFFO4.js";

// browser-external:node:module
var require_node_module = __commonJS({
  "browser-external:node:module"(exports, module) {
    module.exports = Object.create(new Proxy({}, {
      get(_, key) {
        if (key !== "__esModule" && key !== "__proto__" && key !== "constructor" && key !== "splice") {
          console.warn(`Module "node:module" has been externalized for browser compatibility. Cannot access "node:module.${key}" in client code. See https://vite.dev/guide/troubleshooting.html#module-externalized-for-browser-compatibility for more details.`);
        }
      }
    }));
  }
});
export default require_node_module();
//# sourceMappingURL=node_module-D4EJA35X.js.map
