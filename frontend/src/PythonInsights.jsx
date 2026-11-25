import './PythonInsights.css'

function FunctionTable({ title, functions, metric, metricLabel }) {
  return (
    <section className="python-insight-section">
      <h3>{title}</h3>
      {functions.length === 0 ? (
        <p className="python-insight-empty">No function data available.</p>
      ) : (
        <div className="python-insight-table-wrap">
          <table className="python-insight-table">
            <thead>
              <tr>
                <th scope="col">Function</th>
                <th scope="col">File</th>
                <th scope="col">Lines</th>
                <th scope="col">{metricLabel}</th>
              </tr>
            </thead>
            <tbody>
              {functions.map((fn) => (
                <tr key={`${fn.path}:${fn.line}:${fn.name}`}>
                  <td>{fn.name}</td>
                  <td>{fn.path}</td>
                  <td>{fn.line}-{fn.end_line}</td>
                  <td>{fn[metric]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function PythonInsights({ python }) {
  if (!python) {
    return null
  }

  const { summary } = python
  const longestFunctions = summary.longest_functions ?? []
  const mostComplex = summary.most_complex ?? []
  const topImports = summary.top_imports ?? []

  return (
    <div className="python-insights">
      <div className="python-docstring-summary">
        <span>Docstring coverage</span>
        <strong>{summary.docstring_coverage.toFixed(1)}%</strong>
        <span>{summary.undocumented_functions} undocumented functions/methods</span>
      </div>

      <FunctionTable
        title="Longest functions"
        functions={longestFunctions}
        metric="length"
        metricLabel="Length"
      />
      <FunctionTable
        title="Most complex functions"
        functions={mostComplex}
        metric="complexity"
        metricLabel="Complexity"
      />

      <section className="python-insight-section">
        <h3>Most-imported modules</h3>
        {topImports.length === 0 ? (
          <p className="python-insight-empty">No imports found.</p>
        ) : (
          <ol className="python-import-list">
            {topImports.map((module) => (
              <li key={module.name}>
                <span>{module.name}</span>
                <span>{module.files} {module.files === 1 ? 'import' : 'imports'}</span>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  )
}

export default PythonInsights
