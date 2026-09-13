/* Python executes off the UI thread. Cancelling terminates this entire worker. */
let runtime;
async function initialize() {
  importScripts('https://cdn.jsdelivr.net/pyodide/v0.29.2/full/pyodide.js');
  const py = await loadPyodide({indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.29.2/full/'});
  await py.loadPackage('numpy');
  const response = await fetch('/lab/python-bundle.json');
  if (!response.ok) throw new Error('Experiment source could not be downloaded. Please retry.');
  const bundle = await response.json();
  for (const [name, contents] of Object.entries(bundle.files)) {
    const path = '/home/pyodide/' + name;
    py.FS.mkdirTree(path.slice(0, path.lastIndexOf('/')));
    py.FS.writeFile(path, contents);
  }
  py.runPython('import json\nfrom browser_experiments import run');
  return py;
}
self.onmessage = async ({data}) => {
  const {id, inputs} = data;
  try {
    self.postMessage({id, type: 'status', message: runtime ? 'Running experiment…' : 'Loading Python and NumPy. First run may take a moment…'});
    runtime ||= initialize();
    const py = await runtime;
    self.postMessage({id, type: 'status', message: 'Running your inputs…'});
    py.globals.set('request_json', JSON.stringify(inputs));
    py.globals.set('report_progress', (done, total) => self.postMessage({id, type: 'status', message: `Completed ${done} of ${total} paired episodes…`}));
    const result = py.runPython('json.dumps(run(json.loads(request_json), report_progress), allow_nan=False)');
    self.postMessage({id, type: 'result', result: JSON.parse(result)});
  } catch (error) {
    runtime = null;
    self.postMessage({id, type: 'error', message: String(error.message || error)});
  }
};
