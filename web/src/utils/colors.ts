export const entityColors: Record<string, string> = {
  service: '#58a6ff',
  concept: '#d2a8ff',
  person: '#ffa657',
  ticket: '#f778ba',
  infrastructure: '#7ee787',
  tag: '#79c0ff',
  topic: '#d2a8ff',
  code_ref: '#8b949e',
  date: '#ffa657',
}

export const getEntityColor = (entityClass: string): string =>
  entityColors[entityClass.toLowerCase()] || '#58a6ff'

export const getEntityGlow = (entityClass: string): string => {
  const color = getEntityColor(entityClass)
  return `0 0 12px ${color}66`
}
