const button = document.querySelector("#run");
const output = document.querySelector("#output");

button.addEventListener("click", () => {
  button.disabled = true;
  output.textContent = "Loading HiGHS WebAssembly and solving…";

  const worker = new Worker(new URL("./solver-worker.js", import.meta.url), {
    type: "module",
  });

  worker.onmessage = ({ data }) => {
    output.textContent = JSON.stringify(data, null, 2);
    worker.terminate();
    button.disabled = false;
  };

  worker.onerror = (event) => {
    output.textContent = "Worker error: " + event.message;
    worker.terminate();
    button.disabled = false;
  };

  worker.postMessage({ type: "run" });
});
