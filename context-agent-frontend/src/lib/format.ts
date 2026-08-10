export function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value))
  } catch {
    return value
  }
}

export function formatRelative(value: string) {
  try {
    const date = new Date(value)
    const diffMs = Date.now() - date.getTime()
    const hours = Math.floor(diffMs / (1000 * 60 * 60))
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days}d ago`
    return formatDate(value)
  } catch {
    return value
  }
}

export function truncate(text: string, max = 140) {
  if (text.length <= max) return text
  return `${text.slice(0, max).trim()}…`
}
