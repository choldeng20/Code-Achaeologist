import { useState } from 'react'
import './App.css'
import FileTree from './FileTree'
import LanguageChart from './LanguageChart'
import PythonInsights from './PythonInsights'

function App() {
  const [repoUrl, setRepoUrl] = useState('')
  const [zipFile, setZipFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')

  async function analyzeRepository(endpoint, body, isZip = false) {
    setLoading(true)
    setError('')
    setResults(null)

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: isZip ? {} : {
          'Content-Type': 'application/json',
        },
        body: isZip ? body : JSON.stringify(body),
      })

      let data
      try {
        data = await response.json()
      } catch {
        throw new Error(`The server returned an unexpected response (${response.status}).`)
      }

      if (!response.ok) {
        throw new Error(data.error || 'Analysis failed')
      }

      setResults(data)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  function handleGitHubSubmit(event) {
    event.preventDefault()
    analyzeRepository('/api/analyze/github', {
      repo_url: repoUrl,
    })
  }

  function handleZipSubmit(event) {
    event.preventDefault()

    if (!zipFile) {
      setError('Please choose a ZIP file.')
      return
    }

    const formData = new FormData()
    formData.append('file', zipFile)
    analyzeRepository('/api/analyze/zip', formData, true)
  }

  const analysis = results?.analysis || results?.repository?.analysis
  const pythonAnalysis = analysis?.python ?? results?.python

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>⌘ Code<span>Archaeologist</span></h2>
        <nav aria-label="Main navigation">
          <a className="active" href="#dashboard">Dashboard</a>
          <a href="#analyze">Analyze Repository</a>
          <a href="#results">Results</a>
        </nav>
        <p className="sidebar-footer">Developer Intelligence Tool</p>
      </aside>

      <main id="dashboard" className="main-content">
        <header>
          <div>
            <p className="eyebrow">DEVELOPER WORKSPACE</p>
            <h1>Repository Dashboard</h1>
            <p>Understand your codebase, one file at a time.</p>
          </div>
          <span className="status">● System Ready</span>
        </header>

        <section id="analyze" className="panel" aria-labelledby="analyze-title">
          <h2 id="analyze-title">Analyze a repository</h2>
          <p>Connect a GitHub repository or upload a ZIP.</p>

          <form onSubmit={handleGitHubSubmit}>
            <input
              aria-label="GitHub repository URL"
              type="url"
              placeholder="https://github.com/owner/repository"
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              required
            />
            <button type="submit" disabled={loading}>Analyze GitHub</button>
          </form>

          <div className="separator">OR UPLOAD A ZIP</div>

          <form onSubmit={handleZipSubmit}>
            <input
              aria-label="Repository ZIP file"
              type="file"
              accept=".zip,application/zip"
              onChange={(event) => setZipFile(event.target.files?.[0] ?? null)}
              required
            />
            <button type="submit" disabled={loading}>Analyze ZIP</button>
          </form>
        </section>

        {loading && <p role="status" aria-live="polite">Analyzing repository...</p>}
        {error && <p className="error" role="alert">{error}</p>}

        <section className="stats" aria-label="Repository summary">
          <article className="stat-card">
            <p>Total Files</p>
            <h2>{analysis?.total_files ?? '—'}</h2>
          </article>
          <article className="stat-card">
            <p>Directories</p>
            <h2>{analysis?.total_directories ?? '—'}</h2>
          </article>
          <article className="stat-card">
            <p>Languages</p>
            <h2>{analysis ? Object.keys(analysis.languages).length : '—'}</h2>
          </article>
        </section>

        <section id="results" className="panel" aria-labelledby="results-title">
          <h2 id="results-title">Analysis Results</h2>

          {!analysis && <p>Your results will appear here.</p>}

          {analysis && (
            <>
              <h3>Languages detected</h3>
              <LanguageChart languages={analysis.languages} />

              <h3 className="file-heading">Repository files</h3>
              <FileTree files={analysis.files} />
              {analysis.truncated && (
                <p className="tree-summary">
                  File list limited to the first 500 entries.
                </p>
              )}
            </>
          )}
        </section>

        {pythonAnalysis && pythonAnalysis.summary.python_files > 0 && (
          <section className="panel python-panel" aria-labelledby="python-title">
            <h2 id="python-title">Python structure</h2>
            <div className="python-summary">
              <article><span>Files</span><strong>{pythonAnalysis.summary.python_files}</strong></article>
              <article><span>Lines</span><strong>{pythonAnalysis.summary.total_lines}</strong></article>
              <article><span>Classes</span><strong>{pythonAnalysis.summary.classes}</strong></article>
              <article><span>Functions</span><strong>{pythonAnalysis.summary.functions}</strong></article>
              <article><span>Methods</span><strong>{pythonAnalysis.summary.methods}</strong></article>
              <article><span>Parse errors</span><strong>{pythonAnalysis.summary.parse_errors}</strong></article>
            </div>

            <PythonInsights python={pythonAnalysis} />

            <h3>Python files</h3>
            {pythonAnalysis.files.length === 0 ? (
              <p>No Python files were found in this repository.</p>
            ) : (
              <div className="python-files">
                {pythonAnalysis.files.map((file) => (
                  <details className="python-file" key={file.path}>
                    <summary>
                      {file.path}
                      {file.error && <span className="python-file-error"> · {file.error}</span>}
                    </summary>
                    {file.error ? (
                      <p className="error">{file.error}</p>
                    ) : (
                      <div className="python-file-content">
                        {file.classes.length > 0 && (
                          <div>
                            <strong>Classes</strong>
                            <ul>
                              {file.classes.map((classInfo) => (
                                <li key={`${file.path}:${classInfo.name}:${classInfo.line}`}>
                                  <span>{classInfo.name}</span>
                                  {classInfo.bases.length > 0 && (
                                    <span className="python-signature">
                                      {' '}extends {classInfo.bases.join(', ')}
                                    </span>
                                  )}
                                  {classInfo.methods.length > 0 && (
                                    <ul>
                                      {classInfo.methods.map((method) => (
                                        <li key={`${file.path}:${classInfo.name}:${method.name}:${method.line}`}>
                                          {method.is_async ? 'async ' : ''}{method.name}({method.args.join(', ')})
                                        </li>
                                      ))}
                                    </ul>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {file.functions.length > 0 && (
                          <div>
                            <strong>Functions</strong>
                            <ul>
                              {file.functions.map((fn) => (
                                <li key={`${file.path}:${fn.name}:${fn.line}`}>
                                  {fn.is_async ? 'async ' : ''}{fn.name}({fn.args.join(', ')})
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {file.classes.length === 0 && file.functions.length === 0 && (
                          <p>No top-level classes or functions.</p>
                        )}
                      </div>
                    )}
                  </details>
                ))}
              </div>
            )}
            {pythonAnalysis.summary.skipped_files > 0 && (
              <p className="tree-summary">
                {pythonAnalysis.summary.skipped_files} additional Python files were skipped.
              </p>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

export default App
