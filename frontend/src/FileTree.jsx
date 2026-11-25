import { useMemo, useState } from 'react'

function buildTree(paths) {
  const root = { name: '', children: new Map(), isFile: false }

  for (const path of paths) {
    const parts = path.split(/[\\/]/).filter(Boolean)
    let node = root

    parts.forEach((part, index) => {
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part,
          children: new Map(),
          isFile: false,
        })
      }
      node = node.children.get(part)
      if (index === parts.length - 1) {
        node.isFile = true
      }
    })
  }

  return root
}

function countFiles(node) {
  let total = node.isFile ? 1 : 0
  for (const child of node.children.values()) {
    total += countFiles(child)
  }
  return total
}

function sortedChildren(node) {
  return [...node.children.values()].sort((a, b) => {
    const aFolder = a.children.size > 0
    const bFolder = b.children.size > 0
    if (aFolder !== bFolder) return aFolder ? -1 : 1
    return a.name.localeCompare(b.name)
  })
}

function TreeNode({ node, depth, forceOpen }) {
  const isFolder = node.children.size > 0

  return (
    <li>
      {node.isFile && <div className="tree-file">📄 {node.name}</div>}
      {isFolder && (
        <details open={forceOpen || depth === 0}>
          <summary>
            📁 {node.name}
            <span className="tree-count">{countFiles(node)}</span>
          </summary>
          <ul>
            {sortedChildren(node).map((child) => (
              <TreeNode
                key={child.name}
                node={child}
                depth={depth + 1}
                forceOpen={forceOpen}
              />
            ))}
          </ul>
        </details>
      )}
    </li>
  )
}

function FileTree({ files }) {
  const [filter, setFilter] = useState('')

  const filtered = useMemo(() => {
    const query = filter.trim().toLowerCase()
    if (!query) return files
    return files.filter((path) => path.toLowerCase().includes(query))
  }, [files, filter])

  const tree = useMemo(() => buildTree(filtered), [filtered])
  const active = filter.trim() !== ''

  return (
    <div className="file-tree">
      <input
        type="search"
        aria-label="Filter repository files"
        placeholder="Filter files..."
        value={filter}
        onChange={(event) => setFilter(event.target.value)}
      />
      <p className="tree-summary">
        Showing {filtered.length} of {files.length} files
      </p>

      {filtered.length === 0 ? (
        <p>No files match your filter.</p>
      ) : (
        <ul className="tree-root" key={active ? 'filtered' : 'all'}>
          {sortedChildren(tree).map((child) => (
            <TreeNode
              key={child.name}
              node={child}
              depth={0}
              forceOpen={active}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

export default FileTree
