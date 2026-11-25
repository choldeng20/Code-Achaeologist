const COLORS = [
  '#6366f1',
  '#22d3ee',
  '#4ade80',
  '#fbbf24',
  '#f472b6',
  '#fb923c',
  '#a78bfa',
  '#94a3b8',
]

function LanguageChart({ languages }) {
  const entries = Object.entries(languages)
    .map(([name, count]) => ({ name, count: Number(count) || 0 }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)

  const total = entries.reduce((sum, item) => sum + item.count, 0)

  if (total === 0) {
    return <p>No recognised languages found.</p>
  }

  const withShare = entries.map((item, index) => ({
    ...item,
    percent: (item.count / total) * 100,
    color: COLORS[index % COLORS.length],
  }))

  return (
    <div className="lang-chart">
      <div
        className="lang-stack"
        role="img"
        aria-label={`Language distribution: ${withShare
          .map((item) => `${item.name} ${item.percent.toFixed(1)}%`)
          .join(', ')}`}
      >
        {withShare.map((item) => (
          <span
            key={item.name}
            className="lang-stack-segment"
            style={{ width: `${item.percent}%`, background: item.color }}
            title={`${item.name}: ${item.percent.toFixed(1)}%`}
          />
        ))}
      </div>

      <ul className="lang-list">
        {withShare.map((item) => (
          <li key={item.name} className="lang-row">
            <span className="lang-name">
              <span
                className="lang-dot"
                style={{ background: item.color }}
                aria-hidden="true"
              />
              {item.name}
            </span>
            <span className="lang-bar" aria-hidden="true">
              <span
                className="lang-bar-fill"
                style={{ width: `${item.percent}%`, background: item.color }}
              />
            </span>
            <span className="lang-meta">
              {item.count} {item.count === 1 ? 'file' : 'files'} ·{' '}
              {item.percent.toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default LanguageChart
