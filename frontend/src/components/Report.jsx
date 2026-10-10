function List({ title, items }) {
  if (!items?.length) return null
  return (
    <section>
      <h3>{title}</h3>
      <ul>{items.map((s, i) => <li key={i}>{s}</li>)}</ul>
    </section>
  )
}

export default function Report({ report }) {
  return (
    <div className="card report">
      <h2>Interview report</h2>
      <div className="score">{report.overall_score}<span>/10</span></div>
      <p>{report.summary}</p>
      <List title="Strengths" items={report.strengths} />
      <List title="Weaknesses" items={report.weaknesses} />
      <List title="Suggestions" items={report.suggestions} />
    </div>
  )
}
